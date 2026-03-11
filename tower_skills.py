import json
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from tower import (
    get_conn, get_tower_char, calc_max_hp, calc_max_mp,
    CLASSES, get_mod, safe
)
from tower_battle import get_battle, save_battle, update_char_hp_mp

# ═══════════════════════════════════════════════════════════════
# СЛОВАРЬ НАВЫКОВ
# ═══════════════════════════════════════════════════════════════
# effect_fn(char, state) -> (лог_строки, новый_hp_игрока, новый_hp_врага)

SKILLS = {

    # ══════════════ ВОИН ══════════════
    "warrior_heavy_strike": {
        "name": "Мощный удар", "emoji": "⚔️",
        "class": "warrior", "level_req": 3,
        "mana": 2, "cd": 2,
        "desc": "+50% к урону оружием. Если враг защищается — ещё +25%.",
        "fn": "heavy_strike",
    },
    "warrior_shield_stance": {
        "name": "Стойка щита", "emoji": "🛡️",
        "class": "warrior", "level_req": 7,
        "mana": 3, "cd": 3,
        "desc": "Следующий полученный урон уменьшается на 70%.",
        "fn": "shield_stance",
    },
    "warrior_cleave": {
        "name": "Разрубание", "emoji": "⚔️",
        "class": "warrior", "level_req": 15,
        "mana": 4, "cd": 3,
        "desc": "Мощный удар, игнорирует броню врага.",
        "fn": "cleave",
    },
    "warrior_battle_cry": {
        "name": "Боевой клич", "emoji": "📢",
        "class": "warrior", "level_req": 25,
        "mana": 4, "cd": 4,
        "desc": "+2 Сила и +2 Скорость на 2 хода.",
        "fn": "battle_cry",
    },
    "warrior_execution": {
        "name": "Казнь", "emoji": "💥",
        "class": "warrior", "level_req": 40,
        "mana": 6, "cd": 5,
        "desc": "Если у врага <30% HP — наносит огромный урон.",
        "fn": "execution",
    },

    # ══════════════ СЛЕДОПЫТ ══════════════
    "ranger_aimed_shot": {
        "name": "Меткий выстрел", "emoji": "🏹",
        "class": "ranger", "level_req": 3,
        "mana": 2, "cd": 2,
        "desc": "+3 к броску атаки, почти не промахивается.",
        "fn": "aimed_shot",
    },
    "ranger_trap": {
        "name": "Ловушка", "emoji": "🕸️",
        "class": "ranger", "level_req": 7,
        "mana": 3, "cd": 3,
        "desc": "Враг теряет следующий ход (Сон 1 ход).",
        "fn": "trap",
    },
    "ranger_double_shot": {
        "name": "Двойной выстрел", "emoji": "🏹",
        "class": "ranger", "level_req": 15,
        "mana": 4, "cd": 3,
        "desc": "2 атаки оружием подряд.",
        "fn": "double_shot",
    },
    "ranger_nature_regen": {
        "name": "Природная регенерация", "emoji": "🌿",
        "class": "ranger", "level_req": 25,
        "mana": 3, "cd": 4,
        "desc": "Восстанавливает 20% от максимального HP.",
        "fn": "nature_regen",
    },
    "ranger_hunt_instinct": {
        "name": "Охотничий инстинкт", "emoji": "🦅",
        "class": "ranger", "level_req": 40,
        "mana": 5, "cd": 5,
        "desc": "Следующий удар — гарантированный крит (×2 урона).",
        "fn": "hunt_instinct",
    },

    # ══════════════ ВАРВАР ══════════════
    "barbarian_rage_strike": {
        "name": "Яростный удар", "emoji": "🪓",
        "class": "barbarian", "level_req": 3,
        "mana": 2, "cd": 2,
        "desc": "+70% урона, но ты открываешься: следующий удар по тебе +25%.",
        "fn": "rage_strike",
    },
    "barbarian_fury": {
        "name": "Ярость", "emoji": "😡",
        "class": "barbarian", "level_req": 7,
        "mana": 3, "cd": 4,
        "desc": "+3 Сила и −1 КД на 2 хода.",
        "fn": "fury",
    },
    "barbarian_crush": {
        "name": "Разрушительный удар", "emoji": "💥",
        "class": "barbarian", "level_req": 15,
        "mana": 4, "cd": 3,
        "desc": "Огромный урон + 40% шанс оглушить врага (Шок 1 ход).",
        "fn": "crush",
    },
    "barbarian_bloodthirst": {
        "name": "Кровавая жажда", "emoji": "🩸",
        "class": "barbarian", "level_req": 25,
        "mana": 4, "cd": 4,
        "desc": "Удар: 30% нанесённого урона восстанавливает тебе HP.",
        "fn": "bloodthirst",
    },
    "barbarian_berserk": {
        "name": "Берсерк", "emoji": "☠️",
        "class": "barbarian", "level_req": 40,
        "mana": 6, "cd": 5,
        "desc": "+5 Сила, +3 Скорость на 3 хода. После — пропуск хода.",
        "fn": "berserk",
    },

    # ══════════════ АССАСИН ══════════════
    "assassin_backstab": {
        "name": "Удар в спину", "emoji": "🗡️",
        "class": "assassin", "level_req": 3,
        "mana": 2, "cd": 2,
        "desc": "Следующий удар гарантированный крит (×2 урона).",
        "fn": "backstab",
    },
    "assassin_evade": {
        "name": "Уклонение", "emoji": "💨",
        "class": "assassin", "level_req": 7,
        "mana": 2, "cd": 3,
        "desc": "Следующая атака по тебе промахнётся.",
        "fn": "evade_skill",
    },
    "assassin_combo": {
        "name": "Серия ударов", "emoji": "🗡️",
        "class": "assassin", "level_req": 15,
        "mana": 4, "cd": 3,
        "desc": "3 быстрых удара подряд (каждый 40% базового урона).",
        "fn": "combo",
    },
    "assassin_poison_skill": {
        "name": "Яд", "emoji": "☠️",
        "class": "assassin", "level_req": 25,
        "mana": 3, "cd": 4,
        "desc": "Накладывает Яд(3) на врага.",
        "fn": "poison_skill",
    },
    "assassin_shadow_strike": {
        "name": "Теневая атака", "emoji": "👤",
        "class": "assassin", "level_req": 40,
        "mana": 5, "cd": 5,
        "desc": "Большой урон (×2.5), невозможно уклониться.",
        "fn": "shadow_strike",
    },

    # ══════════════ ВОЛШЕБНИК ══════════════
    "mage_fireball_skill": {
        "name": "Огненный шар", "emoji": "🔥",
        "class": "mage", "level_req": 3,
        "mana": 3, "cd": 2,
        "desc": "Урон: 10 + Инт×1.5. Накладывает Ожог(2).",
        "fn": "mage_fireball",
    },
    "mage_ice_slow": {
        "name": "Ледяное замедление", "emoji": "❄️",
        "class": "mage", "level_req": 7,
        "mana": 3, "cd": 3,
        "desc": "Холод(2) + Слабость(1) на врага.",
        "fn": "ice_slow",
    },
    "mage_lightning_skill": {
        "name": "Молния", "emoji": "⚡",
        "class": "mage", "level_req": 15,
        "mana": 4, "cd": 3,
        "desc": "Урон: 15 + Инт×2. Шанс Шок(1).",
        "fn": "mage_lightning",
    },
    "mage_shield_skill": {
        "name": "Магический щит", "emoji": "🔮",
        "class": "mage", "level_req": 25,
        "mana": 4, "cd": 4,
        "desc": "Барьер поглощает 20 + Инт×2 урона.",
        "fn": "mage_shield",
    },
    "mage_meteor_skill": {
        "name": "Метеор", "emoji": "☄️",
        "class": "mage", "level_req": 40,
        "mana": 7, "cd": 6,
        "desc": "Урон: 30 + Инт×3. Ожог(3).",
        "fn": "mage_meteor",
    },

    # ══════════════ КОЛДУН ══════════════
    "warlock_curse": {
        "name": "Проклятие", "emoji": "☠️",
        "class": "warlock", "level_req": 3,
        "mana": 2, "cd": 2,
        "desc": "Враг наносит на 30% меньше урона (Слабость врага 2 хода).",
        "fn": "curse",
    },
    "warlock_drain": {
        "name": "Высасывание жизни", "emoji": "🩸",
        "class": "warlock", "level_req": 7,
        "mana": 3, "cd": 3,
        "desc": "Урон: 8 + Инт×1.2. 50% урона восстанавливает тебе HP.",
        "fn": "drain",
    },
    "warlock_shadow_wave": {
        "name": "Теневая волна", "emoji": "👻",
        "class": "warlock", "level_req": 15,
        "mana": 4, "cd": 3,
        "desc": "Урон: 12 + Инт×1.8. Страх(1) + Слепота(1).",
        "fn": "shadow_wave",
    },
    "warlock_strong_curse": {
        "name": "Сильное проклятие", "emoji": "☠️",
        "class": "warlock", "level_req": 25,
        "mana": 5, "cd": 4,
        "desc": "Враг получает +30% урона (Слабость(3) + Слепота(2)).",
        "fn": "strong_curse",
    },
    "warlock_soul_harvest": {
        "name": "Жатва душ", "emoji": "💀",
        "class": "warlock", "level_req": 40,
        "mana": 6, "cd": 5,
        "desc": "Если враг умирает — восстанавливает 40% HP и 15 MP.",
        "fn": "soul_harvest",
    },
}

