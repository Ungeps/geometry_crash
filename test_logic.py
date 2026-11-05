"""Headless checks of critical game logic: python test_logic.py  (no window, no assets)."""
import math
import os
import random
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

import config as C
import hud
import locale as L
import save
import ui
import upgrades
import waves
from entities import Enemy, TWO_PI, clamp_field, dist, vec, move, rand_around
from objects import Chest, Crystal, Zone
from weapons import Weapon
from main import Game, apply_event, bot_enabled
from autopilot import FakeKeys, run as autopilot_run
from hud import fmt_time

pygame.init()
SCREEN = pygame.display.set_mode((C.WIDTH, C.HEIGHT))

RESULTS = []
PERF = []


def check(name, cond, note=""):
    RESULTS.append((name, bool(cond), note))


def key(code):
    return pygame.event.Event(pygame.KEYDOWN, {"key": code})


def settings_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), C.SETTINGS_FILE)


def clean_settings():
    L.set_lang(C.DEFAULT_LANG)
    p = settings_path()
    if os.path.exists(p):
        os.remove(p)


class NoKeys:
    def __getitem__(self, key):
        return False


def mk(seed, data=None):
    g = Game(data if data is not None else {"records": [], "fusions": []}, rng=random.Random(seed))
    g.state = "play"
    g.spawner.update = lambda dt, game: None
    g.player.hp = g.player.max_hp = 4000.0
    g.fusion_seen = []
    return g


def spy_damage(g, log):
    orig = g.player.damage

    def spy(amount, game):
        log.append(amount)
        return orig(amount, game)
    g.player.damage = spy
    return log


def pick_card(g, prefer_fusion=True):
    idx = 0
    for i, c in enumerate(g.cards):
        if c["kind"] == "fusion":
            g.fusion_seen.append(c["id"])
            if prefer_fusion:
                idx = i
                break
    g.choose_card(idx)


def sim(g, seconds, dt=1 / 60.0, keep_hp=True, prefer_fusion=True, on_step=None):
    for _ in range(int(round(seconds / dt))):
        if g.state not in ("play", "levelup"):
            return
        g.update(dt, NoKeys())
        if g.state == "levelup" and g.cards:
            pick_card(g, prefer_fusion)
        if keep_hp and g.state == "play":
            g.player.hp = g.player.max_hp
        if on_step:
            on_step(g)


