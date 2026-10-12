# Draws the article cover: figures/cover.png (Medium, 1600x900) and figures/cover-devto.png (Dev.to, 1000x420).
# Usage: uv run --with matplotlib python scripts/cover.py
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parent.parent / "figures"
BG, TEAL, RED, TILE, GREY = "#FBFAF7", "#0B7F6F", "#C2410C", "#D6E9E4", "#6B6B6B"
FONT = "Helvetica Neue"
RED_TILES = {(0, 3), (1, 2), (2, 1), (3, 0), (3, 3), (4, 2)}


def tiles(ax, x0, y0, size, gap):
    for row in range(5):
        for col in range(4):
            x, y = x0 + col * (size + gap), y0 - row * (size + gap)
            color = RED if (row, col) in RED_TILES else TILE
            ax.add_patch(FancyBboxPatch((x, y - size), size, size, boxstyle=f"round,pad=0,rounding_size={size * 0.12}",
                                        facecolor=color, edgecolor="none"))


def cover(path, w, h, big, mid, small, tile_size, tile_gap, tile_x, tile_y, text_x, y_big, y_mid, y_small):
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.text(text_x, y_big, "“Zero attacks”", fontsize=big, color=TEAL, fontweight="bold", family=FONT, va="baseline")
    ax.text(text_x, y_mid, "I re-ran the tests", fontsize=mid, color=RED, fontweight="bold", family=FONT, va="baseline")
    if small:
        ax.text(text_x, y_small, "OpenAPPA, an AI agent guard, on four models", fontsize=small, color=GREY, family=FONT,
                va="baseline")
    tiles(ax, tile_x, tile_y, tile_size, tile_gap)
    fig.savefig(path, dpi=100, facecolor=BG)
    plt.close(fig)


cover(OUT / "cover.png", 1600, 900, big=88, mid=56, small=30, tile_size=92, tile_gap=20,
      tile_x=1080, tile_y=748, text_x=120, y_big=470, y_mid=360, y_small=110)
cover(OUT / "cover-devto.png", 1000, 420, big=62, mid=38, small=0, tile_size=52, tile_gap=12,
      tile_x=720, tile_y=376, text_x=70, y_big=215, y_mid=140, y_small=0)
print("wrote", OUT / "cover.png", OUT / "cover-devto.png")