# Группировка по классу
SKILLS_BY_CLASS = {}
for sk, sv in SKILLS.items():
    SKILLS_BY_CLASS.setdefault(sv['class'], []).append(sk)

# ═══════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════

def get_available_skills(char):
    """Навыки класса, открытые по уровню."""
    ck = char['class_key']
    lvl = char['level']
    result = []
    for sk in SKILLS_BY_CLASS.get(ck, []):
        if lvl >= SKILLS[sk]['level_req']:
            result.append(sk)
    return result

def get_skill_slots(char):
    """Возвращает список из 5 слотов (None если пусто)."""
    return [
        char.get('skill_1'), char.get('skill_2'), char.get('skill_3'),
        char.get('skill_4'), char.get('skill_5'),
    ]

def save_skill_slots(user_id, slots):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''UPDATE tower_chars SET
        skill_1=%s, skill_2=%s, skill_3=%s, skill_4=%s, skill_5=%s
        WHERE user_id=%s''',
        (slots[0], slots[1], slots[2], slots[3], slots[4], user_id))
    conn.commit()
    conn.close()

def get_skill_cds(state):
    return state.get('skill_cds', {})

def set_skill_cd(state, skill_key, cd):
    cds = state.get('skill_cds', {})
    cds[skill_key] = cd
    state['skill_cds'] = cds

def tick_skill_cds(state):
    """Уменьшает все КД на 1 в конце хода."""
    cds = state.get('skill_cds', {})
    new_cds = {k: max(0, v - 1) for k, v in cds.items() if v > 0}
    state['skill_cds'] = new_cds

def reset_skill_cds(state):
    """Сбрасывает все КД при переходе на новый этаж."""
    state['skill_cds'] = {}

def skill_available(state, skill_key, char):
    """Проверяет — готов ли навык (КД=0 и хватает маны)."""
    cds = get_skill_cds(state)
    cd_left = cds.get(skill_key, 0)
    sk = SKILLS[skill_key]
    return cd_left == 0 and char['mp'] >= sk['mana']

def _weapon_dmg(char, state):
    from tower import WEAPONS
    from tower_battle import calc_player_attack
    return calc_player_attack(char, state)

def _apply_dmg_to_enemy(state, dmg):
    state['enemy_hp'] = max(0, state['enemy_hp'] - dmg)

# ═══════════════════════════════════════════════════════════════
# ЭФФЕКТЫ НАВЫКОВ
# ═══════════════════════════════════════════════════════════════

def apply_skill(skill_key, char, state, user_id):
    """
    Применяет навык. Возвращает (лог, новый_hp_игрока, новый_hp_врага, нужно_победа_check).
    """
    sk = SKILLS[skill_key]
    fn = sk['fn']
    log = []
    player_hp = char['hp']
    max_hp = calc_max_hp(char)
    max_mp = calc_max_mp(char)
    e_st = state.get('enemy_statuses', {})
    p_st = state.get('player_statuses', {})

    # Тратим ману
    new_mp = char['mp'] - sk['mana']
    update_char_hp_mp(user_id, player_hp, new_mp)

    # Устанавливаем КД
    set_skill_cd(state, skill_key, sk['cd'])

    # ── ВОИН ────────────────────────────────────────────────
    if fn == 'heavy_strike':
        base = _weapon_dmg(char, state)
        dmg = int(base * 1.5)
        if state.get('enemy_blocking'):
            dmg = int(dmg * 1.25)
            state['enemy_blocking'] = False
        _apply_dmg_to_enemy(state, dmg)
        log.append(f"⚔️ *Мощный удар* — {dmg} урона!")

    elif fn == 'shield_stance':
        state['skill_heavy_defense'] = 0.70
        p_st['shield_stance'] = 1
        log.append("🛡️ *Стойка щита* — следующий урон снижен на 70%!")

    elif fn == 'cleave':
        base = _weapon_dmg(char, state)
        dmg = int(base * 1.8)
        state['_ignore_armor'] = True
        _apply_dmg_to_enemy(state, dmg)
        state['_ignore_armor'] = False
        log.append(f"⚔️ *Разрубание* — {dmg} урона (игнор брони)!")

    elif fn == 'battle_cry':
        p_st['str_buff'] = p_st.get('str_buff', 0) + 2
        p_st['spd_buff'] = p_st.get('spd_buff', 0) + 2
        state['skill_battle_cry'] = 2
        log.append("📢 *Боевой клич!* +2 Сила, +2 Скорость на 2 хода!")

    elif fn == 'execution':
        ehp = state['enemy_hp']
        emaxhp = state['enemy_max_hp']
        if ehp / emaxhp < 0.30:
            base = _weapon_dmg(char, state)
            dmg = int(base * 4)
            _apply_dmg_to_enemy(state, dmg)
            log.append(f"💥 *КАЗНЬ!* — {dmg} урона!")
        else:
            log.append("💥 *Казнь* — враг ещё слишком силён (нужно <30% HP).")

    # ── СЛЕДОПЫТ ────────────────────────────────────────────
    elif fn == 'aimed_shot':
        base = _weapon_dmg(char, state)
        dmg = int(base * 1.3)
        _apply_dmg_to_enemy(state, dmg)
        log.append(f"🏹 *Меткий выстрел* — {dmg} урона (точный)!")

    elif fn == 'trap':
        e_st['sleep'] = max(e_st.get('sleep', 0), 1)
        log.append("🕸️ *Ловушка!* Враг пропускает следующий ход.")

    elif fn == 'double_shot':
        base = _weapon_dmg(char, state)
        d1 = int(base * 0.9)
        d2 = int(base * 0.9)
        _apply_dmg_to_enemy(state, d1)
        _apply_dmg_to_enemy(state, d2)
        log.append(f"🏹 *Двойной выстрел* — {d1} + {d2} урона!")

    elif fn == 'nature_regen':
        heal = int(max_hp * 0.20)
        new_hp = min(max_hp, player_hp + heal)
        player_hp = new_hp
        update_char_hp_mp(user_id, player_hp, new_mp)
        log.append(f"🌿 *Природная регенерация* — восстановлено {heal} HP!")

    elif fn == 'hunt_instinct':
        state['_next_crit'] = True
        log.append("🦅 *Охотничий инстинкт* — следующий удар критический!")

    # ── ВАРВАР ──────────────────────────────────────────────
    elif fn == 'rage_strike':
        base = _weapon_dmg(char, state)
        dmg = int(base * 1.7)
        _apply_dmg_to_enemy(state, dmg)
        state['player_open'] = 1  # +25% урона по игроку следующий ход
        log.append(f"🪓 *Яростный удар* — {dmg} урона! Ты открыт для контратаки.")

    elif fn == 'fury':
        p_st['str_buff'] = p_st.get('str_buff', 0) + 3
        state['skill_fury'] = 2
        log.append("😡 *Ярость!* +3 Сила на 2 хода.")

    elif fn == 'crush':
        base = _weapon_dmg(char, state)
        dmg = int(base * 2.2)
        _apply_dmg_to_enemy(state, dmg)
        if random.random() < 0.40:
            e_st['shock'] = max(e_st.get('shock', 0), 1)
            log.append(f"💥 *Разрушительный удар* — {dmg} урона + 💫Оглушение!")
        else:
            log.append(f"💥 *Разрушительный удар* — {dmg} урона!")

    elif fn == 'bloodthirst':
        base = _weapon_dmg(char, state)
        dmg = base
        _apply_dmg_to_enemy(state, dmg)
        heal = int(dmg * 0.30)
        new_hp = min(max_hp, player_hp + heal)
        player_hp = new_hp
        update_char_hp_mp(user_id, player_hp, new_mp)
        log.append(f"🩸 *Кровавая жажда* — {dmg} урона, восстановлено {heal} HP!")

    elif fn == 'berserk':
        p_st['str_buff'] = p_st.get('str_buff', 0) + 5
        p_st['spd_buff'] = p_st.get('spd_buff', 0) + 3
        state['skill_berserk'] = 3
        state['skill_berserk_exhaust'] = True
        log.append("☠️ *БЕРСЕРК!* +5 Сила, +3 Скорость на 3 хода. Потом — пропуск хода.")

    # ── АССАСИН ─────────────────────────────────────────────
    elif fn == 'backstab':
        state['_next_crit'] = True
        base = _weapon_dmg(char, state)
        dmg = int(base * 2)
        _apply_dmg_to_enemy(state, dmg)
        log.append(f"🗡️ *Удар в спину* — {dmg} урона (КРИТ)!")

    elif fn == 'evade_skill':
        state['player_evade_next'] = True
        log.append("💨 *Уклонение* — следующая атака по тебе промахнётся!")

    elif fn == 'combo':
        base = _weapon_dmg(char, state)
        hits = []
        for _ in range(3):
            d = int(base * 0.4)
            _apply_dmg_to_enemy(state, d)
            hits.append(str(d))
            if state['enemy_hp'] <= 0:
                break
        log.append(f"🗡️ *Серия ударов* — {' + '.join(hits)} урона!")

    elif fn == 'poison_skill':
        e_st['poison'] = e_st.get('poison', 0) + 3
        log.append("☠️ *Яд* — враг получает ☠️Яд(3)!")

    elif fn == 'shadow_strike':
        base = _weapon_dmg(char, state)
        dmg = int(base * 2.5)
        # Игнорирует уклонение врага
        state['enemy_dodging'] = False
        _apply_dmg_to_enemy(state, dmg)
        log.append(f"👤 *Теневая атака* — {dmg} урона (неуклонимо)!")

    # ── ВОЛШЕБНИК ───────────────────────────────────────────
    elif fn == 'mage_fireball':
        intel = char['intellect']
        dmg = int(10 + intel * 1.5)
        boost = state.get('weapon_spell_boost', 0)
        if boost: dmg = int(dmg * (1 + boost))
        _apply_dmg_to_enemy(state, dmg)
        e_st['burn'] = max(e_st.get('burn', 0), 2)
        log.append(f"🔥 *Огненный шар* — {dmg} урона + 🔥Ожог(2)!")

    elif fn == 'ice_slow':
        e_st['cold'] = max(e_st.get('cold', 0), 2)
        e_st['weakness'] = max(e_st.get('weakness', 0), 1)
        log.append("❄️ *Ледяное замедление* — враг получает ❄️Холод(2) и ⛓️Слабость(1)!")

    elif fn == 'mage_lightning':
        intel = char['intellect']
        dmg = int(15 + intel * 2)
        boost = state.get('weapon_spell_boost', 0)
        if boost: dmg = int(dmg * (1 + boost))
        _apply_dmg_to_enemy(state, dmg)
        if random.random() < 0.5:
            e_st['shock'] = max(e_st.get('shock', 0), 1)
            log.append(f"⚡ *Молния* — {dmg} урона + 💫Шок!")
        else:
            log.append(f"⚡ *Молния* — {dmg} урона!")

    elif fn == 'mage_shield':
        intel = char['intellect']
        barrier = int(20 + intel * 2)
        boost = state.get('weapon_spell_boost', 0)
        if boost: barrier = int(barrier * (1 + boost))
        state['player_barrier'] = state.get('player_barrier', 0) + barrier
        log.append(f"🔮 *Магический щит* — барьер {barrier} HP!")

    elif fn == 'mage_meteor':
        intel = char['intellect']
        dmg = int(30 + intel * 3)
        boost = state.get('weapon_spell_boost', 0)
        if boost: dmg = int(dmg * (1 + boost))
        _apply_dmg_to_enemy(state, dmg)
        e_st['burn'] = max(e_st.get('burn', 0), 3)
        log.append(f"☄️ *МЕТЕОР* — {dmg} урона + 🔥Ожог(3)!")

    # ── КОЛДУН ──────────────────────────────────────────────
    elif fn == 'curse':
        e_st['weakness'] = max(e_st.get('weakness', 0), 2)
        log.append("☠️ *Проклятие* — враг наносит меньше урона (⛓️Слабость(2))!")

    elif fn == 'drain':
        intel = char['intellect']
        dmg = int(8 + intel * 1.2)
        boost = state.get('weapon_spell_boost', 0)
        if boost: dmg = int(dmg * (1 + boost))
        _apply_dmg_to_enemy(state, dmg)
        heal = int(dmg * 0.50)
        player_hp = min(max_hp, player_hp + heal)
        update_char_hp_mp(user_id, player_hp, new_mp)
        log.append(f"🩸 *Высасывание жизни* — {dmg} урона, восстановлено {heal} HP!")

    elif fn == 'shadow_wave':
        intel = char['intellect']
        dmg = int(12 + intel * 1.8)
        boost = state.get('weapon_spell_boost', 0)
        if boost: dmg = int(dmg * (1 + boost))
        _apply_dmg_to_enemy(state, dmg)
        e_st['fear'] = max(e_st.get('fear', 0), 1)
        e_st['blind'] = max(e_st.get('blind', 0), 1)
        log.append(f"👻 *Теневая волна* — {dmg} урона + 😱Страх + 👁️Слепота!")

    elif fn == 'strong_curse':
        e_st['weakness'] = max(e_st.get('weakness', 0), 3)
        e_st['blind'] = max(e_st.get('blind', 0), 2)
        log.append("☠️ *Сильное проклятие* — враг получает ⛓️Слабость(3) + 👁️Слепота(2)!")

    elif fn == 'soul_harvest':
        # Эффект активируется при смерти врага — ставим флаг
        state['skill_soul_harvest'] = True
        log.append("💀 *Жатва душ* готова — если враг падёт, ты восстановишь HP и ману!")

    state['enemy_statuses'] = e_st
    state['player_statuses'] = p_st

    return log, player_hp, state['enemy_hp']


def calc_max_hp(char):
    from tower import calc_max_hp as _c
    return _c(char)

def calc_max_mp(char):
    from tower import calc_max_mp as _c
    return _c(char)


# ═══════════════════════════════════════════════════════════════
# ПОСТ-ПОБЕДНЫЙ ЭФФЕКТ (жатва душ)
# ═══════════════════════════════════════════════════════════════

def check_soul_harvest(char, state, user_id):
    """Вызывается после смерти врага. Возвращает лог."""
    if not state.get('skill_soul_harvest'):
        return []
    state['soul_harvest'] = False
    max_hp = calc_max_hp(char)
    max_mp = calc_max_mp(char)
    heal_hp = int(max_hp * 0.40)
    heal_mp = 15
    new_hp = min(max_hp, char['hp'] + heal_hp)
    new_mp = min(max_mp, char['mp'] + heal_mp)
    update_char_hp_mp(user_id, new_hp, new_mp)
    return [f"💀 *Жатва душ* — восстановлено {heal_hp} HP и {heal_mp} MP!"]


# ═══════════════════════════════════════════════════════════════
# ОБРАБОТКА БУФФОВ В КОНЦЕ ХОДА
# ═══════════════════════════════════════════════════════════════

def tick_skill_buffs(char, state, user_id):
    """Уменьшает счётчики длительных навыков. Вызывать после хода."""
    log = []
    p_st = state.get('player_statuses', {})

    # Боевой клич / Ярость / Берсерк
    for key, stat_pairs in [
        ('skill_battle_cry',  [('str_buff', 2), ('spd_buff', 2)]),
        ('skill_fury',        [('str_buff', 3)]),
        ('skill_berserk',     [('str_buff', 5), ('spd_buff', 3)]),
    ]:
        if key in state:
            state[key] -= 1
            if state[key] <= 0:
                del state[key]
                for stat, val in stat_pairs:
                    p_st[stat] = max(0, p_st.get(stat, 0) - val)
                if key == 'skill_berserk' and state.get('skill_berserk_exhaust'):
                    p_st['shock'] = max(p_st.get('shock', 0), 1)
                    state.pop('skill_berserk_exhaust', None)
                    log.append("☠️ *Берсерк* закончился — ты истощён (пропуск хода)!")

    state['player_statuses'] = p_st
    tick_skill_cds(state)
    return log


# ═══════════════════════════════════════════════════════════════
# MIGRATION — добавить skill_4/skill_5
# ═══════════════════════════════════════════════════════════════

def init_skills_columns():
    conn = get_conn()
    c = conn.cursor()
    for col in ['skill_4', 'skill_5']:
        try:
            c.execute(f'ALTER TABLE tower_chars ADD COLUMN {col} TEXT DEFAULT NULL')
            conn.commit()
        except:
            conn.rollback()
    conn.close()


# ═══════════════════════════════════════════════════════════════
# UI — МЕНЮ НАВЫКОВ
# ═══════════════════════════════════════════════════════════════

SLOT_EMOJIS = ['1️⃣','2️⃣','3️⃣','4️⃣','5️⃣']

def skills_menu_text(char):
    slots = get_skill_slots(char)
    available = get_available_skills(char)
    cls = CLASSES[char['class_key']]
    lvl = char['level']

    lines = [f"📜 *НАВЫКИ — {cls['emoji']} {cls['name']}*\n"]

    lines.append("*── Слоты ──*")
    for i, sk_key in enumerate(slots):
        em = SLOT_EMOJIS[i]
        if sk_key and sk_key in SKILLS:
            sk = SKILLS[sk_key]
            lines.append(f"{em} {sk['emoji']} {sk['name']} (КД:{sk['cd']}, Мана:{sk['mana']})")
        else:
            lines.append(f"{em} — пусто")

    lines.append("\n*── Доступные навыки ──*")
    if not available:
        lines.append("_Навыков пока нет. Повышай уровень!_")
    else:
        for sk_key in available:
            sk = SKILLS[sk_key]
            lines.append(f"{sk['emoji']} *{sk['name']}* — ур.{SKILLS[sk_key]['level_req']}")

    # Навыки которые откроются позже
    ck = char['class_key']
    locked = [k for k in SKILLS_BY_CLASS.get(ck, []) if lvl < SKILLS[k]['level_req']]
    if locked:
        lines.append("\n*── Заблокировано ──*")
        for sk_key in locked:
            sk = SKILLS[sk_key]
            lines.append(f"🔒 {sk['emoji']} {sk['name']} — ур.{sk['level_req']}")

    return "\n".join(lines)

def skills_menu_keyboard(char):
    available = get_available_skills(char)
    markup = InlineKeyboardMarkup(row_width=1)

    # Кнопки просмотра навыков
    for sk_key in available:
        sk = SKILLS[sk_key]
        markup.add(InlineKeyboardButton(
            f"{sk['emoji']} {sk['name']}",
            callback_data=f"sk_info_{sk_key}"
        ))

    markup.add(InlineKeyboardButton("🔧 Управлять слотами", callback_data="sk_manage"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="sk_back"))
    return markup

def skill_info_text(sk_key):
    sk = SKILLS[sk_key]
    return (
        f"{sk['emoji']} *{sk['name']}*\n\n"
        f"📖 Открывается: уровень {sk['level_req']}\n"
        f"⚡ Мана: {sk['mana']}\n"
        f"⏳ КД: {sk['cd']} хода\n\n"
        f"{sk['desc']}"
    )

def skill_info_keyboard(sk_key):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📌 Назначить в слот", callback_data=f"sk_assign_{sk_key}"),
        InlineKeyboardButton("🔙 Назад", callback_data="sk_list"),
    )
    return markup

def skill_assign_keyboard(char, sk_key):
    slots = get_skill_slots(char)
    markup = InlineKeyboardMarkup(row_width=1)
    for i, slot_val in enumerate(slots):
        if slot_val and slot_val in SKILLS:
            label = f"{SLOT_EMOJIS[i]} Заменить: {SKILLS[slot_val]['name']}"
        else:
            label = f"{SLOT_EMOJIS[i]} Пустой слот"
        markup.add(InlineKeyboardButton(label, callback_data=f"sk_set_{i}_{sk_key}"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data=f"sk_info_{sk_key}"))
    return markup


# ═══════════════════════════════════════════════════════════════
# UI — НАВЫКИ В БОЮ
# ═══════════════════════════════════════════════════════════════

def battle_skills_keyboard(char, state):
    slots = get_skill_slots(char)
    cds = get_skill_cds(state)
    markup = InlineKeyboardMarkup(row_width=1)
    has_any = False
    for sk_key in slots:
        if not sk_key or sk_key not in SKILLS:
            continue
        has_any = True
        sk = SKILLS[sk_key]
        cd_left = cds.get(sk_key, 0)
        can_use = cd_left == 0 and char['mp'] >= sk['mana']
        if can_use:
            label = f"✅ {sk['emoji']} {sk['name']} (⚡{sk['mana']})"
        elif cd_left > 0:
            label = f"⏳ {sk['emoji']} {sk['name']} — КД {cd_left}"
        else:
            label = f"❌ {sk['emoji']} {sk['name']} — нет маны"
        markup.add(InlineKeyboardButton(label, callback_data=f"tb_skill_use_{sk_key}"))
    if not has_any:
        markup.add(InlineKeyboardButton("— навыки не назначены —", callback_data="noop"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tb_back_to_battle"))
    return markup


# ═══════════════════════════════════════════════════════════════
# РЕГИСТРАЦИЯ ХЭНДЛЕРОВ
# ═══════════════════════════════════════════════════════════════

def register_tower_skills(bot):

    init_skills_columns()

    # ── Меню навыков из главного меню башни ───────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tower_skills')
    def cb_tower_skills(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char: return
        bot.send_message(call.message.chat.id,
            skills_menu_text(char),
            reply_markup=skills_menu_keyboard(char),
            parse_mode='Markdown')

    # ── Назад к списку навыков ────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'sk_list')
    def cb_sk_list(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char: return
        try: bot.edit_message_text(
            skills_menu_text(char),
            call.message.chat.id, call.message.message_id,
            reply_markup=skills_menu_keyboard(char),
            parse_mode='Markdown')
        except:
            bot.send_message(call.message.chat.id,
                skills_menu_text(char),
                reply_markup=skills_menu_keyboard(char),
                parse_mode='Markdown')

    # ── Информация о навыке ───────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data.startswith('sk_info_'))
    def cb_sk_info(call):
        bot.answer_callback_query(call.id)
        sk_key = call.data[8:]
        if sk_key not in SKILLS: return
        try: bot.edit_message_text(
            skill_info_text(sk_key),
            call.message.chat.id, call.message.message_id,
            reply_markup=skill_info_keyboard(sk_key),
            parse_mode='Markdown')
        except:
            bot.send_message(call.message.chat.id,
                skill_info_text(sk_key),
                reply_markup=skill_info_keyboard(sk_key),
                parse_mode='Markdown')

    # ── Управление слотами ────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'sk_manage')
    def cb_sk_manage(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char: return
        slots = get_skill_slots(char)
        available = get_available_skills(char)
        markup = InlineKeyboardMarkup(row_width=1)
        for sk_key in available:
            sk = SKILLS[sk_key]
            in_slots = sk_key in slots
            label = f"{'✅' if in_slots else '  '} {sk['emoji']} {sk['name']}"
            markup.add(InlineKeyboardButton(label, callback_data=f"sk_assign_{sk_key}"))
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="sk_list"))
        try: bot.edit_message_text(
            "🔧 *Управление слотами*\nВыбери навык для назначения:",
            call.message.chat.id, call.message.message_id,
            reply_markup=markup, parse_mode='Markdown')
        except:
            bot.send_message(call.message.chat.id,
                "🔧 *Управление слотами*\nВыбери навык для назначения:",
                reply_markup=markup, parse_mode='Markdown')

    # ── Выбор слота для назначения ────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data.startswith('sk_assign_'))
    def cb_sk_assign(call):
        bot.answer_callback_query(call.id)
        sk_key = call.data[10:]
        char = get_tower_char(call.from_user.id)
        if not char or sk_key not in SKILLS: return
        try: bot.edit_message_text(
            f"📌 Куда назначить *{SKILLS[sk_key]['name']}*?",
            call.message.chat.id, call.message.message_id,
            reply_markup=skill_assign_keyboard(char, sk_key),
            parse_mode='Markdown')
        except:
            bot.send_message(call.message.chat.id,
                f"📌 Куда назначить *{SKILLS[sk_key]['name']}*?",
                reply_markup=skill_assign_keyboard(char, sk_key),
                parse_mode='Markdown')

    # ── Сохранение навыка в слот ──────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data.startswith('sk_set_'))
    def cb_sk_set(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        parts = call.data[7:].split('_', 1)  # "sk_set_2_warrior_heavy_strike" -> ["2","warrior_heavy_strike"]
        if len(parts) < 2: return
        slot_idx = int(parts[0])
        sk_key = parts[1]
        char = get_tower_char(user_id)
        if not char or sk_key not in SKILLS: return

        slots = get_skill_slots(char)
        # Убираем навык из другого слота если он там есть
        slots = [None if s == sk_key else s for s in slots]
        slots[slot_idx] = sk_key
        save_skill_slots(user_id, slots)

        sk = SKILLS[sk_key]
        bot.answer_callback_query(call.id,
            f"✅ {sk['name']} → слот {slot_idx+1}", show_alert=True)

        char = get_tower_char(user_id)
        try: bot.edit_message_text(
            skills_menu_text(char),
            call.message.chat.id, call.message.message_id,
            reply_markup=skills_menu_keyboard(char),
            parse_mode='Markdown')
        except:
            bot.send_message(call.message.chat.id,
                skills_menu_text(char),
                reply_markup=skills_menu_keyboard(char),
                parse_mode='Markdown')

    # ── Назад из меню навыков ─────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'sk_back')
    def cb_sk_back(call):
        bot.answer_callback_query(call.id)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        from tower import tower_main_text, tower_main_keyboard
        char = get_tower_char(call.from_user.id)
        if char:
            bot.send_message(call.message.chat.id,
                tower_main_text(char),
                reply_markup=tower_main_keyboard(char),
                parse_mode='Markdown')

    # ── Навыки в бою ──────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tb_skill')
    def cb_tb_skill(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        char = get_tower_char(user_id)
        state = get_battle(user_id)
        if not char or not state: return

        markup = battle_skills_keyboard(char, state)
        bot.send_message(call.message.chat.id,
            "📜 *Выбери навык:*",
            reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tb_skill_use_'))
    def cb_tb_skill_use(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        sk_key = call.data[13:]
        char = get_tower_char(user_id)
        state = get_battle(user_id)
        if not char or not state or sk_key not in SKILLS: return

        sk = SKILLS[sk_key]
        cds = get_skill_cds(state)

        if cds.get(sk_key, 0) > 0:
            bot.answer_callback_query(call.id, f"⏳ КД ещё {cds[sk_key]} хода", show_alert=True)
            return
        if char['mp'] < sk['mana']:
            bot.answer_callback_query(call.id, f"❌ Нет маны ({char['mp']}/{sk['mana']})", show_alert=True)
            return

        # Применяем навык
        log, new_player_hp, new_enemy_hp = apply_skill(sk_key, char, state, user_id)

        # Тики буффов
        char = get_tower_char(user_id)
        buff_log = tick_skill_buffs(char, state, user_id)
        log.extend(buff_log)

        # Проверка смерти врага
        if state['enemy_hp'] <= 0:
            harvest_log = check_soul_harvest(char, state, user_id)
            log.extend(harvest_log)
            from tower_battle import _handle_victory
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            _handle_victory(bot, call.message.chat.id, user_id, get_tower_char(user_id), state, log)
            return

        # Ход врага
        from tower_battle import (
            roll_enemy_action, apply_enemy_ability, process_end_of_turn,
            send_battle, ENEMIES
        )
        action = state.get('next_enemy_action', {})
        char = get_tower_char(user_id)
        enemy_log, new_player_hp2 = apply_enemy_ability(char, state, action)
        log.extend(enemy_log)

        tick_log, nhp_final, nehp_final = process_end_of_turn(
            {**char, 'hp': new_player_hp2}, state)
        log.extend(tick_log)
        state['enemy_hp'] = max(0, nehp_final)

        update_char_hp_mp(user_id, max(0, nhp_final))
        char = get_tower_char(user_id)

        if char['hp'] <= 0 or state['enemy_hp'] <= 0:
            if state['enemy_hp'] <= 0:
                harvest_log = check_soul_harvest(char, state, user_id)
                log.extend(harvest_log)
                from tower_battle import _handle_victory
                _handle_victory(bot, call.message.chat.id, user_id, char, state, log)
            else:
                from tower_battle import _handle_defeat
                _handle_defeat(bot, call.message.chat.id, user_id, char, state, log)
            return

        state['next_enemy_action'] = roll_enemy_action(state['enemy_key'], state['enemy_base_dmg'])
        save_battle(user_id, state)

        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        send_battle(bot, call.message.chat.id, user_id, char, state, log,
                    msg_id_to_delete=state.get('last_msg_id'))

    @bot.callback_query_handler(func=lambda call: call.data == 'noop')
    def cb_noop(call):
        bot.answer_callback_query(call.id)