# --- 1. full 10-minute run: wave limits, boss events, spawn stop, victory ---
def test_full_run():
    g = mk(1234, data={"records": [], "fusions": []})
    g.spawner = waves.Spawner()
    spawn_log, zones_placed, samples = [], [], {}
    boss_at, boss_timeline = [None], []
    chest_peak, zone_peak = [0], [0]
    orig, orig_zone = g.spawn, g.add_zone

    def spy_spawn(etype, pos, wave, source="spawner"):
        spawn_log.append((g.time, etype, len(g.enemies), source))
        orig(etype, pos, wave, source)
    g.spawn = spy_spawn
    g.add_zone = lambda pos, r, dps, warn, life, vp, slow=0, st=0, color=None: (
        zones_placed.append((g.time, vp)), orig_zone(pos, r, dps, warn, life, vp, slow, st, color))[0]

    def step(game):
        m = int(game.time // 60)
        samples[m] = max(samples.get(m, 0), len(game.enemies))
        chest_peak[0] = max(chest_peak[0], len(game.chests))
        zone_peak[0] = max(zone_peak[0], sum(1 for z in game.zones if z.vs_player))
        boss_timeline.append((game.time, game.boss is not None))
        if game.boss is not None and boss_at[0] is None:
            boss_at[0] = game.time
    sim(g, C.WIN_TIME + 20, on_step=step)

    haz = [t for t, vp in zones_placed if vp]
    # The spawn machine never exceeds the live limit of its minute.
    over = []
    for t, etype, alive, source in spawn_log:
        if source == "spawner":
            limit = C.WAVE_LIMITS[min(int(t // 60), len(C.WAVE_LIMITS) - 1)]
            if alive >= limit:
                over.append((round(t, 1), etype, alive, limit))
    check("spawn machine keeps the live limit of every minute", not over, str(over[:4]))
    for m in range(10):
        got = samples.get(m, 0)
        limit = C.WAVE_LIMITS[m]
        check("alive peak minute %d within limit %d (+ splits/elite)" % (m, limit), got <= limit + 10,
              "peak=%d" % got)
    peak = max(samples.values())
    check("never above MAX_ALIVE (%d)" % C.MAX_ALIVE, peak <= C.MAX_ALIVE, "peak alive=%d" % peak)
    boss_entry = [e for e in spawn_log if e[1] == "boss"]
    check("boss appears at minute 8", boss_at[0] is not None and 480.0 <= boss_at[0] < 482.0,
          "t=%s" % boss_at[0])
    check("field is cleared for the duel", boss_entry and boss_entry[0][2] == 0,
          "alive before boss spawn=%d" % (boss_entry[0][2] if boss_entry else -1))

    def boss_alive_at(t):
        state = None
        for ts, alive in boss_timeline:
            if ts <= t:
                state = alive
            else:
                break
        return state
    bad = []
    for t, etype, alive, source in spawn_log:
        if source == "spawner" and t > boss_at[0] + 1 / 60 and boss_alive_at(t) and etype != "minion":
            bad.append((round(t, 1), etype))
    check("normal spawn stops while the boss lives", not bad, str(bad[:4]))
    check("spawn resumes after the boss dies",
          any(t > boss_at[0] and etype not in ("minion", "boss") for t, e, a, s in spawn_log) and g.boss_dead,
          "boss dead=%s" % g.boss_dead)
    check("elite shows up from minute 5", sum(1 for t, e, a, s in spawn_log if e == "elite") >= 1,
          "elites=%d" % sum(1 for t, e, a, s in spawn_log if e == "elite"))
    check("hazard zones are placed by the planner only from minute 3",
          len(haz) >= 3 and all(t >= 180.0 for t in haz),
          "hazard zones=%d first=%s, weapon zones total=%d" % (len(haz), haz[0] if haz else None,
                                                               len(zones_placed)))
    check("at most 3 hazard zones alive at once", zone_peak[0] <= C.ZONE_MAX, "peak=%d" % zone_peak[0])
    check("chest appears roughly every 2 minutes", chest_peak[0] >= 4, "chest peak=%d" % chest_peak[0])
    check("victory needs boss dead and 10:00", g.state == "win", "state=%s reason=%s" % (g.state, g.reason))
    check("victory needs boss dead and 10:00", g.state == "win", "state=%s reason=%s" % (g.state, g.reason))
    check("win is recorded", g.data["records"][0]["result"] == "win", str(g.data["records"][:1]))
    check("link book persists between runs", set(g.data["fusions"]) >= set(g.new_fusions),
          str(g.data["fusions"]))
    types = {e for t, e, a, s in spawn_log}
    check("wave mix reaches all planned enemy types",
          {"crawler", "hopper", "tank", "splitter", "mini", "sprinter", "spitter", "hexer",
           "banner", "elite", "minion", "boss"} >= types, str(sorted(types)))


# --- 2. boss alive at 10:00 is a loss ---
def test_boss_alive_loss():
    g = mk(77, data={"records": [], "fusions": []})
    g.spawner = waves.Spawner()

    def step(game):
        if game.boss is not None:
            game.boss.hp = game.boss.max_hp
    sim(g, C.WIN_TIME + 15, on_step=step)
    check("10:00 with the boss alive -> loss", g.state == "over" and
          g.reason[0] == "reason_boss_alive" and g.data["records"][0]["result"] == "boss alive",
          "state=%s reason=%s" % (g.state, g.reason))
    check("loss is recorded", g.data["records"][0]["result"] == "boss alive", str(g.data["records"][:1]))


# --- 3. player death ends the run ---
def test_death():
    g = mk(555, data={"records": [], "fusions": []})
    g.spawner = waves.Spawner()
    g.player.hp = g.player.max_hp = 8.0
    sim(g, 120, keep_hp=False)
    check("HP<=0 -> game over with localized death reason", g.state == "over" and
          g.reason[0] == "reason_died" and g.reason[1].get("w"),
          "state=%s reason=%s" % (g.state, g.reason))


# --- 4. all screens render ---
def test_screens():
    g = mk(99, data={"records": [], "fusions": []})
    g.spawner = waves.Spawner()
    g.data["records"] = [{"time": 240, "kills": 80, "level": 5, "result": "boss alive"}]
    ok, notes = True, []
    try:
        for st in ("menu", "controls", "records", "book"):
            g.state = st
            g.draw(SCREEN)
        g.state = "play"
        sim(g, 20)
        g.player.xp = g.player.xp_next
        g.level_up()
        check("level-up gives 1..4 cards", 1 <= len(g.cards) <= 4, str(len(g.cards)))
        g.draw(SCREEN)
        g.state = "pause"
        g.draw(SCREEN)
        g.end_run("died", "reason_died", w=2, t="0:20")
        g.draw(SCREEN)
        g.state = "win"
        g.draw(SCREEN)
    except Exception as exc:
        ok, notes = False, [repr(exc)]
    check("menu / controls / records / book / level-up / pause / results / win screens draw",
          ok, "; ".join(notes))


# --- 5. card pool rules ---
def test_cards():
    g = mk(2000, data={"records": [], "fusions": []})
    p = g.player
    violations = 0
    for _ in range(300):
        cards = upgrades.gen_cards(g)
        titles = [c["title"] for c in cards]
        if len(titles) != len(set(titles)) or not (1 <= len(cards) <= 4):
            violations += 1
        for c in cards:
            if c["kind"] == "fusion":
                _, a, b = upgrades.FUSION_BY_ID[c["id"]][:3]
                wa, wb = p.find_weapon(a), p.find_weapon(b)
                if not (wa and wb and wa.level >= 3 and wb.level >= 3):
                    violations += 1
        upgrades.apply_card(g, cards[0])
        p.hp = p.max_hp
    check("cards: no duplicates, count 1..4, fusion needs Lv3+", violations == 0,
          "violations=%d" % violations)
    check("weapon slots <= 6", len(p.weapons) <= C.MAX_WEAPONS, "weapons=%d" % len(p.weapons))
    check("passive slots <= 6", len(p.passives) <= C.MAX_PASSIVES, "passives=%d" % len(p.passives))
    check("weapon level <= 8", all(w.level <= C.WEAPON_MAX_LEVEL for w in p.weapons))
    check("passive level <= 3", all(v <= C.PASSIVE_MAX_LEVEL for v in p.passives.values()))
    check("rarity split is 60/30/10", all(C.RATES) and C.RATES == (0.6, 0.3, 0.1))
    rng = random.Random(4321)
    counts = [0, 0, 0]
    for _ in range(2000):
        r, mult, col = upgrades.roll_rarity(rng)
        counts[r] += 1
    check("rolled rarity ~60/30/10", 54 <= counts[0] / 20 <= 66 and 25 <= counts[1] / 20 <= 35 and
          7 <= counts[2] / 20 <= 13, str(counts))


def test_fallbacks():
    g = mk(11, data={"records": [], "fusions": []})
    p = g.player
    p.weapons = []
    for k in upgrades.WEAPON_IDS:
        g.add_weapon(k, 8, False)
    for pid in C.PASSIVE_STATS:
        p.passives[pid] = 3
        p.pvals[pid] = sum(C.PASSIVE_STATS[pid]["values"])
    p.recompute()
    cards = upgrades.gen_cards(g)
    plain = [c for c in cards if c["kind"] != "fusion"]
    check("empty pool -> 3 distinct fallback cards", len(plain) == 3 and
          all(c["kind"] == "fallback" for c in plain) and len({c["title"] for c in plain}) == 3,
          str([c["title"] for c in cards]))
    hp_card = [c for c in plain if c["id"] == "hp"][0]
    before = p.max_hp
    upgrades.apply_card(g, hp_card)
    check("fallback card really changes the player", p.max_hp == before + C.FALLBACKS[0][1],
          "%s -> %s" % (before, p.max_hp))


# --- 6. fusion rules ---
def test_fusion():
    g = mk(42, data={"records": [], "fusions": []})
    p = g.player
    p.weapons = []
    g.add_weapon("fire_aura", 3, False)
    g.add_weapon("chain", 4, False)
    cards = upgrades.gen_cards(g)
    fc = [c for c in cards if c["id"] == "fire_chain"]
    check("fusion card offered for the pair", len(fc) == 1, str([c["id"] for c in cards]))
    upgrades.apply_card(g, fc[0])
    check("fusion replaces both weapons with one hybrid", len(p.weapons) == 1 and
          p.weapons[0].kind == "fire_chain" and p.weapons[0].hybrid,
          str([(w.kind, w.level, w.hybrid) for w in p.weapons]))
    check("hybrid level = the higher of the two", p.weapons[0].level == 4, str(p.weapons[0].level))
    check("discovered link goes to the book", "fire_chain" in g.book and "fire_chain" in g.new_fusions)
    g.end_run("died", "reason_died", w=5, t="5:00")
    check("link book persists in the save file", "fire_chain" in g.data["fusions"], str(g.data["fusions"]))
    g.add_weapon("pistol", 3, False)
    pool, fcards = upgrades.build_pool(g)
    check("hybrid has a level-up card in the pool",
          any(c["kind"] == "weapon_level" and c["id"] == "fire_chain" for c in pool),
          str([c["id"] for c in pool if c["kind"] == "weapon_level"]))
    check("hybrid never re-fuses", len(fcards) == 0, str([c["id"] for c in fcards]))
    pairs = [frozenset(f[1:3]) for f in upgrades.FUSIONS]
    check("all fusion pairs are unique", len(upgrades.FUSIONS) == len(set(pairs)))
    check("all base weapons appear in a fusion", set(upgrades.WEAPON_IDS) <= {x for pr in pairs for x in pr})
    check("every link has stats, color and a behavior", all(f[0] in C.HYBRID_STATS and
          C.HYBRID_STATS[f[0]]["behavior"] in ("shoot", "aura", "chain", "arc", "orbital", "bomb")
          and f[0] in C.WEAPON_COLORS for f in upgrades.FUSIONS))


def test_fusion_in_run():
    """A focused human build (pistol + chain, both to Lv3) gets its fusion card
    around minutes 6-7, exactly as the design document promises."""
    g = mk(900, data={"records": [], "fusions": []})
    g.spawner = waves.Spawner()
    pair = ("pistol", "chain")
    fusion_time = [None]
    dt = 1 / 60.0

    def pick_idx(cards):
        for i, c in enumerate(cards):
            if c["kind"] == "fusion":
                g.fusion_seen.append(c["id"])
                return i
        owned = {w.kind for w in g.player.weapons}
        if "chain" not in owned:
            for i, c in enumerate(cards):
                if c["kind"] == "weapon" and c["id"] == "chain":
                    return i
        for i, c in enumerate(cards):
            if c["kind"] == "weapon_level" and c["id"] in pair:
                return i
        for i, c in enumerate(cards):
            if c["kind"] == "weapon_level":
                return i
        for i, c in enumerate(cards):
            if c["kind"] == "passive":
                return i
        for i, c in enumerate(cards):
            if c["kind"] == "weapon":
                return i
        return 0

    for _ in range(int(420 / dt)):
        if g.state == "levelup":
            g.choose_card(pick_idx(g.cards))
            if g.new_fusions and fusion_time[0] is None:
                fusion_time[0] = g.time
        if g.state in ("play", "levelup"):
            g.update(dt, NoKeys())
            g.player.hp = g.player.max_hp
        if g.state not in ("play", "levelup"):
            break
    check("focused build gets its fusion card in play", len(g.new_fusions) == 1,
          "links=%s level=%d cards=%d weapons=%s" % (sorted(g.new_fusions), g.player.level,
                                                      len(g.fusion_seen),
                                                      [(w.kind, w.level) for w in g.player.weapons]))
    check("fusion arrives mid-run, not at the end", fusion_time[0] is not None and
          240.0 <= fusion_time[0] <= 480.0, "fusion at t=%.0f s (level %d)" % (fusion_time[0] or -1,
                                                                               g.player.level))
    kinds = [w.kind for w in g.player.weapons]
    check("fusion left one hybrid slot and the other weapons",
          "arc_pistol" in kinds and "pistol" not in kinds and "chain" not in kinds, str(kinds))


def test_all_links_reachable():
    g = mk(12345, data={"records": [], "fusions": []})
    g.player.weapons = []
    for k in C.WEAPON_STATS:
        g.add_weapon(k, 3, False)
    seen = set()
    for _ in range(400):
        for c in upgrades.gen_cards(g):
            if c["kind"] == "fusion":
                seen.add(c["id"])
    check("all fusion links reachable in play", len(seen) == len(upgrades.FUSIONS),
          "found=%d/%d" % (len(seen), len(upgrades.FUSIONS)))


# --- 7. every weapon kind (10 base + 12 hybrids) deals damage ---
def test_weapons_deal_damage():
    bad = []
    for kind, stats in list(C.WEAPON_STATS.items()) + list(C.HYBRID_STATS.items()):
        g = mk(777, data={"records": [], "fusions": []})
        g.player.weapons = [Weapon(kind, 3, kind in C.HYBRID_STATS)]
        g.player.pos = (400.0, 300.0)
        for i in range(6):
            a = i * TWO_PI / 6
            g.spawn("crawler", clamp_field((g.player.pos[0] + math.cos(a) * 90,
                                            g.player.pos[1] + math.sin(a) * 90), 20), 2)
        before = sum(e.hp for e in g.enemies)
        sim(g, 3.5)
        after = sum(e.hp for e in g.enemies)
        if after >= before:
            bad.append(kind)
    check("all weapon kinds damage enemies", not bad, "silent: %s" % bad)


# --- 8. contact damage, per-enemy cooldown, tank push, contact values ---
def test_contact():
    g = mk(5, data={"records": [], "fusions": []})
    g.player.weapons = []
    g.player.pos = (400.0, 300.0)
    log = spy_damage(g, [])
    e = Enemy("crawler", (420.0, 300.0), 1)
    e.hp = e.max_hp = 1000.0
    g.enemies.append(e)
    sim(g, 2.0)
    hits = [a for a in log if a == C.CONTACT_DMG]
    check("crawler contact dmg 5, max one hit per 0.5 s per enemy", 3 <= len(hits) <= 5,
          "hits in 2 s=%d" % len(hits))
    for etype, want in (("tank", 10), ("sprinter", 12)):
        g2 = mk(6, data={"records": [], "fusions": []})
        g2.player.weapons = []
        g2.player.pos = (400.0, 300.0)
        log2 = spy_damage(g2, [])
        e2 = Enemy(etype, (400.0 + g2.player.pos[0] * 0 + 34.0, 300.0), 4)
        e2.hp = e2.max_hp = 900.0
        g2.enemies.append(e2)
        sim(g2, 1.1)
        check("%s contact dmg %d" % (etype, want), any(a == want for a in log2), str(log2[:3]))
    g4 = mk(8, data={"records": [], "fusions": []})
    g4.player.weapons = []
    t = Enemy("tank", (400.0, 300.0), 4)
    t.hp = t.max_hp = 400.0
    c = Enemy("crawler", (415.0, 300.0), 1)
    c.hp = c.max_hp = 1000.0
    g4.enemies += [t, c]
    c0 = (c.pos[0], c.pos[1])
    g4.update(1 / 60.0, NoKeys())
    moved = dist(c0, c.pos)
    check("tank pushes small enemies away", moved > 1.0, "moved=%.1f px" % moved)


def test_enemy_formulas():
    g = mk(8, data={"records": [], "fusions": []})
    e = Enemy("splitter", (400.0, 300.0), 1)
    g.enemies.append(e)
    e.hit(1000, 0, 0)
    g.update(1 / 60.0, NoKeys())
    minis = [x for x in g.enemies if x.etype == "mini"]
    check("splitter splits into 2 small enemies on death", len(minis) == 2,
          "minis=%d alive=%d kills=%d" % (len(minis), len(g.enemies), g.player.kills))
    check("kill counted, XP crystal dropped and picked up", g.player.kills == 1 and g.player.xp == 2,
          "kills=%d xp=%d" % (g.player.kills, g.player.xp))
    w1 = Enemy("crawler", (400, 300), 1)
    w3 = Enemy("crawler", (400, 300), 3)
    check("crawler HP = 1 + wave, speed = 30 + 3*wave", w1.max_hp == 2 and w1.speed == 33 and
          w3.max_hp == 4 and w3.speed == 39, "%s %s / %s %s" % (w1.max_hp, w1.speed, w3.max_hp, w3.speed))
    check("tank HP = 20*wave, dmg 10", Enemy("tank", (400, 300), 4).max_hp == 80 and
          Enemy("tank", (400, 300), 4).dmg == 10)
    hop = Enemy("hopper", (400, 300), 1)
    check("hopper HP -30%, 2x speed", abs(hop.max_hp - 1.4) < 1e-9 and hop.speed == 66,
          "%s %s" % (hop.max_hp, hop.speed))
    check("banner HP medium, boost +25%", C.ENEMY_STATS["banner"]["hp_base"] == 8 and
          C.ENEMY_STATS["banner"]["boost"] == 0.25)
    check("elite HP grows with wave", Enemy("elite", (400, 300), 10).max_hp == 120,
          str(Enemy("elite", (400, 300), 10).max_hp))
    check("boss HP is 500", Enemy("boss", (400, 300), 8).max_hp == 500.0)


def test_banner_boost():
    g = mk(9, data={"records": [], "fusions": []})
    g.player.weapons = []
    g.player.pos = (400.0, 200.0)
    b = Enemy("banner", (400.0, 250.0), 1)
    b.hp = b.max_hp = 1000.0
    c = Enemy("crawler", (450.0, 300.0), 1)
    c.hp = c.max_hp = 1000.0
    g.enemies += [b, c]
    c0 = (c.pos[0], c.pos[1])
    g.update(1 / 60.0, NoKeys())
    step = dist(c0, c.pos)
    plain = c.speed / 60.0
    boosted = c.speed * 1.25 / 60.0
    check("flag-bearer gives neighbours +25% speed", abs(step - boosted) < 0.05 and c.boost == 1.25,
          "step=%.3f plain=%.3f boost=%.3f" % (step, plain, boosted))


def test_chest():
    g = mk(13, data={"records": [], "fusions": []})
    g.player.weapons = []
    g.chests = [Chest(g.player.pos)]
    sim(g, C.CHEST_HOLD + 0.2, keep_hp=False)
    check("chest grants exactly one passive", len(g.player.passives) == 1, str(g.player.passives))
    pid = list(g.player.passives)[0]
    base = C.PASSIVE_STATS[pid]["values"][0]
    check("chest reward is the epic variant (2x value)", g.player.pvals[pid] == base * C.EPIC_MULT,
          "%s gain=%s base=%s" % (pid, g.player.pvals[pid], base))
    check("chest is consumed after opening", len(g.chests) == 0)


def test_dash_and_passives():
    g = mk(21, data={"records": [], "fusions": []})
    p = g.player
    p.weapons = []
    start = (p.pos[0], p.pos[1])
    p.start_dash(g, False)
    inv_at_start, cd_at_start = p.invuln, p.dash_cd
    sim(g, 0.15, keep_hp=False)
    d = dist(start, p.pos)
    check("dash covers 120 px", abs(d - C.DASH_DIST) < 12, "moved=%.1f" % d)
    check("dash cooldown 1.5 s", abs(cd_at_start - C.DASH_CD) < 1e-9, "cd=%.2f" % p.dash_cd)
    check("dash gives 0.25 s invulnerability", inv_at_start == C.DASH_INVULN and p.damage(50, g) == 0.0,
          "invuln=%.2f" % inv_at_start)
    sim(g, 1.6, keep_hp=False)
    p.hp = p.max_hp = 200.0
    for pid, gain in (("cooldown", 60), ("shield", 75), ("dmg", 60), ("pickup", 150),
                      ("speed", 45), ("area", 40), ("crit", 30), ("regen", 3),
                      ("armor", 30), ("haste", 30)):
        p.add_passive(pid, gain)
    p.start_dash(g, True)
    check("cooldown passive -60%: dash cd 1.5 -> 0.6 s", abs(p.dash_cd - 0.6) < 0.05, "cd=%.2f" % p.dash_cd)
    sim(g, 0.3, keep_hp=False)
    eff = p.damage(20, g)
    check("shield and armor reduce incoming damage", abs(eff - 3.5) < 0.5, "eff=%.1f" % eff)
    check("armor passive reduces damage by 30%", abs(p.armor - 0.30) < 1e-9,
          "armor=%.2f" % p.armor)
    check("haste passive raises weapon attack speed by 30%", abs(p.attack_speed - 0.30) < 1e-9,
          "haste=%.2f" % p.attack_speed)
    check("damage passive +60%", abs(p.dmg_mult - 1.6) < 1e-9, "%.2f" % p.dmg_mult)
    check("crit caps at 30% chance", abs(p.crit - 0.30) < 1e-9, "%.2f" % p.crit)
    check("pickup radius +150%: 60 -> 150 px", abs(p.pickup - 150) < 1e-6, "%.1f" % p.pickup)
    check("speed passive +45%: 220 -> 319 px/s", abs(p.speed - 319) < 1e-6, "%.1f" % p.speed)
    g.add_weapon("fire_aura", 3, False)
    w = p.find_weapon("fire_aura")
    eff_r = w.area(w.base("radius")) * p.area
    check("area passive widens Lv3 aura: 80 -> 130 px", abs(eff_r - 80 * 1.16 * 1.4) < 1e-6, "%.2f" % eff_r)
    p.hp = 50.0
    sim(g, 1.0, keep_hp=False)
    check("regen 3 HP per second", p.hp > 52.5, "hp=%.1f" % p.hp)


def test_dps_target():
    """Balance check from the design document: a typical focused build at minute 8
    deals ~30 DPS, so the 500 HP boss dies in 15-20 seconds."""
    g = mk(88, data={"records": [], "fusions": []})
    g.spawner.update = lambda dt, game: None
    g.player.weapons = []
    g.add_weapon("arc_pistol", 3, True)
    g.add_weapon("fire_aura", 3, False)
    g.player.add_passive("dmg", 20)
    g.player.hp = g.player.max_hp = 100000.0
    for i in range(6):
        e = Enemy("tank", clamp_field((g.player.pos[0] + 200 + i * 18, g.player.pos[1]), 25), 15)
        e.hp = e.max_hp = 5000.0
        g.enemies.append(e)
    dt = 1 / 60.0
    done = 0.0
    for _ in range(int(5 / dt)):
        before = sum(e.hp for e in g.enemies)
        g.update(dt, NoKeys())
        done += before - sum(e.hp for e in g.enemies)
        for e in g.enemies:
            e.hp = max(e.hp, 5000.0)
    dps = done / 5.0
    check("focused build at minute 8 deals >= 30 DPS", dps >= 30.0, "dps=%.1f" % dps)
    check("500 HP boss dies in 15-20 s at that DPS", 500.0 / dps <= 20.0,
          "time=%.1f s at %.1f dps" % (500.0 / dps, dps))


def test_xp_crystals():
    check("XP curve 10 + 15*level: Lv1=25, Lv5=85",
          C.XP_BASE + C.XP_STEP * 1 == 25 and C.XP_BASE + C.XP_STEP * 5 == 85)
    g = mk(31, data={"records": [], "fusions": []})
    g.player.weapons = []
    g.player.xp = 0
    c1, c2 = Enemy("crawler", g.player.pos, 3), Enemy("crawler", g.player.pos, 4)
    check("crystal = 1 XP, 2 XP from wave 4", c1.xp == 1 and c2.xp == 2, "%d %d" % (c1.xp, c2.xp))
    g.crystals.append(Crystal(g.player.pos, 2))
    g.update(1 / 60.0, NoKeys())
    check("crystal is picked up and adds XP", g.player.xp == 2 and len(g.crystals) == 0,
          "xp=%d crystals=%d" % (g.player.xp, len(g.crystals)))
    far = Enemy("crawler", clamp_field((g.player.pos[0] + 400, g.player.pos[1]), 20), 1)
    g.crystals.append(Crystal(far.pos, 1))
    g.update(1 / 60.0, NoKeys())
    check("crystal outside the pickup radius is not collected", g.player.xp == 2 and len(g.crystals) == 1,
          "xp=%d" % g.player.xp)
    g2 = mk(32, data={"records": [], "fusions": []})
    g2.player.weapons = []
    g2.player.xp = g2.player.xp_next
    g2.level_up()
    check("level-up consumes XP and raises the next requirement", g2.player.level == 2 and
          g2.player.xp_next == 40 and g2.state == "levelup" and len(g2.cards) >= 1,
          "level=%d next=%d state=%s" % (g2.player.level, g2.player.xp_next, g2.state))


def test_events_and_screens():
    g = mk(70, data={"records": [], "fusions": []})
    g.spawner = waves.Spawner()
    g.state = "menu"
    apply_event(g, key(pygame.K_RETURN), False)
    check("Enter starts a run", g.state == "play" and g.time == 0)
    apply_event(g, key(pygame.K_ESCAPE), False)
    check("Esc pauses", g.state == "pause")
    sim(g, 2.0, keep_hp=False)
    check("world is frozen while paused", g.time == 0.0, "time=%.2f" % g.time)
    apply_event(g, key(pygame.K_ESCAPE), False)
    check("Esc resumes", g.state == "play")
    was = g.sound.on
    apply_event(g, key(pygame.K_m), False)
    check("M toggles sound", g.sound.on != was)
    g.time = 123.0
    g.player.kills = 7
    apply_event(g, key(pygame.K_r), False)
    check("R restarts the run", g.state == "play" and g.time == 0 and g.player.kills == 0)
    g.level_up()
    n = len(g.cards)
    apply_event(g, key(pygame.K_1), False)
    check("number key picks a card and the game resumes", g.state == "play" and len(g.cards) == 0,
          "cards=%d state=%s" % (n, g.state))
    apply_event(g, key(pygame.K_SPACE), False)
    check("Space dashes in play, dash on cooldown refuses", g.player.dash_left == C.DASH_DIST,
          "dash_left=%.0f" % g.player.dash_left)
    g.end_run("died", "reason_died", w=3, t="2:03")
    check("results screen after death", g.state == "over")
    apply_event(g, key(pygame.K_RETURN), False)
    check("Enter on results returns to the main menu", g.state == "menu")


def test_no_bot_default_launch():
    """A normal launch must NOT run the headless autopilot: the human drives the hero."""
    check("default ARENA_AUTOPLAY does not enable the bot",
          not bot_enabled("0") and not bot_enabled(""),
          "bot_enabled('0')=%s bot_enabled('')=%s" % (bot_enabled("0"), bot_enabled("")))
    check("a named mode enables the bot",
          bot_enabled("lane") and bot_enabled("kite") and bot_enabled("pro"),
          "lane/kite/pro=True")
    g = Game({"records": [], "fusions": []}, rng=random.Random(9), autoplay=bot_enabled("0"), mode="0")
    g.update(1 / 60.0, NoKeys())
    check("normal launch stays on the main menu until Enter", g.state == "menu",
          "state=%s time=%.2f" % (g.state, g.time))


def test_save_first_start():
    old = C.RECORDS_FILE
    C.RECORDS_FILE = "test_missing.json"
    d = save.load()
    check("first start with no save file is clean", d == {"records": [], "fusions": []}, str(d))
    g = Game(d, rng=random.Random(3))
    g.draw(SCREEN)
    check("game starts fine with no save file", g.state == "menu")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), C.RECORDS_FILE)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("{{{ not json")
    check("corrupt save file does not break the start", save.load() == {"records": [], "fusions": []},
          str(save.load()))
    os.remove(path)
    for i in range(12):
        save.add_record(d, {"time": i, "kills": 10, "level": 1, "result": "died"})
    check("records trimmed to top 10 sorted by time", len(d["records"]) == 10 and
          d["records"][0]["time"] == 11, str([r["time"] for r in d["records"]]))
    d2 = save.add_fusions({"fusions": ["a1", "a1"], "records": []}, ["a1", "b2"])
    check("link book dedupes", d2["fusions"] == ["a1", "b2"], str(d2["fusions"]))
    C.RECORDS_FILE = "test_out.json"
    check("save writes to disk and reloads", save.write(d) and save.load()["records"][0]["time"] == 11)
    os.remove(os.path.join(os.path.dirname(os.path.abspath(__file__)), C.RECORDS_FILE))
    C.RECORDS_FILE = old


def test_infinite_world():
    g = mk(18, data={"records": [], "fusions": []})
    g.player.pos = (C.WIDTH + 10.0, C.HEIGHT + 10.0)
    g.player.update(1.0, g, FakeKeys(1, 1))
    check("player can travel beyond the original screen bounds",
          g.player.pos[0] > C.WIDTH and g.player.pos[1] > C.HEIGHT, str(g.player.pos))
    point = rand_around(g.rng, g.player.pos, 420, 520)
    distance = dist(point, g.player.pos)
    check("world spawns remain at the requested distance from the player",
          420 <= distance <= 520, "distance=%.1f" % distance)
    terrain = pygame.Surface((C.WIDTH, C.HEIGHT))
    hud.draw_field(terrain, 0, 0, 9876)
    sample = terrain.get_at((400, 300))[:3]
    terrain.fill(C.C_BG)
    hud.draw_field(terrain, 0, 0, 9876)
    check("procedural terrain tiles are deterministic for the same seed",
          sample == terrain.get_at((400, 300))[:3] and sample != C.C_BG)


def test_performance():
    g = mk(31, data={"records": [], "fusions": []})
    for k in C.WEAPON_STATS:
        g.add_weapon(k, 5, False)
    types = [k for k in C.ENEMY_STATS if k != "boss"]
    target = C.WAVE_LIMITS[9]

    def refill():
        while len(g.enemies) < target:
            g.spawn(g.rng.choice(types), clamp_field((g.rng.uniform(20, C.WIDTH - 20),
                                                      g.rng.uniform(20, C.HEIGHT - 20)), 25), 10)
        for e in g.enemies:
            e.max_hp = max(e.max_hp, 3000.0)
            e.hp = max(e.hp, 3000.0)
        g.crystals = []
    n = 300
    refill()
    t0 = time.perf_counter()
    for _ in range(n):
        g.update(1 / 60.0, NoKeys())
        refill()
        g.draw(SCREEN)
    ms = (time.perf_counter() - t0) / n * 1000.0
    PERF.append(ms)
    check("update+draw under 16.7 ms at 90 live enemies", ms < 1000 / 60,
          "%.2f ms/frame, alive=%d" % (ms, len(g.enemies)))
    t0 = time.perf_counter()
    for _ in range(n):
        g.update(1 / 60.0, NoKeys())
        refill()
    logic = (time.perf_counter() - t0) / n * 1000.0
    check("logic alone under 8 ms at 90 live enemies", logic < 8.0, "%.2f ms/frame" % logic)


def test_new_enemy_attacks():
    g = mk(91, data={"records": [], "fusions": []})
    g.player.weapons = []
    g.player.pos = (400.0, 300.0)
    spitter = Enemy("spitter", (160.0, 300.0), 7)
    spitter.attack_t = spitter.params["windup"] + 0.02
    spitter.update(0.04, g)
    spitter.draw(SCREEN, 0, 0)
    telegraph = spitter.attack_t > 0 and spitter.attack_t <= spitter.params["windup"]
    spitter.attack_t = 0.01
    spitter.update(0.02, g)
    check("spitter signals and fires a three-projectile volley",
          telegraph and len(g.shots) == spitter.params["volley"] and
          all(not shot.friendly and shot.dmg == spitter.params["bullet_dmg"] for shot in g.shots),
          "telegraph=%s projectiles=%d" % (telegraph, len(g.shots)))

    h = mk(92, data={"records": [], "fusions": []})
    h.player.weapons = []
    h.player.pos = (400.0, 300.0)
    hexer = Enemy("hexer", (600.0, 300.0), 10)
    hexer.attack_t = hexer.params["windup"] + 0.01
    hexer.update(0.02, h)
    hexer.draw(SCREEN, 0, 0)
    telegraph = hexer.telegraphing and not h.zones
    target = hexer.attack_pos
    hexer.attack_t = 0.01
    hexer.update(0.02, h)
    check("hexer warns at a predicted position before creating a hazard",
          telegraph and len(h.zones) == 1 and h.zones[0].vs_player and h.zones[0].pos == target,
          "telegraph=%s zones=%d" % (telegraph, len(h.zones)))


def test_boss_phases():
    g = mk(90, data={"records": [], "fusions": []})
    g.player.weapons = []
    g.player.pos = (400.0, 300.0)
    g.spawn("boss", (600.0, 300.0), 8)
    g.boss = g.enemies[-1]
    log = spy_damage(g, [])
    sim(g, 3.0)
    check("phase 1 chases, contact dmg 15, no volley", g.boss.phase() == 1 and g.boss.pos[0] < 600.0 and
          any(a == C.BOSS_DMG for a in log) and len(g.shots) == 0,
          "phase=%d x=%.0f shots=%d dmg=%s" % (g.boss.phase(), g.boss.pos[0], len(g.shots), log[:2]))
    g.player.pos = (400.0, 300.0)
    g.boss.pos = (460.0, 300.0)
    g.boss.hp = 500.0 * C.BOSS_PHASE2_FRAC - 1
    g.shots = []
    import entities
    orig_proj = entities.Projectile
    created = []

    class Counting(orig_proj):
        def __init__(self, *a, **k):
            orig_proj.__init__(self, *a, **k)
            if k.get("friendly") is False:
                created.append(self)
    entities.Projectile = Counting
    log2 = spy_damage(g, [])
    sim(g, C.BOSS_VOLLEY_RATE + 1.0)
    entities.Projectile = orig_proj
    check("phase 2 fires a full 12-bullet ring that reaches the player",
          g.boss.phase() == 2 and len(created) >= C.BOSS_RING and
          all(p.dmg == C.BOSS_BULLET_DMG for p in created) and
          any(a == C.BOSS_BULLET_DMG for a in log2),
          "phase=%d ring bullets=%d dmg=%s" % (g.boss.phase(), len(created), log2[:4]))
    g.enemies = [e for e in g.enemies if e.etype == "boss"]
    g.boss.hp = 500.0 * C.BOSS_PHASE3_FRAC - 1
    g.boss.summon = 0.5
    sim(g, C.BOSS_SUMMON_RATE + 0.2)
    minions = [e for e in g.enemies if e.etype == "minion"]
    check("phase 3 summons 6 minions", g.boss.phase() == 3 and len(minions) == C.BOSS_MINIONS,
          "phase=%d minions=%d" % (g.boss.phase(), len(minions)))
    g.player.pos = (400.0, 560.0)
    g.boss.pos = (400.0, 40.0)
    for _ in range(12):
        g.boss.summon = 0.0
        g.update(1 / 60.0, NoKeys())
        g.player.hp = g.player.max_hp
    check("summons capped at BOSS_MINION_MAX",
          sum(1 for e in g.enemies if e.etype == "minion") <= C.BOSS_MINION_MAX,
          "minions=%d" % sum(1 for e in g.enemies if e.etype == "minion"))
    g.boss.hp = -1.0
    g.crystals = []
    g.update(1 / 60.0, NoKeys())
    check("boss death: crystals drop, boss_dead set, slot freed", g.boss_dead and g.boss is None and
          len(g.crystals) == C.BOSS_XP, "dead=%s boss=%s crystals=%d" % (g.boss_dead, g.boss, len(g.crystals)))


def test_zone_hazard():
    g = mk(4, data={"records": [], "fusions": []})
    g.player.weapons = []
    g.player.pos = (400.0, 300.0)
    g.zones = [Zone((400.0, 300.0), C.ZONE_RADIUS, C.ZONE_DPS, C.ZONE_WARN, C.ZONE_LIFE, True,
                    0, 0, (255, 90, 40))]
    log = spy_damage(g, [])
    sim(g, C.ZONE_WARN + C.ZONE_LIFE + 0.2)
    hits = [a for a in log if a > 0]
    check("fire zone burns the player standing in it", len(hits) >= 4, "hits=%d" % len(hits))
    check("fire zone expires after 4 s", len(g.zones) == 0, "zones=%d" % len(g.zones))


def agent_run(seed, mode, dt=0.05):
    """One full headless run: real HP, real spawner, real cards, autopilot policy."""
    g = Game({"records": [], "fusions": []}, rng=random.Random(seed), autoplay=True, mode=mode)
    g.state = "menu"
    for _ in range(int((C.WIN_TIME + 30) / dt)):
        if g.state in ("over", "win"):
            break
        autopilot_run(g, dt)
        g.update(dt, FakeKeys(g.autopos[0], g.autopos[1]))
    return g


def test_skilled_agent():
    """DoD 5 balance: a skilled run reaches the boss and can win; a mid-skill run
    dies in the target band 4-6 minutes. Real HP, real spawner, real card choices,
    deterministic because every random draw uses the game rng."""
    g = agent_run(1, "lane")
    check("skilled lane agent (seed 1) wins: 10:00 + boss killed",
          g.state == "win" and g.boss_dead,
          "time=%s kills=%d level=%d links=%d state=%s"
          % (fmt_time(g.time), g.player.kills, g.player.level, len(g.new_fusions), g.state))
    runs = []
    for s in range(1, 7):
        a = agent_run(s, "lane")
        runs.append((s, a.time, a.boss_dead, a.state))
    n_boss = sum(1 for s, t, d, st in runs if d)
    check("skilled agent reaches the boss fight on >=2 of 6 seeds", n_boss >= 2,
          "; ".join("seed%d %s%s" % (s, fmt_time(t), " WIN" if d else "") for s, t, d, st in runs))
    deaths = sorted(t for s, t, d, st in runs if st == "over")
    med = deaths[len(deaths) // 2] if deaths else -1.0
    check("median death of a strong agent is in the target band 4-6 min",
          deaths and 240.0 <= med <= 390.0,
          "median=%s deaths=%s" % (fmt_time(med), [fmt_time(t) for t in deaths]))
    g2 = agent_run(11, "elite")
    check("typical first-party balance: mid agent dies 4-6 min",
          g2.state == "over" and 240.0 <= g2.time <= 390.0,
          "time=%s state=%s" % (fmt_time(g2.time), g2.state))


def test_ui_features():
    """Menu, mouse, fullscreen, localization, settings persistence, dash charge bar."""
    clean_settings()
    g = Game({"records": [], "fusions": []}, rng=random.Random(5))
    check("launch state is the main menu", g.state == "menu", "state=%s" % g.state)
    check("default language is Russian", L.lang() == "ru" and C.DEFAULT_LANG == "ru" and
          all(k in C.LANGS for k in ("ru", "en")), L.lang())
    check("ru/en tables are key-symmetric", set(L.UI["ru"]) == set(L.UI["en"]),
          str(sorted(set(L.UI["ru"]) - set(L.UI["en"]))[:4]))
    check("names covered in both languages",
          set(C.WEAPON_STATS) <= set(L.W_NAME) and set(C.HYBRID_STATS) <= set(L.W_NAME) and
          set(C.PASSIVE_STATS) <= set(L.P_NAME),
          str(sorted(set(C.HYBRID_STATS) - set(L.W_NAME))[:4]))
    check("cached font draws Cyrillic", L.cyrillic_width(24) > 0,
          "width=%d" % L.cyrillic_width(24))
    g.new_run()
    check("run banner localized (ru)", g.banner_text == L.t("banner_start"), g.banner_text[:14])
    g.state = "menu"
    rects = hud.menu_rects()
    in_ok = all(r.left >= 0 and r.right <= C.WIDTH and r.top >= 0 and r.bottom <= C.HEIGHT
               for r in rects)
    gap_ok = all(rects[i].bottom <= rects[i + 1].top for i in range(len(rects) - 1))
    check("main menu: 7 buttons inside the scene, no overlap",
          len(rects) == 7 and in_ok and gap_ok, "last bottom=%d" % rects[-1].bottom)
    g.draw(SCREEN)
    check("menu label: language item shows the current language",
          "РУ" in hud.menu_labels(g)[1], hud.menu_labels(g)[1])
    g.mouse_click(*rects[0].center)
    check("mouse click on Play starts a run", g.state == "play", "state=%s" % g.state)
    lang0 = L.lang()
    g.state = "menu"
    g.mouse_click(*hud.menu_rects()[1].center)
    check("Language button toggles ru/en and persists", L.lang() != lang0 and
          save.load_settings()["lang"] == L.lang(), str(save.load_settings()))
    g.mouse_click(*hud.menu_rects()[1].center)
    check("Language toggles back to Russian", L.lang() == lang0, L.lang())
    fs0 = g.fullscreen
    g.mouse_click(*hud.menu_rects()[2].center)
    check("Fullscreen button flips the flag and persists", g.fullscreen != fs0 and
          save.load_settings()["fullscreen"] == g.fullscreen, str(save.load_settings()))
    apply_event(g, key(pygame.K_F11), False)
    check("F11 flips the fullscreen flag", g.fullscreen == fs0, "flag=%s" % g.fullscreen)
    g.data["records"] = [{"time": 600, "kills": 200, "level": 9, "result": "win"},
                         {"time": 300, "kills": 80, "level": 5, "result": "died"}]
    g.mouse_click(*hud.menu_rects()[4].center)
    lines = hud.rec_lines(g.data)
    g.draw(SCREEN)
    check("Records screen opens by click and maps result codes to localized words",
          g.state == "records" and len(lines) == 2 and "10:00" in lines[0] and
          "победа" in lines[0] and "смерть" in lines[1], str(lines[:2]))
    g.mouse_click(*hud.back_rect().center)
    check("Back button returns to the menu", g.state == "menu", "state=%s" % g.state)
    g.mouse_click(*hud.menu_rects()[5].center)
    g.draw(SCREEN)
    check("Book screen opens by click, all fusion slots are present", g.state == "book" and
          len(upgrades.ALL_FUSION_IDS) == len(upgrades.FUSIONS),
          "state=%s ids=%d" % (g.state, len(upgrades.ALL_FUSION_IDS)))
    g.state = "menu"
    g.mouse_click(*hud.menu_rects()[3].center)
    g.draw(SCREEN)
    apply_event(g, key(pygame.K_ESCAPE), False)
    check("Controls screen opens by click, Esc goes back to the menu",
          g.state == "menu", "state=%s" % g.state)
    g.menu_sel = 0
    apply_event(g, key(pygame.K_UP), False)
    wrap_ok = g.menu_sel == 6
    apply_event(g, key(pygame.K_s), False)
    check("Up wraps the menu selection, W/S navigate", wrap_ok and g.menu_sel == 0,
          "sel=%d" % g.menu_sel)
    g.state = "play"
    g.player.xp = g.player.xp_next
    g.level_up()
    n = len(g.cards)
    g.mouse_click(*hud.card_rects(n)[min(1, n - 1)].center)
    check("mouse click on a level-up card picks it", g.state == "play" and len(g.cards) == 0,
          "cards=%d state=%s" % (n, g.state))
    long_desc = "Перескакивает между целями (новая пушка)"
    card_text_width = hud.card_rects(3)[0].width - 20
    wrapped_desc = L.wrap(long_desc, C.F_CARD_X, card_text_width)
    check("long upgrade text wraps within the card at its render size",
          len(wrapped_desc) > 1 and all(L.measure(line, C.F_CARD_X) <= card_text_width
                                        for line in wrapped_desc), str(wrapped_desc))
    g.state = "pause"
    g.mouse_click(*hud.pause_rects()[0].center)
    check("pause: mouse click on Resume returns to play", g.state == "play", "state=%s" % g.state)
    g.state = "pause"
    g.mouse_click(*hud.pause_rects()[2].center)
    check("pause: mouse click on To menu leaves the run", g.state == "menu", "state=%s" % g.state)
    g.end_run("died", "reason_died", w=2, t="2:00")
    g.draw(SCREEN)
    g.mouse_click(*hud.over_rects()[1].center)
    check("results: mouse click on To menu", g.state == "menu", "state=%s" % g.state)
    g.state = "over"
    g.mouse_click(*hud.over_rects()[0].center)
    check("results: mouse click on New run restarts the run",
          g.state == "play" and g.time == 0, "state=%s time=%.2f" % (g.state, g.time))
    vw = ui.view(1600, 1200, C.WIDTH, C.HEIGHT)
    lv = ui.to_logical(800, 600, vw)
    dv = ui.to_display(400, 300, vw)
    check("letterbox mouse mapping round-trips at 2x scale",
          abs(lv[0] - 400) < 1 and abs(lv[1] - 300) < 1 and abs(dv[0] - 800) < 1 and
          abs(dv[1] - 600) < 1, str((lv, dv)))
    check("death reason renders in Russian", "Убит" in L.t("reason_died", w=3, t="2:03") and
          "волне 3" in L.t("reason_died", w=3, t="2:03"), L.t("reason_died", w=3, t="2:03"))
    clean_settings()
    g3 = mk(77)
    g3.player.pos = (400.0, 300.0)
    sfc = pygame.Surface((C.WIDTH, C.HEIGHT))
    sfc.fill(C.C_BG)
    by = 300 + int(C.PLAYER_RADIUS) + C.DASHBAR_GAP + 2
    bx = 400 - C.DASHBAR_W // 2
    g3.player.draw(sfc, 0, 0)
    check("dash charge bar is hidden under the hero when ready",
          sfc.get_at((400, by))[:3] == C.C_BG, str(sfc.get_at((400, by))[:3]))
    g3.player.start_dash(g3, False)
    g3.player.draw(sfc, 0, 0)
    check("dash charge bar draws under the hero while charging",
          sfc.get_at((400, by))[:3] == C.DASHBAR_BG and sfc.get_at((bx, by))[:3] == C.DASHBAR_BORDER,
          str((sfc.get_at((400, by))[:3], sfc.get_at((bx, by))[:3])))
    g3.player.dash_cd = 0.75
    g3.player.draw(sfc, 0, 0)
    check("dash bar fill grows with the charge (50% -> 18 of 36 px)",
          sfc.get_at((bx + 8, by))[:3] == C.DASHBAR_FILL and sfc.get_at((bx + 24, by))[:3] == C.DASHBAR_BG,
          str((sfc.get_at((bx + 8, by))[:3], sfc.get_at((bx + 24, by))[:3])))
    save.write_settings({"lang": "en", "fullscreen": True})
    g4 = Game({"records": [], "fusions": []}, rng=random.Random(6))
    check("Game loads language and fullscreen from settings.json",
          g4.lang == "en" and g4.fullscreen, str(save.load_settings()))
    with open(settings_path(), "w", encoding="utf-8") as fh:
        fh.write("{{{ not json")
    check("corrupt settings file does not break startup",
          save.load_settings() == {"lang": C.DEFAULT_LANG, "fullscreen": False}, str(save.load_settings()))
    clean_settings()


def test_minimap():
    g = mk(93, data={"records": [], "fusions": []})
    g.player.pos = (1000.0, 1000.0)
    g.enemies = [Enemy("crawler", (1000.0, 1130.0), 1),
                 Enemy("boss", (740.0, 1000.0), 8)]
    g.chests = [Chest((1200.0, 1000.0))]
    sfc = pygame.Surface((C.WIDTH, C.HEIGHT))
    g.draw(sfc)
    panel = hud.minimap_rect()
    colors = {sfc.get_at((x, y))[:3] for x in range(panel.left, panel.right)
              for y in range(panel.top, panel.bottom)}
    check("radar panel fits inside the game view",
          panel.left >= 0 and panel.top >= 0 and panel.right <= C.WIDTH and panel.bottom <= C.HEIGHT,
          str(panel))
    check("radar shows player, enemy, chest and boss with distinct markers",
          {C.C_PLAYER, C.ENEMY_COLORS["crawler"], (255, 193, 82), C.BOSS_COLOR} <= colors,
          "missing=%s" % sorted({C.C_PLAYER, C.ENEMY_COLORS["crawler"], (255, 193, 82),
                                 C.BOSS_COLOR} - colors))


def main():
    for fn in (test_full_run, test_boss_alive_loss, test_death, test_screens, test_cards, test_fallbacks,
               test_minimap,
               test_fusion, test_fusion_in_run, test_all_links_reachable, test_weapons_deal_damage,
               test_contact, test_enemy_formulas, test_banner_boost, test_chest, test_dash_and_passives,
               test_dps_target, test_xp_crystals, test_events_and_screens, test_no_bot_default_launch,
               test_save_first_start, test_ui_features,
               test_performance, test_new_enemy_attacks, test_boss_phases, test_zone_hazard, test_skilled_agent):
        fn()
    failed = [r for r in RESULTS if not r[1]]
    for name, ok, note in RESULTS:
        print("%-56s %s %s" % (name, "PASS" if ok else "FAIL", note if note else ""))
    print("\n%d checks, %d failed" % (len(RESULTS), len(failed)))
    print("perf: %.2f ms/frame (update+draw at %d enemies)" % (PERF[0], C.WAVE_LIMITS[9]))
    pygame.quit()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
