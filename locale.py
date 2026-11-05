"""Localization: ru + en, all visible text lives here; cached Cyrillic-capable fonts."""
import pygame

import config as C

LANG = C.DEFAULT_LANG

# Content names and descriptions (weapons, hybrids, passives)
W_NAME = {
    "pistol": {"ru": "Пистолет", "en": "Pistol"},
    "fire_aura": {"ru": "Огненная аура", "en": "Fire Aura"},
    "chain": {"ru": "Цепная молния", "en": "Chain Lightning"},
    "scythe": {"ru": "Косилька", "en": "Scythe"},
    "frost": {"ru": "Морозные шипы", "en": "Frost Spikes"},
    "ice_zone": {"ru": "Ледяная зона", "en": "Ice Zone"},
    "rocket": {"ru": "Ракеты", "en": "Rockets"},
    "arrow": {"ru": "Стрелы", "en": "Arrows"},
    "orbital": {"ru": "Турель-спутник", "en": "Orbital Turret"},
    "bomb": {"ru": "Бомба-липучка", "en": "Sticky Bomb"},
    "laser": {"ru": "Лазер", "en": "Laser"},
    "pulse": {"ru": "Импульс", "en": "Pulse"},
    "fire_chain": {"ru": "Огненная цепь", "en": "Fire Chain"},
    "frost_rocket": {"ru": "Морозные ракеты", "en": "Frost Rockets"},
    "scythe_satellite": {"ru": "Спутник-косилька", "en": "Scythe Satellite"},
    "storm_volley": {"ru": "Шквальный веер", "en": "Storm Volley"},
    "ice_bomb": {"ru": "Ледяная бомба", "en": "Ice Bomb"},
    "arc_pistol": {"ru": "Арочный пистолет", "en": "Arc Pistol"},
    "flame_scythe": {"ru": "Пламенная косилька", "en": "Flame Scythe"},
    "blizzard": {"ru": "Буран", "en": "Blizzard"},
    "arrow_bomb": {"ru": "Стрела-бомба", "en": "Arrow Bomb"},
    "rocket_satellite": {"ru": "Ракетный спутник", "en": "Rocket Satellite"},
    "inferno": {"ru": "Инферно", "en": "Inferno"},
    "twin_turret": {"ru": "Двойная турель", "en": "Twin Turret"},
    "laser_storm": {"ru": "Лазерный шторм", "en": "Laser Storm"},
    "frost_pulse": {"ru": "Морозный импульс", "en": "Frost Pulse"},
}

