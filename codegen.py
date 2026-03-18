"""
Лабораторная работа №3: Перевод ОПЗ в текст на выходном языке R
Транслятор с языка JavaScript на язык R  |  Вариант 10

Реализует МП-автомат (методичка стр. 46–53).

Входные данные  — результат Лабы 2 (output2_rpn.txt):
  последовательность элементов ОПЗ

Выходные данные — программа на языке R (output3_r.R)

МП-автомат (методичка стр. 47):
  1. Операнд → заносится в стек
  2. Операция → семантическая процедура (извлекает операнды из стека,
     генерирует строку кода, наращивает STR)
  3. После каждой семантической процедуры STR += 1

Таблица семантических процедур (методичка табл. 3.1, адаптация для R):
  НП   → # Начало функции: имя <- function() {
  КП   → }
  ТИП  → # объявление переменных (в R нет явных объявлений)
  КО   → (пропускаем — конец описания)
  :=   → арг2 <- арг1
  +,-,*,/,%,^  → Rp <- арг2 OP арг1
  ==,!=,<,>,<=,>= → Rp <- арг2 OP арг1
  УПЛ  → if (!арг2) goto арг1  (через метку)
  БП   → goto арг1
  :    → метка арг1 в таблицу меток
  Ф    → Rp <- имя(арг1, арг2, ...)
  АЭМ  → арг1[арг2]  (заносится в стек как единый операнд)
  return → return(арг1)

Особенность R как выходного языка:
  - нет оператора goto, поэтому УПЛ и БП реализуются через
    структурные конструкции if/while которые уже закодированы в ОПЗ
  - функции объявляются через <- function(параметры) { ... }
  - нет нумерации строк (в отличие от Бейсика в примере методички)
  - поэтому таблица меток хранит символьные метки→позиции в коде
"""

import os, sys, re
from dataclasses import dataclass, field
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rpn import RpnElement


# ============================================================
#  ЗАГРУЗКА ОПЗ ИЗ ФАЙЛА ЛАБЫ 2
# ============================================================

def load_rpn(path: str) -> List[RpnElement]:
    """
    Читает output2_rpn.txt и восстанавливает список RpnElement.
    Формат файла:
      №     Элемент               Вид
      1     a1                    operand
      2     1ТИП                  ТИП
      ...
    """
    elements = []
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Файл ОПЗ не найден: {path}\n"
            f"Сначала запустите Лабу 2: python main2.py"
        )
    in_table = False
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            stripped = line.strip()
            # Заголовок таблицы
            if stripped.startswith('№') and 'Элемент' in stripped:
                in_table = True
                continue
            if not in_table:
                continue
            if stripped.startswith('─') or not stripped:
                continue
            # Строка данных: "1     a1                    operand"
            parts = stripped.split()
            if len(parts) < 2:
                continue
            # Первый токен — номер
            try:
                int(parts[0])
            except ValueError:
                continue
            # Последний токен — вид (kind)
            kind = parts[-1]
            # Всё между номером и видом — значение элемента
            value_parts = parts[1:-1]
            if not value_parts:
                continue
            value = ' '.join(value_parts)

            # Восстанавливаем count для ТИП, Ф, АЭМ
            count = 0
            display_value = value
            if kind in ('ТИП', 'Ф', 'АЭМ'):
                m = re.match(r'^(\d+)(ТИП|Ф|АЭМ)$', value)
                if m:
                    count = int(m.group(1))
                    display_value = value  # оставляем как есть для display
                else:
                    count = 1

            elements.append(RpnElement(kind=kind, value=display_value, count=count))

    return elements


# ============================================================
#  СТРОКА СГЕНЕРИРОВАННОГО КОДА
# ============================================================

@dataclass
class CodeLine:
    """Одна строка выходного кода на R."""
    num: int         # номер строки (STR)
    text: str        # текст строки
    indent: int = 0  # уровень отступа


# ============================================================
#  МП-АВТОМАТ — КОДОГЕНЕРАТОР
# ============================================================

