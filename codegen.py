"""
Лабораторная работа №3: Перевод ОПЗ в текст на выходном языке R
Транслятор с языка JavaScript на язык R  |  Вариант 10

МП-автомат (методичка стр. 46–53, таблица 3.1).

Адаптация для R (вариант 10 — выходной язык R, не Бейсик):
  В Бейсике используется goto + нумерация строк.
  В R нет goto → паттерны УПЗ/БП распознаются и
  превращаются в структурные конструкции: if/else, while.

Паттерны ОПЗ (из Лабы 2):

  if без else:    <cond> M1 УПЛ <body> M1: :
  if-else:        <cond> M1 УПЛ <then> M2 БП M1: : <else> M2: :
  while:          M1: : <cond> M2 УПЛ <body> M1 БП M2: :
  function:       name num lev НП <body> КП
  array assign:   name idx АЭМ val :=
  func call:      name arg1..argN NФ
"""

import os, sys, re
from dataclasses import dataclass
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rpn import RpnElement


# ──────────────────────────────────────────────────────────────
#  Загрузка ОПЗ из файла Лабы 2
# ──────────────────────────────────────────────────────────────

def load_rpn(path: str) -> List[RpnElement]:
    elements = []
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Файл ОПЗ не найден: {path}\n"
            "Сначала запустите Лабу 2: python main2.py"
        )
    in_table = False
    with open(path, encoding='utf-8') as f:
        for line in f:
            s = line.strip()
            if s.startswith('№') and 'Элемент' in s:
                in_table = True; continue
            if not in_table or s.startswith('─') or not s:
                continue
            parts = s.split()
            if len(parts) < 2: continue
            try: int(parts[0])
            except ValueError: continue
            kind  = parts[-1]
            value = ' '.join(parts[1:-1])
            if not value: continue
            count = 0
            if kind in ('ТИП', 'Ф', 'АЭМ'):
                m = re.match(r'^(\d+)(ТИП|Ф|АЭМ)$', value)
                count = int(m.group(1)) if m else 1
            elements.append(RpnElement(kind=kind, value=value, count=count))
    return elements


# ──────────────────────────────────────────────────────────────
#  Строка кода
# ──────────────────────────────────────────────────────────────

@dataclass
class CodeLine:
    num:    int
    text:   str
    indent: int = 0


# ──────────────────────────────────────────────────────────────
#  МП-автомат
# ──────────────────────────────────────────────────────────────

