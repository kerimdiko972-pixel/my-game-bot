# ============================================================
#  arena_combat.py  — Движок боя для системы Арены
# ============================================================

import random
from arena_data import (
    WEAPONS, ARTIFACTS, GOBLIN_DATA,
    STATUS_DISPLAY, NEGATIVE_EFFECTS, POSITIVE_EFFECTS,
    pick_goblin_action, calc_max_hp, calc_max_mana, calc_kd, calc_speed
)


# ═══════════════════════════════════════════════════════════
#  Вспомогательные функции
# ═══════════════════════════════════════════════════════════

def effective_stat(fighter: dict, stat: str) -> int:
    """Возвращает значение стата с учётом эффектов статусов."""
    base = fighter.get(stat, 0)
    eff  = fighter.get('effects', {})

    bonus = 0
    # Баффы
    if stat in ('str','dex','con','int','cha','lck'):
        stat_up_map = {
            'str': 'str_up', 'dex': 'dex_up', 'con': 'con_up',
            'int': 'int_up', 'cha': 'cha_up', 'lck': 'lck_up'
        }
        bonus += eff.get(stat_up_map.get(stat, '__'), 0)
        bonus += eff.get('all_up', 0)
        bonus -= eff.get('all_down', 0)
        if stat in ('str', 'dex'):
            bonus -= eff.get('weakness', 0) * 2
    return max(0, base + bonus)


def get_effective_speed(fighter: dict) -> float:
    base   = fighter.get('speed', 5)
    eff    = fighter.get('effects', {})
    freeze = eff.get('freeze', 0)
    if freeze > 0:
        return max(0, base - 2)  # после разморозки -2
    speed_mod = fighter.get('speed_modifier', 0)
    return base + speed_mod


def format_effects(effects: dict) -> str:
    if not effects:
        return '—'
    parts = []
    for key, stacks in effects.items():
        if stacks > 0:
            name = STATUS_DISPLAY.get(key, key)
            parts.append(f'{name} ({stacks})')
    return '\n'.join(parts) if parts else '—'


# ═══════════════════════════════════════════════════════════
#  Применение / снятие эффектов
# ═══════════════════════════════════════════════════════════

def add_effect(target: dict, effect: str, stacks: int):
    """Добавить/увеличить эффект на target."""
    if effect in target.get('immunity', []):
        return f'🛡️ {target["name"]} иммунен к {STATUS_DISPLAY.get(effect, effect)}!'
    
    # Огонь + лёд аннигилируют друг друга
    effs = target['effects']
    if effect == 'burn' and effs.get('freeze', 0) > 0:
        del effs['freeze']
        return f'❄️🔥 Заморозка и Горение аннигилировали!'
    if effect == 'freeze' and effs.get('burn', 0) > 0:
        del effs['burn']
        return f'🔥❄️ Горение и Заморозка аннигилировали!'

    effs[effect] = effs.get(effect, 0) + stacks
    name = STATUS_DISPLAY.get(effect, effect)
    return f'🎯 Наложен {name} ({effs[effect]})'


def remove_effect(target: dict, effect: str):
    effs = target['effects']
    if effect in effs:
        del effs[effect]


def remove_one_negative(target: dict) -> str:
    effs = target['effects']
    for key in NEGATIVE_EFFECTS:
        if key in effs:
            name = STATUS_DISPLAY.get(key, key)
            del effs[key]
            return f'✨ Снят {name}'
    return '❌ Негативных эффектов нет'


def tick_effects_start_of_turn(target: dict) -> list[str]:
    """
    Обрабатывает эффекты в начале хода цели.
    Возвращает список строк с описаниями.
    """
    msgs = []
    effs = target['effects']
    name = target['name']

    # 🔥 Горение: урон = stacks*2, потом -1
    if effs.get('burn', 0) > 0:
        dmg = effs['burn'] * 2
        target['hp'] = max(0, target['hp'] - dmg)
        msgs.append(f'🔥 {name} получает {dmg} урона от Горения!')
        effs['burn'] -= 1
        if effs['burn'] <= 0:
            del effs['burn']

    # ☠️ Яд: урон = stacks, потом -1
    if effs.get('poison', 0) > 0:
        dmg = effs['poison']
        target['hp'] = max(0, target['hp'] - dmg)
        msgs.append(f'☠️ {name} получает {dmg} урона от Яда!')
        effs['poison'] -= 1
        if effs['poison'] <= 0:
            del effs['poison']

    # 🌿 Регенерация: лечение = stacks, потом -1
    if effs.get('regen', 0) > 0:
        heal = effs['regen']
        old_hp = target['hp']
        target['hp'] = min(target['max_hp'], target['hp'] + heal)
        healed = target['hp'] - old_hp
        msgs.append(f'🌿 {name} восстанавливает {healed} ХП от Регенерации!')
        effs['regen'] -= 1
        if effs['regen'] <= 0:
            del effs['regen']

    return msgs


