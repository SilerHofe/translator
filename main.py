"""
Лабораторная работа №1: Лексический анализатор JS → R
Вариант 10

Запуск:
    python main.py input.js       — анализ файла
    python main.py                — встроенный тестовый пример
"""

import sys
import os
from lexer import (LexicalAnalyzer, KEYWORDS, OPERATIONS,
                   PART_OF_TWO_LIT, SEPARATORS)

# ============================================================
#  ТЕСТОВАЯ ПРОГРАММА НА JAVASCRIPT
# ============================================================
TEST_JS = """\
// Лабораторная работа №1 — тестовая программа на JavaScript

var a1;
var a2;
a1 = 15;
a2 = 4;

// Числовые константы разных типов
var x;
x = 123.45;
x = .25;
x = 25.;
x = 1.23e-5;
x = 1.5E+10;

// Строковые константы
var str;
str = "Привет мир";
str = 'hello';

// Операции
var sum;
var mult;
sum = a1 + a2;
mult = a1 * a2;

// Вывод через console.log
console.log("Сумма:");
console.log(sum);
console.log("Произведение:");
console.log(mult);

// Условный оператор
if (a1 > a2) {
    console.log("a1 больше a2");
} else {
    console.log("a2 >= a1");
}

// Функция
function square(x) {
    var result;
    result = x * x;
    return result;
}

/* Блочный комментарий
   занимает несколько строк */

var sq;
sq = square(a1);
console.log("Квадрат a1:");
console.log(sq);

// Цикл
var i;
i = 1;
while (i <= 3) {
    console.log(i);
    i = i + 1;
}

// Массив
var arr;
arr = new array(10);
arr[0] = 42;
arr[i + 1] = 100;
"""

# ============================================================
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ВЫВОДА
# ============================================================

def sep(title='', width=65, char='─'):
    if title:
        s = (width - len(title) - 2) // 2
        print(f"\n{char*s} {title} {char*(width - s - len(title) - 2)}")
    else:
        print(char * width)


def print_two_col_table(rows, col1, col2, width1=30, width2=10):
    """Печатает таблицу из двух столбцов."""
    print(f"  {col1:<{width1}} {col2}")
    print(f"  {'─'*width1} {'─'*width2}")
    for k, v in rows:
        print(f"  {str(k):<{width1}} {v}")


def print_tables(analyzer: LexicalAnalyzer):
    """Печатает все таблицы лексем."""

    sep("ТАБЛИЦА СЛУЖЕБНЫХ СЛОВ (W) — постоянная")
    print_two_col_table(
        sorted(KEYWORDS.items(), key=lambda x: x[1]),
        "Служебное слово", "Код", 30, 5
    )

    sep("ТАБЛИЦА ОПЕРАЦИЙ (O) — постоянная")
    print_two_col_table(
        sorted(OPERATIONS.items(), key=lambda x: x[1]),
        "Операция", "Код", 30, 5
    )

    sep("ВСПОМОГАТЕЛЬНАЯ ТАБЛИЦА (начало двулитерных операций)")
    print_two_col_table(
        sorted(PART_OF_TWO_LIT.items(), key=lambda x: x[1]),
        "Символ", "Код", 30, 5
    )

    sep("ТАБЛИЦА РАЗДЕЛИТЕЛЕЙ (R) — постоянная")
    display_seps = [(repr(k) if k in (' ', '\t') else k, v)
                    for k, v in SEPARATORS.items() if k != '\t']
    print_two_col_table(
        sorted(display_seps, key=lambda x: x[1]),
        "Разделитель", "Код", 30, 5
    )

    sep("ТАБЛИЦА ИДЕНТИФИКАТОРОВ (I) — временная")
    if analyzer.id_table:
        print_two_col_table(
            sorted(analyzer.id_table.items(), key=lambda x: x[1]),
            "Идентификатор", "Код", 30, 5
        )
    else:
        print("  (пусто)")

    sep("ТАБЛИЦА ЧИСЛОВЫХ КОНСТАНТ (N) — временная")
    if analyzer.num_table:
        print_two_col_table(
            sorted(analyzer.num_table.items(), key=lambda x: x[1]),
            "Константа", "Код", 30, 5
        )
    else:
        print("  (пусто)")

    sep("ТАБЛИЦА СТРОКОВЫХ КОНСТАНТ (C) — временная")
    if analyzer.str_table:
        print_two_col_table(
            sorted(analyzer.str_table.items(), key=lambda x: x[1]),
            "Строка", "Код", 30, 5
        )
    else:
        print("  (пусто)")


def print_example_parse(analyzer: LexicalAnalyzer, source_code: str):
    """
    Печатает пример работы лексического анализатора построчно
    (как в методичке стр. 12-13): входная строка → выходная последовательность.
    """
    sep("ПРИМЕР РАБОТЫ ЛЕКСИЧЕСКОГО АНАЛИЗАТОРА")
    print(f"\n  {'Входная строка':<50} Выходная последовательность")
    print(f"  {'─'*50} {'─'*30}")

    lines = source_code.split('\n')
    for i, (line, tokens) in enumerate(zip(lines, analyzer.tokens_by_line)):
        internal = analyzer.get_line_repr(tokens)
        if line.strip() or internal:  # пропускаем пустые строки без токенов
            display_line = line if len(line) <= 48 else line[:45] + '...'
            print(f"  {display_line:<50} {internal}")


