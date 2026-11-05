"""UI primitives: letterboxed scaling of the 800x600 scene, mouse mapping, clickable buttons."""
import pygame

import config as C
import locale as L


def view(dw, dh, lw, lh):
    """Scale the logical scene to the display surface keeping proportions; letterbox fills the rest."""
    s = min(dw / float(lw), dh / float(lh))
    w, h = int(round(lw * s)), int(round(lh * s))
    return (max(0, (dw - w) // 2), max(0, (dh - h) // 2), s, w, h)


def blit(display, scene, vw):
    ox, oy, s, w, h = vw
    display.fill(C.C_LETTER)
    img = scene if abs(s - 1.0) < 1e-6 else pygame.transform.smoothscale(scene, (w, h))
    display.blit(img, (ox, oy))


def to_logical(mx, my, vw):
    """Screen (display) coordinates -> logical 800x600 coordinates."""
    ox, oy, s, w, h = vw
    if s <= 0:
        return (mx, my)
    return ((mx - ox) / s, (my - oy) / s)


def to_display(x, y, vw):
    """Logical coordinates -> display coordinates (used to move the cursor to a button)."""
    ox, oy, s, _w, _h = vw
    return (int(ox + x * s), int(oy + y * s))


def col_rects(x, y, w, h, gap, count):
    out = []
    for i in range(count):
        out.append(pygame.Rect(x, y + i * (h + gap), w, h))
    return out


def row_rects(x, y, w, h, gap, count):
    out = []
    for i in range(count):
        out.append(pygame.Rect(x + i * (w + gap), y, w, h))
    return out


def hit(rects, pos):
    """Index of the rect under pos, or None."""
    if pos is None:
        return None
    for i, r in enumerate(rects):
        if r.collidepoint(int(pos[0]), int(pos[1])):
            return i
    return None


def button(surf, rect, text, selected=False, hovered=False, pressed=False, size=None):
    size = size or C.F_BTN
    ts = L.fit(text, size, rect.width - 16)
    base = C.C_BTN_ACTIVE if pressed else (C.C_BTN_HOVER if hovered else C.C_BTN)
    pygame.draw.rect(surf, base, rect)
    pygame.draw.rect(surf, C.C_BTN_SEL if selected else C.C_BTN_SUB, rect, 2 if selected else 1)
    L.txt(surf, text, rect.x + rect.width // 2, rect.y + rect.height // 2,
          ts, C.C_BTN_TEXT, "c")


def label(surf, rect, text, size, color, anchor="ct"):
    """Centered text inside a rect, auto-shrunk so it never overflows."""
    ts = L.fit(text, size, rect.width)
    L.txt(surf, text, rect.x + rect.width // 2, rect.y + rect.height // 2, ts, color, "c")