def tick_effects_end_of_turn(target: dict) -> list[str]:
    """
    Обрабатывает снижение длительности части эффектов в конце хода.
    """
    msgs = []
    effs = target['effects']
    name = target['name']

    # Снижаем длительность: weakness, stun, sleep, vulnerability, curse, blind, all_down, all_up, stat_ups
    decay_effects = ['weakness','stun','sleep','vulnerability','curse','blind',
                     'all_down','all_up','str_up','dex_up','con_up','int_up','cha_up','lck_up',
                     'thorns','radioactive','reflect']
    for key in decay_effects:
        if key in effs:
            effs[key] -= 1
            if effs[key] <= 0:
                del effs[key]
                msgs.append(f'⏰ {STATUS_DISPLAY.get(key, key)} на {name} истёк')

    # 🧊 Заморозка: уменьшается на 1
    if effs.get('freeze', 0) > 0:
        effs['freeze'] -= 1
        if effs['freeze'] <= 0:
            del effs['freeze']
            # После заморозки: -2 к скорости и ловкости на 1 ход
            target['speed'] = max(1, target.get('speed', 5) - 2)
            msgs.append(f'🧊 Заморозка на {name} спала! -2 к скорости и ловкости')

    # 😶‍🌫️ Скрытность: не снижается тут, снимается при получении урона

    return msgs


def apply_bleed_on_action(target: dict) -> list[str]:
    """Кровотечение: урон при каждом действии."""
    msgs = []
    effs = target['effects']
    if effs.get('bleed', 0) > 0:
        dmg = effs['bleed']
        target['hp'] = max(0, target['hp'] - dmg)
        msgs.append(f'🩸 {target["name"]} истекает кровью! -{dmg} ХП')
    return msgs


def end_of_round_bleed_decay(target: dict):
    """Кровотечение: уменьшается на 1 в конце хода."""
    effs = target['effects']
    if effs.get('bleed', 0) > 0:
        effs['bleed'] -= 1
        if effs['bleed'] <= 0:
            del effs['bleed']


# ═══════════════════════════════════════════════════════════
#  Основной движок боя
# ═══════════════════════════════════════════════════════════

def calculate_hit_chance(attacker_dex: int, defender_dex: int) -> int:
    hit = 85 + attacker_dex * 2 - defender_dex * 1.5
    return int(max(25, min(95, hit)))


def calculate_dodge_chance(defender: dict) -> float:
    dex = effective_stat(defender, 'dex')
    lck = effective_stat(defender, 'lck')
    dodge = dex * 1.5 + lck * 1.0
    # Стойка уклонения
    if defender.get('stance') == 'dodge':
        dodge += 15
    # Скрытность
    if defender['effects'].get('stealth', 0) > 0:
        dodge += 50
    return dodge


def calculate_crit_chance(attacker: dict, weapon_key: str = None) -> int:
    lck = effective_stat(attacker, 'lck')
    crit = 5 + lck * 1.5
    # Стойка боевая
    if attacker.get('stance') == 'battle':
        crit += 5
    # Артефакты (пассивы уже применены в effective_stats, здесь дополнительно)
    for art_slot in ['artifact1', 'artifact2']:
        art_name = attacker.get(art_slot)
        if art_name and art_name in ARTIFACTS:
            key = ARTIFACTS[art_name]['effect_key']
            if key == 'luck_pin':
                crit += 1
            elif key == 'wind_talisman':
                crit += 1
            elif key == 'clarity_glasses':
                crit += 10
    return int(crit)


def calculate_damage(attacker: dict, weapon_data: dict) -> int:
    """Базовый урон от оружия без учёта брони."""
    stat_key = weapon_data['stat']
    base_dmg = weapon_data['base_dmg']
    stat_val = effective_stat(attacker, stat_key)
    dmg = base_dmg + stat_val

    # Стойки
    stance = attacker.get('stance', 'normal')
    if stance == 'battle':
        dmg += 2
    elif stance == 'defense':
        dmg -= 2
    elif stance == 'dodge':
        dmg -= 2

    # Артефакт-пассивы, усиливающие урон
    for art_slot in ['artifact1', 'artifact2']:
        art_name = attacker.get(art_slot)
        if art_name and art_name in ARTIFACTS:
            key = ARTIFACTS[art_name]['effect_key']
            if key == 'destroyer_glove':
                dmg = int(dmg * 1.15)
                if effective_stat(attacker, 'str') >= 12:
                    dmg = int(dmg * 1.0)  # Игнор защиты обрабатывается ниже
            elif key == 'ancient_seal':
                pass  # +2 все статы — уже учтено через effective_stat

    return max(1, dmg)


