"""Weapon: level scaling and 6 behavior types (shoot, aura, chain, arc, orbital, bomb).
All 10 base weapons and 12 hybrids run through these 6 behaviors with different parameters."""
import math

import pygame

import config as C
from entities import Projectile, dist, angle, vec, ang_diff, fade, TWO_PI
from objects import Fx


class Weapon:
    def __init__(self, kind, level=1, hybrid=False):
        self.kind, self.level, self.hybrid = kind, level, hybrid
        self.stats = C.HYBRID_STATS[kind] if hybrid else C.WEAPON_STATS[kind]
        self.color = C.WEAPON_COLORS[kind]
        self.cd, self.angle = 0.15, 0.0

    def base(self, key, d=0):
        return self.stats.get(key, d)

    def dmg(self, base):
        return base * C.LVL_DMG ** (self.level - 1)

    def rate(self, base):
        return base * C.LVL_RATE ** (self.level - 1)

    def area(self, base):
        return base * (1 + C.LVL_AREA * (self.level - 1))

    def targets(self, base):
        return base + (self.level - 1) // C.LVL_TARGET_STEP

    def interval(self, player=None):
        speed = 1.0 - (player.attack_speed if player is not None else 0.0)
        if self.stats["behavior"] == "aura":
            return self.base("tick", 0.25) * speed
        return speed / max(0.05, self.rate(self.base("rate", 1.0)))

    def roll(self, base, p):
        d = self.dmg(base) * p.dmg_mult
        if p.crit > 0 and p.rng.random() < p.crit:
            d *= C.CRIT_MULT
        return d

    def satellites(self, p):
        if not self.base("orbit"):
            return []
        n = self.targets(self.base("count", 1))
        o = self.area(self.base("orbit", 60))
        return [(p.pos[0] + math.cos(self.angle + i * TWO_PI / n) * o,
                 p.pos[1] + math.sin(self.angle + i * TWO_PI / n) * o) for i in range(n)]

    def update(self, dt, game):
        p = game.player
        if self.base("orbit"):
            self.angle = (self.angle + self.base("orbit_speed", 2.0) * dt) % TWO_PI
        self.cd -= dt
        if self.cd > 0:
            return
        self.cd = self.interval(p)
        BEHAVIORS[self.stats["behavior"]](self, game, p)

    def draw(self, s, ox, oy, p):
        if self.base("radius") and self.stats["behavior"] == "aura":
            r = int(self.area(self.base("radius")))
            pygame.draw.circle(s, fade(self.color, 0.20), (int(p.pos[0] + ox), int(p.pos[1] + oy)), r, 2)
        for sp in self.satellites(p):
            pygame.draw.circle(s, self.color, (int(sp[0] + ox), int(sp[1] + oy)), 6)
            pygame.draw.circle(s, (255, 255, 255), (int(sp[0] + ox), int(sp[1] + oy)), 6, 1)


def beh_shoot(w, game, p):
    n = w.targets(w.base("targets", 1))
    volley = w.targets(w.base("volley", 1))
    spread = math.radians(w.base("spread", 0))
    for t in game.pick(p.pos, n, w.base("range", 500), w.base("mode", "near")):
        base_a = angle(p.pos, t.pos)
        for i in range(volley):
            off = (i - (volley - 1) / 2.0) * spread
            game.projs.append(Projectile(p.pos, vec(base_a + off, w.base("speed", 420)),
                                         w.roll(w.base("dmg", 6), p), w.area(w.base("radius", 4)),
                                         w.base("life", 1.4), pierce=w.base("pierce", 0),
                                         slow=w.base("slow", 0), slow_time=w.base("slow_time", 0),
                                         explode=w.base("explode", 0), chain=w.base("chain", 0),
                                         chain_dmg=w.dmg(w.base("chain_dmg", 0)) * p.dmg_mult,
                                         chain_range=w.base("chain_range", 200), color=w.color,
                                         friendly=True))


