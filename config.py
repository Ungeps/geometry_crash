"""Arena Survival - all balance numbers, colors and constants live here."""

WIDTH, HEIGHT = 800, 600
FPS = 60
BORDER = 10

# Player
PLAYER_HP = 100.0
PLAYER_SPEED = 220.0
PLAYER_RADIUS = 11.0
PICKUP_RADIUS = 60.0
CONTACT_DMG = 5.0
CONTACT_CD = 0.5
DASH_DIST = 120.0
DASH_CD = 1.5
DASH_INVULN = 0.25
DASH_SPEED = 1200.0

# XP / levels
XP_BASE = 10
XP_STEP = 15
XP_CRYSTAL = 1
XP_FROM_WAVE = 4
MAX_WEAPONS = 6
MAX_PASSIVES = 6
WEAPON_MAX_LEVEL = 8
PASSIVE_MAX_LEVEL = 3
CARD_COUNT = 3
FUSION_MIN_LEVEL = 3
# Card rarity: normal 60% / rare 30% (1.5x gain) / epic 10% (2x gain, colored text)
RATES = (0.60, 0.30, 0.10)
RARE_MULT = 1.5
EPIC_MULT = 2.0

# Card weights in the level-up draw: a focused build gets its cards often enough
# that the "collect a link by minute 6-7" pacing from the design document is reachable.
CARD_WEIGHTS = {"weapon": 3, "weapon_level": 4, "passive": 1, "fallback": 1}

# Weapon level scaling: +30% dmg, +15% rate, +1 target at levels 4 and 7
LVL_DMG = 1.30
LVL_RATE = 1.15
LVL_TARGET_STEP = 3
LVL_AREA = 0.08

# Passive tables: 3 levels each
CRIT_MULT = 2.0
SHIELD_CAP = 0.75

# Waves
WAVE_INTERVAL = 30.0
WAVE_LIMITS = [6, 10, 14, 20, 28, 40, 55, 70, 80, 90]
SPAWN_RATE = 10.0
MAX_ALIVE = 150
ELITE_TIME = 300.0
ELITE_INTERVAL = 45.0
ELITE_MAX = 2
BOSS_TIME = 480.0
WIN_TIME = 600.0
WAVE_MIX = [
    (1, "crawler", 100),
    (4, "hopper", 18),
    (5, "tank", 10),
    (6, "splitter", 10),
    (7, "spitter", 10),
    (8, "sprinter", 12),
    (10, "hexer", 8),
    (12, "banner", 8),
]
CRAWLER_DECAY = 6
CRAWLER_MIN_WEIGHT = 35

# Fire zones (placed by the wave planner from minute 3)
ZONES_START = 180.0
ZONE_INTERVAL = (20.0, 30.0)
ZONE_WARN = 1.5
ZONE_LIFE = 4.0
ZONE_DPS = 5.0
ZONE_RADIUS = 70
ZONE_MAX = 3
ZONE_SPAWN_MIN = 1
ZONE_SPAWN_MAX = 3
ZONE_OFFSET = (60, 140)

# Chest
CHEST_INTERVAL = 120.0
CHEST_HOLD = 1.0
CHEST_RADIUS = 26.0

# Boss
BOSS_HP = 500.0
BOSS_RADIUS = 28.0
BOSS_SPEED = 55.0
BOSS_SPEED2 = 45.0
BOSS_SPEED3 = 70.0
BOSS_DMG = 15.0
BOSS_XP = 25
BOSS_PHASE2 = BOSS_HP * 2 / 3
BOSS_PHASE3 = BOSS_HP / 3
BOSS_PHASE2_FRAC = 2 / 3
BOSS_PHASE3_FRAC = 1 / 3
BOSS_VOLLEY_RATE = 2.5
BOSS_RING = 12
BOSS_BULLET_DMG = 10.0
BOSS_BULLET_SPEED = 130.0
BOSS_SUMMON_RATE = 6.0
BOSS_MINIONS = 6
BOSS_MINION_MAX = 30

# Records / book
RECORDS_FILE = "records.json"
TOP_RECORDS = 10

# Generated beeps: name -> (freq Hz, ms, volume, min gap s). No audio asset files.
SFX = {"kill": (620, 60, 0.14, 0.06), "levelup": (880, 180, 0.22, 0.20),
       "boss": (150, 500, 0.30, 0.50), "chest": (700, 240, 0.22, 0.30),
       "pickup": (1250, 40, 0.10, 0.05)}