def apply_armor_reduction(dmg: int, kd: float, ignore_pct: float = 0.0) -> int:
    effective_kd = kd * (1.0 - ignore_pct)
    reduction = effective_kd / (effective_kd + 50)
    return max(1, round(dmg * (1.0 - reduction)))


def do_attack(attacker: dict, defender: dict, is_player_attacking: bool) -> dict:
    """
    Выполняет атаку. Возвращает dict с результатом:
    {
        'hit': bool,
        'crit': bool,
        'damage': int,
        'messages': [str],
        'extra_turn': bool,  # для гоблинского быстрого выпада
    }
    """
    msgs   = []
    result = {'hit': False, 'crit': False, 'damage': 0, 'messages': msgs, 'extra_turn': False}

    # ─ Кровотечение при атаке
    bleed_msgs = apply_bleed_on_action(attacker)
    msgs.extend(bleed_msgs)
    if attacker['hp'] <= 0:
        return result

    # ─ Оглушение / сон / заморозка → пропуск хода
    if is_stunned(attacker):
        stun_msg = consume_stun(attacker)
        msgs.append(stun_msg)
        return result

    # ─ Слепота → -30% попадание
    blind_penalty = 0
    if attacker['effects'].get('blind', 0) > 0:
        blind_penalty = 30
        msgs.append(f'👁️‍🗨️ Слепота! -{blind_penalty}% к шансу попадания')

    # ─ Получаем данные об оружии (для NPC используем упрощённый вариант)
    weapon_data = None
    if is_player_attacking:
        weapon_name = attacker.get('weapon')
        weapon_data = WEAPONS.get(weapon_name)

    # ─ Шанс попасть
    atk_dex = effective_stat(attacker, 'dex')
    def_dex = effective_stat(defender, 'dex')
    hit_chance = calculate_hit_chance(atk_dex, def_dex)
    dodge_chance = calculate_dodge_chance(defender)
    final_hit = hit_chance - dodge_chance - blind_penalty

    if random.randint(1, 100) > final_hit:
        msgs.append(f'💨 Промах!')
        result['hit'] = False
        # Скрытность снимается при получении урона, промах не снимает
        return result

    # ─ Снимаем скрытность при попадании
    if defender['effects'].get('stealth', 0) > 0:
        del defender['effects']['stealth']

    result['hit'] = True

    # ─ Крит
    crit_chance = calculate_crit_chance(attacker, weapon_data['ability_key'] if weapon_data else None)
    # Доп. бонусы крита от оружия
    if weapon_data:
        if weapon_data['ability_key'] == 'sniper_bow':
            crit_chance += 15
        elif weapon_data['ability_key'] == 'hunter_bow' and not attacker.get('first_attack_done', False):
            crit_chance += 25

    is_crit = random.randint(1, 100) <= crit_chance

    # ─ Базовый урон
    if is_player_attacking and weapon_data:
        dmg = calculate_damage(attacker, weapon_data)
    else:
        # NPC урон берётся напрямую из параметров боя
        dmg = attacker.get('_dmg', 5)

    # ─ Крит-множитель
    ignore_armor_pct = 0.0
    if is_crit:
        dmg = round(dmg * 1.5)
        result['crit'] = True
        msgs.append(f'💥 Критический удар!')
        # Артефакты при крите
        if weapon_data:
            if weapon_data['ability_key'] == 'sunder_blade':
                ignore_armor_pct = 0.25
            if weapon_data['ability_key'] == 'hellfire_claymore':
                ignore_armor_pct = 0.30
            if weapon_data['ability_key'] == 'rune_blade':
                dmg = round(dmg * 1.5)  # +50% к уже критовому

    # ─ Стойка атакующего (доп. игнор через артефакт)
    for art_slot in ['artifact1', 'artifact2']:
        art_name = attacker.get(art_slot)
        if art_name and art_name in ARTIFACTS:
            if ARTIFACTS[art_name]['effect_key'] == 'destroyer_glove':
                if effective_stat(attacker, 'str') >= 12:
                    ignore_armor_pct = max(ignore_armor_pct, 0.20)

    # ─ Уязвимость защищающегося: +50% входящего урона
    if defender['effects'].get('vulnerability', 0) > 0:
        dmg = round(dmg * 1.5)

    # ─ Броня
    def_kd = defender.get('kd', 10)
    dmg = apply_armor_reduction(dmg, def_kd, ignore_armor_pct)

    # ─ Защита (действие)
    if defender.get('defending', False):
        dmg = max(1, round(dmg * 0.5))
        msgs.append(f'🛡️ Защита снизила урон вдвое!')

    # ─ Щит
    if defender.get('shield', 0) > 0:
        shield_absorb = min(defender['shield'], dmg)
        dmg -= shield_absorb
        defender['shield'] -= shield_absorb
        if defender['shield'] <= 0:
            defender['shield'] = 0
        msgs.append(f'🛡️ Щит поглотил {shield_absorb} урона!')

    # ─ Отражение урона (артефакт)
    if defender.get('reflect_pct', 0) > 0:
        reflect_dmg = max(1, round(dmg * defender['reflect_pct']))
        attacker['hp'] = max(0, attacker['hp'] - reflect_dmg)
        msgs.append(f'🪞 Отражено {reflect_dmg} урона обратно!')

    # ─ Шипы
    if defender['effects'].get('thorns', 0) > 0:
        thorns_dmg = defender['effects']['thorns']
        attacker['hp'] = max(0, attacker['hp'] - thorns_dmg)
        msgs.append(f'🌵 Шипы нанесли {thorns_dmg} урона атакующему!')

    # ─ Радиоактивность
    if defender['effects'].get('radioactive', 0) > 0:
        add_effect(attacker, 'poison', 1)
        msgs.append(f'☢️ Радиоактивность заразила атакующего ядом!')

    # ─ Финально применяем урон
    final_dmg = max(1, dmg)
    defender['hp'] = max(0, defender['hp'] - final_dmg)
    result['damage'] = final_dmg

    atk_name = attacker['name']
    def_name = defender['name']
    crit_txt = ' (крит!)' if is_crit else ''
    msgs.append(f'⚔️ {atk_name} → {def_name}: -{final_dmg} ХП{crit_txt}')

    # ─ Способности оружия (для игрока)
    if is_player_attacking and weapon_data and weapon_data.get('ability_key'):
        ability_msgs = apply_weapon_ability(attacker, defender, weapon_data, is_crit)
        msgs.extend(ability_msgs)

    # ─ Отмечаем первую атаку
    attacker['first_attack_done'] = True

    return result


