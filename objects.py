"""Field objects: XP crystals, fire zones, chest, visual effects and particles."""
import math

import pygame

import config as C
from entities import dist, move, angle, vec, clamp_field, fade, TWO_PI


class Fx:
    """Line, ring, flash: short-lived visual that fades toward the dark background."""

    def __init__(self, kind, pos, r=0, target=None, life=0.15, color=(255, 255, 255), width=2):
        self.kind, self.pos, self.r, self.target = kind, pos, r, target
        self.life, self.color, self.width, self.t = life, color, width, 0.0

    def update(self, dt):
        self.t += dt
        return self.t < self.life

    def draw(self, s, ox, oy):
        a = max(0.0, 1.0 - self.t / self.life)
        col = fade(self.color, 0.15 + 0.85 * a)
        x, y = int(self.pos[0] + ox), int(self.pos[1] + oy)
        if self.kind == "line" and self.target:
            pygame.draw.line(s, col, (x, y), (int(self.target[0] + ox), int(self.target[1] + oy)),
                             max(1, self.width))
        elif self.kind == "ring":
            pygame.draw.circle(s, col, (x, y), int(self.r), max(1, self.width))
        else:
            pygame.draw.circle(s, col, (x, y), int(self.r * (self.t / self.life + 0.3)))


class Particle:
    def __init__(self, pos, vel, life, color, size=3):
        self.pos, self.vel, self.life, self.color, self.size, self.t = pos, vel, life, color, size, 0.0

    def update(self, dt):
        self.pos = move(self.pos, self.vel, dt)
        self.vel = (self.vel[0] * 0.90, self.vel[1] * 0.90)
        self.t += dt
        return self.t < self.life

    def draw(self, s, ox, oy):
        a = 1.0 - self.t / self.life
        r = max(1, int(self.size * a))
        pygame.draw.rect(s, fade(self.color, 0.2 + 0.8 * a),
                         (int(self.pos[0] + ox), int(self.pos[1] + oy), r, r))


class Crystal:
    def __init__(self, pos, xp):
        self.pos, self.xp, self.done = pos, xp, False

    def update(self, dt, game):
        p = game.player
        if dist(self.pos, p.pos) <= p.pickup:
            self.pos = move(self.pos, vec(angle(self.pos, p.pos), 400), dt)
            if dist(self.pos, p.pos) <= C.PLAYER_RADIUS:
                self.done = True
        return self.done

    def draw(self, s, ox, oy):
        x, y = int(self.pos[0] + ox), int(self.pos[1] + oy)
        pygame.draw.polygon(s, C.C_XP, ((x, y - 5), (x + 4, y), (x, y + 5), (x - 4, y)))


class Zone:
    """Telegraphed circle. vs_player=True: hazard placed by the wave planner.
    vs_player=False: weapon field that burns enemies (and may slow them)."""

    def __init__(self, pos, radius, dps, warn, life, vs_player, slow=0, slow_time=0, color=(255, 90, 40)):
        self.pos, self.radius, self.dps, self.warn, self.life = pos, radius, dps, warn, life
        self.vs_player, self.slow, self.slow_time, self.color = vs_player, slow, slow_time, color
        self.t, self.acc = 0.0, 0.0

    def update(self, dt, game):
        self.t += dt
        if self.t >= self.warn + self.life:
            return False
        if self.t >= self.warn:
            self.acc += dt
            if self.acc >= 0.25:
                self.acc = 0.0
                slice_dmg = self.dps * 0.25
                if self.vs_player:
                    p = game.player
                    if dist(self.pos, p.pos) <= self.radius + C.PLAYER_RADIUS:
                        p.damage(slice_dmg, game)
                else:
                    for e in game.enemies:
                        if e.hp > 0 and dist(e.pos, self.pos) <= self.radius + e.radius:
                            e.hit(slice_dmg, self.slow, self.slow_time)
        return True

    def draw(self, s, ox, oy):
        x, y = int(self.pos[0] + ox), int(self.pos[1] + oy)
        r = int(self.radius)
        if self.t < self.warn:
            k = self.t / self.warn
            pygame.draw.circle(s, fade(self.color, 0.15 + 0.55 * k), (x, y), r, 2)
            pygame.draw.circle(s, fade(self.color, 0.35 + 0.6 * k), (x, y), int(r * k))
        else:
            rem = (self.warn + self.life - self.t) / self.life
            pygame.draw.circle(s, fade(self.color, 0.35 * rem), (x, y), r)
            pygame.draw.circle(s, fade(self.color, 0.9), (x, y), r, 2)


class Chest:
    def __init__(self, pos):
        self.pos, self.hold, self.opened = pos, 0.0, False

    def update(self, dt, game):
        if dist(self.pos, game.player.pos) <= C.CHEST_RADIUS:
            self.hold += dt
            if self.hold >= C.CHEST_HOLD:
                self.opened = True
        return self.opened

    def draw(self, s, ox, oy):
        x, y = int(self.pos[0] + ox), int(self.pos[1] + oy)
        pygame.draw.ellipse(s, (54, 42, 31), (x - 17, y + 7, 34, 10))
        pygame.draw.circle(s, (94, 67, 34), (x, y), 19, 1)
        pygame.draw.rect(s, (112, 68, 38), (x - 12, y - 8, 24, 17))
        pygame.draw.rect(s, (70, 48, 34), (x - 12, y - 8, 24, 17), 2)
        pygame.draw.rect(s, (223, 170, 76), (x - 12, y - 11, 24, 7))
        pygame.draw.rect(s, (126, 83, 44), (x - 12, y - 5, 24, 4))
        pygame.draw.rect(s, (245, 202, 104), (x - 3, y - 10, 6, 18))
        pygame.draw.rect(s, (255, 236, 175), (x - 2, y - 5, 4, 5))
        pygame.draw.circle(s, (255, 230, 150), (x, y - 2), 2)
        if self.hold > 0:
            k = min(1.0, self.hold / C.CHEST_HOLD)
            pygame.draw.circle(s, (105, 78, 38), (x, y), 22, 1)
            pygame.draw.arc(s, C.C_EPIC, (x - 20, y - 28, 40, 40), math.pi / 2,
                            math.pi / 2 + k * TWO_PI, 3)
