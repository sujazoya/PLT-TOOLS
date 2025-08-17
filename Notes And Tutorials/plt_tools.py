import tkinter as tk
from tkinter import filedialog, messagebox
import re
import os

HPGL_TO_MM = 0.025  # 1 plotter unit ≈ 0.025 mm

# ------------------- PLT PARSER -------------------
def parse_hpgl(file_path):
    """Parse PLT/HPGL file into list of (x, y) coordinates."""
    with open(file_path, 'r') as f:
        content = f.read().replace('\n', '').replace(' ', '')
    commands = content.split(';')

    coords = []
    x, y = 0, 0
    for cmd in commands:
        if cmd.startswith(('PU', 'PD')):  # Pen up/down moves
            points = re.findall(r'(-?\d+),(-?\d+)', cmd)
            for px, py in points:
                x, y = int(px), int(py)
                coords.append((x, y))
    return coords

# ------------------- DXF WRITER -------------------
def write_dxf(coords, dxf_file):
    """Write coordinates as DXF line entities."""
    with open(dxf_file, 'w') as f:
        f.write("0\nSECTION\n2\nENTITIES\n")
        for i in range(len(coords) - 1):
            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]
            f.write("0\nLINE\n8\n0\n")
            f.write(f"10\n{x1 * HPGL_TO_MM}\n20\n{y1 * HPGL_TO_MM}\n30\n0.0\n")
            f.write(f"11\n{x2 * HPGL_TO_MM}\n21\n{y2 * HPGL_TO_MM}\n31\n0.0\n")
        f.write("0\nENDSEC\n0\nEOF")

# ------------------- DIMENSIONS -------------------
def write_dimensions(coords, txt_file):
    """Calculate bounding box and save width/height in mm."""
    if not coords:
        return
    xs = [x for x, y in coords]
    ys = [y for x, y in coords]

    width_units = max(xs) - min(xs)
    height_units = max(ys) - min(ys)

    width_mm = width_units * HPGL_TO_MM
    height_mm = height_units * HPGL_TO_MM

    with open(txt_file, 'w') as f:
        f.write(f"Design Width: {width_mm:.2f} mm\n")
        f.write(f"Design Height: {height_mm:.2f} mm\n")

# ------------------- PREVIEW -------------------
def show_preview(coords):
    """Draw a preview of the design on the canvas."""
    if not coords:
        return
    canvas.delete("all")

    xs = [x for x, y in coords]
    ys = [y for x, y in coords]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    width = max_x - min_x
    height = max_y - min_y

    if width == 0 or height == 0:
        return

    # Fit to canvas
    scale_x = PREVIEW_SIZE / width
    scale_y = PREVIEW_SIZE / height
    scale = min(scale_x, scale_y) * 0.9  # add some margin

    # Centering offsets
    offset_x = (PREVIEW_SIZE - width * scale) / 2
    offset_y = (PREVIEW_SIZE - height * scale) / 2

    # Draw lines
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]
        cx1 = (x1 - min_x) * scale + offset_x
        cy1 = PREVIEW_SIZE - ((y1 - min_y) * scale + offset_y)  # flip Y
        cx2 = (x2 - min_x) * scale + offset_x
        cy2 = PREVIEW_SIZE - ((y2 - min_y) * scale + offset_y)
        canvas.create_line(cx1, cy1, cx2, cy2, fill="lime", width=1)

# ------------------- GUI FUNCTIONS -------------------
def convert():
    """Convert PLT to DXF and dimension text file, update preview."""
    try:
        plt_file = entry_ptrn.get().strip()
        dxf_file = entry_output.get().strip()

        if not os.path.exists(plt_file):
            raise FileNotFoundError(f"PLT file not found:\n{plt_file}")

        txt_file = os.path.join(os.path.dirname(dxf_file), "dimensions.txt")

        coords = parse_hpgl(plt_file)
        if not coords:
            raise ValueError("No coordinates found in file.")

        write_dxf(coords, dxf_file)
        write_dimensions(coords, txt_file)
        show_preview(coords)

        messagebox.showinfo(
            "Success",
            f"Converted:\n{dxf_file}\n\nDimensions saved in:\n{txt_file}"
        )
    except Exception as e:
        messagebox.showerror("Error", str(e))

def browse_file():
    """Select PLT file and auto-fill output DXF name, show preview."""
    file_path = filedialog.askopenfilename(filetypes=[("PLT files", "*.plt;*.hpgl")])
    if file_path:
        entry_ptrn.delete(0, tk.END)
        entry_ptrn.insert(0, file_path)
        # Auto-fill output name
        output_path = os.path.splitext(file_path)[0] + ".dxf"
        entry_output.delete(0, tk.END)
        entry_output.insert(0, output_path)

        # Preview on load
        coords = parse_hpgl(file_path)
        show_preview(coords)

# ------------------- GUI -------------------
root = tk.Tk()
root.title("PLT TOOLS")
root.configure(bg="#003366")

label1 = tk.Label(root, text="PTRN NAME:", fg="white", bg="#003366", font=("Arial", 12, "bold"))
label1.pack(pady=5)
entry_ptrn = tk.Entry(root, width=40, font=("Arial", 12))
entry_ptrn.pack(pady=5)
btn_browse = tk.Button(root, text="Browse", command=browse_file,
                       bg="#005599", fg="white", font=("Arial", 10, "bold"))
btn_browse.pack(pady=5)

label2 = tk.Label(root, text="OUTPUT NAME:", fg="white", bg="#003366", font=("Arial", 12, "bold"))
label2.pack(pady=5)
entry_output = tk.Entry(root, width=40, font=("Arial", 12))
entry_output.pack(pady=5)

btn = tk.Button(root, text="CONVERT", command=convert, bg="#007acc", fg="white",
                font=("Arial", 12, "bold"), width=20, relief="flat")
btn.pack(pady=10)

# Preview canvas
PREVIEW_SIZE = 300
label3 = tk.Label(root, text="Preview:", fg="white", bg="#003366", font=("Arial", 12, "bold"))
label3.pack()
canvas = tk.Canvas(root, width=PREVIEW_SIZE, height=PREVIEW_SIZE, bg="black")
canvas.pack(pady=10)

root.mainloop()