def is_stunned(entity: dict) -> bool:
    effs = entity['effects']
    return effs.get('stun', 0) > 0 or effs.get('sleep', 0) > 0 or effs.get('freeze', 0) > 0


def consume_stun(entity: dict) -> str:
    effs = entity['effects']
    if effs.get('stun', 0) > 0:
        effs['stun'] -= 1
        if effs['stun'] <= 0:
            del effs['stun']
        return f'⚡ {entity["name"]} оглушён и пропускает ход!'
    if effs.get('sleep', 0) > 0:
        # Сон: шанс снять при уроне (обрабатывается в do_attack)
        effs['sleep'] -= 1
        if effs['sleep'] <= 0:
            del effs['sleep']
        return f'💤 {entity["name"]} спит и пропускает ход!'
    if effs.get('freeze', 0) > 0:
        # Заморозка: ход пропускается, уменьшается в end_of_turn
        return f'🧊 {entity["name"]} заморожен и пропускает ход!'
    return ''


# ═══════════════════════════════════════════════════════════
#  Способности оружий
# ═══════════════════════════════════════════════════════════

def apply_weapon_ability(attacker: dict, defender: dict,
                          weapon_data: dict, is_crit: bool) -> list[str]:
    msgs = []
    key = weapon_data.get('ability_key')
    if not key:
        return msgs

    # Бонус от Кроны Радужного Владыки: +20% к шансу эффектов
    effect_bonus = 0
    for art_slot in ['artifact1', 'artifact2']:
        art_name = attacker.get(art_slot)
        if art_name and art_name in ARTIFACTS:
            if ARTIFACTS[art_name]['effect_key'] == 'rainbow_crown':
                effect_bonus += 20

    def chance(pct):
        return random.randint(1, 100) <= (pct + effect_bonus)

    if key == 'rune_blade':
        if is_crit and chance(25):
            msgs.append(add_effect(defender, 'vulnerability', 1))
    elif key == 'stun_hammer':
        if chance(20):
            msgs.append(add_effect(defender, 'stun', 1))
    elif key == 'exhaustion_pike':
        if chance(25):
            msgs.append(add_effect(defender, 'weakness', 1))
            defender['speed'] = max(1, defender.get('speed', 5) - 1)
            msgs.append('⏬ Скорость врага снижена на 1!')
    elif key == 'berserker_axe':
        if chance(30):
            msgs.append(add_effect(attacker, 'str_up', 1))
    elif key == 'sunder_blade':
        if is_crit and chance(20):
            msgs.append(add_effect(defender, 'all_down', 1))
    elif key == 'poison_dagger':
        if chance(35):
            extra = 1 if is_crit else 0
            msgs.append(add_effect(defender, 'poison', 1 + extra))
    elif key == 'sniper_bow':
        if is_crit:
            msgs.append(add_effect(defender, 'blind', 1))
    elif key == 'hunter_bow':
        if not attacker.get('first_attack_done', True) and chance(20):
            msgs.append(add_effect(defender, 'vulnerability', 1))
    elif key == 'spark_wand':
        guaranteed = is_crit
        if guaranteed or chance(25):
            msgs.append(add_effect(defender, 'stun', 1))
    elif key == 'life_staff':
        if chance(25):
            msgs.append(add_effect(attacker, 'regen', 1))
    elif key == 'abyss_shard':
        if chance(30):
            msgs.append(add_effect(defender, 'burn', 1))
    elif key == 'wind_fan':
        if chance(25):
            msgs.append(add_effect(attacker, 'stealth', 2))
    elif key == 'ice_wand':
        stacks = 2 if is_crit else 1
        if chance(25):
            msgs.append(add_effect(defender, 'freeze', stacks))
    elif key == 'shadow_blade':
        if is_crit:
            effect = random.choice(NEGATIVE_EFFECTS)
            msgs.append(add_effect(defender, effect, 1))
    elif key == 'fire_spirit_staff':
        stacks = 3 if is_crit else 2
        if chance(25):
            msgs.append(add_effect(defender, 'burn', stacks))
    elif key == 'spider_excalibur':
        if is_crit and chance(35):
            msgs.append(add_effect(defender, 'poison', 2))
            msgs.append(add_effect(attacker, 'stealth', 2))
    elif key == 'aqua_wedge':
        if chance(30):
            msgs.append(add_effect(defender, 'burn', 2))
        if is_crit:
            msgs.append(add_effect(attacker, 'regen', 2))
    elif key == 'sky_discord':
        if chance(30):
            msgs.append(add_effect(defender, 'stun', 2))
            msgs.append(add_effect(defender, 'freeze', 1))
    elif key == 'twins':
        if chance(25):
            msgs.append(add_effect(defender, 'bleed', 2))
    elif key == 'arcane_bow':
        if chance(30):
            msgs.append(add_effect(defender, 'blind', 2))
        if is_crit:
            msgs.append(add_effect(defender, 'vulnerability', 2))
    elif key == 'hellfire_claymore':
        if chance(35):
            msgs.append(add_effect(defender, 'burn', 2))
    elif key == 'abyss_blade':
        if is_crit and chance(30):
            msgs.append(add_effect(defender, 'poison', 2))
            msgs.append(add_effect(attacker, 'stealth', 2))
    elif key == 'thunder_mace':
        if chance(25):
            msgs.append(add_effect(defender, 'stun', 2))
    elif key == 'amethyst_dagger':
        if is_crit and chance(40):
            msgs.append(add_effect(defender, 'poison', 3))
            msgs.append(add_effect(attacker, 'stealth', 3))
    elif key == 'rainbow_excalibur':
        if chance(35):
            msgs.append(add_effect(defender, 'vulnerability', 3))
            msgs.append(add_effect(defender, 'burn', 3))
    elif key == 'kraken_axe':
        if chance(30):
            msgs.append(add_effect(defender, 'stun', 3))
            msgs.append(add_effect(defender, 'weakness', 2))
    elif key == 'black_hole_sword':
        if is_crit:
            msgs.append(add_effect(defender, 'bleed', 3))
            msgs.append(add_effect(defender, 'vulnerability', 3))
    elif key == 'skull_staff':
        if chance(35):
            msgs.append(add_effect(defender, 'curse', 3))
            msgs.append(add_effect(defender, 'burn', 3))

    return msgs


