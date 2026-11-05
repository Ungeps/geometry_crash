"""Arena: Survival - game loop, state machine, rendering, input. Run: python main.py"""
import os, random
import pygame
import config as C
import hud
import locale as L
import save
import ui
import waves
from menu import MenuMixin
from autopilot import FakeKeys, run as autopilot_run
from entities import Player, Enemy, TWO_PI, vec, move, dist, dist2, rand_around
from objects import Crystal, Particle, Fx, Zone
from sound import SoundPack
from weapons import Weapon
from hud import fmt_time
from upgrades import gen_cards, apply_card, grant_epic_passive

MOVEMENT = (pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s, pygame.K_LEFT, pygame.K_RIGHT,
            pygame.K_UP, pygame.K_DOWN)
def apply_event(game, ev, moving):
    """Key handling, kept as a function so headless checks can feed synthetic keys."""
    if ev.type != pygame.KEYDOWN:
        return
    k = ev.key
    if k == pygame.K_ESCAPE:
        if game.state == "play":
            game.state = "pause"
        elif game.state == "pause": 
            game.state = "play"
        elif game.state in ("controls", "records", "book"):
            game.state = "menu"
    elif k == pygame.K_m:
        game.sound.on = not game.sound.on
        game.banner(L.t("banner_sound", s=L.t("st_on") if game.sound.on else L.t("st_off")), 1.0)
    elif k == pygame.K_r:
        game.new_run()
    elif k == pygame.K_F11:
        game.toggle_fullscreen()
    elif k == pygame.K_SPACE:
        if game.state == "play":
            game.player.start_dash(game, moving)
    elif k == pygame.K_RETURN:
        if game.state == "menu":
            game.menu_act(game.menu_sel)
        elif game.state in ("controls", "records", "book"):
            game.state = "menu"
        elif game.state == "pause":
            game.state = "play"
        elif game.state in ("over", "win"):
            game.state = "menu"
    elif k in (pygame.K_UP, pygame.K_w) and game.state == "menu":
        game.menu_move(-1)
    elif k in (pygame.K_DOWN, pygame.K_s) and game.state == "menu":
        game.menu_move(1)
    elif k in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
        if game.state == "levelup":
            game.choose_card(k - pygame.K_1)


