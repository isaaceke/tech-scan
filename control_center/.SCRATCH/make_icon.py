import math
from PIL import Image, ImageDraw

def create_control_center_icon():
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Dark squircle background with subtle gradient
    # Apple rounded rectangle
    margin = 12
    radius = 54
    # Draw soft drop shadow
    for i in range(8):
        alpha = int(25 - i * 3)
        shadow_rect = [margin - i, margin + 4 - i, size - margin + i, size - margin + 8 + i]
        draw.rounded_rectangle(shadow_rect, radius=radius + i, fill=(0, 0, 0, alpha))

    # Base squircle
    base_rect = [margin, margin, size - margin, size - margin]
    draw.rounded_rectangle(base_rect, radius=radius, fill=(15, 23, 42, 255)) # Slate 900

    # Subtle inner border
    draw.rounded_rectangle(base_rect, radius=radius, outline=(30, 41, 59, 255), width=3) # Slate 800

    # 2. Concentric radar rings (Aviation Control Center motif)
    cx, cy = size // 2, size // 2
    for r in [80, 56, 32]:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(38, 50, 75, 180), width=2)

    # Crosshairs
    draw.line([cx - 86, cy, cx + 86, cy], fill=(56, 189, 248, 120), width=2) # Cyan crosshair
    draw.line([cx, cy - 86, cx, cy + 86], fill=(56, 189, 248, 120), width=2)

    # 3. Radar Sweep Arc (Cyan to Emerald glowing gradient)
    sweep_r = 74
    for a in range(45):
        angle_rad = math.radians(a - 30)
        x2 = cx + int(sweep_r * math.cos(angle_rad))
        y2 = cy + int(sweep_r * math.sin(angle_rad))
        alpha = int(180 * (a / 45.0))
        draw.line([cx, cy, x2, y2], fill=(16, 185, 129, alpha), width=3) # Emerald glow

    # 4. Central Control Beacon (Emerald dot with pulsing ring)
    draw.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=(16, 185, 129, 60))
    draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=(16, 185, 129, 255), outline=(255, 255, 255, 220), width=2)

    # 5. Aircraft Vector Wing Motif (Top Accent)
    wing_pts = [
        (cx, cy - 54),
        (cx - 36, cy - 36),
        (cx - 16, cy - 40),
        (cx, cy - 46),
        (cx + 16, cy - 40),
        (cx + 36, cy - 36)
    ]
    draw.polygon(wing_pts, fill=(56, 189, 248, 240)) # Sky cyan vector wings

    # Save multi-size .ico
    ico_path = "control_center/app.ico"
    img.save(
        ico_path,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    )
    print("Icon generated at:", ico_path)

if __name__ == "__main__":
    create_control_center_icon()