class CodeGenerator:
    """
    МП-автомат для генерации кода на R из ОПЗ.
    Методичка стр. 46–53, таблица 3.1.
    """

    def __init__(self):
        self.stack: List[str] = []       # стек операндов
        self.code: List[CodeLine] = []   # выходные строки кода
        self.STR: int = 1                # счётчик строк
        self.P: int = 0                  # счётчик вспомогательных переменных
        self.label_table: dict = {}      # метка → номер строки
        self.pending_labels: List[str] = []  # метки ожидающие STR
        self._indent: int = 0            # текущий отступ
        # Трассировка (для GUI): список шагов
        self.trace: List[dict] = []

    def reset(self):
        self.stack = []
        self.code  = []
        self.STR   = 1
        self.P     = 0
        self.label_table = {}
        self.pending_labels = []
        self._indent = 0
        self.trace = []

    # ── вспомогательные ─────────────────────────────────────

    def _new_rp(self) -> str:
        self.P += 1
        return f"R{self.P}"

    def _push(self, val: str):
        self.stack.append(val)

    def _pop(self) -> str:
        return self.stack.pop() if self.stack else '?'

    def _emit(self, text: str, is_comment: bool = False):
        """Добавить строку кода. STR наращивается только для не-пустых строк."""
        if text.strip():
            line = CodeLine(num=self.STR, text=text, indent=self._indent)
            self.code.append(line)
            self.STR += 1

    def _emit_comment(self, text: str):
        self._emit(f"# {text}")

    # ── главный метод ────────────────────────────────────────

    def generate(self, elements: List[RpnElement]) -> List[CodeLine]:
        self.reset()
        for elem in elements:
            self._step(elem)
        # Второй проход: замена символьных меток на номера строк (для goto)
        self._resolve_labels()
        return self.code

    def _step(self, elem: RpnElement):
        """Обрабатывает один элемент ОПЗ."""
        kind  = elem.kind
        value = elem.value
        count = elem.count

        # Сохраняем состояние для трассировки
        snap = {
            'elem': elem.display(),
            'kind': kind,
            'stack_before': list(self.stack),
            'STR': self.STR,
            'P': self.P,
            'code_line': None,
        }

        # ── Операнд → в стек ────────────────────────────────
        if kind == 'operand':
            # Метки вида "M1:" — это определение метки (kind='label' обработан ниже)
            if value.endswith(':') and re.match(r'^M\d+:$', value):
                # Это определение метки — запоминаем текущий STR
                lbl = value[:-1]  # убираем ':'
                self.label_table[lbl] = self.STR
            else:
                self._push(value)
        elif kind == 'label':
            # ':' — операция определения метки
            # арг1 уже вышел как operand "M1:" и обработан выше
            pass

        # ── НП — начало процедуры ────────────────────────────
        elif kind == 'НП':
            # Стек: ... имя номер уровень  (арг3=уровень на вершине)
            level  = self._pop()
            num    = self._pop()
            name   = self._pop()
            snap['code_line'] = f"# Начало процедуры {name}"
            self._emit_comment(f"Начало процедуры {name} (уровень {level})")
            self._emit(f"{name} <- function() {{")
            self._indent += 1

        # ── КП — конец процедуры ─────────────────────────────
        elif kind == 'КП':
            self._indent = max(0, self._indent - 1)
            snap['code_line'] = "}"
            self._emit("}")
            self._emit_comment("Конец процедуры")

        # ── ТИП — описание переменных ────────────────────────
        elif kind == 'ТИП':
            # Стек: перем1 ... перемN, count=N
            # В R объявления переменных не нужны — просто очищаем стек.
            # По методичке табл. 3.1: ТИП генерирует "REM Вещественные переменные..."
            # для Бейсика, но в R этот оператор бессмысленен — пропускаем.
            for _ in range(count):
                self._pop()
            snap['code_line'] = None  # ничего не генерируем

        # ── КО — конец описания ──────────────────────────────
        elif kind == 'КО':
            # В R ничего не генерируем (нет аналога конца описания)
            pass

        # ── := — присваивание ────────────────────────────────
        elif kind == 'assign':
            arg1 = self._pop()  # правая часть (вершина стека)
            arg2 = self._pop()  # левая часть
            line = f"{arg2} <- {arg1}"
            snap['code_line'] = line
            self._emit(line)

        # ── Арифметические и логические операции ─────────────
        elif kind == 'op':
            op = value
            # Маппинг JS → R операций
            r_op = {'==': '==', '!=': '!=', '<': '<', '>': '>',
                    '<=': '<=', '>=': '>=', '+': '+', '-': '-',
                    '*': '*', '/': '/', '%': '%%', '^': '^'}.get(op, op)
            arg1 = self._pop()  # вершина стека
            arg2 = self._pop()
            rp   = self._new_rp()
            line = f"{rp} <- {arg2} {r_op} {arg1}"
            snap['code_line'] = line
            self._emit(line)
            self._push(rp)

        # ── УПЛ — условный переход по лжи ────────────────────
        elif kind == 'УПЛ':
            # Стек: условие метка (метка на вершине)
            label = self._pop()
            cond  = self._pop()
            # В R используем структурный if
            line = f"if (!({cond})) goto({label})"
            snap['code_line'] = line
            self._emit(line)

        # ── БП — безусловный переход ──────────────────────────
        elif kind == 'БП':
            label = self._pop()
            line  = f"goto({label})"
            snap['code_line'] = line
            self._emit(line)

        # ── Ф — вызов функции ────────────────────────────────
        elif kind == 'Ф':
            # По методичке: <имя> <арг1>...<аргN> NФ
            # count = N (только аргументы, имя отдельно)
            n_args = count
            args = []
            for _ in range(n_args):
                args.insert(0, self._pop())
            name = self._pop()
            rp   = self._new_rp()
            args_str = ', '.join(args)
            line = f"{rp} <- {name}({args_str})"
            snap['code_line'] = line
            self._emit(line)
            self._push(rp)

        # ── АЭМ — обращение к элементу массива ───────────────
        elif kind == 'АЭМ':
            # По методичке: <имя> <индекс1>...<индексN> (N+1)АЭМ
            # count = N+1 (имя + индексы), индексов = count-1
            n_idx = count - 1 if count > 0 else 1
            indices = []
            for _ in range(n_idx):
                indices.insert(0, self._pop())
            arr_name = self._pop()
            # R использует 1-based индексацию → добавляем +1
            r_indices = []
            for idx in indices:
                try:
                    r_indices.append(str(int(idx) + 1))
                except ValueError:
                    r_indices.append(f"({idx}) + 1")
            operand = f"{arr_name}[{', '.join(r_indices)}]"
            self._push(operand)
            snap['code_line'] = f"(массив: {operand})"

        # ── return ────────────────────────────────────────────
        elif kind == 'return':
            val  = self._pop()
            line = f"return({val})"
            snap['code_line'] = line
            self._emit(line)

        snap['stack_after'] = list(self.stack)
        snap['STR_after'] = self.STR
        self.trace.append(snap)

    def _resolve_labels(self):
        """
        Второй проход: заменяем символьные метки (M1, M2, ...) на номера строк.
        По методичке стр. 49: необходим для языков без символьных меток.
        """
        for line in self.code:
            for label, lineno in self.label_table.items():
                # Заменяем goto(M1) → goto(STR_номер)
                line.text = line.text.replace(f"goto({label})", f"goto_line_{lineno}")
                line.text = line.text.replace(f'"{label}"', f'"{lineno}"')


