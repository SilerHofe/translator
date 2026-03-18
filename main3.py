"""
Лабораторная работа №3: Генерация кода на языке R
Вариант 10: JavaScript → R

ЦЕПОЧКА ЗАПУСКА:
  python main.py [input.js]   — Лаба 1: лексический анализ
  python main2.py             — Лаба 2: перевод в ОПЗ
  python main3.py             — Лаба 3: генерация кода R  ← этот файл

Читает: output2_rpn.txt (результат Лабы 2)
Пишет:  output3_r.R    (программа на языке R)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from codegen import (CodeGenerator, load_rpn, format_r_code,
                     format_r_code_clean, save_r_code, print_trace_table)


def sep(title: str):
    pad = max(0, (65 - len(title) - 2) // 2)
    print(f"\n{'─'*pad} {title} {'─'*(max(0,65-pad-len(title)-2))}")


def main():
    rpn_file = sys.argv[1] if len(sys.argv) > 1 else 'output2_rpn.txt'

    print("=" * 65)
    print("  ЛАБОРАТОРНАЯ РАБОТА №3: ГЕНЕРАЦИЯ КОДА R")
    print("  Вариант 10: JavaScript → R")
    print("=" * 65)

    # ── Шаг 1: Загрузка ОПЗ из Лабы 2 ──
    sep(f"ЗАГРУЗКА ОПЗ (файл: {rpn_file})")
    print()
    try:
        elements = load_rpn(rpn_file)
    except FileNotFoundError as e:
        print(f"  ОШИБКА: {e}")
        sys.exit(1)
    print(f"  Загружено элементов ОПЗ: {len(elements)}")

    # ── Шаг 2: Генерация кода ──
    sep("ГЕНЕРАЦИЯ КОДА (МП-автомат)")
    gen   = CodeGenerator()
    lines = gen.generate(elements)
    print(f"  Сгенерировано строк кода: {len(lines)}")
    print(f"  Вспомогательных переменных: {gen.P}")
    print(f"  Меток: {len(gen.label_table)}")

    # ── Шаг 3: Таблица меток ──
    if gen.label_table:
        sep("ТАБЛИЦА МЕТОК")
        print(f"\n  {'Метка':<10} Строка R")
        print(f"  {'─'*10} {'─'*10}")
        for lbl, num in sorted(gen.label_table.items()):
            print(f"  {lbl:<10} {num}")

    # ── Шаг 4: Трассировка МП-автомата ──
    sep("ТРАССИРОВКА МП-АВТОМАТА (таблица 3.2)")
    print_trace_table(gen.trace)

    # ── Шаг 5: Вывод кода R ──
    sep("СГЕНЕРИРОВАННЫЙ КОД R")
    print()
    print(format_r_code(lines))

    # ── Шаг 6: Сохранение ──
    sep("СОХРАНЕНИЕ")
    print()
    save_r_code(lines, gen.label_table, prefix='output3')

    print("\n" + "=" * 65)
    print("  Готово. Результат: output3_r.R")
    print("=" * 65)


if __name__ == '__main__':
    main()