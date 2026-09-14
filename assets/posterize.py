"""Three-tone posterisation in the statue register: slate / mid / parchment over alpha.

Usage: python3 assets/posterize.py assets/portrait-cutout.png assets/portrait-3tone.png
Thresholds are luminance cut points on the alpha-matted source; tweak T1/T2 to taste.
"""
import sys
from PIL import Image, ImageFilter, ImageOps

SLATE, MID, PARCH = (0x2B, 0x3A, 0x42), (0x88, 0x98, 0x90), (0xEC, 0xE8, 0xDA)
T1, T2 = int(sys.argv[3]) if len(sys.argv) > 3 else 92, int(sys.argv[4]) if len(sys.argv) > 4 else 170

src = Image.open(sys.argv[1]).convert("RGBA")
alpha = src.getchannel("A")
# crop to the subject's bounding box + a little air, then drop the lower third (car, legs)
bbox = alpha.point(lambda a: 255 if a > 40 else 0).getbbox()
x0, y0, x1, y1 = bbox
y1 = y0 + int((y1 - y0) * 0.72)
src = src.crop((x0, y0, x1, y1)); alpha = src.getchannel("A")

lum = ImageOps.autocontrast(src.convert("L"), cutoff=1).filter(ImageFilter.GaussianBlur(0.8))
tone = lum.point(lambda v: 0 if v < T1 else (1 if v < T2 else 2))
out = Image.new("RGBA", src.size, (0, 0, 0, 0))
for idx, col in enumerate((SLATE, MID, PARCH)):
    mask = tone.point(lambda t, i=idx: 255 if t == i else 0)
    out.paste(Image.new("RGBA", src.size, col + (255,)), mask=mask)
out.putalpha(alpha.point(lambda a: 255 if a > 110 else 0))  # hard edge like the statue
out.save(sys.argv[2], optimize=True)
print(out.size)