# ============================================================
#  ФОРМАТИРОВАНИЕ ВЫВОДА
# ============================================================

def format_r_code(lines: List[CodeLine]) -> str:
    """Форматирует код R с отступами и номерами строк."""
    result = []
    for ln in lines:
        indent = '  ' * ln.indent
        result.append(f"{ln.num:>3}  {indent}{ln.text}")
    return '\n'.join(result)


def format_r_code_clean(lines: List[CodeLine]) -> str:
    """Чистый код R без номеров строк."""
    result = []
    for ln in lines:
        indent = '  ' * ln.indent
        result.append(f"{indent}{ln.text}")
    return '\n'.join(result)


def save_r_code(lines: List[CodeLine], label_table: dict, prefix: str = 'output3'):
    """Сохраняет сгенерированный код R в файл."""
    fname = f"{prefix}_r.R"
    with open(fname, 'w', encoding='utf-8') as f:
        f.write("# Сгенерировано транслятором JS→R\n")
        f.write("# Лабораторная работа №3  |  Вариант 10\n")
        f.write("# " + "─" * 50 + "\n\n")
        f.write(format_r_code_clean(lines))
        f.write("\n\n# " + "─" * 50 + "\n")
        f.write("# Таблица меток:\n")
        for lbl, num in sorted(label_table.items()):
            f.write(f"#   {lbl} → строка {num}\n")
    print(f"  ✓ {fname}")
    return fname


def print_trace_table(trace: List[dict]):
    """Выводит трассировку МП-автомата (как табл. 3.2 методички)."""
    print(f"\n  {'Шаг':<5} {'Элемент ОПЗ':<18} {'Стек':<30} {'STR':<5} Код")
    print(f"  {'─'*5} {'─'*18} {'─'*30} {'─'*5} {'─'*30}")
    for i, step in enumerate(trace):
        stack_str = str(step['stack_after'][-3:]) if step['stack_after'] else '[]'
        code_str  = step.get('code_line') or ''
        if len(code_str) > 30: code_str = code_str[:27] + '...'
        print(f"  {i+1:<5} {step['elem']:<18} {stack_str:<30} {step['STR_after']:<5} {code_str}")