def save_tables(analyzer: LexicalAnalyzer, source_code: str, prefix='output'):
    """Сохраняет все таблицы и внутреннее представление в файлы."""

    def write(fname, content):
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✓ {fname}")

    print("\nСохранение файлов:")

    # Постоянные таблицы
    lines = ["ТАБЛИЦА СЛУЖЕБНЫХ СЛОВ (W)\n", f"{'Слово':<20} Код\n", "─"*25+"\n"]
    lines += [f"{w:<20} {c}\n" for w, c in sorted(KEYWORDS.items(), key=lambda x: x[1])]
    write(f"{prefix}_W_keywords.txt", ''.join(lines))

    lines = ["ТАБЛИЦА ОПЕРАЦИЙ (O)\n", f"{'Операция':<20} Код\n", "─"*25+"\n"]
    lines += [f"{op:<20} {c}\n" for op, c in sorted(OPERATIONS.items(), key=lambda x: x[1])]
    write(f"{prefix}_O_operations.txt", ''.join(lines))

    lines = ["ТАБЛИЦА РАЗДЕЛИТЕЛЕЙ (R)\n", f"{'Разделитель':<20} Код\n", "─"*25+"\n"]
    for sep_char, c in sorted(SEPARATORS.items(), key=lambda x: x[1]):
        if sep_char == '\t':
            continue
        display = repr(sep_char) if sep_char == ' ' else sep_char
        lines.append(f"{display:<20} {c}\n")
    write(f"{prefix}_R_separators.txt", ''.join(lines))

    # Временные таблицы
    lines = ["ТАБЛИЦА ИДЕНТИФИКАТОРОВ (I)\n", f"{'Идентификатор':<20} Код\n", "─"*25+"\n"]
    lines += [f"{n:<20} {c}\n" for n, c in sorted(analyzer.id_table.items(), key=lambda x: x[1])]
    write(f"{prefix}_I_identifiers.txt", ''.join(lines))

    lines = ["ТАБЛИЦА ЧИСЛОВЫХ КОНСТАНТ (N)\n", f"{'Константа':<20} Код\n", "─"*25+"\n"]
    lines += [f"{v:<20} {c}\n" for v, c in sorted(analyzer.num_table.items(), key=lambda x: x[1])]
    write(f"{prefix}_N_numbers.txt", ''.join(lines))

    lines = ["ТАБЛИЦА СТРОКОВЫХ КОНСТАНТ (C)\n", f"{'Строка':<30} Код\n", "─"*35+"\n"]
    lines += [f"{v:<30} {c}\n" for v, c in sorted(analyzer.str_table.items(), key=lambda x: x[1])]
    write(f"{prefix}_C_strings.txt", ''.join(lines))

    # Внутреннее представление — построчно
    out_lines = []
    src_lines = source_code.split('\n')
    for src_line, tok_line in zip(src_lines, analyzer.tokens_by_line):
        internal = analyzer.get_line_repr(tok_line)
        if internal:
            out_lines.append(internal + '\n')
    write(f"{prefix}_tokens.txt", ''.join(out_lines))


# ============================================================
#  ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

def main():
    W = 65

    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        with open(sys.argv[1], encoding='utf-8') as f:
            source = f.read()
        print(f"Входной файл: {sys.argv[1]}")
    else:
        source = TEST_JS

    print('═' * W)
    print('  ЛР №1: Лексический анализатор  JS → R  |  Вариант 10')
    print('═' * W)

    # ── Входной файл ──
    sep("ВХОДНОЙ ФАЙЛ (JavaScript)")
    for i, line in enumerate(source.splitlines(), 1):
        print(f"  {i:>3}│ {line}")

    # ── Лексический анализ ──
    analyzer = LexicalAnalyzer()
    analyzer.analyze(source)

    # ── Таблицы ──
    sep("ТАБЛИЦЫ ЛЕКСЕМ")
    print_tables(analyzer)

    # ── Пример работы построчно ──
    print_example_parse(analyzer, source)

    # ── Полное внутреннее представление ──
    sep("ПОЛНОЕ ВНУТРЕННЕЕ ПРЕДСТАВЛЕНИЕ")
    tokens_list = analyzer.get_internal_repr().split()
    for i in range(0, len(tokens_list), 12):
        print("  " + ' '.join(tokens_list[i:i+12]))

    # ── Ошибки ──
    if analyzer.errors:
        sep("ОШИБКИ")
        for e in analyzer.errors:
            print(f"  [!] {e}")
    else:
        print(f"\n  Ошибок лексического анализа не обнаружено.")

    # ── Сохранение файлов ──
    save_tables(analyzer, source, prefix='output')

    print('\n' + '═' * W)
    print("  Лексический анализ завершён.")
    print('═' * W)


if __name__ == '__main__':
    main()