class Game(MenuMixin):
    def __init__(self, data, rng=None, autoplay=False, mode="wander"):
        self.rng = rng or random.Random()
        self.autoplay = autoplay
        self.autopilot_mode = mode if mode in ("kite", "pro", "elite", "circle", "lane") else "wander"
        self.data = data
        self.book = set(data["fusions"])
        self.new_fusions = []
        self.notes = []
        settings = save.load_settings()
        L.set_lang(settings["lang"])
        self.lang, self.fullscreen = settings["lang"], settings["fullscreen"]
        self.menu_sel, self.hover, self.quit = 0, None, False
        self.reset()
        self.state = "menu"
        self.sound = SoundPack()

    def reset(self):
        self.player = Player()
        self.player.rng = self.rng
        self.world_seed = self.rng.getrandbits(32)
        self.add_weapon("pistol", 1, False)
        self.enemies, self.projs, self.shots = [], [], []
        self.crystals, self.zones, self.chests, self.fx = [], [], [], []
        self.spawner = waves.Spawner()
        self.boss = None
        self.boss_dead = False
        self.time = 0.0
        self.wave = 1
        self.cards = []
        self.reason = ("", {})
        self.banner_text, self.banner_t = "", 0.0
        self.shake_mag, self.shake_t, self.ox, self.oy = 0.0, 0.0, 0.0, 0.0
        self.autopos, self.auto_timer = (1, 0), 0.0
        self.lane = (1.0, 0.0)

    def new_run(self):
        self.reset()
        self.new_fusions = []
        self.notes = []
        self.state = "play"
        self.banner(L.t("banner_start"), 2.5)

    def banner(self, text, dur=2.0):
        self.banner_text, self.banner_t = text, dur

    def shake(self, mag):
        self.shake_mag = min(14.0, max(self.shake_mag, mag))
        self.shake_t = 0.18

    def nearest(self, pos, max_d, exclude=None):
        ex = exclude or set()
        best, bd = None, max_d
        for e in self.enemies:
            if e.hp <= 0 or e in ex:
                continue
            d = dist(e.pos, pos)
            if d <= bd:
                bd, best = d, e
        return best

    def pick(self, pos, n, max_d, mode="near"):
        cand = [e for e in self.enemies if e.hp > 0 and dist(e.pos, pos) <= max_d]
        if not cand:
            return []
        cand.sort(key=lambda e: dist2(e.pos, pos), reverse=(mode == "far"))
        return cand[:n]

    def chain(self, pos, jumps, dmg, length, exclude=None, bolt=0.18):
        ex = set(exclude or ())
        for _ in range(jumps):
            t = self.nearest(pos, length, ex)
            if t is None:
                break
            ex.add(t)
            self.fx.append(Fx("line", pos, target=t.pos, life=bolt, color=(210, 225, 255), width=2))
            t.hit(dmg, 0, 0)
            pos = t.pos

    def explosion(self, pos, r, dmg, slow=0, slow_time=0):
        for e in self.enemies:
            if e.hp > 0 and dist(e.pos, pos) <= r + e.radius:
                e.hit(dmg, slow, slow_time)
        self.fx.append(Fx("flash", pos, r, life=0.2, color=(255, 210, 140)))
        self.fx.append(Fx("ring", pos, r, life=0.3, color=(255, 140, 70), width=2))

    def add_zone(self, pos, radius, dps, warn, life, vs_player, slow=0, slow_time=0, color=(255, 90, 40)):
        self.zones.append(Zone(pos, radius, dps, warn, life, vs_player, slow, slow_time, color))

    def add_weapon(self, kind, level=1, hybrid=False):
        self.player.weapons.append(Weapon(kind, level, hybrid))

    def spawn(self, etype, pos, wave, source="spawner"):
        self.enemies.append(Enemy(etype, pos, wave))

    def clear_field(self):
        """Field is dismantled for the boss duel: normal enemies and hazard zones go away."""
        for e in self.enemies:
            for _ in range(3):
                a = self.rng.uniform(0, TWO_PI)
                self.fx.append(Particle(e.pos, vec(a, self.rng.uniform(60, 160)), 0.45, e.color, 3))
        self.enemies = []
        self.zones = [z for z in self.zones if not z.vs_player]
        self.shake(10)

    def kill_enemy(self, e):
        self.player.kills += 1
        if e.etype == "boss":
            self.boss = None
            self.boss_dead = True
            for i in range(C.BOSS_XP):
                a = i * TWO_PI / C.BOSS_XP
                self.crystals.append(Crystal(move(e.pos, vec(a, 25 + i * 2), 1.0), 1))
            for _ in range(40):
                a = self.rng.uniform(0, TWO_PI)
                self.fx.append(Particle(e.pos, vec(a, self.rng.uniform(90, 320)), 0.6, e.color, 4))
            self.shake(14)
            self.banner(L.t("banner_boss_slain"), 4.0)
            self.notes.append(L.t("note_boss_killed", t=fmt_time(self.time)))
            self.sound.play("boss")
            return
        self.crystals.append(Crystal(e.pos, e.xp))
        for i in range(7):
            a = self.rng.uniform(0, TWO_PI)
            self.fx.append(Particle(e.pos, vec(a, self.rng.uniform(60, 200)), 0.35, e.color, 3))
        split = e.params.get("split")
        if split:
            for i in range(split):
                a = i * TWO_PI / split + self.rng.uniform(0, 1.0)
                self.spawn("mini", move(e.pos, vec(a, 18), 1.0), self.wave, "split")
        if e.etype in ("elite", "tank"):
            self.shake(4)
        self.sound.play("kill")

    def level_up(self):
        self.player.xp -= self.player.xp_next
        self.player.level += 1
        self.player.xp_next = C.XP_BASE + C.XP_STEP * self.player.level
        self.cards = gen_cards(self)
        self.state = "levelup"

    def choose_card(self, i):
        if not (0 <= i < len(self.cards)):
            return
        card = self.cards.pop(i)
        self.cards = []
        apply_card(self, card)
        self.state = "play"
        if self.player.xp >= self.player.xp_next:
            self.level_up()

    def end_run(self, result, key, win=False, **args):
        self.reason = (key, args)
        self.state = "win" if win else "over"
        entry = {"time": int(self.time), "kills": self.player.kills,
                 "level": self.player.level, "result": result}
        save.add_record(self.data, entry)
        save.add_fusions(self.data, self.new_fusions)
        save.write(self.data)

    def update(self, dt, keys):
        if self.banner_t > 0:
            self.banner_t = max(0.0, self.banner_t - dt)
        if self.shake_t > 0:
            self.shake_t = max(0.0, self.shake_t - dt)
            m = self.shake_mag * (self.shake_t / 0.18)
            self.ox, self.oy = self.rng.uniform(-m, m), self.rng.uniform(-m, m)
        else:
            self.shake_mag, self.ox, self.oy = 0.0, 0.0, 0.0
        if self.state != "play":
            return
        self.time += dt
        self.wave = int(self.time // C.WAVE_INTERVAL) + 1
        self.player.update(dt, self, keys)
        for w in self.player.weapons:
            w.update(dt, self)
        self.projs = [p for p in self.projs if p.update(dt, self)]
        self.shots = [s for s in self.shots if s.update(dt, self)]
        self._banner_boost()
        alive = []
        for e in self.enemies:
            e.update(dt, self)
            if e.hp > 0:
                alive.append(e)
            else:
                self.kill_enemy(e)
        self.enemies = alive
        for c in self.crystals:
            if c.update(dt, self):
                self.player.xp += c.xp
                self.sound.play("pickup")
        self.crystals = [c for c in self.crystals if not c.done]
        self.zones = [z for z in self.zones if z.update(dt, self)]
        self.fx = [f for f in self.fx if f.update(dt)]
        for ch in [ch for ch in self.chests if ch.update(dt, self)]:
            self.chests.remove(ch)
            name = grant_epic_passive(self)
            self.banner(L.t("banner_chest", name=name), 2.5)
            self.sound.play("chest")
        self.spawner.update(dt, self)
        if self.player.hp <= 0:
            self.end_run("died", "reason_died", w=self.wave, t=fmt_time(self.time))
        elif self.time >= C.WIN_TIME:
            if self.boss_dead:
                self.end_run("win", "", win=True)
            else:
                self.end_run("boss alive", "reason_boss_alive")
        if self.player.xp >= self.player.xp_next and self.state == "play":
            self.level_up()

    def _banner_boost(self):
        """Flag-bearers give neighbours +25% speed: the player chooses to kill them first."""
        banners = [e for e in self.enemies if e.etype == "banner"]
        for e in self.enemies:
            e.boost = 1.0
        for b in banners:
            r = b.params["boost_radius"]
            factor = 1.0 + b.params["boost"]
            for e in self.enemies:
                if e.hp > 0 and dist(e.pos, b.pos) <= r:
                    e.boost = factor

    def draw(self, s):
        if self.state == "menu":
            hud.draw_menu(self, s)
            return
        if self.state in ("controls", "records", "book"):
            pick_screen = {"controls": hud.draw_controls, "records": hud.draw_records,
                           "book": hud.draw_book}[self.state]
            pick_screen(self, s)
            return
        s.fill(C.C_BG)
        ox = C.WIDTH / 2.0 - self.player.pos[0] + self.ox
        oy = C.HEIGHT / 2.0 - self.player.pos[1] + self.oy
        hud.draw_field(s, ox, oy, self.world_seed)
        for z in self.zones:
            z.draw(s, ox, oy)
        for ch in self.chests:
            ch.draw(s, ox, oy)
        for w in self.player.weapons:
            w.draw(s, ox, oy, self.player)
        for c in self.crystals:
            c.draw(s, ox, oy)
        for e in self.enemies:
            e.draw(s, ox, oy)
        self.player.draw(s, ox, oy)
        for p in self.projs:
            p.draw(s, ox, oy)
        for sh in self.shots:
            sh.draw(s, ox, oy)
        for f in self.fx:
            f.draw(s, ox, oy)
        hud.draw_hud(self, s)
        hud.draw_minimap(self, s)
        hud.draw_banner(self, s)
        if self.state == "levelup":
            hud.draw_cards(self, s)
        elif self.state == "pause":
            hud.draw_pause(self, s)
        elif self.state in ("over", "win"):
            hud.draw_over(self, s)


def bot_enabled(auto):
    """The headless autopilot runs only when ARENA_AUTOPLAY is a mode; default "0" must NOT start it."""
    return auto not in ("0", "")


def set_display(fullscreen):
    size = (C.WIDTH, C.HEIGHT)
    flags = 0
    if fullscreen:
        modes = pygame.display.list_modes()
        if modes:
            size = modes[0]
        flags = pygame.FULLSCREEN
    pygame.display.set_mode(size, flags)
    pygame.display.set_caption(L.t("game_title"))


def main():
    frames = int(os.environ.get("ARENA_TEST_FRAMES", "0"))
    auto = os.environ.get("ARENA_AUTOPLAY", "0")
    forced_dt = float(os.environ.get("ARENA_DT", "0"))
    seed = os.environ.get("ARENA_SEED")
    rng = random.Random(int(seed)) if seed else None
    pygame.init()
    game = Game(save.load(), rng=rng, autoplay=bot_enabled(auto), mode=auto)
    set_display(game.fullscreen)
    scene = pygame.Surface((C.WIDTH, C.HEIGHT))
    clock = pygame.time.Clock()
    applied = game.fullscreen
    fps = []
    running = True
    while running:
        if forced_dt:
            dt = forced_dt
        else:
            dt = min(clock.tick(C.FPS) / 1000.0, 1 / 30.0)
        keys = pygame.key.get_pressed()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                moving = any(keys[k] for k in MOVEMENT)
                if ev.key == pygame.K_RETURN and (keys[pygame.K_LALT] or keys[pygame.K_RALT]):
                    game.toggle_fullscreen()
                else:
                    apply_event(game, ev, moving)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                surf = pygame.display.get_surface()
                vw = ui.view(surf.get_width(), surf.get_height(), C.WIDTH, C.HEIGHT)
                game.mouse_click(*ui.to_logical(ev.pos[0], ev.pos[1], vw))
        if game.fullscreen != applied:
            set_display(game.fullscreen)
            applied = game.fullscreen
        if bot_enabled(auto):
            autopilot_run(game, dt)
            keys = FakeKeys(game.autopos[0], game.autopos[1])
        surf = pygame.display.get_surface()
        vw = ui.view(surf.get_width(), surf.get_height(), C.WIDTH, C.HEIGHT)
        game.hover = ui.to_logical(*pygame.mouse.get_pos(), vw)
        game.update(dt, keys)
        game.draw(scene)
        ui.blit(surf, scene, vw)
        pygame.display.flip()
        if game.quit:
            running = False
        if frames:
            fps.append(clock.get_fps())
            frames -= 1
            if frames <= 0:
                avg = sum(fps) / len(fps) if fps else 0
                print("TEST RUN: time=%.1f state=%s kills=%d level=%d alive=%d links=%d "
                      "boss_dead=%s avg_fps=%.1f sound=%s"
                      % (game.time, game.state, game.player.kills, game.player.level,
                         len(game.enemies), len(game.new_fusions), game.boss_dead, avg, game.sound.ok))
                running = False
    pygame.quit()


if __name__ == "__main__":
    main()