# Fallback cards when the real pool is exhausted: (id, value). Text comes from locale.py
FALLBACKS = (("hp", 20), ("speed", 10), ("dmg", 10))

# Locale: default Russian, ru + en, all UI text comes from locale.py
DEFAULT_LANG = "ru"
LANGS = ("ru", "en")
LANG_LABEL = {"ru": "РУ", "en": "EN"}
FONT_CHAIN = "dejavusans,segoeui,arial,liberationsans,freesansbold,freesans"
F_TITLE, F_SUB, F_BTN, F_HUD, F_SMALL, F_CARD_T, F_CARD_X = 52, 24, 26, 18, 16, 22, 18
MIN_FONT = 13
SETTINGS_FILE = "settings.json"
TOP_RECORDS_SHOWN = 10

# UI buttons and menu layout
BTN_W, BTN_H, BTN_GAP = 260, 42, 10
C_BTN, C_BTN_HOVER, C_BTN_ACTIVE = (44, 52, 70), (62, 76, 104), (86, 108, 146)
C_BTN_SEL, C_BTN_TEXT, C_BTN_SUB = (200, 240, 255), (232, 238, 248), (150, 160, 180)
C_LETTER = (0, 0, 0)
MENU_TITLE_Y, MENU_SUB_Y, MENU_BTN_Y0 = 96, 150, 196
BACK_Y, BACK_W, BACK_H = 548, 170, 40
PAUSE_BTN_Y0, OVER_BTN_Y0, OVER_GAP = 292, 486, 16

# Dash charge bar under the hero (hidden when the dash is ready)
DASHBAR_W, DASHBAR_H, DASHBAR_GAP = 36, 5, 5
DASHBAR_BG, DASHBAR_FILL, DASHBAR_BORDER = (26, 36, 52), (120, 225, 255), (200, 240, 255)
HP_BAR_W, HP_BAR_H, HP_BAR_GAP, HP_BAR_TIME = 38, 5, 5, 1.4

# Colors (6-8 palette, no assets)
C_BG = (18, 20, 28)
C_GRID = (28, 32, 44)
C_WALL = (70, 80, 110)
C_PLAYER = (90, 220, 255)
C_PLAYER_HIT = (255, 240, 120)
C_XP = (120, 240, 170)
C_TEXT = (230, 235, 245)
C_DIM = (140, 150, 170)
C_HP = (230, 70, 70)
C_XPBAR = (110, 200, 130)
C_OVER = (12, 14, 22)
C_CARD = (40, 46, 62)
C_CARDsel = (60, 70, 96)
C_FUSION = (200, 120, 255)
C_EPIC = (255, 200, 60)
C_RARE = (120, 180, 255)

ENEMY_COLORS = {
    "crawler": (210, 90, 90),
    "hopper": (230, 150, 70),
    "tank": (150, 80, 60),
    "splitter": (200, 110, 160),
    "mini": (220, 130, 180),
    "sprinter": (250, 220, 90),
    "spitter": (100, 220, 150),
    "hexer": (190, 120, 250),
    "banner": (250, 90, 180),
    "elite": (160, 90, 220),
    "minion": (120, 120, 220),
    "boss": (255, 60, 60),
}
BOSS_COLOR = (255, 60, 60)

WEAPON_COLORS = {
    "pistol": (250, 240, 150),
    "fire_aura": (255, 120, 40),
    "chain": (160, 200, 255),
    "scythe": (200, 220, 200),
    "frost": (140, 220, 255),
    "ice_zone": (90, 180, 230),
    "rocket": (255, 160, 60),
    "arrow": (180, 255, 180),
    "orbital": (255, 220, 120),
    "bomb": (255, 90, 90),
    "laser": (110, 255, 245),
    "pulse": (190, 140, 255),
    "fire_chain": (255, 180, 60),
    "frost_rocket": (120, 200, 255),
    "scythe_satellite": (220, 240, 210),
    "storm_volley": (200, 255, 160),
    "ice_bomb": (110, 190, 240),
    "arc_pistol": (180, 210, 250),
    "flame_scythe": (255, 150, 60),
    "blizzard": (120, 230, 250),
    "arrow_bomb": (230, 200, 120),
    "rocket_satellite": (255, 140, 80),
    "inferno": (255, 80, 50),
    "twin_turret": (255, 240, 140),
    "laser_storm": (110, 230, 255),
    "frost_pulse": (155, 220, 255),
}

