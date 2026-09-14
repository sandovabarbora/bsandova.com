"""Soft tritone: continuous gradient map slate -> mid -> parchment, light posterise.

Usage: python3 assets/tritone.py assets/portrait-cutout.png assets/portrait-soft.png [levels=10] [gamma=0.85]
"""
import sys
from PIL import Image, ImageOps, ImageFilter

SLATE, MID, PARCH = (0x2B,0x3A,0x42), (0x88,0x98,0x90), (0xEC,0xE8,0xDA)
levels = int(sys.argv[3]) if len(sys.argv) > 3 else 10
gamma  = float(sys.argv[4]) if len(sys.argv) > 4 else 0.85

src = Image.open(sys.argv[1]).convert("RGBA")
a = src.getchannel("A"); bb = a.point(lambda v: 255 if v > 40 else 0).getbbox()
x0,y0,x1,y1 = bb; y1 = y0 + int((y1-y0)*(float(sys.argv[5]) if len(sys.argv) > 5 else 0.72))
src = src.crop((x0,y0,x1,y1)); a = src.getchannel("A")

lum = ImageOps.autocontrast(src.convert("L"), cutoff=1).filter(ImageFilter.GaussianBlur(0.6))
lum = lum.point(lambda v: int(255 * (v/255) ** gamma))          # lift shadows (cap shade)
if levels: lum = lum.point(lambda v: round(v/255*(levels-1))/(levels-1)*255)

def lerp(c0, c1, t): return tuple(int(c0[i] + (c1[i]-c0[i])*t) for i in range(3))
lut = []
for v in range(256):
    t = v/255
    lut.append(lerp(SLATE, MID, t/0.55) if t < 0.55 else lerp(MID, PARCH, (t-0.55)/0.45))
r = lum.point([c[0] for c in lut]); g = lum.point([c[1] for c in lut]); b = lum.point([c[2] for c in lut])
out = Image.merge("RGBA", (r, g, b, a.point(lambda v: 255 if v > 110 else 0)))
out.save(sys.argv[2], optimize=True); print(out.size)