# ═══════════════════════════════════════════════════════════
#  Использование артефактов (активные)
# ═══════════════════════════════════════════════════════════

def use_active_artifact(attacker: dict, defender: dict, artifact_name: str) -> list[str]:
    msgs = []
    if artifact_name not in ARTIFACTS:
        return ['❌ Артефакт не найден']

    art = ARTIFACTS[artifact_name]
    if art['type'] != 'active':
        return ['❌ Это пассивный артефакт']

    cooldowns = attacker.get('artifact_cooldowns', {})
    key = art['effect_key']
    if cooldowns.get(key, 0) > 0:
        return [f'⏳ Артефакт на перезарядке ({cooldowns[key]} ходов)']

    # ─── Эффекты активных артефактов ──────────────────────
    if key == 'sweet_nectar':
        heal = min(5, attacker['max_hp'] - attacker['hp'])
        attacker['hp'] += heal
        msgs.append(f'🧃 Восстановлено {heal} ХП')
    elif key == 'small_bell':
        msg = remove_one_negative(attacker)
        msgs.append(msg)
    elif key == 'small_totem':
        attacker['shield'] = attacker.get('shield', 0) + 5
        msgs.append('🪵 Щит +5 на 1 ход')
    elif key == 'salt_pinch':
        removed = False
        for eff in ['bleed', 'poison']:
            if attacker['effects'].get(eff, 0) > 0:
                stacks = attacker['effects'][eff]
                remove_stacks = min(1, stacks)
                attacker['effects'][eff] -= remove_stacks
                if attacker['effects'][eff] <= 0:
                    del attacker['effects'][eff]
                msgs.append(f'🧂 Снят 1 стак {STATUS_DISPLAY.get(eff, eff)}')
                removed = True
                break
        if not removed:
            msgs.append('🧂 Нечего лечить')
    elif key == 'black_token':
        defender['effects']['hit_penalty'] = defender['effects'].get('hit_penalty', 0) + 5
        msgs.append('🕳️ Шанс попадания врага снижен на 5%')
    elif key == 'ice_chunk':
        defender['speed'] = max(1, defender.get('speed', 5) - 1)
        msgs.append('🧊 Скорость врага снижена на 1')
    elif key == 'burning_coal':
        dmg = 4
        defender['hp'] = max(0, defender['hp'] - dmg)
        msgs.append(f'🔥 Нанесено {dmg} урона')
        if random.randint(1, 100) <= 10:
            msgs.append(add_effect(defender, 'burn', 1))
    elif key == 'small_trap':
        if random.randint(1, 100) <= 15:
            msgs.append(add_effect(defender, 'weakness', 1))
        else:
            msgs.append('🪤 Капкан не сработал')
    elif key == 'dim_mirror':
        attacker['reflect_pct'] = 0.05
        msgs.append('🪞 Отражение 5% урона активировано на 1 ход')
    elif key == 'clarity_elixir':
        attacker['mana'] = min(attacker['max_mana'], attacker['mana'] + 3)
        msgs.append(add_effect(attacker, 'int_up', 1))
        msgs.append('🧴 +3 маны')
    elif key == 'endurance_potion':
        heal = min(6, attacker['max_hp'] - attacker['hp'])
        attacker['hp'] += heal
        msgs.append(add_effect(attacker, 'con_up', 1))
        msgs.append(f'🧪 +{heal} ХП')
    elif key == 'weak_candle':
        # +5% крит на 1 ход — используем временный эффект
        attacker['effects']['crit_bonus'] = 1
        msgs.append('🕯️ +5% крит на 1 ход')
    elif key == 'old_lock':
        attacker['effects']['dodge_bonus'] = attacker['effects'].get('dodge_bonus', 0) + 2
        msgs.append('🎒 +2% уклонение на 1 ход')
    elif key == 'water_flask':
        attacker['mana'] = min(attacker['max_mana'], attacker['mana'] + 7)
        msgs.append('🧴 +7 маны')
    elif key == 'small_box':
        stat = random.choice(['str', 'dex', 'con', 'int', 'cha', 'lck'])
        effect = f'{stat}_up'
        msgs.append(add_effect(attacker, effect, 1))
        msgs.append(f'📦 Случайный бонус к {stat.upper()}!')
    # Легендарные активные
    elif key == 'chaos_dice':
        pos_eff = random.choice(POSITIVE_EFFECTS)
        neg_eff = random.choice(NEGATIVE_EFFECTS)
        msgs.append(add_effect(attacker, pos_eff, 3))
        msgs.append(add_effect(defender, neg_eff, 2))
        msgs.append('🎲 Кости хаоса брошены!')
    elif key == 'genie_lamp':
        heal = round(attacker['max_hp'] * 0.3)
        attacker['hp'] = min(attacker['max_hp'], attacker['hp'] + heal)
        attacker['mana'] = min(attacker['max_mana'], attacker['mana'] + round(attacker['max_mana'] * 0.3))
        msgs.append(add_effect(attacker, 'all_up', 3))
        msgs.append(f'🪔 +{heal} ХП и мана восстановлены!')
    elif key == 'war_horn':
        msgs.append(add_effect(attacker, 'str_up', 4))
        attacker['speed'] = attacker.get('speed', 5) + 2
        msgs.append('🎺 +4 сила, +2 скорость на 2 хода!')
    elif key == 'eternal_fruit':
        heal = round(attacker['max_hp'] * 0.4)
        attacker['hp'] = min(attacker['max_hp'], attacker['hp'] + heal)
        msgs.append(add_effect(attacker, 'regen', 4))
        msgs.append(f'🍎 +{heal} ХП + Регенерация(4)!')
    elif key == 'time_feather':
        attacker['ap'] = attacker.get('ap', 0) + 2
        msgs.append('🪶 Получено +2 АП (дополнительный ход)!')
    elif key == 'stardust_seal':
        msgs.append(add_effect(attacker, 'all_up', 4))
        msgs.append('✨ +25% крит на 2 хода + повышение всех характ.!')
    elif key == 'meteor_fragment':
        # Сильный урон
        base_dmg = 20
        defender['hp'] = max(0, defender['hp'] - base_dmg)
        if defender['hp'] < defender['max_hp'] * 0.5:
            base_dmg = round(base_dmg * 1.5)
            defender['hp'] = max(0, defender['hp'] - round(base_dmg * 0.5))
        msgs.append(f'☄️ Нанесено {base_dmg} урона!')
        msgs.append(add_effect(defender, 'stun', 2))
        msgs.append(add_effect(defender, 'vulnerability', 3))
    else:
        msgs.append(f'✅ Артефакт использован: {art["effect"]}')

    # Устанавливаем кулдаун
    cooldowns[key] = art['cooldown']
    attacker['artifact_cooldowns'] = cooldowns

    return msgs


