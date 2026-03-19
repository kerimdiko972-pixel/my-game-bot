# ============================================================
#  arena_db.py  — Работа с базой данных для системы Арены
# ============================================================

import json
import psycopg2
import psycopg2.extras
from arena_data import (
    CLASS_BASE_STATS, STARTER_WEAPONS,
    calc_max_hp, calc_max_mana, calc_kd, calc_speed
)


def init_arena_tables(get_conn):
    conn = get_conn()
    c = conn.cursor()

    # Таблица бойцов
    c.execute('''
        CREATE TABLE IF NOT EXISTS arena_fighters (
            id          SERIAL PRIMARY KEY,
            user_id     BIGINT,
            slot        INTEGER,
            name        TEXT,
            class       TEXT,
            level       INTEGER DEFAULT 1,
            xp          INTEGER DEFAULT 0,
            sp          INTEGER DEFAULT 0,
            str         INTEGER DEFAULT 0,
            dex         INTEGER DEFAULT 0,
            con         INTEGER DEFAULT 0,
            intel       INTEGER DEFAULT 0,
            cha         INTEGER DEFAULT 0,
            lck         INTEGER DEFAULT 0,
            weapon      TEXT DEFAULT NULL,
            artifact1   TEXT DEFAULT NULL,
            artifact2   TEXT DEFAULT NULL,
            money       INTEGER DEFAULT 0,
            record_floor INTEGER DEFAULT 0,
            created_at  TIMESTAMP DEFAULT NOW(),
            UNIQUE(user_id, slot)
        )
    ''')

    # Таблица состояния боя (JSON)
    c.execute('''
        CREATE TABLE IF NOT EXISTS arena_battle_state (
            user_id     BIGINT PRIMARY KEY,
            state_json  TEXT,
            updated_at  TIMESTAMP DEFAULT NOW()
        )
    ''')

    conn.commit()
    conn.close()
    print("Arena tables initialized!")


# ─── Бойцы ───────────────────────────────────────────────────

def get_arena_fighters(get_conn, user_id):
    """Вернуть список [slot1_fighter_or_None, slot2, slot3]"""
    conn = get_conn()
    c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    c.execute('SELECT * FROM arena_fighters WHERE user_id=%s ORDER BY slot', (user_id,))
    rows = c.fetchall()
    conn.close()
    result = {1: None, 2: None, 3: None}
    for row in rows:
        result[row['slot']] = dict(row)
    return result


def create_fighter(get_conn, user_id, slot, name, cls):
    """Создать нового бойца в БД и вернуть его dict"""
    stats = CLASS_BASE_STATS[cls]
    s, d, co, i, ch, lk = stats['str'], stats['dex'], stats['con'], stats['int'], stats['cha'], stats['lck']
    weapon = STARTER_WEAPONS[cls]

    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO arena_fighters
            (user_id, slot, name, class, level, xp, sp,
             str, dex, con, intel, cha, lck, weapon, money)
        VALUES (%s,%s,%s,%s,1,0,0,%s,%s,%s,%s,%s,%s,%s,100)
        ON CONFLICT (user_id, slot) DO UPDATE SET
            name=%s, class=%s, level=1, xp=0, sp=0,
            str=%s, dex=%s, con=%s, intel=%s, cha=%s, lck=%s,
            weapon=%s, artifact1=NULL, artifact2=NULL, money=100
        RETURNING *
    ''', (
        user_id, slot, name, cls, s, d, co, i, ch, lk, weapon,
        name, cls, s, d, co, i, ch, lk, weapon
    ))
    row = c.fetchone()
    conn.commit()
    conn.close()
    return get_fighter_by_id(get_conn, row[0])


def get_fighter_by_id(get_conn, fighter_id):
    conn = get_conn()
    c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    c.execute('SELECT * FROM arena_fighters WHERE id=%s', (fighter_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_fighter_by_slot(get_conn, user_id, slot):
    conn = get_conn()
    c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    c.execute('SELECT * FROM arena_fighters WHERE user_id=%s AND slot=%s', (user_id, slot))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def update_fighter(get_conn, fighter_id, **kwargs):
    if not kwargs:
        return
    cols = ', '.join(f'{k}=%s' for k in kwargs)
    vals = list(kwargs.values()) + [fighter_id]
    conn = get_conn()
    c = conn.cursor()
    c.execute(f'UPDATE arena_fighters SET {cols} WHERE id=%s', vals)
    conn.commit()
    conn.close()


def delete_fighter(get_conn, user_id, slot):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM arena_fighters WHERE user_id=%s AND slot=%s', (user_id, slot))
    conn.commit()
    conn.close()


# ─── Состояние боя ───────────────────────────────────────────

def save_battle_state(get_conn, user_id, state: dict):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO arena_battle_state (user_id, state_json, updated_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (user_id) DO UPDATE SET
            state_json=%s, updated_at=NOW()
    ''', (user_id, json.dumps(state, ensure_ascii=False),
          json.dumps(state, ensure_ascii=False)))
    conn.commit()
    conn.close()


def load_battle_state(get_conn, user_id) -> dict | None:
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT state_json FROM arena_battle_state WHERE user_id=%s', (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None


def clear_battle_state(get_conn, user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM arena_battle_state WHERE user_id=%s', (user_id,))
    conn.commit()
    conn.close()


# ─── Вспомогательная: построить dict бойца для боя ──────────
def build_battle_fighter(fighter_row: dict) -> dict:
    """
    Преобразует запись из БД в dict для использования
    в движке боя (arena_combat.py).
    """
    cls = fighter_row['class']
    lvl = fighter_row['level']
    s   = fighter_row['str']
    d   = fighter_row['dex']
    co  = fighter_row['con']
    i   = fighter_row['intel']
    ch  = fighter_row['cha']
    lk  = fighter_row['lck']

    max_hp   = calc_max_hp(cls, lvl, co)
    max_mana = calc_max_mana(cls, lvl, i, ch)
    speed    = calc_speed(cls, d, lk)
    kd       = calc_kd(d)

    return {
        'id':        fighter_row['id'],
        'name':      fighter_row['name'],
        'class':     cls,
        'level':     lvl,
        'xp':        fighter_row['xp'],
        'str':       s, 'dex': d, 'con': co,
        'int':       i, 'cha': ch, 'lck': lk,
        'max_hp':    max_hp,
        'hp':        max_hp,
        'max_mana':  max_mana,
        'mana':      max_mana,
        'speed':     speed,
        'kd':        kd,
        'weapon':    fighter_row['weapon'],
        'artifact1': fighter_row['artifact1'],
        'artifact2': fighter_row['artifact2'],
        'money':     fighter_row['money'],
        'effects':   {},       # {effect_key: stacks}
        'shield':    0,        # временный щит
        'defending': False,    # защитное действие
        'stance':    'normal', # normal|battle|defense|precise|dodge
        'ap':        2,
        'artifact_cooldowns': {},   # {effect_key: turns_left}
        'first_attack_done': False, # для hunter_bow
        'reflect_pct': 0,
        'immunity': [],        # список иммунных эффектов
    }
