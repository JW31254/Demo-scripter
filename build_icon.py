"""Generate the DemoScripter app icon as .ico for PyInstaller."""
from PIL import Image, ImageDraw

def create_icon():
    sizes = [16, 32, 48, 64, 128, 256]
    images = []
    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        pad = max(1, size // 16)
        # Purple circle
        draw.ellipse([pad, pad, size - pad, size - pad], fill=(124, 92, 252))
        # Lightning bolt scaled to size
        s = size / 64.0
        bolt = [
            (34 * s, 10 * s),
            (22 * s, 30 * s),
            (30 * s, 30 * s),
            (26 * s, 54 * s),
            (42 * s, 26 * s),
            (34 * s, 26 * s),
        ]
        draw.polygon(bolt, fill=(255, 255, 255))
        images.append(img)

    images[0].save(
        "assets/app.ico",
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print("Created assets/app.ico")

if __name__ == "__main__":
    import os
    os.makedirs("assets", exist_ok=True)
    create_icon()