# ═══════════════════════════════════════════════════════════
#  Пассивные бонусы артефактов
# ═══════════════════════════════════════════════════════════

def apply_passive_artifact_stats(fighter: dict):
    """
    Применяет пассивные артефакты к характеристикам бойца.
    Вызывается при старте боя.
    """
    for art_slot in ['artifact1', 'artifact2']:
        art_name = fighter.get(art_slot)
        if not art_name or art_name not in ARTIFACTS:
            continue
        art = ARTIFACTS[art_name]
        if art['type'] != 'passive':
            continue
        key = art['effect_key']

        if key == 'luck_pin':
            fighter['lck'] += 1
        elif key == 'smooth_stone':
            fighter['con'] += 1
        elif key == 'amber_drop':
            fighter['int'] += 1
        elif key == 'memory_knot':
            fighter['cha'] += 1
        elif key == 'wind_feather':
            fighter['speed'] = fighter.get('speed', 5) + 1
        elif key == 'plush_talisman':
            fighter['con'] += 1
            fighter['max_hp'] += 2
            fighter['hp'] = fighter['max_hp']
        elif key == 'str_amulet':
            fighter['str'] += 1
        elif key == 'wind_talisman':
            fighter['speed'] = fighter.get('speed', 5) + 1
        elif key == 'protection_thread':
            fighter['con'] += 1
        elif key == 'small_book':
            fighter['int'] += 1
        elif key == 'copper_ring':
            fighter['lck'] += 1
        elif key == 'night_feather':
            fighter['dex'] += 1
        elif key == 'warm_scarf':
            fighter['con'] += 1
            # +1 щит в начале хода — обрабатывается отдельно
        elif key == 'dry_ear':
            fighter['con'] += 1
        elif key == 'totem_chip':
            fighter['str'] += 1
        elif key == 'spellcaster_bracelet':
            fighter['int'] += 4
        elif key == 'destroyer_glove':
            fighter['str'] += 4
        elif key == 'clarity_glasses':
            fighter['immunity'] = fighter.get('immunity', [])
            if 'blind' not in fighter['immunity']:
                fighter['immunity'].append('blind')
        elif key == 'double_strike_ring':
            pass  # обрабатывается в do_attack
        elif key == 'ancient_seal':
            stats = ['str', 'dex', 'con', 'int', 'cha', 'lck']
            for s in stats:
                fighter[s] += 2
            if all(fighter.get(s, 0) >= 8 for s in stats):
                for s in stats:
                    fighter[s] += 2
        elif key == 'galaxy_heart':
            for s in ['str', 'dex', 'con', 'int', 'cha', 'lck']:
                fighter[s] += 5
        elif key == 'rainbow_crown':
            fighter['cha'] += 4
            fighter['lck'] += 4