W_DESC = {
    "pistol": {"ru": "Снаряд в ближайшего врага", "en": "Aimed bullet at the closest enemy"},
    "fire_aura": {"ru": "Жжёт всё в радиусе вокруг", "en": "Burns everything within reach"},
    "chain": {"ru": "Перескакивает между целями", "en": "Jumps between targets"},
    "scythe": {"ru": "Дуга перед героем, несколько целей", "en": "Arc in front, several targets"},
    "frost": {"ru": "Снаряды замедляют на 30%", "en": "Bullets that slow by 30%"},
    "ice_zone": {"ru": "Замедляющая аура вокруг героя", "en": "Slowing aura around you"},
    "rocket": {"ru": "2 дальние цели, взрыв 40 px", "en": "Two far targets, 40 px explosion"},
    "arrow": {"ru": "Веер из 3, пробивает насквозь", "en": "Fan of 3, pierces through"},
    "orbital": {"ru": "Спутник, который стреляет", "en": "Satellite that shoots"},
    "bomb": {"ru": "Бросок бомбы, горящее поле 4 с", "en": "Lobbed bomb, fire field 4 s"},
    "laser": {"ru": "Дальний пробивающий лазерный луч", "en": "Long-range piercing laser beam"},
    "pulse": {"ru": "Широкий удар дугой по врагам", "en": "Wide arc strike against enemies"},
    "fire_chain": {"ru": "Горящая аура, перескакивает на 2 цели", "en": "Burning aura that jumps to 2 more targets"},
    "frost_rocket": {"ru": "Взрывы замедляют на 50%", "en": "Explosions slow enemies by 50%"},
    "scythe_satellite": {"ru": "Спутник бьёт дугой по кругу", "en": "Satellite sweeps an arc all around"},
    "storm_volley": {"ru": "7 пробивающих снарядов веером", "en": "7 piercing bullets in a wide fan"},
    "ice_bomb": {"ru": "Горящее поле также замедляет на 40%", "en": "Burning field also slows enemies by 40%"},
    "arc_pistol": {"ru": "Снаряды бьют дугой по 2 дополнительным целям", "en": "Bullets arc into 2 extra targets"},
    "flame_scythe": {"ru": "4 цели, оставляет горящее поле", "en": "4 targets, leaves a burning field"},
    "blizzard": {"ru": "Большая замораживающая аура, шипы летят наружу", "en": "Big freezing aura, spikes fly outward"},
    "arrow_bomb": {"ru": "Пробивающая стрела, взрывается при попадании", "en": "Piercing arrow that explodes on hit"},
    "rocket_satellite": {"ru": "Спутник стреляет ракетами со взрывом", "en": "Satellite fires exploding rockets"},
    "inferno": {"ru": "Аура шире, роняет 2 горящих поля", "en": "Wider burning aura, drops 2 fire fields"},
    "twin_turret": {"ru": "2 спутника со скорострельными пулями", "en": "2 satellites firing fast bullets"},
    "laser_storm": {"ru": "Пробивающий лазер разряжает цепную молнию", "en": "Piercing laser releases chain lightning"},
    "frost_pulse": {"ru": "Широкий импульс замедляет поражённых врагов", "en": "Wide pulse slows enemies it hits"},
}

P_NAME = {
    "speed": {"ru": "Быстрые ботинки", "en": "Swift Boots"},
    "dmg": {"ru": "Силовой модуль", "en": "Power Core"},
    "crit": {"ru": "Точный прицел", "en": "Precise Aim"},
    "pickup": {"ru": "Магнит", "en": "Magnet"},
    "regen": {"ru": "Регенерация", "en": "Regeneration"},
    "shield": {"ru": "Барьер", "en": "Barrier"},
    "area": {"ru": "Широкое поле", "en": "Wide Field"},
    "cooldown": {"ru": "Тайминг", "en": "Timing"},
    "armor": {"ru": "Укреплённый корпус", "en": "Reinforced Hull"},
    "haste": {"ru": "Ускоритель стрельбы", "en": "Rapid-Fire Module"},
}

P_TEXT = {
    "speed": {"ru": "Скорость +{v}%", "en": "Movement speed +{v}%"},
    "dmg": {"ru": "Урон оружия +{v}%", "en": "All weapon damage +{v}%"},
    "crit": {"ru": "Шанс крита +{v}% (x{m} урона)", "en": "Crit chance +{v}% (x{m} damage)"},
    "pickup": {"ru": "Радиус подбора +{v}%", "en": "Pickup radius +{v}%"},
    "regen": {"ru": "Реген {v} HP/с", "en": "Regen {v} HP/s"},
    "shield": {"ru": "Щит поглощает {v}% урона", "en": "Shield absorbs {v}% damage"},
    "area": {"ru": "Площадь оружия +{v}%", "en": "Weapon area +{v}%"},
    "cooldown": {"ru": "Откат рывка -{v}%", "en": "Dash cooldown -{v}%"},
    "armor": {"ru": "Получаемый урон -{v}%", "en": "Damage taken -{v}%"},
    "haste": {"ru": "Скорость атак оружия +{v}%", "en": "Weapon attack speed +{v}%"},
}

