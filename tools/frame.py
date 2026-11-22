"""Carve the gilt frame that hangs around the site's hero terminal.

The frame is a height field: a Louis XVI moulding profile (egg-and-dart, a
fluted cove, a twisted ribbon, a course of pearls) with a shell in each
corner. It is lit once from the upper left, so all four rails and every
ornament share the same light. The result is a square nine-slice image for CSS
border-image: four WIDTH-px corners and edge tiles that repeat every REPEAT px.
Stdlib only, like the rest of the tools.
"""

from __future__ import annotations

import math

WIDTH = 128   # outer edge to sight edge, and the border-image slice
REPEAT = 96   # every running ornament's period divides this
SIZE = 2 * WIDTH + REPEAT

GOLD = ((0.0, (30, 15, 5)), (0.22, (84, 48, 16)), (0.45, (150, 104, 36)), (0.66, (198, 156, 70)),
        (0.84, (228, 196, 112)), (1.0, (252, 240, 192)))
LIGHT = (-0.52, -0.70, 0.49)   # toward the lamp: up and to the left
RELIEF = 1.25
COVE = (32, 84)                # the hollow between the carved courses


def dome(x: float) -> float:
    return math.sqrt(1 - x * x) if -1 < x < 1 else 0.0


def moulding(t: float, u: float, flutes: bool = True) -> float:
    """Height of a rail, t px in from the outer edge and u px along it."""
    if t < 8:                                   # back edge
        return min(9.0, 3 * t)
    if t < 28:                                  # ovolo, carved with egg-and-dart
        dt = (t - 18) / 10
        h = 9 + 8 * dome(dt)
        du = (u % 16 - 8) / 8
        egg = 1 - (du / 0.68) ** 2 - (dt / 0.86) ** 2
        if egg > 0:
            return h + 4.6 * math.sqrt(egg)
        if abs(du) > 0.84:
            return h + 2.8 * (abs(du) - 0.84) / 0.16 * dome(dt * 1.15)
        return h - 1.8 * max(0.0, 1 + egg * 3)   # the channel around each egg
    if t < COVE[0]:
        return 8.0
    if t < COVE[1]:                             # cove, fluted across the rail
        s = (t - COVE[0]) / (COVE[1] - COVE[0])
        h = 8 + 7 * s - 8 * math.sin(math.pi * s)
        if flutes:
            reach = math.hypot(u % 12 - 6, t - min(73.0, max(43.0, t)))
            h -= 3.2 * dome(reach / 4.3)
        return h
    if t < 88:
        return 15.0
    if t < 106:                                 # twisted ribbon
        dt = (t - 97) / 9
        return 13 + dome(dt) * (9 + 2.4 * math.cos(2 * math.pi * (u / 16 + dt / 2)))
    if t < 109:
        return 11.0
    if t < 122:                                 # pearls
        d2 = (u % 12 - 6) ** 2 + (t - 115.5) ** 2
        return 8 + math.sqrt(27.0 - d2) if d2 < 27.0 else 8.0
    return 12.0 if t < 125 else 12 - 2.4 * (t - 125)   # sight edge


def corner(a: float, b: float) -> float | None:
    """Height of the corner shell, or None outside it; a and b are px in from the corner's two outer edges.

    The shell is hinged at the cove's inner corner and opens toward the outer one,
    covering the mitre across the cove and the egg-and-dart.
    """
    hinge = COVE[1] + 2
    da, db = hinge - a, hinge - b
    r = math.hypot(da, db)
    if r < 10:                                  # the boss at the hinge
        return 15 + 9 * dome(r / 10)
    if da <= 0 or db <= 0:
        return None
    lobe = abs(math.cos(9 * (math.atan2(db, da) - math.pi / 4) * 2))
    x = r / ((hinge - 9) * (0.92 + 0.08 * lobe))
    if x >= 1:
        return None
    swell = min(1.0, x * 2.6) ** 0.7 * dome(max(0.0, (x - 0.74) / 0.26))
    return 11 + 3 * x + 8.5 * swell * (0.25 + 0.75 * lobe ** 0.55)


def height(x: float, y: float) -> float:
    edges = (y, x, SIZE - y, SIZE - x)          # top, left, bottom, right
    t = min(edges)
    if t >= WIDTH:
        return 0.0
    side = edges.index(t)
    u = (x if side % 2 == 0 else y) - WIDTH
    a, b = min(x, SIZE - x), min(y, SIZE - y)
    if a >= WIDTH or b >= WIDTH:
        return moulding(t, u)
    # In a corner the flutes stop short of the shell.
    h = moulding(t, u, flutes=max(a, b) > COVE[1] + 8)
    shell = corner(a, b)
    return h if shell is None else shell


def gold(v: float) -> tuple[float, ...]:
    v = min(1.0, max(0.0, v))
    for (v0, c0), (v1, c1) in zip(GOLD, GOLD[1:]):
        if v <= v1:
            f = (v - v0) / (v1 - v0)
            return tuple(p + (q - p) * f for p, q in zip(c0, c1))
    return GOLD[-1][1]


def rows() -> list[bytes]:
    """The lit frame as SIZE rows of 8-bit RGB."""
    n = SIZE
    field = [[height(x + 0.5, y + 0.5) for x in range(n)] for y in range(n)]
    at = lambda x, y: field[min(n - 1, max(0, y))][min(n - 1, max(0, x))]
    lx, ly, lz = LIGHT
    hx, hy, hz = lx, ly, lz + 1
    hn = math.sqrt(hx * hx + hy * hy + hz * hz)
    hx, hy, hz = hx / hn, hy / hn, hz / hn
    out = []
    for y in range(n):
        row = bytearray()
        for x in range(n):
            h = field[y][x]
            gx = (at(x + 1, y) - at(x - 1, y)) * 0.5 * RELIEF
            gy = (at(x, y + 1) - at(x, y - 1)) * 0.5 * RELIEF
            inv = 1 / math.sqrt(gx * gx + gy * gy + 1)
            nx, ny, nz = -gx * inv, -gy * inv, inv
            diffuse = max(0.0, nx * lx + ny * ly + nz * lz)
            shine = max(0.0, nx * hx + ny * hy + nz * hz) ** 48
            around = (at(x + 4, y) + at(x - 4, y) + at(x, y + 4) + at(x, y - 4)
                      + at(x + 3, y + 3) + at(x - 3, y - 3) + at(x + 3, y - 3) + at(x - 3, y + 3)) / 8
            hollow = min(1.0, max(-0.6, (around - h) / 6))   # dirt settles in the hollows
            r, g, b = gold(0.1 + 1.02 * diffuse ** 1.15 - 0.4 * hollow)
            row += bytes(min(255, int(c + shine * k)) for c, k in ((r, 150), (g, 140), (b, 110)))
        out.append(bytes(row))
    return out