# ═══════════════════════════════════════════════════════════
#  Ход гоблина
# ═══════════════════════════════════════════════════════════

def execute_goblin_action(goblin: dict, player: dict, action: dict) -> list[str]:
    msgs = []
    key = action['key']

    # Кровотечение при действии
    msgs.extend(apply_bleed_on_action(goblin))
    if goblin['hp'] <= 0:
        return msgs

    # Оглушение / заморозка
    if is_stunned(goblin):
        msgs.append(consume_stun(goblin))
        return msgs

    if key == 'caution':
        goblin['defending'] = True
        goblin['speed'] = goblin.get('speed', 5) + action.get('speed_bonus', 0)
        msgs.append('🛡️ Гоблин принял защитную стойку!')
        return msgs

    # Атакующие действия
    dmg_min = action.get('dmg_min', 3)
    dmg_max = action.get('dmg_max', 6)
    base_dmg = random.randint(dmg_min, dmg_max)

    extra_crit = action.get('extra_crit_bonus', 0)
    goblin_dex = goblin.get('dex', 4)
    crit_chance = 5 + goblin_dex * 0.5 + extra_crit
    is_crit = random.randint(1, 100) <= crit_chance

    if is_crit:
        base_dmg = round(base_dmg * 1.5)
        msgs.append('💥 Гоблин нанёс критический удар!')

    # Проверяем попадание
    goblin_dex = goblin.get('dex', 4)
    player_dex = effective_stat(player, 'dex')
    hit_chance = calculate_hit_chance(goblin_dex, player_dex)
    dodge_chance = calculate_dodge_chance(player)
    final_hit = hit_chance - dodge_chance

    if random.randint(1, 100) > final_hit:
        msgs.append('💨 Гоблин промахнулся!')
        return msgs

    # Снимаем скрытность игрока
    if player['effects'].get('stealth', 0) > 0:
        del player['effects']['stealth']

    # Уязвимость
    if player['effects'].get('vulnerability', 0) > 0:
        base_dmg = round(base_dmg * 1.5)

    # Броня игрока
    dmg = apply_armor_reduction(base_dmg, player.get('kd', 10))

    # Защита
    if player.get('defending', False):
        dmg = max(1, round(dmg * 0.5))
        msgs.append('🛡️ Защита снизила урон!')

    # Щит
    if player.get('shield', 0) > 0:
        absorbed = min(player['shield'], dmg)
        dmg -= absorbed
        player['shield'] -= absorbed

    final_dmg = max(1, dmg)
    player['hp'] = max(0, player['hp'] - final_dmg)
    msgs.append(f'👹 Гоблин: -{final_dmg} ХП игроку!')

    # Специальные эффекты гоблина
    if key == 'quick_lunge' and is_crit and action.get('extra_turn_on_crit'):
        goblin['_extra_turn'] = True
        msgs.append('⚡ Гоблин получил дополнительный ход!')
    elif key == 'dirty_trick':
        msgs.append(add_effect(player, 'bleed', action.get('apply_bleed', 1)))
        if random.randint(1, 100) <= action.get('blind_chance', 30):
            msgs.append(add_effect(player, 'blind', 1))

    # Шипы игрока при атаке гоблина
    if player['effects'].get('thorns', 0) > 0:
        thorns_dmg = player['effects']['thorns']
        goblin['hp'] = max(0, goblin['hp'] - thorns_dmg)
        msgs.append(f'🌵 Шипы нанесли {thorns_dmg} урона гоблину!')

    return msgs