# UI strings
UI = {
    "ru": {
        "game_title": "АРЕНА: ВЫЖИВАНИЕ",
        "subtitle": "Аркада-выживалка: оружие стреляет само. Продержись 10:00 и убей босса.",
        "m_play": "Играть", "m_lang": "Язык: {lang}", "m_full": "Во весь экран: {state}",
        "m_controls": "Управление", "m_records": "Рекорды", "m_book": "Книга связок",
        "m_quit": "Выход", "m_back": "Назад", "m_resume": "Продолжить", "m_restart": "Рестарт",
        "m_menu": "В меню", "m_new_run": "Новая партия",
        "menu_hint": "Стрелки / W-S - выбор пункта, Enter - открыть, Esc - назад, мышь - клик",
        "mouse_hint": "Клик мышью по кнопкам работает везде, где есть UI.",
        "st_on": "вкл", "st_off": "выкл",
        "ctrl_title": "УПРАВЛЕНИЕ",
        "ctrl": ["WASD / стрелки - движение, оружие стреляет само по ближайшему врагу",
                 "ПРОБЕЛ - рывок: 120 px, откат 1,5 с, 0,25 с неуязвимости",
                 "1 / 2 / 3 / 4 - выбор карты при повышении уровня (4 = карта слияния)",
                 "ESC - пауза, R - рестарт партии, ENTER - старт / возврат в меню",
                 "M - звук вкл/выкл, F11 или ALT+ENTER - полноэкранный режим",
                 "Мышь - клик по кнопкам меню, паузы, итогов и карт улучшения"],
        "hud_hp": "Здоровье {hp}/{max}", "hud_xp": "Ур. {lv}  опыт {xp}/{next}",
        "hud_wave": "Волна {w}   Врагов {n}", "hud_kills": "Убийств {k}",
        "hud_links": "Связки {c}/{total}", "hud_boss": "БОСС",
        "hud_dash_ready": "РЫВОК [ПРОБЕЛ] готов", "hud_dash_cd": "РЫВОК {s} c",
        "hud_sound": "Звук: {s} [M]", "hud_w_label": "Оружие:", "hud_p_label": "Пассивки:",
        "radar_title": "РАДАР · {n}", "radar_enemy": "враг", "radar_chest": "ящик", "radar_boss": "босс",
        "hud_no_w": "нет оружия", "hud_no_p": "нет пассивок", "wlv": "{name} {p} {lv}", "lv_p": "Ур.",
        "card_title": "ПОВЫШЕНИЕ УРОВНЯ - ВЫБЕРИ ОДНУ КАРТУ",
        "card_new_suffix": " (новая пушка)", "card_p_suffix": " (пассивка)",
        "card_level_text": "+{d}% урона, +{r}% скорострельности, +1 цель на {t4} и {t7}",
        "card_fusion_title": "СЛИЯНИЕ: {name}", "card_fusion_suffix": " (требует оба оружия)",
        "fb_hp_name": "Макс. HP +{v}", "fb_hp_text": "+{v} к макс. HP, здоровье до нового максимума",
        "fb_speed_name": "Скорость +{v}", "fb_speed_text": "+{v} px/s к скорости движения",
        "fb_dmg_name": "Урон +{v}%", "fb_dmg_text": "+{v}% ко всему урону оружия",
        "banner_start": "ПРОДЕРЖИСЬ 10:00 - УБЕЙ БОССА",
        "banner_boss_slain": "БОСС УБИТ - ДЕРЖИСЬ ДО 10:00",
        "banner_new_link": "НОВАЯ СВЯЗКА: {name} {p} {lv}",
        "banner_chest": "СУНДУК ОТКРЫТ: {name}",
        "banner_sound": "Звук: {s}",
        "note_boss_killed": "Босс убит в {t}",
        "note_chest": "Сундук открыт: {name} {p} {lv} - {text}",
        "reason_died": "Убит на волне {w} в {t}",
        "reason_boss_alive": "10:00 прошло, босс ещё жив",
        "res_win": "победа", "res_died": "смерть", "res_boss_alive": "босс жив",
        "over_title": "ПАРТИЯ ОКОНЧЕНА", "win_title": "ТЫ УСТОЯЛ 10:00",
        "win_sub": "Прожил 10:00 и убил босса.",
        "over_stats": "ВРЕМЯ {t}   УБИЙСТВ {k}   УРОВЕНЬ {lv}",
        "links_found": "Связки за партию: {list}", "links_none": "Связки за партию: нет",
        "top10": "ТОП-10 РЕКОРДОВ", "book_title": "КНИГА СВЯЗОК",
        "book_line": "КНИГА СВЯЗОК - {n} из {total} открыто", "book_locked": "???",
        "no_records": "пока нет записанных забегов", "rec_line": "{n}. {t}   убийств {k}   ур. {lv}   {r}",
        "recs_title": "РЕКОРДЫ - ТОП-10 ПО ВРЕМЕНИ",
        "press_r": "R - новая партия", "press_menu": "Esc - меню",
        "press_enter": "ENTER - старт", "pause_title": "ПАУЗА",
        "pause_hint": "ESC - продолжить, R - рестарт, Enter - продолжить",
        "pause_hint2": "Оружие стреляет само: позиционирование - твоя работа.",
        "over_note": "{note}",
    },
    "en": {
        "game_title": "ARENA: SURVIVAL",
        "subtitle": "Survivors arcade: the weapon fires itself. Hold 10:00 and kill the boss.",
        "m_play": "Play", "m_lang": "Language: {lang}", "m_full": "Fullscreen: {state}",
        "m_controls": "Controls", "m_records": "Records", "m_book": "Combo Book",
        "m_quit": "Quit", "m_back": "Back", "m_resume": "Resume", "m_restart": "Restart",
        "m_menu": "To menu", "m_new_run": "New run",
        "menu_hint": "Arrows / W-S pick an item, Enter activates, Esc goes back, mouse clicks",
        "mouse_hint": "Mouse clicks work on every UI button.",
        "st_on": "on", "st_off": "off",
        "ctrl_title": "CONTROLS",
        "ctrl": ["WASD / Arrows - move, the weapon fires itself at the closest enemy",
                 "SPACE - dash: 120 px, 1.5 s cooldown, 0.25 s invulnerable",
                 "1 / 2 / 3 / 4 - pick a card on level-up (4 = fusion card)",
                 "ESC - pause, R - restart the run, ENTER - start / back to menu",
                 "M - sound on/off, F11 or ALT+ENTER - fullscreen mode",
                 "Mouse - click buttons in menu, pause, results and upgrade cards"],
        "hud_hp": "HP {hp}/{max}", "hud_xp": "Lv {lv}  XP {xp}/{next}",
        "hud_wave": "WAVE {w}   ENEMIES {n}", "hud_kills": "KILLS {k}",
        "hud_links": "LINKS {c}/{total}", "hud_boss": "BOSS",
        "hud_dash_ready": "DASH READY [SPACE]", "hud_dash_cd": "DASH {s}s",
        "hud_sound": "SOUND: {s} [M]", "hud_w_label": "Weapons:", "hud_p_label": "Passives:",
        "radar_title": "RADAR · {n}", "radar_enemy": "foe", "radar_chest": "chest", "radar_boss": "boss",
        "hud_no_w": "no weapons", "hud_no_p": "no passives", "wlv": "{name} {p} {lv}", "lv_p": "Lv",
        "card_title": "LEVEL UP - CHOOSE ONE CARD",
        "card_new_suffix": " (new weapon)", "card_p_suffix": " (passive)",
        "card_level_text": "+{d}% damage, +{r}% fire rate, +1 target at Lv {t4} and {t7}",
        "card_fusion_title": "FUSION: {name}", "card_fusion_suffix": " (costs both weapons)",
        "fb_hp_name": "Max HP +{v}", "fb_hp_text": "+{v} max HP, healed to the new cap",
        "fb_speed_name": "Movement +{v}", "fb_speed_text": "+{v} px/s movement speed",
        "fb_dmg_name": "Damage +{v}%", "fb_dmg_text": "+{v}% all weapon damage",
        "banner_start": "SURVIVE 10:00 - KILL THE BOSS",
        "banner_boss_slain": "BOSS SLAIN - HOLD UNTIL 10:00",
        "banner_new_link": "NEW LINK: {name} {p} {lv}",
        "banner_chest": "CHEST OPENED: {name}",
        "banner_sound": "SOUND: {s}",
        "note_boss_killed": "Boss killed at {t}",
        "note_chest": "Chest opened: {name} {p} {lv} - {text}",
        "reason_died": "Killed on wave {w} at {t}",
        "reason_boss_alive": "10:00 passed with the boss still alive",
        "res_win": "win", "res_died": "died", "res_boss_alive": "boss alive",
        "over_title": "RUN OVER", "win_title": "YOU HELD THE ARENA",
        "win_sub": "Survived 10:00 and killed the boss.",
        "over_stats": "TIME {t}   KILLS {k}   LEVEL {lv}",
        "links_found": "Links found this run: {list}", "links_none": "Links found this run: none",
        "top10": "TOP 10 RECORDS", "book_title": "BOOK OF LINKS",
        "book_line": "BOOK OF LINKS - {n} of {total} discovered", "book_locked": "???",
        "no_records": "no runs recorded yet", "rec_line": "{n}. {t}   kills {k}   Lv {lv}   {r}",
        "recs_title": "RECORDS - TOP 10 BY TIME",
        "press_r": "R - new run", "press_menu": "Esc - menu",
        "press_enter": "ENTER - start", "pause_title": "PAUSED",
        "pause_hint": "ESC - resume, R - restart, Enter - resume",
        "pause_hint2": "Weapons fire automatically: positioning is your job.",
        "over_note": "{note}",
    },
}