class CodeGenerator:
    """
    МП-автомат для генерации R-кода из ОПЗ (методичка стр. 46-53).

    Алгоритм:
      1. Индексируем все метки M1:, M2:... → позиция в ОПЗ
      2. Линейный проход по ОПЗ:
         - Операнд    → в стек операндов
         - Операция   → семантическая процедура (табл. 3.1)
         - УПЛ        → определяем паттерн (if/if-else/while)
                        и рекурсивно генерируем блок
    """

    def __init__(self):
        self.stack:        List[str]        = []
        self.code:         List[CodeLine]   = []
        self.STR:          int              = 1
        self.P:            int              = 0
        self._label_pos:   dict             = {}  # 'M1' → индекс 'M1:' в ОПЗ
        self._indent:      int              = 0
        self._elems:       List[RpnElement] = []
        self._pos:         int              = 0
        self.trace:        List[dict]       = []
        self.label_table:  dict             = {}  # для GUI: метка → STR

    def reset(self):
        self.__init__()

    # ── вспомогательные ──────────────────────────────────────

    def _new_rp(self) -> str:
        self.P += 1
        return f"R{self.P}"

    def _push(self, v: str):   self.stack.append(v)
    def _pop(self)  -> str:    return self.stack.pop() if self.stack else '?'

    def _emit(self, text: str):
        if text.strip():
            self.code.append(CodeLine(num=self.STR, text=text, indent=self._indent))
            self.STR += 1

    def _cur(self) -> Optional[RpnElement]:
        return self._elems[self._pos] if self._pos < len(self._elems) else None

    def _eat(self) -> Optional[RpnElement]:
        e = self._cur(); self._pos += 1; return e

    def _label_name(self, e: RpnElement) -> Optional[str]:
        """Возвращает имя метки если элемент это 'M1:' (operand)."""
        if e.kind == 'operand':
            m = re.match(r'^(M\d+):$', e.value)
            return m.group(1) if m else None
        return None

    # ── Фаза 1: индексация меток ──────────────────────────────

    def _index_labels(self):
        """Запоминаем позиции 'M1:' элементов в массиве ОПЗ."""
        for i, e in enumerate(self._elems):
            lbl = self._label_name(e)
            if lbl:
                self._label_pos[lbl] = i   # i указывает на 'M1:' operand

    def _pos_of(self, lbl: str) -> int:
        """Индекс элемента 'M1:' в ОПЗ."""
        return self._label_pos.get(lbl, len(self._elems))

    # ── Главный метод ─────────────────────────────────────────

    def generate(self, elements: List[RpnElement]) -> List[CodeLine]:
        self.reset()
        self._elems = elements
        self._index_labels()
        self._pos = 0
        while self._pos < len(self._elems):
            self._step()
        return self.code

    # ── Один шаг МП-автомата ─────────────────────────────────

    def _step(self):
        e = self._cur()
        if e is None: return
        self._pos += 1

        snap = {
            'elem': e.display(), 'kind': e.kind,
            'stack_before': list(self.stack),
            'STR': self.STR, 'P': self.P, 'code_line': None,
        }

        self._handle(e, snap)

        snap['stack_after'] = list(self.stack)
        snap['STR_after']   = self.STR
        self.trace.append(snap)

    def _handle(self, e: RpnElement, snap: dict):
        kind, val, cnt = e.kind, e.value, e.count

        # ── Операнд ──────────────────────────────────────────
        if kind == 'operand':
            lbl = self._label_name(e)
            if lbl:
                # Определение метки — регистрируем STR, не пишем в код
                self.label_table[lbl] = self.STR
            else:
                self._push(val)

        # ── Метка ':' — обрабатывается через operand выше ────
        elif kind == 'label':
            pass

        # ── ТИП / КО — пропускаем (в R нет объявлений) ──────
        elif kind == 'ТИП':
            for _ in range(cnt): self._pop()
        elif kind == 'КО':
            pass

        # ── НП — начало функции ───────────────────────────────
        elif kind == 'НП':
            _lev  = self._pop()
            _num  = self._pop()
            name  = self._pop()
            # Параметры: ищем что осталось на стеке до этого момента
            # Они были занесены как операнды до НП (формальные параметры)
            line = f"{name} <- function() {{"
            snap['code_line'] = line
            self._emit(line)
            self._indent += 1

        # ── КП — конец функции ───────────────────────────────
        elif kind == 'КП':
            self._indent = max(0, self._indent - 1)
            snap['code_line'] = '}'
            self._emit('}')

        # ── Присваивание ─────────────────────────────────────
        elif kind == 'assign':
            rhs = self._pop()
            lhs = self._pop()
            line = f"{lhs} <- {rhs}"
            snap['code_line'] = line
            self._emit(line)

        # ── Арифметика / сравнения ────────────────────────────
        elif kind == 'op':
            r_op = {
                '==': '==', '!=': '!=', '<': '<',  '>': '>',
                '<=': '<=', '>=': '>=', '+': '+',  '-': '-',
                '*':  '*',  '/':  '/',  '%': '%%', '^': '^',
            }.get(val, val)
            arg1 = self._pop()   # вершина стека
            arg2 = self._pop()
            # Сворачиваем простые операнды в inline-выражение (без Rp)
            if _simple(arg1) and _simple(arg2):
                expr = f"({arg2} {r_op} {arg1})"
                self._push(expr)
                snap['code_line'] = f"→ expr {expr}"
            else:
                rp = self._new_rp()
                line = f"{rp} <- {arg2} {r_op} {arg1}"
                snap['code_line'] = line
                self._emit(line)
                self._push(rp)

        # ── УПЛ — условный переход → генерируем if/while ─────
        elif kind == 'УПЛ':
            m_jump = self._pop()   # метка перехода
            cond   = self._pop()   # условие
            code = self._gen_branch(cond, m_jump)
            snap['code_line'] = code

        # ── БП — встречается только внутри _gen_branch ───────
        elif kind == 'БП':
            # Операнд-метка уже на стеке — убираем
            if self.stack and re.match(r'^M\d+$', self.stack[-1]):
                self.stack.pop()

        # ── Вызов функции ─────────────────────────────────────
        elif kind == 'Ф':
            args = []
            for _ in range(cnt): args.insert(0, self._pop())
            name = self._pop()
            rp = self._new_rp()
            line = f"{rp} <- {name}({', '.join(args)})"
            snap['code_line'] = line
            self._emit(line)
            self._push(rp)

        # ── Элемент массива ───────────────────────────────────
        elif kind == 'АЭМ':
            n_idx = max(cnt - 1, 1)
            idxs = []
            for _ in range(n_idx): idxs.insert(0, self._pop())
            arr = self._pop()
            # R использует 1-based индексацию.
            # Сдвигаем ТОЛЬКО числовые константы: arr[0] → arr[1], arr[2] → arr[3].
            # Выражения с переменными оставляем как есть — программист
            # сам отвечает за значение индекса.
            r_idxs = []
            for ix in idxs:
                clean = _unwrap(ix)
                try:
                    # Чистая числовая константа → сдвигаем на 1
                    r_idxs.append(str(int(clean) + 1))
                except ValueError:
                    # Выражение с переменными → оставляем без изменений
                    r_idxs.append(clean)
            operand = f"{arr}[{', '.join(r_idxs)}]"
            self._push(operand)
            snap['code_line'] = f"→ {operand}"

        # ── return ───────────────────────────────────────────
        elif kind == 'return':
            val = self._pop()
            line = f"return({val})"
            snap['code_line'] = line
            self._emit(line)

    # ── Генерация структурных блоков ─────────────────────────

    def _gen_branch(self, cond: str, m_jump: str) -> str:
        """
        Определяет паттерн и генерирует R-код.
        Вызывается при встрече УПЛ в потоке.

        m_jump — метка куда прыгаем если условие ЛОЖЬ.

        Паттерны (по индексам в ОПЗ):
          while:    m_jump определён РАНЬШЕ текущей позиции
                    (метка начала цикла) — значит это while
          if-else:  между текущей позицией и m_jump есть БП m_end
          if:       нет БП до m_jump
        """
        pos_mjump = self._pos_of(m_jump)  # позиция 'M_jump:' в ОПЗ

        # ── while? ───────────────────────────────────────────
        # while: метка m_jump (M_end) впереди, но перед нами была M_start:
        # Ищем БП в теле, которое ссылается назад (на уже пройденную метку)
        m_back = self._find_back_bp(self._pos, pos_mjump)
        if m_back:
            return self._gen_while(cond, m_jump, m_back, pos_mjump)

        # ── if-else? ─────────────────────────────────────────
        # Ищем БП m_end в теле then
        m_end, pos_bp = self._find_fwd_bp(self._pos, pos_mjump)
        if m_end:
            return self._gen_if_else(cond, m_jump, m_end, pos_bp, pos_mjump)

        # ── if без else ───────────────────────────────────────
        return self._gen_if_only(cond, m_jump, pos_mjump)

    def _find_back_bp(self, start: int, end: int) -> Optional[str]:
        """
        Ищет БП на метку РАНЬШЕ start (метка начала цикла).
        Если находим — это while.
        """
        for i in range(start, min(end, len(self._elems))):
            e = self._elems[i]
            if e.kind == 'БП':
                # Перед БП должен быть операнд-метка
                if i > 0 and self._elems[i-1].kind == 'operand':
                    m = re.match(r'^(M\d+)$', self._elems[i-1].value)
                    if m:
                        lbl = m.group(1)
                        # Метка должна быть определена ДО start (назад)
                        if self._pos_of(lbl) < start:
                            return lbl
        return None

    def _find_fwd_bp(self, start: int, end: int):
        """
        Ищет БП на метку ВПЕРЕДИ (вперёд) в диапазоне [start, end).
        Возвращает (метка, позиция БП) или (None, None).
        """
        for i in range(start, min(end, len(self._elems))):
            e = self._elems[i]
            if e.kind == 'БП':
                if i > 0 and self._elems[i-1].kind == 'operand':
                    m = re.match(r'^(M\d+)$', self._elems[i-1].value)
                    if m:
                        lbl = m.group(1)
                        # Метка должна быть определена ПОСЛЕ end (вперёд)
                        if self._pos_of(lbl) > end:
                            return lbl, i
        return None, None

    def _gen_if_only(self, cond: str, m_false: str, pos_mfalse: int) -> str:
        # Убираем лишние скобки вокруг условия
        c = _unwrap(cond)
        self._emit(f"if ({c}) {{")
        self._indent += 1
        while self._pos < pos_mfalse:
            self._step()
        self._indent -= 1
        self._emit("}")
        self._skip_label(m_false)
        return f"if ({c}) {{ ... }}"

    def _gen_if_else(self, cond: str, m_false: str, m_end: str,
                     pos_bp: int, pos_mfalse: int) -> str:
        c = _unwrap(cond)
        self._emit(f"if ({c}) {{")
        self._indent += 1
        then_end = pos_bp - 1
        while self._pos < then_end:
            self._step()
        self._indent -= 1
        if self._pos < len(self._elems) and self._elems[self._pos].kind == 'operand':
            self._pos += 1
        if self._pos < len(self._elems) and self._elems[self._pos].kind == 'БП':
            self._pos += 1
        self._skip_label(m_false)
        self._emit("} else {")
        self._indent += 1
        pos_mend = self._pos_of(m_end)
        while self._pos < pos_mend:
            self._step()
        self._indent -= 1
        self._emit("}")
        self._skip_label(m_end)
        return f"if ({c}) {{ ... }} else {{ ... }}"

    def _gen_while(self, cond: str, m_end: str, m_start: str,
                   pos_mend: int) -> str:
        c = _unwrap(cond)
        self._emit(f"while ({c}) {{")
        self._indent += 1
        pos_bp = pos_mend - 1
        for i in range(self._pos, pos_mend):
            if i < len(self._elems) and self._elems[i].kind == 'БП':
                pos_bp = i
                break
        body_end = pos_bp - 1
        while self._pos < body_end:
            self._step()
        self._indent -= 1
        self._emit("}")
        if self._pos < len(self._elems) and self._elems[self._pos].kind == 'operand':
            self._pos += 1
        if self._pos < len(self._elems) and self._elems[self._pos].kind == 'БП':
            self._pos += 1
        self._skip_label(m_end)
        return f"while ({c}) {{ ... }}"

    def _skip_label(self, lbl: str):
        """Пропускает пару: operand 'M1:' + label ':'"""
        if (self._pos < len(self._elems) and
                self._elems[self._pos].kind == 'operand' and
                self._elems[self._pos].value == f"{lbl}:"):
            self._pos += 1
        if (self._pos < len(self._elems) and
                self._elems[self._pos].kind == 'label'):
            self._pos += 1


