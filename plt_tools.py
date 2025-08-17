import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import re, ezdxf, os

HPGL_TO_MM = 0.025  # HPGL unit to mm

# -------- HPGL PARSER (PU/PD, PA/PR only, no LB/text) --------
def parse_hpgl(file_path):
    with open(file_path, 'r') as f:
        content = f.read().replace('\n', '').replace(' ', '')
    commands = content.split(';')

    x, y = 0, 0
    is_absolute = True
    pen_down = False
    paths, current_path = [], []

    for cmd in commands:
        if not cmd or cmd.startswith("LB"):  # skip labels/text
            continue
        if cmd.startswith('PA'):
            is_absolute = True
            coords = re.findall(r'[-]?\d+', cmd[2:])
            for i in range(0, len(coords), 2):
                nx, ny = int(coords[i]), int(coords[i+1])
                x, y = (nx, ny) if is_absolute else (x+nx, y+ny)
                if pen_down:
                    current_path.append((x*HPGL_TO_MM, y*HPGL_TO_MM))
                else:
                    if current_path: paths.append(current_path)
                    current_path = [(x*HPGL_TO_MM, y*HPGL_TO_MM)]
        elif cmd.startswith('PR'):
            is_absolute = False
            coords = re.findall(r'[-]?\d+', cmd[2:])
            for i in range(0, len(coords), 2):
                x += int(coords[i]); y += int(coords[i+1])
                if pen_down:
                    current_path.append((x*HPGL_TO_MM, y*HPGL_TO_MM))
                else:
                    if current_path: paths.append(current_path)
                    current_path = [(x*HPGL_TO_MM, y*HPGL_TO_MM)]
        elif cmd.startswith('PU'):
            pen_down = False
            if current_path: paths.append(current_path); current_path = []
            coords = re.findall(r'[-]?\d+', cmd[2:])
            if coords:
                for i in range(0, len(coords), 2):
                    x = int(coords[i]) if is_absolute else x+int(coords[i])
                    y = int(coords[i+1]) if is_absolute else y+int(coords[i+1])
        elif cmd.startswith('PD'):
            pen_down = True
            coords = re.findall(r'[-]?\d+', cmd[2:])
            for i in range(0, len(coords), 2):
                x = int(coords[i]) if is_absolute else x+int(coords[i])
                y = int(coords[i+1]) if is_absolute else y+int(coords[i+1])
                current_path.append((x*HPGL_TO_MM, y*HPGL_TO_MM))
    if current_path: paths.append(current_path)
    return paths


# -------- DXF EXPORT --------
def save_as_dxf(paths, out_path):
    doc = ezdxf.new()
    msp = doc.modelspace()
    for path in paths:
        if len(path) > 1:
            msp.add_lwpolyline(path)
    doc.saveas(out_path)


# -------- DIMENSIONS --------
def get_dimensions(paths):
    all_x = [p[0] for path in paths for p in path]
    all_y = [p[1] for path in paths for p in path]
    return max(all_x)-min(all_x), max(all_y)-min(all_y)


# -------- GUI APP --------
class HPGLViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("HPGL Viewer with Zoom & Pan")
        self.file_path = None
        self.paths = []

        # Matplotlib Figure
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Buttons
        frame = tk.Frame(root)
        frame.pack(fill=tk.X)
        tk.Button(frame, text="Open .PLT", command=self.open_file).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(frame, text="Export DXF", command=self.export_dxf).pack(side=tk.LEFT, padx=5, pady=5)

        # Connect zoom/pan
        self.fig.canvas.mpl_connect('scroll_event', self.onscroll)
        self.fig.canvas.mpl_connect('button_press_event', self.onpress)
        self.fig.canvas.mpl_connect('motion_notify_event', self.onmotion)
        self.fig.canvas.mpl_connect('button_release_event', self.onrelease)

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("PLT files", "*.plt")])
        if not file_path: return
        self.file_path = file_path
        self.paths = parse_hpgl(file_path)
        self.update_plot()

    def export_dxf(self):
        if not self.file_path or not self.paths:
            messagebox.showerror("Error", "No .PLT loaded")
            return
        folder = os.path.dirname(self.file_path)
        base = os.path.splitext(os.path.basename(self.file_path))[0]
        dxf_file = os.path.join(folder, base + ".dxf")
        save_as_dxf(self.paths, dxf_file)
        w, h = get_dimensions(self.paths)
        with open(os.path.join(folder, "dimension.txt"), "w") as f:
            f.write(f"Design Width: {w:.2f} mm\nDesign Height: {h:.2f} mm\n")
        messagebox.showinfo("Export", f"Saved:\n{dxf_file}\ndimension.txt")

    def update_plot(self):
        self.ax.clear()
        for path in self.paths:
            xs, ys = zip(*path)
            self.ax.plot(xs, ys, 'k-')
        self.ax.set_aspect('equal')
        self.ax.autoscale()
        self.canvas.draw()

    # ---- Zoom & Pan ----
    def onscroll(self, event):
        if not event.xdata or not event.ydata: return
        scale = 1.2
        cur_xlim, cur_ylim = self.ax.get_xlim(), self.ax.get_ylim()
        if event.button == 'up':
            scale_factor = 1/scale
        else:
            scale_factor = scale
        new_width = (cur_xlim[1]-cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1]-cur_ylim[0]) * scale_factor
        relx = (cur_xlim[1]-event.xdata)/(cur_xlim[1]-cur_xlim[0])
        rely = (cur_ylim[1]-event.ydata)/(cur_ylim[1]-cur_ylim[0])
        self.ax.set_xlim([event.xdata-new_width*(1-relx), event.xdata+new_width*relx])
        self.ax.set_ylim([event.ydata-new_height*(1-rely), event.ydata+new_height*rely])
        self.canvas.draw_idle()

    def onpress(self, event):
        if event.button == 1:
            self._pan_start = (event.xdata, event.ydata, self.ax.get_xlim(), self.ax.get_ylim())

    def onmotion(self, event):
        if hasattr(self, "_pan_start") and event.xdata and event.ydata:
            x0, y0, (xlim0, xlim1), (ylim0, ylim1) = self._pan_start
            dx, dy = event.xdata-x0, event.ydata-y0
            self.ax.set_xlim(xlim0-dx, xlim1-dx)
            self.ax.set_ylim(ylim0-dy, ylim1-dy)
            self.canvas.draw_idle()

    def onrelease(self, event):
        if hasattr(self, "_pan_start"):
            del self._pan_start


# -------- RUN --------
if __name__ == "__main__":
    root = tk.Tk()
    app = HPGLViewer(root)
    root.mainloop()
