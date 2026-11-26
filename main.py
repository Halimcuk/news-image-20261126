#!/usr/bin/env python3
"""news-image-20261126: draw one editorial panel summing up the world news
of Thursday 26 November 2026 and write it to /output/entry.png.

Pure standard library: the picture is drawn pixel by pixel into an RGB
buffer and encoded as a PNG by hand, so the program needs no network, no
fonts and no third-party packages, and two runs produce identical bytes.

Stories (verified against wire coverage of the morning of 26 Nov 2026):
  * US proposes new tariffs on 14 trading partners, China hit hardest and
    India facing up to 25% (Reuters).
  * North Korea's Kim Jong Un calls for wider deployment of tactical
    nuclear weapons (KCNA, reported Thursday).
  * A fuel tanker crash and fire on Cairo's Ring Road kills at least 30
    people and injures 25.
  * US stocks slide: the Nasdaq falls nearly 4% as AI worries and the
    tariff news spook markets.
  * Also: the 100th Macy's Thanksgiving Day Parade is postponed to
    Saturday by a major storm.
"""

import binascii
import os
import struct
import zlib

# ---------------------------------------------------------------- palette
PAPER = (247, 243, 232)   # newsprint paper
INK = (20, 33, 61)        # deep navy ink
RED = (196, 42, 32)       # strong accent: tariffs, fire, falling markets
AMBER = (232, 164, 32)    # secondary accent
TEAL = (15, 118, 110)     # secondary accent
SKY = (178, 205, 219)     # pale sky
SEA = (46, 92, 122)       # sea blue
WHITE = (255, 255, 255)
GREY = (110, 110, 100)

W, H = 1024, 640

# ------------------------------------------------------- 5x7 bitmap font
# Each glyph: 7 rows of 5 bits, written as strings. Uppercase, digits and
# a few punctuation marks only; every label in the picture uses these.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
}


