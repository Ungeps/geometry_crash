"""Core entities: geometry helpers, Projectile, Enemy (8 types + boss), Player."""
import math
import random

import pygame

import config as C

TWO_PI = math.pi * 2


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def dist2(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def angle(a, b):
    return math.atan2(b[1] - a[1], b[0] - a[0])


def vec(ang, speed):
    return (math.cos(ang) * speed, math.sin(ang) * speed)


def move(pos, vel, dt):
    return (pos[0] + vel[0] * dt, pos[1] + vel[1] * dt)


def ang_diff(a, b):
    return (b - a + math.pi) % TWO_PI - math.pi


def clamp_field(pos, r):
    lo = C.BORDER + r
    hx = C.WIDTH - C.BORDER - r
    hy = C.HEIGHT - C.BORDER - r
    return (max(lo, min(hx, pos[0])), max(lo, min(hy, pos[1])))


def rand_point(rng, margin, border=False):
    """Legacy screen-space helper retained for tests and fixed-layout utilities."""
    m = C.BORDER + margin
    x = rng.uniform(m, C.WIDTH - m)
    y = rng.uniform(m, C.HEIGHT - m)
    if not border:
        return (x, y)
    side = rng.randrange(4)
    if side == 0:
        return (x, m)
    if side == 1:
        return (x, C.HEIGHT - m)
    if side == 2:
        return (m, y)
    return (C.WIDTH - m, y)


def rand_around(rng, center, min_radius, max_radius):
    """Choose a world position in an annulus around a moving camera target."""
    a = rng.uniform(0.0, TWO_PI)
    r = rng.uniform(min_radius, max_radius)
    return (center[0] + math.cos(a) * r, center[1] + math.sin(a) * r)


def weighted(rng, items):
    total = sum(w for _, w in items)
    r = rng.uniform(0, total)
    acc = 0.0
    for value, w in items:
        acc += w
        if r <= acc:
            return value
    return items[-1][0]


def fade(color, k):
    return tuple(max(0, min(255, int(c * k))) for c in color)


class Projectile:
    def __init__(self, pos, vel, dmg, radius, life, pierce=0, slow=0, slow_time=0, explode=0,
                 chain=0, chain_dmg=0, chain_range=200, color=(255, 255, 255), friendly=True,
                 target=None, zone=None, bolt_life=0.18):
        self.pos, self.vel, self.dmg, self.radius, self.life = pos, vel, dmg, radius, life
        self.pierce, self.hits = pierce + 1, set()
        self.slow, self.slow_time, self.explode = slow, slow_time, explode
        self.chain, self.chain_dmg, self.chain_range = chain, chain_dmg, chain_range
        self.color, self.friendly, self.target, self.zone, self.bolt_life = color, friendly, target, zone, bolt_life
        self.t = 0.0

    def update(self, dt, game):
        self.pos = move(self.pos, self.vel, dt)
        self.t += dt
        if self.t >= self.life:
            return False
        if self.target is not None:
            if dist(self.pos, self.target) <= 8:
                r, dps, life, slow, slow_time = self.zone
                game.add_zone(self.target, r, dps, 0.1, life, False, slow, slow_time, self.color)
            return self.t < self.life
        if self.friendly:
            for e in game.enemies:
                if e.hp <= 0 or e in self.hits:
                    continue
                if dist(self.pos, e.pos) <= e.radius + self.radius:
                    self.hits.add(e)
                    e.hit(self.dmg, self.slow, self.slow_time)
                    if self.explode:
                        game.explosion(self.pos, self.explode, self.dmg, self.slow, self.slow_time)
                    if self.chain:
                        game.chain(self.pos, self.chain, self.chain_dmg, self.chain_range, {e},
                                   self.bolt_life)
                    self.pierce -= 1
                    if self.pierce <= 0:
                        return False
                    break
        else:
            p = game.player
            if dist(self.pos, p.pos) <= C.PLAYER_RADIUS + self.radius:
                p.damage(self.dmg, game)
                return False
        return True

    def draw(self, s, ox, oy):
        x, y = int(self.pos[0] + ox), int(self.pos[1] + oy)
        r = int(self.radius)
        pygame.draw.circle(s, self.color, (x, y), r)
        pygame.draw.circle(s, fade(self.color, 0.5), (x, y), r + 2, 1)


class Enemy:
    def __init__(self, etype, pos, wave):
        s = C.ENEMY_STATS[etype]
        self.etype, self.pos, self.params, self.wave = etype, pos, s, wave
        self.max_hp = max(1.0, (s["hp_base"] + s["hp_wave"] * wave) * s.get("hp_mult", 1.0))
        self.hp = self.max_hp
        self.speed = (s["speed"] + s["speed_wave"] * wave) * s.get("speed_mult", 1.0)
        self.dmg, self.radius = s["dmg"], s["radius"]
        self.xp = int(round(s["xp"] * (2 if wave >= C.XP_FROM_WAVE else 1)))
        self.behavior = s["behavior"]
        self.color = C.ENEMY_COLORS[etype]
        self.hit_cd = self.flash = self.slow_t = 0.0
        self.burn_t = self.burn_dmg = 0.0
        self.slow = self.boost = 1.0
        self.aim, self.fire, self.volley, self.summon, self.aura_acc = 0.0, 1.0, 1.0, 3.0, 0.0
        self.attack_t = s.get("fire_rate", 1.0) + s.get("windup", 0.0)
        self.attack_pos, self.telegraphing = pos, False
        self.state = "burst" if self.behavior == "hop" else "aim"
        self.timer = s.get("telegraph", s.get("burst", 0.35))

    def phase(self):
        """Boss phases by HP fraction: chase / ring volley / summon."""
        if self.hp > self.max_hp * C.BOSS_PHASE2_FRAC:
            return 1
        if self.hp > self.max_hp * C.BOSS_PHASE3_FRAC:
            return 2
        return 3

    def hit(self, dmg, slow=0, slow_time=0):
        if dmg <= 0:
            return
        self.hp -= dmg
        self.flash = 0.12
        if slow > 0:
            self.slow = min(self.slow, 1.0 - slow)
            self.slow_t = max(self.slow_t, slow_time)

    def speed_now(self):
        return self.speed * self.slow * self.boost

    def update(self, dt, game):
        p = game.player
        self.hit_cd = max(0.0, self.hit_cd - dt)
        self.flash = max(0.0, self.flash - dt)
        if self.slow_t > 0:
            self.slow_t -= dt
            if self.slow_t <= 0:
                self.slow = 1.0
        if self.burn_t > 0:
            self.burn_t -= dt
            self.hp -= self.burn_dmg * dt
        d = dist(self.pos, p.pos)
        a = angle(self.pos, p.pos)
        sp = self.speed_now()
        if self.behavior == "chase":
            self.pos = move(self.pos, vec(a, sp), dt)
        elif self.behavior == "hop":
            self.timer -= dt
            if self.state == "burst":
                self.pos = move(self.pos, vec(self.aim, sp), dt)
                if self.timer <= 0:
                    self.state, self.timer = "idle", self.params["idle"]
            elif self.timer <= 0:
                self.state, self.timer, self.aim = "burst", self.params["burst"], a
        elif self.behavior == "charge":
            self.timer -= dt
            if self.state == "aim":
                self.aim = a
                if self.timer <= 0:
                    self.state, self.timer = "charge", self.params["charge_time"]
            elif self.state == "charge":
                self.pos = move(self.pos, vec(self.aim, self.params["charge_speed"] * self.slow), dt)
                if self.timer <= 0:
                    self.state, self.timer = "rest", self.params["rest"]
            elif self.timer <= 0:
                self.state, self.timer = "aim", self.params["telegraph"]
        elif self.behavior == "spitter":
            keep = self.params["keep"]
            if d > keep + 30:
                self.pos = move(self.pos, vec(a, sp), dt)
            elif d < keep - 30:
                self.pos = move(self.pos, vec(a + math.pi, sp), dt)
            self.attack_t -= dt
            if self.attack_t <= self.params["windup"]:
                self.aim = a
            if self.attack_t <= 0:
                self.attack_t = self.params["fire_rate"] + self.params["windup"]
                spread = math.radians(self.params["spread_deg"])
                for i in range(self.params["volley"]):
                    off = (i - (self.params["volley"] - 1) / 2.0) * spread
                    game.shots.append(Projectile(
                        self.pos, vec(self.aim + off, self.params["bullet_speed"]),
                        self.params["bullet_dmg"], 5, 3.2, color=self.color, friendly=False))
        elif self.behavior == "hexer":
            keep = self.params["keep"]
            if d > keep + 25:
                self.pos = move(self.pos, vec(a, sp), dt)
            elif d < keep - 25:
                self.pos = move(self.pos, vec(a + math.pi, sp), dt)
            self.attack_t -= dt
            if self.attack_t <= self.params["windup"] and not self.telegraphing:
                self.telegraphing = True
                lead = move(p.pos, (p.dash_dir[0] * 70, p.dash_dir[1] * 70), 1.0)
                self.attack_pos = lead
            if self.attack_t <= 0:
                game.add_zone(self.attack_pos, self.params["zone_radius"], self.params["zone_dps"],
                              self.params["zone_warn"], self.params["zone_life"], True, 0, 0, self.color)
                self.attack_t = self.params["fire_rate"] + self.params["windup"]
                self.telegraphing = False
        elif self.behavior == "boss":
            ph = self.phase()
            self.pos = move(self.pos, vec(a, (C.BOSS_SPEED, C.BOSS_SPEED2, C.BOSS_SPEED3)[ph - 1]
                                           * self.slow * self.boost), dt)
            self.volley -= dt
            if ph >= 2 and self.volley <= 0:
                self.volley = C.BOSS_VOLLEY_RATE
                self.aim = (self.aim + 0.25) % TWO_PI
                for i in range(C.BOSS_RING):
                    ang = self.aim + i * TWO_PI / C.BOSS_RING
                    game.shots.append(Projectile(
                        self.pos, vec(ang, C.BOSS_BULLET_SPEED), C.BOSS_BULLET_DMG, 6, 3.5,
                        color=self.color, friendly=False))
                from objects import Fx
                game.fx.append(Fx("ring", self.pos, self.radius + 18, life=0.35, color=self.color,
                                   width=3))
            self.summon -= dt
            if ph == 3 and self.summon <= 0:
                self.summon = C.BOSS_SUMMON_RATE
                live = sum(1 for e in game.enemies if e.etype == "minion")
                for i in range(min(C.BOSS_MINIONS, C.BOSS_MINION_MAX - live)):
                    ang = i * TWO_PI / C.BOSS_MINIONS
                    game.spawn("minion", move(self.pos, vec(ang, 46), 1.0), self.wave, "minion")
                game.banner("BOSS SUMMONS MINIONS", 1.5)
        elif self.behavior == "elite":
            if d > self.params["keep"]:
                self.pos = move(self.pos, vec(a, sp), dt)
            self.aura_acc += dt
            if self.aura_acc >= 0.25:
                self.aura_acc = 0.0
                if d <= self.params["aura_radius"] + C.PLAYER_RADIUS:
                    p.damage(self.params["aura_dps"] * 0.25, game)
            self.fire -= dt
            if self.fire <= 0:
                self.fire = 1.0 / self.params["fire_rate"]
                game.shots.append(Projectile(self.pos, vec(angle(self.pos, p.pos),
                                                           self.params["bullet_speed"]), self.dmg, 5, 2.6,
                                             color=self.color, friendly=False))
        if self.hit_cd <= 0 and d <= self.radius + C.PLAYER_RADIUS:
            self.hit_cd = C.CONTACT_CD
            p.damage(self.dmg, game)
        if self.etype == "tank":
            for e in game.enemies:
                if e is not self and e.etype in ("crawler", "hopper", "mini"):
                    if dist(e.pos, self.pos) <= self.radius + e.radius:
                        e.pos = move(e.pos, vec(angle(self.pos, e.pos), self.params["push"]), 1.0)
        return self.hp > 0

    def draw(self, s, ox, oy):
        x, y = int(self.pos[0] + ox), int(self.pos[1] + oy)
        r = int(self.radius)
        k = self.flash / 0.12
        col = tuple(min(255, c + int(110 * k)) for c in self.color)
        if self.etype == "sprinter" and self.state == "aim":
            end = (int(self.pos[0] + ox + math.cos(self.aim) * 260),
                   int(self.pos[1] + oy + math.sin(self.aim) * 260))
            pygame.draw.line(s, fade((255, 240, 120), 0.3 + 0.7 * (1 - self.timer / 0.5)),
                             (x, y), end, 2)
        if self.etype == "spitter" and self.attack_t <= self.params["windup"]:
            reach = 340
            end = (int(x + math.cos(self.aim) * reach), int(y + math.sin(self.aim) * reach))
            progress = 1.0 - max(0.0, self.attack_t) / self.params["windup"]
            pygame.draw.line(s, fade(self.color, 0.25 + 0.65 * progress), (x, y), end, 2)
        if self.etype == "hexer" and self.telegraphing:
            tx = int(self.attack_pos[0] + ox)
            ty = int(self.attack_pos[1] + oy)
            pygame.draw.circle(s, fade(self.color, 0.65), (tx, ty), self.params["zone_radius"], 2)
            pygame.draw.line(s, fade(self.color, 0.5), (tx - 7, ty), (tx + 7, ty), 1)
            pygame.draw.line(s, fade(self.color, 0.5), (tx, ty - 7), (tx, ty + 7), 1)
        pygame.draw.circle(s, col, (x, y), r)
        if self.etype == "boss":
            pygame.draw.circle(s, (20, 22, 30), (x, y), r + 4)
            pygame.draw.circle(s, (255, 255, 255), (x, y), r, 2)
        elif self.etype in ("tank", "elite", "banner", "splitter", "spitter", "hexer"):
            pygame.draw.circle(s, (20, 22, 30), (x, y), r, 2)
        if self.etype == "spitter":
            points = [(int(x + math.cos(self.aim + i * TWO_PI / 3) * (r + 4)),
                       int(y + math.sin(self.aim + i * TWO_PI / 3) * (r + 4))) for i in range(3)]
            pygame.draw.polygon(s, (220, 255, 230), points, 2)
        elif self.etype == "hexer":
            points = [(int(x + math.cos(i * TWO_PI / 6) * (r + 3)),
                       int(y + math.sin(i * TWO_PI / 6) * (r + 3))) for i in range(6)]
            pygame.draw.polygon(s, (240, 220, 255), points, 2)
        if self.etype == "banner":
            pygame.draw.circle(s, fade(self.color, 0.25), (x, y), int(self.params["boost_radius"]), 1)
            pygame.draw.line(s, (255, 255, 255), (x, y - r), (x, y - r - 14), 2)
            pygame.draw.rect(s, self.color, (x, y - r - 14, 10, 8))
        if self.etype == "elite":
            pygame.draw.circle(s, fade(self.color, 0.35), (x, y), int(self.params["aura_radius"]), 1)
        if self.slow_t > 0:
            pygame.draw.circle(s, (150, 220, 255), (x, y), r, 2)
        if self.hp < self.max_hp and (self.max_hp > 20 or self.etype in ("tank", "elite", "boss")):
            w = 2 * r
            k = max(0.0, self.hp / self.max_hp)
            pygame.draw.rect(s, (30, 35, 45), (x - w // 2, y - r - 8, w, 4))
            pygame.draw.rect(s, C.C_HP, (x - w // 2, y - r - 8, int(w * k), 4))


class Player:
    def __init__(self):
        self.pos = (0.0, 0.0)
        self.max_hp = self.hp = C.PLAYER_HP
        self.level, self.xp = 1, 0
        self.xp_next = C.XP_BASE + C.XP_STEP
        self.kills = 0
        self.weapons, self.passives, self.pvals = [], {}, {}
        self.bonus = {"hp": 0.0, "speed": 0.0, "dmg": 0.0}
        self.dash_cd = self.dash_left = self.invuln = self.flash = 0.0
        self.hp_bar_t = 0.0
        self.dash_dir = (1.0, 0.0)
        self.rng = random.Random()   # replaced by the game's rng, so a seed replays a full run
        self.speed, self.dmg_mult, self.crit = C.PLAYER_SPEED, 1.0, 0.0
        self.pickup, self.regen, self.shield, self.area, self.cd_red = C.PICKUP_RADIUS, 0.0, 0.0, 1.0, 0.0
        self.armor, self.attack_speed = 0.0, 0.0

    def add_passive(self, pid, gain):
        self.passives[pid] = min(C.PASSIVE_MAX_LEVEL, self.passives.get(pid, 0) + 1)
        self.pvals[pid] = self.pvals.get(pid, 0.0) + gain
        self.recompute()

    def find_weapon(self, kind):
        for w in self.weapons:
            if w.kind == kind:
                return w
        return None

    def recompute(self):
        def v(pid):
            return self.pvals.get(pid, 0.0)
        self.speed = (C.PLAYER_SPEED + self.bonus["speed"]) * (1 + v("speed") / 100.0)
        self.dmg_mult = 1.0 + (self.bonus["dmg"] + v("dmg")) / 100.0
        self.crit = min(0.60, v("crit") / 100.0)
        self.pickup = C.PICKUP_RADIUS * (1 + v("pickup") / 100.0)
        self.regen = v("regen")
        self.shield = min(C.SHIELD_CAP, v("shield") / 100.0)
        self.area = 1.0 + v("area") / 100.0
        self.cd_red = min(0.60, v("cooldown") / 100.0)
        self.armor = min(0.50, v("armor") / 100.0)
        self.attack_speed = min(0.50, v("haste") / 100.0)

    def damage(self, amount, game):
        if self.invuln > 0:
            return 0.0
        eff = amount * (1.0 - self.shield) * (1.0 - self.armor)
        self.hp -= eff
        self.hp_bar_t = C.HP_BAR_TIME
        self.flash = 0.15
        game.shake(1.5 + min(5.0, eff / 3.0))
        return eff

    def start_dash(self, game, moving):
        if self.dash_cd > 0:
            return False
        if not moving:
            t = game.nearest(self.pos, 1e9)
            if t is not None:
                a = angle(self.pos, t.pos)
                self.dash_dir = (math.cos(a), math.sin(a))
        self.dash_left = C.DASH_DIST
        self.invuln = C.DASH_INVULN
        self.dash_cd = C.DASH_CD * (1.0 - self.cd_red)
        from objects import Fx
        game.fx.append(Fx("flash", self.pos, 30, life=0.3, color=C.C_PLAYER))
        return True

    def update(self, dt, game, keys):
        self.dash_cd = max(0.0, self.dash_cd - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.flash = max(0.0, self.flash - dt)
        self.hp_bar_t = max(0.0, self.hp_bar_t - dt)
        dx = dy = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1
        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071
        if self.dash_left > 0:
            step = min(C.DASH_SPEED * dt, self.dash_left)
            self.pos = move(self.pos, (self.dash_dir[0] * step, self.dash_dir[1] * step), 1.0)
            self.dash_left -= step
        elif dx or dy:
            self.dash_dir = (dx, dy)
            self.pos = move(self.pos, (dx * self.speed, dy * self.speed), dt)
        if self.regen > 0 and self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + self.regen * dt)

    def draw(self, s, ox, oy):
        x, y = int(self.pos[0] + ox), int(self.pos[1] + oy)
        r = int(C.PLAYER_RADIUS)
        col = C.C_PLAYER_HIT if self.flash > 0 else C.C_PLAYER
        if self.invuln > 0 and int(self.invuln * 24) % 2:
            col = (60, 130, 170)
        pygame.draw.circle(s, fade(col, 0.22), (x, y), r + 7, 1)
        pygame.draw.circle(s, fade(col, 0.30), (x, y), r + 3)
        pygame.draw.circle(s, col, (x, y), r)
        pygame.draw.circle(s, (245, 250, 255), (x, y), r, 1)
        tip = (int(x + self.dash_dir[0] * (r + 5)), int(y + self.dash_dir[1] * (r + 5)))
        pygame.draw.line(s, (245, 250, 255), (x, y), tip, 2)
        pygame.draw.circle(s, (255, 255, 255), (x, y), 2)
        if self.hp_bar_t > 0:
            bw, bh = C.HP_BAR_W, C.HP_BAR_H
            bx, by = x - bw // 2, y - r - C.HP_BAR_GAP - bh
            pygame.draw.rect(s, C.DASHBAR_BG, (bx, by, bw, bh))
            pygame.draw.rect(s, C.C_HP, (bx, by, int(bw * max(0.0, self.hp / self.max_hp)), bh))
            pygame.draw.rect(s, C.DASHBAR_BORDER, (bx, by, bw, bh), 1)
        span = C.DASH_CD * (1.0 - self.cd_red)
        if self.dash_cd > 0:  # charge bar under the hero, hidden when the dash is ready
            frac = 1.0 - self.dash_cd / span
            bx = x - C.DASHBAR_W // 2
            by = y + r + C.DASHBAR_GAP
            pygame.draw.rect(s, C.DASHBAR_BG, (bx, by, C.DASHBAR_W, C.DASHBAR_H))
            if frac > 0:
                pygame.draw.rect(s, C.DASHBAR_FILL, (bx, by, int(C.DASHBAR_W * min(1.0, frac)),
                                                     C.DASHBAR_H))
            pygame.draw.rect(s, C.DASHBAR_BORDER, (bx, by, C.DASHBAR_W, C.DASHBAR_H), 1)