# ═══════════════════════════════════════════════════════════
#  Инициализация нового боя
# ═══════════════════════════════════════════════════════════

def init_battle(fighter_row: dict) -> dict:
    """Создаёт начальное состояние боя из записи бойца в БД."""
    from arena_db import build_battle_fighter

    player = build_battle_fighter(fighter_row)
    apply_passive_artifact_stats(player)

    # Пересчитываем КД с учётом артефактов
    player['kd'] = calc_kd(player['dex'])
    # Пересчитываем скорость
    player['speed'] = calc_speed(player['class'], player['dex'], player['lck'])
    # Пересчитываем после артефактов
    player['max_hp']   = calc_max_hp(player['class'], player['level'], player['con'])
    player['hp']       = player['max_hp']
    player['max_mana'] = calc_max_mana(player['class'], player['level'],
                                       player['int'], player['cha'])
    player['mana']     = player['max_mana']

    goblin = {
        'name':      GOBLIN_DATA['name'],
        'max_hp':    GOBLIN_DATA['max_hp'],
        'hp':        GOBLIN_DATA['max_hp'],
        'speed':     GOBLIN_DATA['speed'],
        'dex':       GOBLIN_DATA['dex'],
        'kd':        GOBLIN_DATA['kd'],
        'effects':   {},
        'defending': False,
        'shield':    0,
        '_extra_turn': False,
    }

    first_action = pick_goblin_action()

    state = {
        'player':            player,
        'enemy':             goblin,
        'goblin_next_action': first_action,
        'round':             1,
        'log':               [f'Вы встретили {goblin["name"]}!\nОн собирается: {first_action["name"]}'],
        'phase':             'player_turn',  # player_turn | goblin_turn | finished
        'winner':            None,  # 'player' | 'goblin'
    }
    return state