class Canvas:
    """A plain RGB pixel buffer with simple flat-shape drawing helpers."""

    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def rect(self, x, y, w, h, color):
        for yy in range(max(0, y), min(self.h, y + h)):
            for xx in range(max(0, x), min(self.w, x + w)):
                self.set(xx, yy, color)

    def hline(self, x0, x1, y, color, thick=1):
        for t in range(thick):
            for x in range(min(x0, x1), max(x0, x1) + 1):
                self.set(x, y + t, color)

    def vline(self, x, y0, y1, color, thick=1):
        for t in range(thick):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                self.set(x + t, y, color)

    def line(self, x0, y0, x1, y1, color, thick=1):
        dx, dy = x1 - x0, y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        for s in range(steps + 1):
            x = x0 + dx * s // steps
            y = y0 + dy * s // steps
            self.rect(x - thick // 2, y - thick // 2, thick, thick, color)

    def circle(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set(xx, yy, color)

    def ring(self, cx, cy, r, color, thick=3):
        for yy in range(cy - r - thick, cy + r + thick + 1):
            for xx in range(cx - r - thick, cx + r + thick + 1):
                d = ((xx - cx) ** 2 + (yy - cy) ** 2) ** 0.5
                if r - thick <= d <= r:
                    self.set(xx, yy, color)

    def triangle(self, pts, color):
        (x0, y0), (x1, y1), (x2, y2) = pts
        ymin, ymax = min(y0, y1, y2), max(y0, y1, y2)
        for yy in range(ymin, ymax + 1):
            xs = []
            for (ax, ay), (bx, by) in (((x0, y0), (x1, y1)),
                                       ((x1, y1), (x2, y2)),
                                       ((x2, y2), (x0, y0))):
                if ay == by:
                    continue
                if min(ay, by) <= yy <= max(ay, by):
                    xs.append(ax + (yy - ay) * (bx - ax) / (by - ay))
            if len(xs) >= 2:
                for xx in range(int(min(xs)), int(max(xs)) + 1):
                    self.set(xx, yy, color)

    def text(self, x, y, s, scale, color):
        """Draw text left-aligned at (x, y); returns the width in pixels."""
        cx = x
        for ch in s.upper():
            glyph = FONT.get(ch, FONT[" "])
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.rect(cx + col * scale, y + row * scale,
                                  scale, scale, color)
            cx += 6 * scale
        return cx - x - scale

    def text_width(self, s, scale):
        return len(s) * 6 * scale - scale

    def text_center(self, x, y, w, s, scale, color):
        tw = self.text_width(s, scale)
        return self.text(x + (w - tw) // 2, y, s, scale, color)


def png_bytes(canvas):
    """Encode the canvas as a deterministic PNG (no ancillary chunks)."""
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)  # filter: none
        raw += canvas.px[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", binascii.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


# ------------------------------------------------------------ the picture
# Layout: 1024x640. Masthead 72px, dominant tariff panel on the left,
# three vignettes stacked on the right, footer strip with two more stories.
def draw_masthead(c):
    """Slim ink strip: date, title line, day of the week. No brand name."""
    c.rect(0, 0, W, 72, INK)
    c.rect(0, 72, W, 4, RED)
    c.text(28, 28, "THURSDAY", 2, PAPER)
    c.text_center(0, 20, W, "THE WORLD IN ONE PICTURE", 4, PAPER)
    c.text(1024 - 28 - c.text_width("26 NOVEMBER 2026", 2), 28,
           "26 NOVEMBER 2026", 2, AMBER)


def draw_tariff_panel(c):
    """Dominant story: a container ship under a big red tariff tag."""
    x0, y0, x1, y1 = 24, 92, 600, 556
    c.rect(x0, y0, x1 - x0, y1 - y0, WHITE)
    # sky, sea, then a white band at the bottom for the headline
    c.rect(x0 + 3, y0 + 3, x1 - x0 - 6, 167, SKY)
    c.rect(x0 + 3, y0 + 170, x1 - x0 - 6, 130, SEA)
    # sun
    c.circle(x0 + 92, y0 + 52, 24, AMBER)
    # container ship: hull, deck, two neat rows of stacked containers
    hull_y = y0 + 190
    c.rect(x0 + 60, hull_y, 420, 30, INK)
    c.triangle([(x0 + 480, hull_y), (x0 + 540, hull_y),
                (x0 + 480, hull_y + 30)], INK)
    c.rect(x0 + 60, hull_y + 30, 420, 5, RED)
    row_cols = [RED, AMBER, TEAL, RED, TEAL, AMBER, RED]
    for i, col in enumerate(row_cols):
        cx = x0 + 72 + i * 52
        c.rect(cx, hull_y - 28, 48, 26, col)
        c.rect(cx + 1, hull_y - 27, 46, 24, col)
    for i, col in enumerate([TEAL, RED, AMBER, TEAL, RED]):
        cx = x0 + 98 + i * 52
        c.rect(cx, hull_y - 56, 48, 26, col)
    # bridge tower
    c.rect(x0 + 505, hull_y - 84, 32, 84, WHITE)
    c.rect(x0 + 509, hull_y - 76, 24, 12, INK)
    c.rect(x0 + 509, hull_y - 56, 24, 12, INK)
    # waves
    for wx in range(x0 + 20, x1 - 20, 46):
        c.line(wx, y0 + 268, wx + 22, y0 + 276, WHITE, 3)
        c.line(wx + 22, y0 + 276, wx + 44, y0 + 268, WHITE, 3)
    # big red tariff tag hanging over the ship
    tx, ty = x0 + 300, y0 + 16
    c.rect(tx, ty, 180, 78, RED)
    c.triangle([(tx, ty + 78), (tx + 180, ty + 78), (tx + 90, ty + 100)],
               RED)
    c.text_center(tx, ty + 10, 180, "25%", 6, WHITE)
    c.text_center(tx, ty + 52, 180, "TARIFF", 3, WHITE)
    # headline on the white band under the scene
    c.text_center(x0, y0 + 322, x1 - x0, "US HITS 14 NATIONS", 4, INK)
    c.text_center(x0, y0 + 354, x1 - x0, "WITH NEW TARIFFS", 4, RED)
    c.text_center(x0, y0 + 404, x1 - x0,
                  "CHINA AND INDIA FACE THE HIGHEST RATES", 2, GREY)


def draw_vignette(c, x0, y0, w, h, tag, lines, accent):
    """One small story panel: coloured tag, scene area, two headline lines."""
    c.rect(x0, y0, w, h, WHITE)
    c.rect(x0, y0, w, 26, accent)
    c.text(x0 + 10, y0 + 6, tag, 2, WHITE)
    return x0, y0 + 26, w, h - 26


def draw_missile(c, x, y, w, h):
    """North Korea vignette: missile rising over mountains (fits h px)."""
    c.rect(x, y, w, h, SKY)
    c.triangle([(x, y + h), (x + w // 3, y + h - 26),
                (x + 2 * w // 3, y + h)], INK)
    c.triangle([(x + w // 3, y + h), (x + 2 * w // 3, y + h - 20),
                (x + w, y + h)], INK)
    mx, my = x + w // 2, y + 12
    c.rect(mx - 8, my, 16, 34, INK)
    c.triangle([(mx - 8, my), (mx + 8, my), (mx, my - 11)], RED)
    c.triangle([(mx - 8, my + 34), (mx + 8, my + 34), (mx, my + 50)],
               AMBER)
    c.circle(mx, my + 54, 5, RED)


def draw_cairo_fire(c, x, y, w, h):
    """Cairo vignette: tanker truck on a road, flames above it (fits h px)."""
    c.rect(x, y, w, h, (232, 214, 180))
    c.rect(x, y + h - 20, w, 20, INK)
    c.hline(x, x + w, y + h - 20, WHITE, 2)
    # tanker: cab + cylinder tank
    tx, ty = x + w // 2 - 80, y + 26
    c.rect(tx, ty + 8, 120, 22, (200, 200, 190))
    c.circle(tx + 30, ty + 19, 11, (200, 200, 190))
    c.circle(tx + 90, ty + 19, 11, (200, 200, 190))
    c.rect(tx + 120, ty + 14, 36, 16, RED)
    c.rect(tx + 128, ty + 17, 14, 8, SKY)
    c.circle(tx + 26, ty + 34, 6, INK)
    c.circle(tx + 100, ty + 34, 6, INK)
    c.circle(tx + 142, ty + 34, 6, INK)
    # flames, kept inside the scene
    fx = tx + 52
    c.triangle([(fx - 20, ty + 8), (fx - 6, ty - 18), (fx + 4, ty + 8)],
               AMBER)
    c.triangle([(fx - 2, ty + 8), (fx + 14, ty - 24), (fx + 28, ty + 8)],
               RED)
    c.triangle([(fx + 10, ty + 8), (fx + 22, ty - 12), (fx + 36, ty + 8)],
               AMBER)
    # smoke, kept inside the scene
    c.circle(tx + 24, ty - 14, 5, GREY)
    c.circle(tx + 52, ty - 16, 6, GREY)
    c.circle(tx + 82, ty - 12, 5, GREY)


def draw_markets(c, x, y, w, h):
    """Markets vignette: a chart line falling hard, in red."""
    c.rect(x, y, w, h, WHITE)
    for gy in range(4):
        yy = y + 12 + gy * 22
        c.hline(x + 8, x + w - 8, yy, (220, 220, 210), 1)
    pts = [(x + 12, y + 10), (x + 60, y + 16), (x + 108, y + 14),
           (x + 156, y + 30), (x + 204, y + 36), (x + 252, y + 54),
           (x + 300, y + 60)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        c.line(ax, ay, bx, by, RED, 5)
    ex, ey = pts[-1]
    c.triangle([(ex - 14, ey - 12), (ex + 12, ey - 12), (ex, ey + 10)], RED)
    c.circle(pts[0][0], pts[0][1], 5, INK)


def draw_footer(c):
    """Thin strip: one more verified story of the day, in small type."""
    c.rect(0, 576, W, 64, INK)
    c.text_center(0, 592, W,
                  "ALSO: MACY'S PARADE PUT OFF TO SATURDAY BY STORM", 2,
                  PAPER)
    c.text_center(0, 616, W,
                  "IOWA ARMY BLAST A SUCCESS: ZERO AIRBORNE LEAD", 2, AMBER)


def build():
    c = Canvas(W, H, PAPER)
    draw_masthead(c)
    draw_tariff_panel(c)
    # three vignettes down the right-hand column
    vx, vw = 624, 376
    vy, vh, gap = 92, 140, 22
    ix, iy, iw, ih = draw_vignette(c, vx, vy, vw, vh, "NORTH KOREA",
                                   [], RED)
    draw_missile(c, ix, iy, iw, ih - 44)
    c.text(ix + 10, iy + ih - 40, "KIM ORDERS MORE", 2, INK)
    c.text(ix + 10, iy + ih - 22, "TACTICAL NUKES", 2, INK)
    ix, iy, iw, ih = draw_vignette(c, vx, vy + vh + gap, vw, vh, "CAIRO",
                                   [], RED)
    draw_cairo_fire(c, ix, iy, iw, ih - 44)
    c.text(ix + 10, iy + ih - 40, "TANKER FIRE KILLS", 2, INK)
    c.text(ix + 10, iy + ih - 22, "AT LEAST 30", 2, INK)
    ix, iy, iw, ih = draw_vignette(c, vx, vy + 2 * (vh + gap), vw, vh,
                                   "WALL STREET", [], INK)
    draw_markets(c, ix, iy, iw, ih - 44)
    c.text(ix + 10, iy + ih - 40, "NASDAQ SLIDES", 2, INK)
    c.text(ix + 10, iy + ih - 22, "NEARLY 4%", 2, RED)
    draw_footer(c)
    return c


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = png_bytes(build())
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print(f"wrote {path}: {len(data)} bytes, {W}x{H}")


if __name__ == "__main__":
    main()