# Weapon numeric stats (behavior + params), level 1 base values
WEAPON_STATS = {
    "pistol": dict(behavior="shoot", dmg=8.0, rate=1.2, speed=420, life=1.4, radius=5, range=460),
    "fire_aura": dict(behavior="aura", dps=4.0, radius=80, tick=0.25),
    "chain": dict(behavior="chain", dmg=12.0, rate=0.8, jumps=3, range=220, bolt=0.18),
    "scythe": dict(behavior="arc", dmg=15.0, rate=1.0, targets=3, reach=120, arc_deg=80, fx=0.15),
    "frost": dict(behavior="shoot", dmg=6.0, rate=1.0, speed=350, life=1.4, radius=5, range=420,
                  slow=0.30, slow_time=2.0),
    "ice_zone": dict(behavior="aura", dps=3.0, radius=100, tick=0.25, slow=0.30, slow_time=1.0),
    "rocket": dict(behavior="shoot", dmg=20.0, rate=0.6, speed=300, life=2.0, radius=5, range=520,
                   targets=2, explode=40, mode="far"),
    "arrow": dict(behavior="shoot", dmg=7.0, rate=1.0, speed=380, life=1.4, radius=4, range=420,
                  volley=3, spread=14, pierce=3),
    "orbital": dict(behavior="orbital", dmg=6.0, rate=1.0, speed=460, life=1.5, radius=5, range=480,
                    orbit=60, count=1, orbit_speed=2.0),
    "bomb": dict(behavior="bomb", rate=0.4, speed=250, range=300, zone_dps=5.0, zone_life=4.0,
                 zone_radius=70, lob=0.25),
    "laser": dict(behavior="shoot", dmg=11.0, rate=0.75, speed=900, life=0.8, radius=3, range=650,
                  pierce=6),
    "pulse": dict(behavior="arc", dmg=11.0, rate=0.7, targets=4, reach=105, arc_deg=150, fx=0.18),
}
HYBRID_STATS = {
    "fire_chain": dict(behavior="aura", dps=6.0, radius=90, tick=0.25, chain_dmg=10.0, chain_jumps=2,
                       bolt=0.2, burn=1.0),
    "frost_rocket": dict(behavior="shoot", dmg=18.0, rate=0.7, speed=300, life=2.0, radius=5, range=520,
                         targets=2, explode=45, mode="far", slow=0.5, slow_time=2.5),
    "scythe_satellite": dict(behavior="orbital", dmg=12.0, rate=1.4, targets=4, reach=55, arc_deg=120,
                             orbit=70, count=1, orbit_speed=2.5, fx=0.15, arc_mode=True),
    "storm_volley": dict(behavior="shoot", dmg=6.0, rate=1.1, speed=400, life=1.4, radius=5, range=460,
                         volley=7, spread=12, pierce=9),
    "ice_bomb": dict(behavior="bomb", rate=0.4, speed=250, range=300, zone_dps=5.0, zone_life=4.0,
                     zone_radius=65, lob=0.25, slow=0.4, slow_time=2.0),
    "arc_pistol": dict(behavior="shoot", dmg=9.0, rate=1.3, speed=440, life=1.4, radius=5, range=460,
                       chain=2, chain_dmg=7.0, chain_range=200),
    "flame_scythe": dict(behavior="arc", dmg=16.0, rate=1.0, targets=4, reach=125, arc_deg=90, fx=0.15,
                         zone_dps=4.0, zone_life=2.0, zone_radius=45),
    "blizzard": dict(behavior="aura", dps=4.0, radius=130, tick=0.25, slow=0.5, slow_time=1.5,
                     spikes=4, spike_dmg=8.0, speed=340),
    "arrow_bomb": dict(behavior="shoot", dmg=10.0, rate=1.0, speed=360, life=1.5, radius=4, range=420,
                       pierce=3, explode=45),
    "rocket_satellite": dict(behavior="orbital", dmg=15.0, rate=0.9, speed=300, life=1.8, radius=5,
                             range=520, explode=40, orbit=70, count=1, orbit_speed=2.2),
    "inferno": dict(behavior="aura", dps=6.0, radius=104, tick=0.25, zone_dps=5.0, zone_life=2.5,
                    zone_radius=60, zone_shots=2, rate=0.8, range=280),
    "twin_turret": dict(behavior="orbital", dmg=6.0, rate=1.6, speed=480, life=1.5, radius=5, range=480,
                        orbit=65, count=2, orbit_speed=2.4),
    "laser_storm": dict(behavior="shoot", dmg=12.0, rate=0.85, speed=900, life=0.8, radius=3, range=650,
                        pierce=6, chain=2, chain_dmg=9.0, chain_range=220),
    "frost_pulse": dict(behavior="arc", dmg=13.0, rate=0.75, targets=5, reach=125, arc_deg=160, fx=0.2,
                        slow=0.35, slow_time=1.5),
}