def beh_aura(w, game, p):
    r = w.area(w.base("radius"))
    dmg = w.roll(w.base("dps") * w.interval(p), p)
    first = None
    for e in game.enemies:
        if e.hp > 0 and dist(e.pos, p.pos) <= r + e.radius:
            e.hit(dmg, w.base("slow", 0), w.base("slow_time", 0))
            if first is None:
                first = e
            if w.base("burn"):
                e.burn_dmg = w.dmg(w.base("burn")) * p.dmg_mult
                e.burn_t = 2.0
    game.fx.append(Fx("ring", p.pos, r, life=0.2, color=w.color, width=2))
    if w.base("chain_jumps") and first is not None:
        game.chain(first.pos, w.base("chain_jumps"), w.dmg(w.base("chain_dmg")) * p.dmg_mult,
                   w.base("range", 220), {first}, w.base("bolt", 0.18))
    if w.base("spikes"):
        n = w.targets(w.base("spikes"))
        for i in range(n):
            a = i * TWO_PI / n + w.angle
            game.projs.append(Projectile(p.pos, vec(a, w.base("speed", 340)),
                                         w.dmg(w.base("spike_dmg")) * p.dmg_mult, 5, 1.0,
                                         slow=w.base("slow", 0), slow_time=w.base("slow_time", 0),
                                         color=w.color, friendly=True))
    if w.base("zone_shots"):
        for t in game.pick(p.pos, w.base("zone_shots"), w.base("range", 280), "far"):
            game.add_zone(t.pos, w.area(w.base("zone_radius")), w.dmg(w.base("zone_dps")) * p.dmg_mult,
                          0.1, w.base("zone_life"), False, 0, 0, w.color)


def beh_chain(w, game, p):
    reach = w.area(w.base("range"))
    if game.nearest(p.pos, reach) is None:
        return
    game.chain(p.pos, w.targets(w.base("jumps")), w.roll(w.base("dmg"), p), reach, set(),
               w.base("bolt", 0.18))


def beh_arc(w, game, p):
    reach = w.area(w.base("reach"))
    t = game.nearest(p.pos, reach)
    if t is None:
        return
    a0 = angle(p.pos, t.pos)
    half = math.radians(w.base("arc_deg")) / 2.0
    dmg = w.roll(w.base("dmg"), p)
    hits = 0
    for e in game.enemies:
        if e.hp <= 0 or dist(e.pos, p.pos) > reach + e.radius:
            continue
        if abs(ang_diff(a0, angle(p.pos, e.pos))) > half:
            continue
        e.hit(dmg, w.base("slow", 0), w.base("slow_time", 0))
        hits += 1
        if w.base("zone_dps") and hits == 1:
            game.add_zone(e.pos, w.area(w.base("zone_radius")), w.dmg(w.base("zone_dps")) * p.dmg_mult,
                          0.1, w.base("zone_life"), False, 0, 0, w.color)
        if hits >= w.targets(w.base("targets")):
            break
    if hits:
        game.fx.append(Fx("ring", p.pos, reach, life=w.base("fx", 0.15), color=w.color, width=3))


def beh_orbital(w, game, p):
    dmg = w.roll(w.base("dmg"), p)
    for sp in w.satellites(p):
        if w.base("arc_mode"):
            hits = 0
            reach = w.area(w.base("reach"))
            for e in game.enemies:
                if e.hp > 0 and dist(e.pos, sp) <= reach + e.radius:
                    e.hit(dmg, 0, 0)
                    hits += 1
                    if hits >= w.targets(w.base("targets")):
                        break
            game.fx.append(Fx("ring", sp, reach, life=w.base("fx", 0.15), color=w.color, width=2))
        else:
            t = game.nearest(sp, w.base("range", 500))
            if t is not None:
                game.projs.append(Projectile(sp, vec(angle(sp, t.pos), w.base("speed", 440)), dmg,
                                             w.base("radius", 5), w.base("life", 1.5),
                                             explode=w.base("explode", 0), color=w.color, friendly=True))


def beh_bomb(w, game, p):
    t = game.nearest(p.pos, w.base("range", 300))
    if t is None:
        return
    zone = (w.area(w.base("zone_radius")), w.dmg(w.base("zone_dps")) * p.dmg_mult,
            w.base("zone_life"), w.base("slow", 0), w.base("slow_time", 0))
    game.projs.append(Projectile(p.pos, vec(angle(p.pos, t.pos), w.base("speed", 250)), 0, 6,
                                w.base("lob", 0.25) + 0.6, target=t.pos, zone=zone,
                                color=w.color, friendly=True))


BEHAVIORS = {"shoot": beh_shoot, "aura": beh_aura, "chain": beh_chain, "arc": beh_arc,
            "orbital": beh_orbital, "bomb": beh_bomb}
