"""Content: localized card titles and text, level-up card pool, card application, chest reward."""
import config as C
import locale as L

# 12 fixed pairs: (hybrid id, weapon a, weapon b). Names and text live in locale.py
FUSIONS = [("fire_chain", "fire_aura", "chain"), ("frost_rocket", "rocket", "frost"),
           ("scythe_satellite", "orbital", "scythe"), ("storm_volley", "arrow", "pistol"),
           ("ice_bomb", "bomb", "ice_zone"), ("arc_pistol", "pistol", "chain"),
           ("flame_scythe", "scythe", "fire_aura"), ("blizzard", "frost", "ice_zone"),
           ("arrow_bomb", "arrow", "rocket"), ("rocket_satellite", "orbital", "rocket"),
           ("inferno", "bomb", "fire_aura"), ("twin_turret", "pistol", "orbital"),
           ("laser_storm", "laser", "chain"), ("frost_pulse", "pulse", "ice_zone")]
FUSION_BY_ID = {f[0]: f for f in FUSIONS}
ALL_FUSION_IDS = [f[0] for f in FUSIONS]
WEAPON_IDS = list(C.WEAPON_STATS.keys())


def lv_p():
    return L.t("lv_p")


def w_title(kind, level=None):
    return L.t("wlv", name=L.w_name(kind), p=lv_p(), lv=level) if level else L.w_name(kind)


def level_text():
    """Weapon level card text built from the scaling numbers in config.py."""
    return L.t("card_level_text", d=int(round((C.LVL_DMG - 1) * 100)),
               r=int(round((C.LVL_RATE - 1) * 100)), t4=C.LVL_TARGET_STEP + 1,
               t7=2 * C.LVL_TARGET_STEP + 1)


def roll_rarity(rng):
    r = rng.random()
    if r < C.RATES[0]:
        return 0, 1.0, C.C_TEXT
    if r < C.RATES[0] + C.RATES[1]:
        return 1, C.RARE_MULT, C.C_RARE
    return 2, C.EPIC_MULT, C.C_EPIC


def build_pool(game, count=3):
    """Full card pool: new weapons, weapon levels, passives, plus available fusion cards."""
    rng = game.rng
    p = game.player
    pool = []
    taken = {w.kind for w in p.weapons if not w.hybrid}
    hybrids = {w.kind for w in p.weapons if w.hybrid}
    if len(p.weapons) < C.MAX_WEAPONS:
        for k in WEAPON_IDS:
            if k not in taken:
                pool.append(dict(kind="weapon", id=k, title=L.w_name(k),
                                 text=L.w_desc(k) + L.t("card_new_suffix"), color=C.C_TEXT))
    for w in p.weapons:
        if w.level < C.WEAPON_MAX_LEVEL:
            pool.append(dict(kind="weapon_level", id=w.kind, title=w_title(w.kind, w.level + 1),
                             text=level_text(), color=C.C_TEXT))
    used_slots = len(p.passives)
    for pid, info in C.PASSIVE_STATS.items():
        lvl = p.passives.get(pid, 0)
        if lvl >= C.PASSIVE_MAX_LEVEL:
            continue
        if lvl == 0 and used_slots >= C.MAX_PASSIVES:
            continue
        idx = min(lvl, len(info["values"]) - 1)
        rare, mult, col = roll_rarity(rng)
        gain = info["values"][idx] * mult
        title = L.t("wlv", name=L.p_name(pid), p=lv_p(), lv=lvl + 1) if lvl > 0 else L.p_name(pid)
        pool.append(dict(kind="passive", id=pid, title=title, text=L.p_text(pid, gain),
                         color=col, rare=rare, gain=gain))
    fusion_cards = []
    for fid, a, b in FUSIONS:
        wa, wb = p.find_weapon(a), p.find_weapon(b)
        if wa and wb and wa.level >= C.FUSION_MIN_LEVEL and wb.level >= C.FUSION_MIN_LEVEL \
                and fid not in hybrids:
            fusion_cards.append(dict(kind="fusion", id=fid,
                                     title=L.t("card_fusion_title", name=L.w_name(fid)),
                                     text=L.w_desc(fid) + L.t("card_fusion_suffix"),
                                     color=C.C_FUSION))
    return pool, fusion_cards