# ──────────────────────────────────────────────────────────────
#  Утилиты
# ──────────────────────────────────────────────────────────────

def _simple(expr: str) -> bool:
    """True если выражение простое — можно вставлять inline."""
    return bool(re.match(r'^[\w."\'(][^\s]*$', expr))


def _unwrap(expr: str) -> str:
    """Убирает лишние внешние скобки: ((a > b)) → a > b."""
    s = expr.strip()
    while s.startswith('(') and s.endswith(')'):
        # Проверяем что скобки парные (не (a) + (b))
        depth = 0
        paired = True
        for i, ch in enumerate(s[1:-1], 1):
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth < 0:
                    paired = False
                    break
        if paired and depth == 0:
            s = s[1:-1].strip()
        else:
            break
    return s


def format_r_code(lines: List[CodeLine]) -> str:
    return '\n'.join(f"{l.num:>3}  {'  ' * l.indent}{l.text}" for l in lines)


def format_r_code_clean(lines: List[CodeLine]) -> str:
    return '\n'.join(f"{'  ' * l.indent}{l.text}" for l in lines)


def save_r_code(lines: List[CodeLine], label_table: dict, prefix: str = 'output3'):
    fname = f"{prefix}_r.R"
    with open(fname, 'w', encoding='utf-8') as f:
        f.write("# Сгенерировано транслятором JS→R  |  Лаба 3  |  Вариант 10\n\n")
        f.write(format_r_code_clean(lines))
        f.write("\n")
    print(f"  ✓ {fname}")
    return fname


def print_trace_table(trace: List[dict]):
    print(f"\n  {'Шаг':<5} {'Элемент ОПЗ':<18} {'Стек':<28} {'STR':<5} Код")
    print(f"  {'─'*5} {'─'*18} {'─'*28} {'─'*5} {'─'*28}")
    for i, s in enumerate(trace):
        st = str(s['stack_after'][-3:]) if s['stack_after'] else '[]'
        cd = (s.get('code_line') or '')[:28]
        print(f"  {i+1:<5} {s['elem']:<18} {st:<28} {s['STR_after']:<5} {cd}")