def lang():
    return LANG


def set_lang(value):
    global LANG
    LANG = value if value in C.LANGS else C.DEFAULT_LANG
    return LANG


def t(key, **fmt):
    table = UI.get(LANG, UI["en"])
    text = table.get(key, UI["en"].get(key, key))
    return text.format(**fmt) if fmt else text


def w_name(kind):
    return W_NAME.get(kind, {}).get(LANG, W_NAME[kind]["en"])


def w_desc(kind):
    return W_DESC.get(kind, {}).get(LANG, W_DESC[kind]["en"])


def p_name(pid):
    return P_NAME.get(pid, {}).get(LANG, P_NAME[pid]["en"])


def p_text(pid, gain):
    tmpl = P_TEXT.get(pid, {}).get(LANG, P_TEXT[pid]["en"])
    return tmpl.format(v=int(round(gain)), m=int(C.CRIT_MULT))


def fb_text(i, value):
    key = C.FALLBACKS[i][0]
    return t("fb_%s_name" % key, v=value), t("fb_%s_text" % key, v=value)


FONTS = {}


def fnt(size):
    """Cached system font with Cyrillic support; fallback to the built-in font, never a crash."""
    size = int(size)
    f = FONTS.get(size)
    if f is None:
        try:
            f = pygame.font.SysFont(C.FONT_CHAIN, size)
        except Exception:
            f = None
        if f is None:
            f = pygame.font.Font(None, size)
        FONTS[size] = f
    return f


def cyrillic_width(size):
    """Width of Cyrillic glyphs in the current font: 0 means the font cannot draw Russian."""
    return fnt(size).size("АБВГД")[0]


def measure(text, size):
    return fnt(size).size(text)[0]


def fit(text, size, maxw):
    """Largest size down to MIN_FONT that fits `text` into `maxw` pixels."""
    s = int(size)
    while s > C.MIN_FONT and measure(text, s) > maxw:
        s -= 1
    return s


def txt(surf, text, x, y, size, color, anchor="tl"):
    im = fnt(size).render(text, True, color)
    w, h = im.get_size()
    if anchor == "c":
        x, y = x - w // 2, y - h // 2
    elif anchor == "ct":
        x = x - w // 2
    elif anchor == "r":
        x = x - w
    elif anchor == "rt":
        x, y = x - w, y - h
    surf.blit(im, (int(x), int(y)))


def wrap(text, size, maxw):
    f = fnt(size)
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if f.size(trial)[0] <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines
