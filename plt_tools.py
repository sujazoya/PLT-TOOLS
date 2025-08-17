import re
import ezdxf

HPGL_TO_MM = 0.025  # 1 HPGL unit ≈ 0.025 mm

def parse_hpgl(file_path):
    with open(file_path, 'r') as f:
        content = f.read().replace('\n','').replace(' ','')
    commands = content.split(';')
    x, y = 0, 0
    lines = []
    coords_list = []

    for cmd in commands:
        cmd = cmd.strip()
        if not cmd:
            continue
        if cmd.startswith(('PU','PD')):
            coord_str = cmd[2:]
            if not coord_str:
                continue
            coords = re.split(r',', coord_str)
            coords = [float(c) for c in coords if c.strip() != '']
            for i in range(0, len(coords), 2):
                new_x, new_y = coords[i], coords[i+1]
                coords_list.append((new_x, new_y))
                if cmd.startswith('PD'):
                    lines.append((x, y, new_x, new_y))
                x, y = new_x, new_y
    return coords_list, lines

def get_dimensions(coords_list):
    xs = [x for x, y in coords_list]
    ys = [y for x, y in coords_list]
    width_mm = (max(xs) - min(xs)) * HPGL_TO_MM
    height_mm = (max(ys) - min(ys)) * HPGL_TO_MM
    return width_mm, height_mm

def write_dxf(lines, output_file):
    doc = ezdxf.new(dxfversion='R2010')
    msp = doc.modelspace()
    for x1, y1, x2, y2 in lines:
        msp.add_line((x1*HPGL_TO_MM, y1*HPGL_TO_MM),
                     (x2*HPGL_TO_MM, y2*HPGL_TO_MM))
    doc.saveas(output_file)
    print(f"DXF saved: {output_file}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: python plt_tools.py input.plt output.dxf output.txt")
        sys.exit(1)

    input_file = sys.argv[1]
    output_dxf = sys.argv[2]
    output_txt = sys.argv[3]

    coords, lines = parse_hpgl(input_file)
    if not coords:
        print("No coordinates detected in the PLT file.")
        sys.exit(1)

    width, height = get_dimensions(coords)

    # Write DXF
    write_dxf(lines, output_dxf)

    # Write TXT
    text = f"Design Width: {width:.2f} mm\nDesign Height: {height:.2f} mm\n"
    with open(output_txt, 'w') as f:
        f.write(text)

    print(f"Dimensions written to {output_txt}")
    print(text)
