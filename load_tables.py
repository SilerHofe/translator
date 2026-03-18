"""
Загрузчик таблиц Лабы 1.

Читает файлы, сохранённые Лабой 1:
  output_tokens.txt          — внутреннее представление (W1 I1 R3 ...)
  output_I_identifiers.txt   — таблица идентификаторов
  output_N_numbers.txt        — таблица числовых констант
  output_C_strings.txt        — таблица строковых констант
  output_W_keywords.txt       — таблица служебных слов
  output_O_operations.txt     — таблица операций

Восстанавливает список объектов Token(token_class, code, value),
который Лаба 2 использует как входные данные.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from lexer import Token, KEYWORDS, OPERATIONS, SEPARATORS


def _reverse(d: dict) -> dict:
    """Переворачивает словарь {ключ: код} → {код: ключ}."""
    return {v: k for k, v in d.items()}


# Постоянные таблицы (известны заранее из lexer.py)
_W_BY_CODE = _reverse(KEYWORDS)
_O_BY_CODE = _reverse(OPERATIONS)
_R_BY_CODE = _reverse(SEPARATORS)


def load_id_table(path: str) -> dict:
    """
    Читает output_I_identifiers.txt.
    Возвращает {код: имя}.
    """
    result = {}
    if not os.path.exists(path):
        return result
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('─') or line.startswith('Код') or line.startswith('ТАБ'):
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    code = int(parts[0])
                    name = parts[1]
                    result[code] = name
                except ValueError:
                    continue
    return result


def load_num_table(path: str) -> dict:
    """
    Читает output_N_numbers.txt.
    Возвращает {код: значение}.
    """
    result = {}
    if not os.path.exists(path):
        return result
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('─') or line.startswith('Кон') or line.startswith('ТАБ'):
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    value = parts[0]
                    code  = int(parts[1])
                    result[code] = value
                except ValueError:
                    continue
    return result


def load_str_table(path: str) -> dict:
    """
    Читает output_C_strings.txt.
    Возвращает {код: значение}.
    """
    result = {}
    if not os.path.exists(path):
        return result
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('─') or line.startswith('Стр') or line.startswith('ТАБ'):
                continue
            parts = line.split()
            # Формат: "текст строки    код    тип"
            # код — второй с конца, тип — последний
            if len(parts) >= 3:
                try:
                    code = int(parts[-2])
                    # Значение — всё до кода
                    value = ' '.join(parts[:-2])
                    result[code] = value
                except ValueError:
                    continue
    return result


def parse_token_string(token_str: str,
                       id_table: dict,
                       num_table: dict,
                       str_table: dict) -> list:
    """
    Парсит строку вида 'W1 I1 O12 N3 R3 ...'
    Возвращает список объектов Token с восстановленными значениями.
    """
    tokens = []
    for item in token_str.split():
        if not item:
            continue
        tc   = item[0]          # W / I / O / R / N / C
        code_str = item[1:]

        try:
            code = int(code_str)
        except ValueError:
            continue

        # Восстанавливаем значение по коду и классу
        if tc == 'W':
            value = _W_BY_CODE.get(code, f'W{code}')
        elif tc == 'I':
            value = id_table.get(code, f'id{code}')
        elif tc == 'O':
            value = _O_BY_CODE.get(code, f'op{code}')
        elif tc == 'R':
            value = _R_BY_CODE.get(code, f'r{code}')
        elif tc == 'N':
            value = num_table.get(code, f'{code}')
        elif tc == 'C':
            value = str_table.get(code, f'str{code}')
        else:
            value = item

        tokens.append(Token(token_class=tc, code=code, value=value))

    return tokens


def load_lab1_results(prefix: str = 'output') -> list:
    """
    Главная функция: читает все файлы Лабы 1 по префиксу
    и возвращает полный список токенов Token.

    prefix — общий префикс файлов (например 'output' даёт 'output_tokens.txt' и т.д.)
    """
    tokens_file = f"{prefix}_tokens.txt"
    id_file     = f"{prefix}_I_identifiers.txt"
    num_file    = f"{prefix}_N_numbers.txt"
    str_file    = f"{prefix}_C_strings.txt"

    if not os.path.exists(tokens_file):
        raise FileNotFoundError(
            f"Файл токенов не найден: {tokens_file}\n"
            f"Сначала запустите Лабу 1: python main.py [input.js]"
        )

    id_table  = load_id_table(id_file)
    num_table = load_num_table(num_file)
    str_table = load_str_table(str_file)

    all_tokens = []
    with open(tokens_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                line_tokens = parse_token_string(line, id_table, num_table, str_table)
                all_tokens.extend(line_tokens)

    return all_tokens


def print_loaded_tokens(tokens: list):
    """Выводит загруженные токены в табличном виде."""
    print(f"\n  {'№':<5} {'Класс':<6} {'Код':<5} Значение")
    print(f"  {'─'*5} {'─'*6} {'─'*5} {'─'*25}")
    for idx, tok in enumerate(tokens, 1):
        print(f"  {idx:<5} {tok.token_class:<6} {tok.code:<5} {tok.value}")