def sample_cards(pool, count, rng):
    """Draw `count` distinct cards from the pool with weights (no duplicates in one level-up)."""
    pool = list(pool)
    out = []
    while pool and len(out) < count:
        items = [(i, C.CARD_WEIGHTS.get(c["kind"], 1)) for i, c in enumerate(pool)]
        r = rng.uniform(0, sum(w for _, w in items))
        acc, chosen = 0.0, items[-1][0]
        for i, w in items:
            acc += w
            if r <= acc:
                chosen = i
                break
        out.append(pool.pop(chosen))
    return out


def gen_cards(game, count=3):
    """Up to `count` ordinary cards + a 4th fusion card when a pair is available.
    Cards never duplicate inside one selection; when options run out, fallbacks fill in."""
    rng = game.rng
    pool, fusion_cards = build_pool(game, count)
    cards = sample_cards(pool, count, rng)
    names = {c["title"] for c in cards}
    for i, fb in enumerate(C.FALLBACKS):
        if len(cards) >= count:
            break
        title, text = L.fb_text(i, fb[1])
        if title in names:
            continue
        cards.append(dict(kind="fallback", id=fb[0], title=title, text=text, color=C.C_DIM,
                          value=fb[1]))
        names.add(title)
    if fusion_cards:
        cards.append(rng.choice(fusion_cards))
    return cards


def grant_epic_passive(game):
    """Chest reward: guaranteed epic passive (2x value), no slot needed for a taken passive."""
    p = game.player
    eligible = [pid for pid, info in C.PASSIVE_STATS.items()
                if p.passives.get(pid, 0) < C.PASSIVE_MAX_LEVEL]
    if not eligible:
        p.bonus["dmg"] += C.FALLBACKS[2][1]
        p.recompute()
        return L.fb_text(2, C.FALLBACKS[2][1])[0]
    pid = game.rng.choice(eligible)
    lvl = p.passives.get(pid, 0)
    gain = C.PASSIVE_STATS[pid]["values"][min(lvl, 2)] * C.EPIC_MULT
    p.add_passive(pid, gain)
    game.notes.append(L.t("note_chest", name=L.p_name(pid), p=lv_p(), lv=lvl + 1,
                          text=L.p_text(pid, gain)))
    return L.p_name(pid)


def apply_card(game, card):
    p = game.player
    k = card["kind"]
    if k == "weapon":
        game.add_weapon(card["id"], 1, False)
    elif k == "weapon_level":
        w = p.find_weapon(card["id"])
        if w is not None:
            w.level = min(C.WEAPON_MAX_LEVEL, w.level + 1)
    elif k == "passive":
        p.add_passive(card["id"], card["gain"])
    elif k == "fallback":
        key = card["id"]
        p.bonus[key] += card["value"]
        if key == "hp":
            p.max_hp += card["value"]
            before = p.hp
            p.hp = min(p.max_hp, p.hp + card["value"])
            if p.hp > before:
                p.hp_bar_t = C.HP_BAR_TIME
        p.recompute()
    elif k == "fusion":
        fid, a, b = FUSION_BY_ID[card["id"]]
        wa, wb = p.find_weapon(a), p.find_weapon(b)
        level = max(wa.level, wb.level)
        p.weapons.remove(wa)
        p.weapons.remove(wb)
        game.add_weapon(fid, level, True)
        if fid not in game.book:
            game.book.add(fid)
        game.new_fusions.append(fid)
        game.banner(L.t("banner_new_link", name=L.w_name(fid), p=lv_p(), lv=level), 3.0)
    game.sound.play("levelup")
