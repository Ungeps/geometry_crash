"""Headless test driver: keys the autopilot presses, and the autopilot itself.
Used by main.py for 10-minute headless playtests (ARENA_AUTOPLAY=1|kite|pro)."""
import math

import pygame

import config as C
from entities import TWO_PI, dist
from upgrades import FUSIONS


class FakeKeys:
    """Maps a movement direction to the set of pressed keys the game loop reads."""
    CODES = {(0, 0): [], (-1, 0): [pygame.K_a], (1, 0): [pygame.K_d], (0, -1): [pygame.K_w],
             (0, 1): [pygame.K_s], (-1, -1): [pygame.K_a, pygame.K_w], (-1, 1): [pygame.K_a, pygame.K_s],
             (1, -1): [pygame.K_d, pygame.K_w], (1, 1): [pygame.K_d, pygame.K_s]}

    def __init__(self, dx, dy):
        dx = max(-1, min(1, int(round(dx))))
        dy = max(-1, min(1, int(round(dy))))
        self.codes = set(self.CODES.get((dx, dy), []))

    def __getitem__(self, key):
        return key in self.codes


def _score(game, c):
    """Card preference for the autopilot: 'pro' builds a focused fusion pair."""
    k = c["kind"]
    if game.autopilot_mode == "pro":
        links = {a for fid, a, b in FUSIONS if b == "pistol"}
        links |= {b for fid, a, b in FUSIONS if a == "pistol"}
        if k == "fusion":
            return 12
        if k == "weapon_level":
            w = game.player.find_weapon(c["id"])
            return 9 if w.kind in links and w.level < 3 else 5
        if k == "weapon":
            if c["id"] in links:
                return 11
            return 7 if len(game.player.weapons) < 3 else 1
        if k == "passive":
            return 2
        return 1
    if game.autopilot_mode in ("elite", "circle", "lane"):
        # a skilled player: keeps kiting safe (survival passives first),
        # builds a fusion pair, takes the fusion card when it shows up
        links = {a for fid, a, b in FUSIONS if b == "pistol"}
        links |= {b for fid, a, b in FUSIONS if a == "pistol"}
        if k == "fusion":
            return 12
        if k == "weapon_level":
            w = game.player.find_weapon(c["id"])
            return 10 if w.kind in links and w.level < 3 else 4
        if k == "weapon":
            return 9 if c["id"] in links else (3 if len(game.player.weapons) < 4 else 2)
        if k == "passive":
            pid = c["id"]
            if pid in ("speed", "shield", "regen"):
                return 8
            if pid in ("dmg", "crit", "area"):
                return 7
            return 6
        return 1
    if k == "fusion":
        return 4
    if k == "weapon":
        return 3
    if k == "weapon_level":
        return 2
    if k == "passive":
        return 1
    return 0


def chest_pull(game, vx, vy):
    """A chest is free epic power: step onto it when nothing is close."""
    if game.autopilot_mode not in ("elite", "circle", "lane"):
        return vx, vy
    for ch in game.chests:
        d = dist(ch.pos, game.player.pos)
        if d < 250:
            near = 999.0
            for e in game.enemies:
                near = min(near, dist(e.pos, game.player.pos))
            if near > 150:
                vx += (ch.pos[0] - game.player.pos[0]) * 60.0
                vy += (ch.pos[1] - game.player.pos[1]) * 60.0
    return vx, vy


def circle_steer(game):
    """Conga-line steering: walk a large circle around the centre so the swarm
    trails behind the hero instead of surrounding it."""
    cx = cy = 0.0
    ax, ay = game.player.pos[0] - cx, game.player.pos[1] - cy
    r = math.hypot(ax, ay) or 1.0
    th = math.atan2(ay, ax)
    R = 190.0
    nx, ny = ax / r, ay / r
    tx = cx + math.cos(th + 0.5) * R
    ty = cy + math.sin(th + 0.5) * R
    vx = tx - game.player.pos[0] + nx * (R - r) * 1.6
    vy = ty - game.player.pos[1] + ny * (R - r) * 1.6
    for e in game.enemies:
        d = dist(e.pos, game.player.pos)
        if d < 45:
            w = (45.0 - d) * 3.0
            vx += (game.player.pos[0] - e.pos[0]) * w
            vy += (game.player.pos[1] - e.pos[1]) * w
    for z in game.zones:
        if z.t >= z.warn and dist(z.pos, game.player.pos) < z.radius + 80:
            vx += (game.player.pos[0] - z.pos[0]) * 6000.0
            vy += (game.player.pos[1] - z.pos[1]) * 6000.0
    lo, hi = C.BORDER + 60, C.WIDTH - C.BORDER - 60
    lo_y, hi_y = C.BORDER + 60, C.HEIGHT - C.BORDER - 60
    if game.player.pos[0] < lo:
        vx += 3000.0
    if game.player.pos[0] > hi:
        vx -= 3000.0
    if game.player.pos[1] < lo_y:
        vy += 3000.0
    if game.player.pos[1] > hi_y:
        vy -= 3000.0
    vx, vy = chest_pull(game, vx, vy)
    n = math.hypot(vx, vy) or 1.0
    return vx / n, vy / n


def lane_steer(game):
    """Lane steering: run along the arena walls, turn at borders, so the swarm
    trails behind the hero instead of closing into a ring around it."""
    hx, hy = game.lane
    px, py = game.player.pos
    vx, vy = hx * 2.0, hy * 2.0
    for e in game.enemies:
        d = dist(e.pos, game.player.pos)
        if d < 80:
            w = (80.0 - d) * 2.0
            vx += (game.player.pos[0] - e.pos[0]) * w
            vy += (game.player.pos[1] - e.pos[1]) * w
    for z in game.zones:
        if z.t >= z.warn and dist(z.pos, game.player.pos) < z.radius + 80:
            vx += (game.player.pos[0] - z.pos[0]) * 6000.0
            vy += (game.player.pos[1] - z.pos[1]) * 6000.0
    vx, vy = chest_pull(game, vx, vy)
    n = math.hypot(vx, vy) or 1.0
    game.lane = (vx / n, vy / n)
    return game.lane


def run(game, dt):
    """Headless drivers for playtests: 1 = wander, kite = run away from the swarm,
    pro = kiting + focused fusion pair, elite = kiting + survival passives + pair,
    circle = conga-line circle + survival passives + pair. All dash and pick cards."""
    if game.state == "menu":
        game.new_run()
    game.auto_timer -= dt
    if game.autopilot_mode in ("kite", "pro", "elite"):
        vx = vy = 0.0
        for e in game.enemies:
            d = dist(e.pos, game.player.pos)
            if d < 220:
                w = 220.0 - d
                vx += (game.player.pos[0] - e.pos[0]) * w
                vy += (game.player.pos[1] - e.pos[1]) * w
        for z in game.zones:
            if z.t >= z.warn and dist(z.pos, game.player.pos) < z.radius + 70:
                vx += (game.player.pos[0] - z.pos[0]) * 4000.0
                vy += (game.player.pos[1] - z.pos[1]) * 4000.0
        # a chest is free epic power: step onto it when nothing is close
        vx, vy = chest_pull(game, vx, vy)
        if vx == 0.0 and vy == 0.0:
            vx, vy = math.cos(game.time * 0.7), math.sin(game.time * 0.7)
        n = math.hypot(vx, vy) or 1.0
        game.autopos = (vx / n, vy / n)
    elif game.autopilot_mode == "circle":
        game.autopos = circle_steer(game)
    elif game.autopilot_mode == "lane":
        game.autopos = lane_steer(game)
    elif game.auto_timer <= 0:
        game.auto_timer = 1.0
        a = game.rng.uniform(0, TWO_PI)
        game.autopos = (math.cos(a), math.sin(a))
    if game.state == "play":
        if game.player.dash_cd <= 0:
            game.player.start_dash(game, True)
    elif game.state == "levelup" and game.cards:
        best = max(_score(game, c) for c in game.cards)
        picks = [i for i, c in enumerate(game.cards) if _score(game, c) == best]
        game.choose_card(game.rng.choice(picks))
