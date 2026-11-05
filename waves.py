"""Wave planner: spawn table, elite timer, fire zones, chest, boss spawn - the only event source."""
import config as C
from entities import rand_around, weighted, vec, move, TWO_PI
from objects import Chest

FIRE_COLOR = (255, 90, 40)


def pick_type(rng, wave):
    """Wave mix: crawler base weight decays, new enemy types join at their wave."""
    items = []
    for min_wave, etype, weight in C.WAVE_MIX:
        if wave >= min_wave:
            if etype == "crawler":
                weight = max(C.CRAWLER_MIN_WEIGHT, weight - C.CRAWLER_DECAY * (wave - min_wave))
            items.append((etype, weight))
    return weighted(rng, items)


def wave_limit(minute):
    return C.WAVE_LIMITS[min(minute, len(C.WAVE_LIMITS) - 1)]


class Spawner:
    def __init__(self):
        self.acc = 0.0
        self.zone_timer = C.ZONES_START
        self.chest_timer = C.CHEST_INTERVAL
        self.elite_timer = C.ELITE_TIME

    def update(self, dt, game):
        t = game.time
        wave = game.wave
        boss_fight = game.boss is not None
        # Normal spawn is stopped while the boss lives: the field is cleared for the duel.
        if not boss_fight:
            limit = wave_limit(int(t // 60))
            self.acc += dt * C.SPAWN_RATE
            self.acc = min(self.acc, 3.0)
            while self.acc >= 1.0 and len(game.enemies) < limit:
                self.acc -= 1.0
                pos = rand_around(game.rng, game.player.pos, 420, 520)
                game.spawn(pick_type(game.rng, wave), pos, wave)
        # Elite from minute 5, capped so it cannot drown the field.
        if t >= C.ELITE_TIME:
            self.elite_timer -= dt
            if self.elite_timer <= 0:
                self.elite_timer = C.ELITE_INTERVAL
                limit = wave_limit(int(t // 60))
                if sum(1 for e in game.enemies if e.etype == "elite") < C.ELITE_MAX and \
                        len(game.enemies) < limit:
                    game.spawn("elite", rand_around(game.rng, game.player.pos, 420, 520), wave)
        # Fire zones: telegraphed circles, 1-3 alive at a time, placed by this planner.
        if t >= C.ZONES_START and not boss_fight:
            self.zone_timer -= dt
            if self.zone_timer <= 0:
                self.zone_timer = game.rng.uniform(*C.ZONE_INTERVAL)
                live = sum(1 for z in game.zones if z.vs_player)
                n = min(game.rng.randint(C.ZONE_SPAWN_MIN, C.ZONE_SPAWN_MAX), C.ZONE_MAX - live)
                p = game.player
                for _ in range(n):
                    a = game.rng.uniform(0, TWO_PI)
                    o = game.rng.uniform(*C.ZONE_OFFSET)
                    pos = move(p.pos, vec(a, o), 1.0)
                    game.add_zone(pos, C.ZONE_RADIUS, C.ZONE_DPS, C.ZONE_WARN, C.ZONE_LIFE,
                                  True, 0, 0, FIRE_COLOR)
        # Chests appear in reachable world space near the player.
        self.chest_timer -= dt
        if self.chest_timer <= 0:
            self.chest_timer = C.CHEST_INTERVAL
            game.chests.append(Chest(rand_around(game.rng, game.player.pos, 150, 280)))
            game.banner("A CHEST APPEARED", 2.0)
        # Boss at minute 8 spawns just outside the camera view.
        if t >= C.BOSS_TIME and game.boss is None and not game.boss_dead:
            game.clear_field()
            game.spawn("boss", rand_around(game.rng, game.player.pos, 430, 500), wave)
            game.boss = game.enemies[-1]
            game.banner("THE BOSS ARRIVES", 3.0)
            game.sound.play("boss")
