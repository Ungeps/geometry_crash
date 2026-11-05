"""HUD: bars, level-up cards, in-play labels, menu/pause/results screens. Every visible string
comes from locale.py; button rects are shared by drawing and by mouse hit-testing."""
import math

import pygame

import config as C
import locale as L
import ui

from upgrades import w_title, ALL_FUSION_IDS


def fmt_time(sec):
    return "%d:%02d" % (int(sec // 60), int(sec % 60))


def card_rects(n):
    """Layout of the level-up cards: shared by drawing and by mouse hit-test, no dead zones."""
    if n <= 0:
        return []
    gap = 12
    w = int(min(250, (C.WIDTH - gap * (n + 1)) / n))
    h = 190
    x0 = int((C.WIDTH - (n * w + (n - 1) * gap)) / 2)
    y = int((C.HEIGHT - h) / 2)
    return [pygame.Rect(x0 + i * (w + gap), y, w, h) for i in range(n)]


def _fit_wrapped(text, size, max_width, max_lines):
    lines = L.wrap(text, size, max_width)
    while size > C.MIN_FONT and len(lines) > max_lines:
        size -= 1
        lines = L.wrap(text, size, max_width)
    return size, lines[:max_lines]


def draw_cards(game, s):
    rects = card_rects(len(game.cards))
    if not rects:
        return
    title = L.t("card_title")
    size = L.fit(title, 32, C.WIDTH - 40)
    L.txt(s, title, C.WIDTH // 2, rects[0].y - 48, size, C.C_TEXT, "ct")
    for i, (r, c) in enumerate(zip(rects, game.cards)):
        pygame.draw.rect(s, C.C_CARD, r)
        pygame.draw.rect(s, c["color"], r, 2)
        clip = s.get_clip()
        s.set_clip(r.inflate(-2, -2))
        L.txt(s, "[%d]" % (i + 1), r.x + 10, r.y + 6, 20, c["color"])
        title_size, title_lines = _fit_wrapped(c["title"], C.F_CARD_T, r.width - 20, 2)
        ty = r.y + 28
        for ln in title_lines:
            L.txt(s, ln, r.x + 10, ty, title_size, c["color"])
            ty += 24
        text_size, text_lines = _fit_wrapped(c["text"], C.F_CARD_X, r.width - 20, 5)
        ty = r.y + 82
        for ln in text_lines:
            L.txt(s, ln, r.x + 10, ty, text_size, C.C_DIM)
            ty += 20
        s.set_clip(clip)


def draw_banner(game, s):
    if game.banner_t <= 0:
        return
    size = L.fit(game.banner_text, 28, C.WIDTH - 40)
    L.txt(s, game.banner_text, C.WIDTH // 2, 96, size, C.C_EPIC, "ct")


def _bar(s, x, y, w, h, frac, fill):
    pygame.draw.rect(s, (32, 38, 50), (x, y, w, h))
    if frac > 0:
        pygame.draw.rect(s, fill, (x, y, int(w * min(1.0, frac)), h))
    pygame.draw.rect(s, (95, 105, 125), (x, y, w, h), 1)


def draw_hud(game, s):
    p = game.player
    _bar(s, 20, 14, 220, 18, max(0.0, p.hp) / p.max_hp, C.C_HP)
    L.txt(s, L.t("hud_hp", hp=int(p.hp), max=int(p.max_hp)), 130, 23, C.F_HUD, C.C_TEXT, "c")
    _bar(s, C.WIDTH - 240, 14, 220, 18, min(1.0, p.xp / p.xp_next), C.C_XPBAR)
    L.txt(s, L.t("hud_xp", lv=p.level, xp=p.xp, next=p.xp_next), C.WIDTH - 130, 23,
          C.F_HUD, C.C_TEXT, "c")
    L.txt(s, fmt_time(game.time), C.WIDTH // 2, 8, 34, C.C_TEXT, "ct")
    L.txt(s, L.t("hud_wave", w=game.wave, n=len(game.enemies)), C.WIDTH // 2, 44, C.F_SMALL, C.C_DIM, "ct")
    L.txt(s, L.t("hud_kills", k=p.kills), 20, 44, C.F_SMALL, C.C_TEXT)
    L.txt(s, L.t("hud_links", c=len(game.book), total=len(ALL_FUSION_IDS)),
          C.WIDTH - 20, 44, C.F_SMALL, C.C_EPIC, "r")
    if game.boss is not None:
        _bar(s, 300, 66, 200, 10, game.boss.hp / game.boss.max_hp, C.BOSS_COLOR)
        L.txt(s, L.t("hud_boss"), 400, 79, C.F_SMALL, C.BOSS_COLOR, "ct")
    ready = p.dash_cd <= 0
    span = C.DASH_CD * (1.0 - p.cd_red)
    dash_w = 180
    pygame.draw.rect(s, (32, 38, 50), (20, 556, dash_w, 22))
    if not ready:
        fill = int(dash_w * (1.0 - p.dash_cd / span))
        pygame.draw.rect(s, (70, 90, 130), (20, 556, fill, 22))
    pygame.draw.rect(s, (95, 105, 125), (20, 556, dash_w, 22), 1)
    L.txt(s, L.t("hud_dash_ready") if ready else L.t("hud_dash_cd", s="%.1f" % p.dash_cd),
          20 + dash_w // 2, 567, 14, C.C_TEXT, "c")
    L.txt(s, L.t("hud_sound", s=L.t("st_on") if game.sound.on else L.t("st_off")), 224, 567, 14, C.C_DIM)


def minimap_rect():
    return pygame.Rect(C.WIDTH - 164, C.HEIGHT - 178, 152, 168)


def draw_minimap(game, s):
    panel = minimap_rect()
    pygame.draw.rect(s, (10, 15, 25), panel, border_radius=9)
    pygame.draw.rect(s, (66, 86, 112), panel, 1, border_radius=9)
    pygame.draw.line(s, (83, 118, 154), (panel.x + 8, panel.y + 19),
                     (panel.right - 8, panel.y + 19), 1)
    living = [e for e in game.enemies if e.hp > 0]
    L.txt(s, L.t("radar_title", n=len(living)), panel.x + 9, panel.y + 4, 12, C.C_TEXT)

    side = 116
    area = pygame.Rect(panel.centerx - side // 2, panel.y + 23, side, side)
    center = area.center
    radius = side // 2 - 7
    pygame.draw.rect(s, (13, 21, 32), area, border_radius=7)
    old_clip = s.get_clip()
    s.set_clip(area)
    for ring in (radius // 2, radius):
        pygame.draw.circle(s, (35, 51, 69), center, ring, 1)
    pygame.draw.line(s, (30, 45, 62), (center[0] - radius, center[1]),
                     (center[0] + radius, center[1]), 1)
    pygame.draw.line(s, (30, 45, 62), (center[0], center[1] - radius),
                     (center[0], center[1] + radius), 1)
    view_range = 520.0

    def radar_point(pos):
        dx, dy = pos[0] - game.player.pos[0], pos[1] - game.player.pos[1]
        length = math.hypot(dx, dy)
        scale = min(radius - 3, length * radius / view_range) / length if length else 0.0
        return int(center[0] + dx * scale), int(center[1] + dy * scale)

    for chest in game.chests:
        px, py = radar_point(chest.pos)
        pygame.draw.rect(s, (255, 193, 82), (px - 3, py - 3, 6, 6), border_radius=1)
        pygame.draw.rect(s, (255, 239, 178), (px - 3, py - 3, 6, 6), 1, border_radius=1)
    for enemy in living:
        px, py = radar_point(enemy.pos)
        if enemy.etype == "boss":
            pygame.draw.polygon(s, C.BOSS_COLOR, ((px, py - 5), (px + 5, py),
                                                   (px, py + 5), (px - 5, py)))
            pygame.draw.circle(s, (255, 235, 220), (px, py), 2)
        else:
            dot = 3 if enemy.etype == "elite" else 2
            pygame.draw.circle(s, enemy.color, (px, py), dot)
    pygame.draw.circle(s, (18, 37, 50), center, 5)
    pygame.draw.circle(s, C.C_PLAYER, center, 4)
    pygame.draw.circle(s, (245, 250, 255), center, 4, 1)
    pygame.draw.circle(s, (110, 225, 255), center, radius, 1)
    s.set_clip(old_clip)

    legend_y = panel.bottom - 15
    legend = ((panel.x + 8, C.C_HP, "radar_enemy"),
              (panel.x + 57, (255, 193, 82), "radar_chest"),
              (panel.x + 111, C.BOSS_COLOR, "radar_boss"))
    for x, color, key in legend:
        pygame.draw.circle(s, color, (x + 3, legend_y + 5), 3)
        L.txt(s, L.t(key), x + 9, legend_y, 9, C.C_DIM)


def _tile_hash(tx, ty, seed):
    value = (tx * 374761393 + ty * 668265263 + seed * 69069) & 0xFFFFFFFF
    value = ((value ^ (value >> 13)) * 1274126177) & 0xFFFFFFFF
    return value ^ (value >> 16)


def draw_field(s, ox=0, oy=0, seed=0):
    """Stream deterministic terrain tiles through the camera viewport."""
    tile = 64
    start_x = math.floor(-ox / tile)
    start_y = math.floor(-oy / tile)
    cols = C.WIDTH // tile + 2
    rows = C.HEIGHT // tile + 2
    for iy in range(rows):
        ty = start_y + iy
        sy = int(ty * tile + oy)
        for ix in range(cols):
            tx = start_x + ix
            sx = int(tx * tile + ox)
            noise = _tile_hash(tx, ty, seed)
            shade = noise % 5
            pygame.draw.rect(s, (23 + shade, 26 + shade, 36 + shade), (sx, sy, tile, tile))
            pygame.draw.rect(s, (31, 35, 47), (sx, sy, tile, tile), 1)
            if noise % 13 == 0:
                px, py = sx + 12 + (noise >> 8) % 42, sy + 12 + (noise >> 16) % 42
                pygame.draw.circle(s, (35, 40, 51), (px, py), 2 + (noise >> 24) % 3)
            if noise % 31 == 0:
                pygame.draw.line(s, (34, 38, 50), (sx + 16, sy + 20), (sx + 34, sy + 38), 1)
            if noise % 17 == 0:
                cx, cy = sx + 32, sy + 32
                glint = (34 + shade, 43 + shade, 58 + shade)
                pygame.draw.polygon(s, glint, ((cx, cy - 9), (cx + 9, cy),
                                                (cx, cy + 9), (cx - 9, cy)))
                pygame.draw.circle(s, (43 + shade, 52 + shade, 66 + shade), (cx, cy), 2)
            if noise % 29 == 0:
                px, py = sx + 17 + (noise >> 10) % 30, sy + 17 + (noise >> 18) % 30
                pygame.draw.circle(s, (43, 48, 61), (px, py), 5, 1)


def menu_rects():
    return ui.col_rects((C.WIDTH - C.BTN_W) // 2, C.MENU_BTN_Y0, C.BTN_W, C.BTN_H, C.BTN_GAP, 7)


def back_rect():
    return pygame.Rect((C.WIDTH - C.BACK_W) // 2, C.BACK_Y, C.BACK_W, C.BACK_H)


def pause_rects():
    return ui.col_rects((C.WIDTH - C.BTN_W) // 2, C.PAUSE_BTN_Y0, C.BTN_W, C.BTN_H, C.BTN_GAP, 3)


def over_rects():
    return ui.row_rects((C.WIDTH - 2 * C.BTN_W - C.OVER_GAP) // 2, C.OVER_BTN_Y0, C.BTN_W, C.BTN_H,
                        C.OVER_GAP, 2)


def menu_labels(game):
    return [L.t("m_play"), L.t("m_lang", lang=C.LANG_LABEL[L.lang()]),
            L.t("m_full", state=L.t("st_on") if game.fullscreen else L.t("st_off")),
            L.t("m_controls"), L.t("m_records"), L.t("m_book"), L.t("m_quit")]


def _hover(r, hover):
    return hover is not None and r.collidepoint(int(hover[0]), int(hover[1]))


def rec_lines(data):
    out = []
    for i, r in enumerate(data["records"][:C.TOP_RECORDS_SHOWN]):
        key = "res_" + str(r.get("result", "died")).replace(" ", "_")
        out.append(L.t("rec_line", n=i + 1, t=fmt_time(r.get("time", 0)), k=r.get("kills", 0),
                       lv=r.get("level", 1), r=L.t(key)))
    return out


def draw_menu(game, s):
    s.fill(C.C_BG)
    L.txt(s, L.t("game_title"), C.WIDTH // 2, C.MENU_TITLE_Y, C.F_TITLE, C.C_TEXT, "ct")
    sub = L.t("subtitle")
    L.txt(s, sub, C.WIDTH // 2, C.MENU_SUB_Y, L.fit(sub, C.F_SUB, 720), C.C_DIM, "ct")
    for i, (r, t) in enumerate(zip(menu_rects(), menu_labels(game))):
        ui.button(s, r, t, selected=(i == game.menu_sel), hovered=_hover(r, game.hover))
    L.txt(s, L.t("menu_hint"), C.WIDTH // 2, 586, C.F_SMALL, C.C_DIM, "ct")


def _back(s, game):
    r = back_rect()
    ui.button(s, r, L.t("m_back"), hovered=_hover(r, game.hover))


def draw_controls(game, s):
    s.fill(C.C_BG)
    L.txt(s, L.t("ctrl_title"), C.WIDTH // 2, 40, 34, C.C_TEXT, "ct")
    y = 92
    for ln in L.t("ctrl"):
        L.txt(s, ln, C.WIDTH // 2, y, L.fit(ln, C.F_HUD, 760), C.C_TEXT, "ct")
        y += 36
    L.txt(s, L.t("mouse_hint"), C.WIDTH // 2, y + 6, C.F_SMALL, C.C_DIM, "ct")
    _back(s, game)


def draw_records(game, s):
    s.fill(C.C_BG)
    L.txt(s, L.t("recs_title"), C.WIDTH // 2, 36, 30, C.C_TEXT, "ct")
    L.txt(s, L.t("book_line", n=len(game.book), total=len(ALL_FUSION_IDS)),
          C.WIDTH // 2, 70, C.F_HUD, C.C_EPIC, "ct")
    lines = rec_lines(game.data)
    y = 112
    for ln in lines:
        L.txt(s, ln, C.WIDTH // 2, y, C.F_HUD, C.C_TEXT, "ct")
        y += 28
    if not lines:
        L.txt(s, L.t("no_records"), C.WIDTH // 2, y, C.F_HUD, C.C_DIM, "ct")
    _back(s, game)


def draw_book(game, s):
    s.fill(C.C_BG)
    L.txt(s, L.t("book_title"), C.WIDTH // 2, 36, 30, C.C_TEXT, "ct")
    L.txt(s, L.t("book_line", n=len(game.book), total=len(ALL_FUSION_IDS)),
          C.WIDTH // 2, 70, C.F_HUD, C.C_EPIC, "ct")
    rects = []
    for row in range((len(ALL_FUSION_IDS) + 3) // 4):
        rects.extend(ui.row_rects(20, 110 + row * 44, 180, 36, 10, 4))
    for i, fid in enumerate(ALL_FUSION_IDS):
        unlocked = fid in game.book
        ui.label(s, rects[i], L.w_name(fid) if unlocked else L.t("book_locked"),
                 C.F_HUD, C.C_EPIC if unlocked else C.C_DIM)
    _back(s, game)


def draw_pause(game, s):
    s.fill(C.C_OVER)
    L.txt(s, L.t("pause_title"), C.WIDTH // 2, 38, 40, C.C_TEXT, "ct")
    L.txt(s, L.t("pause_hint"), C.WIDTH // 2, 90, C.F_HUD, C.C_TEXT, "ct")
    panels = (pygame.Rect(34, 130, 356, 146), pygame.Rect(410, 130, 356, 146))
    for panel in panels:
        pygame.draw.rect(s, C.C_CARD, panel)
        pygame.draw.rect(s, C.C_WALL, panel, 1)
    p = game.player
    L.txt(s, L.t("hud_w_label"), panels[0].x + 14, 142, C.F_SMALL, C.C_EPIC)
    L.txt(s, L.t("hud_p_label"), panels[1].x + 14, 142, C.F_SMALL, C.C_EPIC)
    weapons = [w_title(w.kind, w.level) for w in p.weapons] or [L.t("hud_no_w")]
    passives = [L.t("wlv", name=L.p_name(pid), p=L.t("lv_p"), lv=p.passives[pid])
                for pid in p.passives] or [L.t("hud_no_p")]
    for i, name in enumerate(weapons[:C.MAX_WEAPONS]):
        L.txt(s, name, panels[0].x + 14, 166 + i * 17,
              L.fit(name, C.F_SMALL, panels[0].width - 28), C.C_TEXT)
    for i, name in enumerate(passives[:C.MAX_PASSIVES]):
        L.txt(s, name, panels[1].x + 14, 166 + i * 17,
              L.fit(name, C.F_SMALL, panels[1].width - 28), C.C_TEXT)
    for i, r in enumerate(pause_rects()):
        ui.button(s, r, L.t(["m_resume", "m_restart", "m_menu"][i]), hovered=_hover(r, game.hover))
    L.txt(s, L.t("pause_hint2"), C.WIDTH // 2, 450, C.F_SMALL, C.C_DIM, "ct")
    L.txt(s, L.t("mouse_hint"), C.WIDTH // 2, 560, C.F_SMALL, C.C_DIM, "ct")


def draw_over(game, s):
    s.fill(C.C_OVER)
    win = game.state == "win"
    title = L.t("win_title") if win else L.t("over_title")
    L.txt(s, title, C.WIDTH // 2, 36, L.fit(title, 34, 700), C.C_EPIC if win else C.C_TEXT, "ct")
    y = 86
    if win:
        L.txt(s, L.t("win_sub"), C.WIDTH // 2, y, C.F_HUD, C.C_DIM, "ct")
        y += 30
    L.txt(s, L.t("over_stats", t=fmt_time(game.time), k=game.player.kills,
                  lv=game.player.level), C.WIDTH // 2, y, 22, C.C_TEXT, "ct")
    y += 32
    if game.reason[0]:
        L.txt(s, L.t(game.reason[0], **game.reason[1]), C.WIDTH // 2, y, C.F_HUD, C.C_DIM, "ct")
        y += 28
    names = [L.w_name(f) for f in game.new_fusions]
    line = L.t("links_found", list=", ".join(names)) if names else L.t("links_none")
    L.txt(s, line, C.WIDTH // 2, y, C.F_SMALL, C.C_EPIC, "ct")
    y += 24
    for note in game.notes[:3]:
        L.txt(s, L.t("over_note", note=note), C.WIDTH // 2, y, C.F_SMALL, C.C_DIM, "ct")
        y += 22
    y = max(y, 244)
    L.txt(s, L.t("top10"), C.WIDTH // 2, y, C.F_HUD, C.C_EPIC, "ct")
    y += 26
    for ln in rec_lines(game.data)[:10]:
        L.txt(s, ln, C.WIDTH // 2, y, C.F_SMALL, C.C_TEXT, "ct")
        y += 22
    for i, r in enumerate(over_rects()):
        ui.button(s, r, L.t(["m_new_run", "m_menu"][i]), hovered=_hover(r, game.hover))
    L.txt(s, L.t("press_r"), C.WIDTH // 2, 546, C.F_SMALL, C.C_DIM, "ct")
    L.txt(s, L.t("press_menu"), C.WIDTH // 2, 566, C.F_SMALL, C.C_DIM, "ct")
