import random

# ===== СИМВОЛЫ =====
SM_SYMBOLS = ['🍋', '🍒', '🍀', '🔔', '💎', '👑', '😈']
SM_WEIGHTS = [25, 25, 15, 15, 12, 7.97, 0.03]

SM_SYMBOL_MULT = {
    '🍋': 1.1,
    '🍒': 1.3,
    '🍀': 1.5,
    '🔔': 2.0,
    '💎': 3.0,
    '👑': 5.0,
    '😈': 8.0,
}

# ===== ПАТТЕРНЫ КОМБИНАЦИЙ =====
# Сетка: 3 строки × 5 столбцов (индексы: строки 0-2, столбцы 0-4)
# Все клетки паттерна должны содержать ОДИНАКОВЫЙ символ

def _build_patterns():
    """
    Возвращает список: (name, combo_mult, is_complex, frozenset_of_cells)
    Порядок важен: сложные идут первыми (для логики перекрытия).
    """
    patterns = []

    # ── ПРОСТЫЕ (могут быть перекрыты сложными) ─────────────────────

    # Горизонталь M (×1.0): 3 подряд одинаковых в любой строке
    # □□□□□        □□□□□        □□□□□
    # ■■■□□  или   □■■■□  или   □□■■■
    # □□□□□        □□□□□        □□□□□
    for r in range(3):
        for c in range(3):  # стартовые позиции: 0,1,2
            patterns.append(('Горизонталь M', 1.0, False,
                              frozenset([(r, c), (r, c+1), (r, c+2)])))

    # Вертикаль M (×1.0): весь столбец (все 3 строки)
    # □□■□□
    # □□■□□
    # □□■□□
    for c in range(5):
        patterns.append(('Вертикаль M', 1.0, False,
                          frozenset([(0, c), (1, c), (2, c)])))

    # Диагональ M (×1.0): 3-клеточные диагонали (оба направления)
    # Вправо-вниз: (0,c),(1,c+1),(2,c+2)
    for c in range(3):
        patterns.append(('Диагональ M', 1.0, False,
                          frozenset([(0, c), (1, c+1), (2, c+2)])))
    # Влево-вниз: (0,c),(1,c-1),(2,c-2)
    for c in range(2, 5):
        patterns.append(('Диагональ M', 1.0, False,
                          frozenset([(0, c), (1, c-1), (2, c-2)])))

    # ── СЛОЖНЫЕ (перекрывают простые) ───────────────────────────────

    # Горизонталь L (×2.0): 4 подряд одинаковых в любой строке
    for r in range(3):
        for c in range(2):  # стартовые позиции: 0,1
            patterns.append(('Горизонталь L', 2.0, True,
                              frozenset([(r, c), (r, c+1), (r, c+2), (r, c+3)])))

    # Горизонталь XL (×3.0): полная строка из 5 одинаковых
    # ■■■■■
    # □□□□□
    # □□□□□
    for r in range(3):
        patterns.append(('Горизонталь XL', 3.0, True,
                          frozenset([(r, c) for c in range(5)])))

    # Вверх (×4.0): треугольник вершиной вверх
    # □□■□□
    # □■■■□
    # ■■■■■
    patterns.append(('Вверх', 4.0, True, frozenset([
        (0, 2),
        (1, 1), (1, 2), (1, 3),
        (2, 0), (2, 1), (2, 2), (2, 3), (2, 4),
    ])))

    # Вниз (×4.0): треугольник вершиной вниз
    # ■■■■■
    # □■■■□
    # □□■□□
    patterns.append(('Вниз', 4.0, True, frozenset([
        (0, 0), (0, 1), (0, 2), (0, 3), (0, 4),
        (1, 1), (1, 2), (1, 3),
        (2, 2),
    ])))

    # Небо (×7.0): верхний ряд полный + боковые столбцы
    # ■■■■■
    # ■□■□■
    # ■□□□■
    patterns.append(('Небо', 7.0, True, frozenset([
        (0, 0), (0, 1), (0, 2), (0, 3), (0, 4),
        (1, 0),          (1, 2),          (1, 4),
        (2, 0),                           (2, 4),
    ])))

    # Земля (×7.0): нижний ряд полный + боковые столбцы
    # ■□□□■
    # ■□■□■
    # ■■■■■
    patterns.append(('Земля', 7.0, True, frozenset([
        (0, 0),                           (0, 4),
        (1, 0),          (1, 2),          (1, 4),
        (2, 0), (2, 1), (2, 2), (2, 3), (2, 4),
    ])))

    # Глаз (×8.0): рамка центральной зоны
    # □■■■□
    # ■□■□■
    # □■■■□
    patterns.append(('Глаз', 8.0, True, frozenset([
        (0, 1), (0, 2), (0, 3),
        (1, 0),          (1, 2),          (1, 4),
        (2, 1), (2, 2), (2, 3),
    ])))

    # Джекпот (×10.0): все 15 клеток одинаковые
    patterns.append(('Джекпот', 10.0, True,
                      frozenset([(r, c) for r in range(3) for c in range(5)])))

    return patterns