# Passive numeric tables (3 levels)
PASSIVE_STATS = {
    "speed": dict(values=(15, 30, 45), kind="speed", text="Movement speed +{v}%"),
    "dmg": dict(values=(20, 40, 60), kind="dmg", text="All weapon damage +{v}%"),
    "crit": dict(values=(10, 20, 30), kind="crit", text="Crit chance +{v}% (x{m} damage)"),
    "pickup": dict(values=(50, 100, 150), kind="pickup", text="Pickup radius +{v}%"),
    "regen": dict(values=(1, 2, 3), kind="regen", text="Regen {v} HP/s"),
    "shield": dict(values=(25, 50, 75), kind="shield", text="Shield absorbs {v}% damage"),
    "area": dict(values=(20, 40, 60), kind="area", text="Weapon area +{v}%"),
    "cooldown": dict(values=(20, 40, 60), kind="cooldown", text="Dash cooldown -{v}%"),
    "armor": dict(values=(10, 20, 30), kind="armor", text="Damage taken -{v}%"),
    "haste": dict(values=(10, 20, 30), kind="haste", text="Weapon attack speed +{v}%"),
}

# Enemy numeric tables
ENEMY_STATS = {
    "crawler": dict(hp_base=1, hp_wave=1, speed=30, speed_wave=3, dmg=5, radius=12, xp=1, behavior="chase"),
    "hopper": dict(hp_base=1, hp_wave=1, hp_mult=0.7, speed=30, speed_wave=3, speed_mult=2.0, dmg=5,
                   radius=10, xp=1, behavior="hop", burst=0.35, idle=0.55),
    "tank": dict(hp_base=0, hp_wave=20, speed=15, speed_wave=1, dmg=10, radius=24, xp=3, behavior="chase",
                 push=20),
    "splitter": dict(hp_base=1, hp_wave=1, speed=26, speed_wave=2.5, dmg=5, radius=16, xp=2,
                     behavior="chase", split=2),
    "mini": dict(hp_base=1, hp_wave=0.5, speed=45, speed_wave=4, dmg=4, radius=8, xp=1, behavior="chase"),
    "sprinter": dict(hp_base=2, hp_wave=1.5, speed=40, speed_wave=3, dmg=12, radius=11, xp=2,
                     behavior="charge", telegraph=0.5, charge_speed=340, charge_time=1.2, rest=1.0),
    "spitter": dict(hp_base=7, hp_wave=2, speed=22, speed_wave=1, dmg=4, radius=13, xp=3,
                    behavior="spitter", keep=230, windup=0.65, fire_rate=2.6, bullet_speed=180,
                    bullet_dmg=6, volley=3, spread_deg=16),
    "hexer": dict(hp_base=10, hp_wave=2.5, speed=26, speed_wave=1.5, dmg=6, radius=14, xp=4,
                   behavior="hexer", keep=150, windup=0.9, fire_rate=4.8, zone_radius=60,
                   zone_dps=8.0, zone_life=2.5, zone_warn=0.9),
    "banner": dict(hp_base=8, hp_wave=2, speed=32, speed_wave=3, dmg=5, radius=15, xp=3, behavior="chase",
                   boost=0.25, boost_radius=110),
    "elite": dict(hp_base=40, hp_wave=8, speed=80, speed_wave=4, dmg=8, radius=16, xp=6, behavior="elite",
                  keep=170, fire_rate=1.2, bullet_speed=240, aura_radius=48, aura_dps=4.0),
    "minion": dict(hp_base=6, hp_wave=4, speed=110, speed_wave=6, dmg=8, radius=10, xp=2, behavior="chase"),
    "boss": dict(hp_base=500, hp_wave=0, speed=55, speed_wave=0, dmg=15, radius=28, xp=25, behavior="boss"),
}
