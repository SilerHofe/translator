"""
Лабораторная работа №2: Перевод исходной программы в ОПЗ
Вариант 10: JavaScript → R

ЦЕПОЧКА ЗАПУСКА:
  Шаг 1: python main.py [input.js]   — Лаба 1, создаёт output_tokens.txt и таблицы
  Шаг 2: python main2.py             — Лаба 2, читает output_tokens.txt, строит ОПЗ

Лаба 2 принимает на вход РЕЗУЛЬТАТ Лабы 1 (файлы output_*.txt),
а не исходный JS напрямую. Это соответствует методичке стр. 45:
«в реальном трансляторе входной текст является результатом работы
лексического анализатора».

Опционально можно указать другой префикс:
  python main2.py myprefix     — читает myprefix_tokens.txt и т.д.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load_tables import load_lab1_results, print_loaded_tokens
from rpn         import RpnTranslator, format_rpn, print_rpn_process


# ============================================================
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ВЫВОДА
# ============================================================

def sep(title: str):
    pad = max(0, (65 - len(title) - 2) // 2)
    print(f"\n{'─'*pad} {title} {'─'*(max(0,65-pad-len(title)-2))}")


def save_rpn(elements, prefix='output2'):
    """Сохраняет ОПЗ в файл."""
    fname = f"{prefix}_rpn.txt"
    with open(fname, 'w', encoding='utf-8') as f:
        f.write("ОБРАТНАЯ ПОЛЬСКАЯ ЗАПИСЬ (ОПЗ)\n")
        f.write("Лабораторная работа №2  |  Вариант 10: JavaScript → R\n")
        f.write("─" * 55 + "\n\n")
        f.write("Строка ОПЗ:\n")
        f.write(format_rpn(elements) + "\n\n")
        f.write("─" * 55 + "\n")
        f.write(f"{'№':<5} {'Элемент':<22} Вид\n")
        f.write("─" * 55 + "\n")
        for idx, e in enumerate(elements, 1):
            f.write(f"{idx:<5} {e.display():<22} {e.kind}\n")
    print(f"  ✓ {fname}")


# ============================================================
#  ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

def main():
    # Определяем префикс входных файлов
    prefix = sys.argv[1] if len(sys.argv) > 1 else 'output'

    print("=" * 65)
    print("  ЛАБОРАТОРНАЯ РАБОТА №2: ПЕРЕВОД В ОПЗ")
    print("  Вариант 10: JavaScript → R")
    print("=" * 65)

    # ── Шаг 1: Загрузка результатов Лабы 1 ──
    sep(f"ЗАГРУЗКА РЕЗУЛЬТАТОВ ЛАБЫ 1 (префикс: {prefix})")
    print()

    try:
        tokens = load_lab1_results(prefix=prefix)
    except FileNotFoundError as e:
        print(f"\n  ОШИБКА: {e}")
        sys.exit(1)

    print(f"  Загружено токенов: {len(tokens)}")
    print(f"  Источник: {prefix}_tokens.txt")
    print(f"  Таблицы:  {prefix}_I_identifiers.txt,")
    print(f"            {prefix}_N_numbers.txt,")
    print(f"            {prefix}_C_strings.txt")

    # ── Шаг 2: Показываем загруженный поток токенов ──
    sep("ВХОДНОЙ ПОТОК ТОКЕНОВ (из файла Лабы 1)")
    print_loaded_tokens(tokens)

    # ── Шаг 3: Перевод в ОПЗ алгоритмом Дейкстры ──
    sep("ПЕРЕВОД В ОПЗ (алгоритм Дейкстры)")
    translator = RpnTranslator()
    elements   = translator.translate(tokens)

    # ── Шаг 4: Вывод результата ──
    sep("ОПЗ — СТРОКА РЕЗУЛЬТАТА")
    print()
    rpn_str = format_rpn(elements)
    words   = rpn_str.split()
    line    = "  "
    for w in words:
        if len(line) + len(w) + 1 > 78:
            print(line)
            line = "  " + w
        else:
            line += (" " if line.strip() else "") + w
    if line.strip():
        print(line)

    sep("ТАБЛИЦА ЭЛЕМЕНТОВ ОПЗ")
    print_rpn_process(elements)

    sep("ТАБЛИЦА ПРИОРИТЕТОВ (адаптация для JS)")
    rows = [
        ("if, (, [, Ф, АЭМ, while",           "0", "открывающие — не выталкиваются"),
        (";, ), ]",                            "1", "закрывающие"),
        ("= (присваивание O12)",               "2", "правоассоциативное"),
        ("==, !=, <, >, <=, >= (O6–O11)",      "3", "операции сравнения"),
        ("+, - (O1, O2)",                      "4", "аддитивные"),
        ("*, /, % (O3, O4, O5)",               "5", "мультипликативные"),
        ("^ (O13)",                            "6", "возведение в степень"),
        ("function, var, return, while, :, НП, КП, КО", "7", "описательные"),
    ]
    print(f"\n  {'Входной элемент':<38} {'Приор.':<8} Примечание")
    print(f"  {'─'*38} {'─'*8} {'─'*28}")
    for el, prio, note in rows:
        print(f"  {el:<38} {prio:<8} {note}")

    # ── Шаг 5: Сохранение ──
    sep("СОХРАНЕНИЕ")
    print()
    save_rpn(elements, prefix='output2')

    print("\n" + "=" * 65)
    print(f"  Готово. Результат: output2_rpn.txt")
    print("=" * 65)


if __name__ == '__main__':
    main()