SM_PATTERNS = _build_patterns()


# ===== ОСНОВНЫЕ ФУНКЦИИ =====

def sm_spin(luck=0):
    """
    Генерирует случайную сетку 3×5 с механикой удачи.
    luck = 0..20, шанс скопировать любой предыдущий символ из уже сгенерированных.
    Порядок генерации: по столбцам сверху вниз.
    """
    grid = [[None]*5 for _ in range(3)]
    all_prev = []  # все сгенерированные символы по порядку

    for col in range(5):
        for row in range(3):
            if all_prev and luck > 0 and random.random() < luck / 100:
                sym = random.choice(all_prev)  # копируем любой из прошлых
            else:
                sym = random.choices(SM_SYMBOLS, weights=SM_WEIGHTS, k=1)[0]
            grid[row][col] = sym
            all_prev.append(sym)

    return grid


def sm_check_wins(grid):
    """
    Проверяет все паттерны на сетке.
    Возвращает список выигрышей (словари).
    Сложные комбинации перекрывают простые.
    """
    raw_wins = []
    seen_keys = set()

    for name, combo_mult, is_complex, cells in SM_PATTERNS:
        # Проверяем: все клетки одинаковы?
        symbols = [grid[r][c] for r, c in cells]
        if len(set(symbols)) != 1:
            continue

        sym = symbols[0]
        key = (name, sym, cells)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        raw_wins.append({
            'name': name,
            'symbol': sym,
            'sym_mult': SM_SYMBOL_MULT[sym],
            'combo_mult': combo_mult,
            'is_complex': is_complex,
            'cells': cells,
        })

    if not raw_wins:
        return []

    # Правило перекрытия: если клетки простой комбинации полностью
    # входят в клетки какой-либо сложной — простая убирается
    complex_wins = [w for w in raw_wins if w['is_complex']]
    final_wins = []

    for w in raw_wins:
        if w['is_complex']:
            final_wins.append(w)
        else:
            covered = any(w['cells'].issubset(cw['cells']) for cw in complex_wins)
            if not covered:
                final_wins.append(w)

    return final_wins


def sm_render_grid(grid, revealed_cols=5):
    """
    Рендерит сетку. revealed_cols = сколько столбцов показать (остальные ❔).
    """
    lines = []
    for row in grid:
        cells = [sym if c < revealed_cols else '❔' for c, sym in enumerate(row)]
        lines.append('     | ' + ' | '.join(cells) + ' |')
    return '\n'.join(lines)


def sm_win_line(win, bet):
    """Форматирует строку одного выигрыша."""
    result = int(bet * win['sym_mult'] * win['combo_mult'])
    return (
        f"{win['name']} из {win['symbol']} "
        f"–> {bet}×{win['sym_mult']}×{win['combo_mult']} = {result} 💵"
    )


def sm_total(wins, bet):
    """Считает суммарный выигрыш."""
    return sum(int(bet * w['sym_mult'] * w['combo_mult']) for w in wins)
