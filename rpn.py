"""
Лабораторная работа №2: Перевод исходной программы в обратную польскую запись (ОПЗ)
Транслятор с языка JavaScript на язык R  |  Вариант 10

Реализует алгоритм Дейкстры (методичка стр. 20–45).

Входные данные  — результат лексического анализа (Лаба 1):
  список объектов Token(token_class, code, value)

Выходные данные — последовательность элементов ОПЗ (список RpnElement).

Специальные операции ОПЗ (методичка стр. 36–40):
  :=       — присваивание
  НП       — начало процедуры: <имя> <номер> <уровень> НП
  КП       — конец процедуры
  КО       — конец описания
  ТИП      — описание типа: <перем1>...<перемN> N ТИП
  УПЛ      — условный переход по лжи: <условие> <метка> УПЛ
  БП       — безусловный переход: <метка> БП
  <метка>: — определение метки
  NФ       — вызов функции: <имя> <арг1>...<аргN> N Ф
  NАЭМ     — обращение к элементу массива: <имя> <индекс1>...<индексN> N АЭМ
  return   — возврат значения из функции

Таблица приоритетов (адаптация Табл. 2.8 методички для JS, стр. 43):
  0: if ( [ Ф АЭМ
  1: ; ) ]
  2: = (присваивание)
  3: == != < > <= >=
  4: + -
  5: * / %
  6: ^
  7: function var return while : НП КП КО (описательные — наибольший)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from lexer import LexicalAnalyzer, Token, KEYWORDS


# ============================================================
#  ЭЛЕМЕНТ ВЫХОДНОЙ СТРОКИ ОПЗ
# ============================================================

@dataclass
class RpnElement:
    """Один элемент выходной строки ОПЗ."""
    kind: str    # тип: operand | op | assign | НП | КП | КО | ТИП |
                 #       УПЛ | БП | label | Ф | АЭМ | return
    value: str   # строковое представление
    count: int = 0  # счётчик операндов для Ф, АЭМ, ТИП

    def display(self) -> str:
        if self.count and self.kind in ('Ф', 'АЭМ', 'ТИП'):
            return f"{self.count}{self.kind}"
        return self.value


# ============================================================
#  ЭЛЕМЕНТ СТЕКА
# ============================================================

@dataclass
class StackItem:
    op: str           # строка операции
    priority: int     # приоритет
    count: int = 0    # счётчик операндов (для Ф, АЭМ)
    label: str = ''   # рабочая метка (для if, while)
    label2: str = ''  # вторая метка (для if+else)
    proc_name: str = ''
    proc_num: int = 0
    proc_level: int = 0


# ============================================================
#  ТАБЛИЦА ПРИОРИТЕТОВ
# ============================================================

# Приоритет элемента, когда он находится в стеке
STACK_PRIO = {
    '(':        0,
    '[':        0,
    'Ф':        0,
    'АЭМ':      0,
    'if':       0,
    # 1 — закрывающие (только входной)
    '=':        2,
    '==':       3,  '!=': 3, '<': 3, '>': 3, '<=': 3, '>=': 3,
    '+':        4,  '-': 4,
    '*':        5,  '/': 5,  '%': 5,
    '^':        6,
    'function': 7,
    'while':    0,   # while аналогично if — открывающий
    'return':   7,
    'var':      7,
    ':':        7,
}


# ============================================================
#  ПЕРЕВОДЧИК В ОПЗ
# ============================================================

class RpnTranslator:
    """
    Алгоритм Дейкстры для перевода JS → ОПЗ.
    Читает список токенов (результат Лабы 1), строит список RpnElement.
    """

    def __init__(self):
        self.output: List[RpnElement] = []
        self.stack:  List[StackItem]  = []
        self._lbl_counter   = 0
        self._proc_counter  = 0
        self._nest_level    = 0
        # Состояния
        self._pending_func: Optional[str] = None  # имя ф-ции после 'function'
        self._expect_func_name = False
        self._dcl_vars: List[str] = []
        self._in_dcl = False
        self._in_func_params = False

    # ── сброс состояния ──────────────────────────────────────

    def reset(self):
        self.output = []
        self.stack  = []
        self.trace  = []   # трассировка шагов для GUI
        self._lbl_counter   = 0
        self._proc_counter  = 0
        self._nest_level    = 0
        self._pending_func  = None
        self._expect_func_name = False
        self._dcl_vars      = []
        self._in_dcl        = False
        self._in_func_params = False

    # ── вспомогательные ──────────────────────────────────────

    def _new_label(self) -> str:
        self._lbl_counter += 1
        return f"M{self._lbl_counter}"

    def _emit(self, kind: str, value: str, count: int = 0):
        self.output.append(RpnElement(kind=kind, value=value, count=count))

    def _emit_operand(self, v: str):
        self._emit('operand', v)

    def _top(self) -> Optional[StackItem]:
        return self.stack[-1] if self.stack else None

    def _pop(self) -> Optional[StackItem]:
        return self.stack.pop() if self.stack else None

    def _push(self, item: StackItem):
        self.stack.append(item)

    def _flush_stack_item(self, item: StackItem):
        """Выводит элемент стека в выходную строку."""
        op = item.op
        if op in ('+', '-', '*', '/', '%', '^', '==', '!=', '<', '>', '<=', '>='):
            self._emit('op', op)
        elif op == '=':
            self._emit('assign', ':=')
        elif op == 'return':
            self._emit('return', 'return')
        elif op in ('Ф',):
            self._emit('Ф', 'Ф', count=item.count)
        elif op == 'АЭМ':
            self._emit('АЭМ', 'АЭМ', count=item.count)

    def _flush_until_prio_below(self, incoming_prio: int):
        """
        Стандартное правило Дейкстры: выталкивать из стека все операции,
        приоритет которых >= incoming_prio, пока не встретим элемент с
        меньшим приоритетом или открывающую скобку (приоритет 0).
        Блок-операторы (function, if, while) никогда не выталкиваются.
        """
        protected = {'(', '[', 'if', 'if_else', 'while', 'function', 'Ф', 'АЭМ'}
        while self.stack:
            top = self.stack[-1]
            if top.op in protected:  # блок-операторы — стоп
                break
            top_prio = STACK_PRIO.get(top.op, 0)
            if top_prio == 0:
                break
            if top_prio >= incoming_prio:
                item = self._pop()
                self._flush_stack_item(item)
            else:
                break

    def _flush_until_op(self, stop_op: str):
        """Вытолкнуть всё из стека до (не включая) stop_op."""
        while self.stack and self.stack[-1].op != stop_op:
            item = self._pop()
            self._flush_stack_item(item)

    # ── главный метод ────────────────────────────────────────

    def translate(self, tokens: List[Token]) -> List[RpnElement]:
        self.reset()
        i = 0
        n = len(tokens)
        while i < n:
            tok = tokens[i]
            stack_before = [s.op for s in self.stack]
            out_before = len(self.output)
            i = self._step(tokens, i, n)
            # Записываем трассировку шага
            new_out = [e.display() for e in self.output[out_before:]]
            self.trace.append({
                'token': f"{tok.token_class}{tok.code}={tok.value}",
                'tc': tok.token_class,
                'val': tok.value,
                'stack_before': stack_before,
                'stack_after': [s.op for s in self.stack],
                'output_added': new_out,
            })
        # Вытолкнуть остаток стека
        while self.stack:
            item = self._pop()
            if item.op not in ('(', '[', 'if', 'while', 'Ф', 'АЭМ', 'function'):
                self._flush_stack_item(item)
        return self.output

    # ── шаг обработки одного токена ──────────────────────────

    def _step(self, tokens: List[Token], i: int, n: int) -> int:
        tok = tokens[i]
        tc, code, val = tok.token_class, tok.code, tok.value

        # ── Идентификатор ──
        if tc == 'I':
            return self._on_ident(val, tokens, i, n)

        # ── Числовая константа ──
        if tc == 'N':
            self._emit_operand(val)
            return i + 1

        # ── Строковая константа ──
        if tc == 'C':
            self._emit_operand(f'"{val}"')
            return i + 1

        # ── Служебное слово ──
        if tc == 'W':
            return self._on_keyword(code, val, tokens, i, n)

        # ── Операция ──
        if tc == 'O':
            return self._on_operation(code, val, tokens, i, n)

        # ── Разделитель ──
        if tc == 'R':
            return self._on_separator(code, val, tokens, i, n)

        return i + 1

    # ── идентификатор ────────────────────────────────────────

    def _on_ident(self, val: str, tokens: List[Token], i: int, n: int) -> int:
        if self._expect_func_name:
            # Имя функции
            self._pending_func = val
            self._expect_func_name = False
            self._in_func_params = True
            return i + 1

        if self._in_dcl:
            # Переменная в описании var
            self._dcl_vars.append(val)
            return i + 1

        if self._in_func_params:
            # Формальные параметры функции в ОПЗ не выводятся —
            # их типы уже зафиксированы в таблице идентификаторов (Лаба 1).
            # По методичке НП имеет вид: <имя> <номер> <уровень> НП
            return i + 1

        # Смотрим вперёд: если следующий токен — '(' → вызов функции
        next_tok = tokens[i + 1] if i + 1 < n else None
        if next_tok and next_tok.token_class == 'R' and next_tok.code == 4:
            # Проверяем что это не после if/while
            top = self._top()
            if not (top and top.op in ('if', 'while')):
                # Вызов функции: имя выходит как операнд, потом Ф в стек
                self._emit_operand(val)
                return i + 1  # '(' обработает _on_separator

        self._emit_operand(val)
        return i + 1

    # ── служебные слова ──────────────────────────────────────

    def _on_keyword(self, code: int, val: str, tokens: List[Token], i: int, n: int) -> int:

        # var — начало описания переменных
        if code == 1:
            self._in_dcl = True
            self._dcl_vars = []
            return i + 1

        # function — объявление функции
        if code == 2:
            self._expect_func_name = True
            return i + 1

        # return — возврат из функции
        if code == 3:
            self._push(StackItem(op='return', priority=7))
            return i + 1

        # if — условный оператор
        if code == 4:
            self._push(StackItem(op='if', priority=0))
            return i + 1

        # else — пропускаем здесь, обрабатывается при '{'
        if code == 5:
            return i + 1

        # while — цикл
        if code == 6:
            lbl_start = self._new_label()
            lbl_end   = self._new_label()
            # Метка начала цикла
            self._emit_operand(f"{lbl_start}:")
            self._emit('label', ':')
            self._push(StackItem(op='while', priority=0,
                                 label=lbl_start, label2=lbl_end))
            return i + 1

        # console (W12), log (W13) — пропускаем (часть console.log)
        if code in (12, 13):
            return i + 1

        # true, false, null — операнды
        if code in (9, 10, 11):
            self._emit_operand(val)
            return i + 1

        return i + 1

    # ── операции ─────────────────────────────────────────────

    def _on_operation(self, code: int, val: str, tokens: List[Token], i: int, n: int) -> int:

        # Присваивание = (O12) — правоассоциативное, приоритет 2
        if code == 12:
            protected = {'(', '[', 'if', 'if_else', 'while', 'function', 'Ф', 'АЭМ'}
            while self.stack:
                top = self.stack[-1]
                if top.op in protected:
                    break
                tp = STACK_PRIO.get(top.op, 0)
                if tp == 0 or tp <= 2:
                    break
                self._flush_stack_item(self._pop())
            self._push(StackItem(op='=', priority=2))
            return i + 1

        # Унарный минус (если предыдущий не операнд)
        # В JS: -a → 0 a -  (пока упрощённо как бинарный с 0)

        prio_map = {
            1: 4,   # +
            2: 4,   # -
            3: 5,   # *
            4: 5,   # /
            5: 5,   # %
            6: 3,   # <
            7: 3,   # >
            8: 3,   # ==
            9: 3,   # !=
            10: 3,  # <=
            11: 3,  # >=
            13: 6,  # ^
        }
        prio = prio_map.get(code, 4)
        self._flush_until_prio_below(prio)
        self._push(StackItem(op=val, priority=prio))
        return i + 1

    # ── разделители ──────────────────────────────────────────

    def _on_separator(self, code: int, val: str, tokens: List[Token], i: int, n: int) -> int:

        if code == 3:  # ;
            return self._on_semicolon(tokens, i, n)
        if code == 4:  # (
            return self._on_open_paren(tokens, i, n)
        if code == 5:  # )
            return self._on_close_paren(tokens, i, n)
        if code == 2:  # ,
            return self._on_comma(tokens, i, n)
        if code == 7:  # [
            return self._on_open_bracket(tokens, i, n)
        if code == 8:  # ]
            return self._on_close_bracket(tokens, i, n)
        if code == 9:  # {
            return self._on_open_brace(tokens, i, n)
        if code == 10: # }
            return self._on_close_brace(tokens, i, n)
        if code == 6:  # . (разделитель console.log)
            return i + 1
        return i + 1

    # ── ; ────────────────────────────────────────────────────

    def _on_semicolon(self, tokens: List[Token], i: int, n: int) -> int:
        """
        ; — конец оператора.
        Выталкиваем из стека всё до открывающего символа/начала блока.
        Если в DCL — выводим ТИП + КО.
        """
        if self._in_dcl:
            # Конец описания var — выводим ТИП
            self._flush_dcl()
            return i + 1

        # Выталкиваем всё до '(', '[', 'if', 'if_else', 'while', 'function'
        while self.stack:
            top = self.stack[-1]
            if top.op in ('(', '[', 'if', 'if_else', 'while', 'function', 'Ф', 'АЭМ'):
                break
            item = self._pop()
            self._flush_stack_item(item)
        return i + 1

    def _flush_dcl(self):
        """Выводит операцию ТИП + КО для var-описания."""
        if not self._dcl_vars:
            return
        # По методичке: список переменных, затем счётчик, затем ТИП, затем КО
        for v in self._dcl_vars:
            self._emit_operand(v)
        self._emit('ТИП', 'ТИП', count=len(self._dcl_vars))
        self._emit('КО', 'КО')
        self._dcl_vars = []
        self._in_dcl = False

    # ── ( ────────────────────────────────────────────────────

    def _on_open_paren(self, tokens: List[Token], i: int, n: int) -> int:
        """
        ( — три случая:
          1. После идентификатора → вызов функции: Ф в стек (счётчик=1)
          2. После while → условие: ( в стек
          3. После if → условие: ( в стек
          4. Если _in_func_params → параметры функции: ничего в стек (счётчик ведётся внутри)
          5. Иначе → группирующая: ( в стек
        """
        # Случай: параметры определения функции
        if self._in_func_params:
            # Ничего не делаем — параметры обрабатываем как операнды
            self._push(StackItem(op='(', priority=0))
            return i + 1

        prev = tokens[i - 1] if i > 0 else None

        # Вызов функции: предыдущий — I
        if prev and prev.token_class == 'I':
            # Имя уже в выходной строке, заносим Ф со счётчиком 1
            self._push(StackItem(op='Ф', priority=0, count=1))
            return i + 1

        # После if — условие
        if self.stack and self.stack[-1].op == 'if':
            self._push(StackItem(op='(', priority=0))
            return i + 1

        # После while — условие
        if self.stack and self.stack[-1].op == 'while':
            self._push(StackItem(op='(', priority=0))
            return i + 1

        # Обычная группирующая скобка
        self._push(StackItem(op='(', priority=0))
        return i + 1

    # ── ) ────────────────────────────────────────────────────

    def _on_close_paren(self, tokens: List[Token], i: int, n: int) -> int:
        """
        ) — выталкиваем до '(', затем проверяем контекст:
          - Под '(' стоит Ф → вызов функции завершён
          - Под '(' стоит if → выводим УПЛ
          - Под '(' стоит while → выводим УПЛ (переход на конец цикла)
          - _in_func_params → конец списка параметров функции
        """
        # Конец списка параметров определения функции
        if self._in_func_params:
            # Убираем '('
            if self.stack and self.stack[-1].op == '(':
                self._pop()
            self._in_func_params = False
            return i + 1

        # Выталкиваем до '('
        self._flush_until_op('(')

        # Убираем '('
        if self.stack and self.stack[-1].op == '(':
            self._pop()

        # Что под '('?
        top = self._top()

        if top and top.op == 'Ф':
            # Вызов функции завершён
            item = self._pop()
            self._emit('Ф', 'Ф', count=item.count)
            return i + 1

        if top and top.op == 'if':
            # Условие if закончилось — выводим УПЛ
            lbl = self._new_label()
            self.stack[-1].label = lbl
            self._emit_operand(lbl)
            self._emit('УПЛ', 'УПЛ')
            return i + 1

        if top and top.op == 'while':
            # Условие while закончилось — выводим УПЛ (переход на конец цикла)
            lbl_end = self.stack[-1].label2
            self._emit_operand(lbl_end)
            self._emit('УПЛ', 'УПЛ')
            return i + 1

        return i + 1

    # ── , ────────────────────────────────────────────────────

    def _on_comma(self, tokens: List[Token], i: int, n: int) -> int:
        """
        , — по методичке стр. 27 и 39:
          - Если вершина стека — Ф → наращиваем счётчик аргументов
          - Если вершина стека — АЭМ → наращиваем счётчик
          - Если в DCL → новая переменная
          - Иначе → выталкиваем до Ф/АЭМ и наращиваем
        """
        if self._in_dcl:
            return i + 1  # переменные собираются в _dcl_vars через _on_ident

        if self._in_func_params:
            return i + 1  # параметры функции просто выходят как операнды

        # Выталкиваем всё до ближайшего Ф или АЭМ
        while self.stack:
            top = self.stack[-1]
            if top.op in ('Ф', 'АЭМ'):
                top.count += 1
                break
            item = self._pop()
            self._flush_stack_item(item)
        return i + 1

    # ── [ ────────────────────────────────────────────────────

    def _on_open_bracket(self, tokens: List[Token], i: int, n: int) -> int:
        """
        [ — начало индексирования. По методичке стр. 24:
        в стек заносится АЭМ со счётчиком операндов = 2.
        """
        self._push(StackItem(op='АЭМ', priority=0, count=2))
        return i + 1

    # ── ] ────────────────────────────────────────────────────

    def _on_close_bracket(self, tokens: List[Token], i: int, n: int) -> int:
        """
        ] — конец индексирования. По методичке стр. 24:
        выталкиваем АЭМ с текущим счётчиком в выходную строку.
        """
        self._flush_until_op('АЭМ')
        if self.stack and self.stack[-1].op == 'АЭМ':
            item = self._pop()
            self._emit('АЭМ', 'АЭМ', count=item.count)
        return i + 1

    # ── { ────────────────────────────────────────────────────

    def _on_open_brace(self, tokens: List[Token], i: int, n: int) -> int:
        """
        { — начало блока.
        Если ожидается тело функции (_pending_func) → выводим НП.
        Если контекст if/while — просто начало тела.
        """
        if self._pending_func is not None:
            # Начало тела функции → НП
            self._proc_counter += 1
            self._nest_level   += 1
            name = self._pending_func
            num  = self._proc_counter
            lvl  = self._nest_level
            self._emit_operand(name)
            self._emit_operand(str(num))
            self._emit_operand(str(lvl))
            self._emit('НП', 'НП')
            self._push(StackItem(op='function', priority=7,
                                 proc_name=name, proc_num=num, proc_level=lvl))
            self._pending_func = None
            return i + 1

        # Тело if — ничего не добавляем, if уже в стеке
        if self.stack and self.stack[-1].op == 'if':
            return i + 1

        # Тело else — помечаем if как else-блок
        # (обработано при '}' предыдущего if)
        if self.stack and self.stack[-1].op == 'if_else':
            return i + 1

        # Тело while
        if self.stack and self.stack[-1].op == 'while':
            return i + 1

        # Обычный блок
        self._push(StackItem(op='{', priority=0))
        return i + 1

    # ── } ────────────────────────────────────────────────────

    def _on_close_brace(self, tokens: List[Token], i: int, n: int) -> int:
        """
        } — конец блока.
        function → КП
        if       → расставляем метку (и если есть else — БП + метка)
        while    → БП на начало + метка конца
        """
        if not self.stack:
            return i + 1

        top = self.stack[-1]

        # Конец функции
        if top.op == 'function':
            self._pop()
            self._emit('КП', 'КП')
            self._nest_level -= 1
            return i + 1

        # Конец блока if
        if top.op == 'if':
            # Смотрим вперёд: есть else?
            next_tok = tokens[i + 1] if i + 1 < n else None
            has_else = (next_tok and next_tok.token_class == 'W'
                        and next_tok.code == 5)
            if has_else:
                # Полный if-else: выводим M2 БП, ставим M1:
                lbl_false = self.stack[-1].label   # M1 — метка УПЛ
                lbl_end   = self._new_label()       # M2 — метка конца
                self.stack[-1].label2 = lbl_end
                self.stack[-1].op = 'if_else'       # переключаем режим
                self._emit_operand(lbl_end)
                self._emit('БП', 'БП')
                self._emit_operand(f"{lbl_false}:")
                self._emit('label', ':')
            else:
                # Неполный if: просто ставим метку
                item = self._pop()
                lbl = item.label
                self._emit_operand(f"{lbl}:")
                self._emit('label', ':')
            return i + 1

        # Конец блока else
        if top.op == 'if_else':
            item = self._pop()
            lbl_end = item.label2
            self._emit_operand(f"{lbl_end}:")
            self._emit('label', ':')
            return i + 1

        # Конец цикла while
        if top.op == 'while':
            item = self._pop()
            lbl_start = item.label
            lbl_end   = item.label2
            # БП на начало цикла
            self._emit_operand(lbl_start)
            self._emit('БП', 'БП')
            # Метка конца цикла
            self._emit_operand(f"{lbl_end}:")
            self._emit('label', ':')
            return i + 1

        # Обычный блок
        if top.op == '{':
            self._pop()
        return i + 1


# ============================================================
#  ФОРМАТИРОВАНИЕ ВЫВОДА
# ============================================================

def format_rpn(elements: List[RpnElement]) -> str:
    """Форматирует ОПЗ в одну строку для вывода."""
    parts = []
    for e in elements:
        parts.append(e.display())
    return ' '.join(parts)


def print_rpn_process(elements: List[RpnElement]):
    """
    Печатает ОПЗ в виде пронумерованной таблицы элементов
    (как таблица 3.2 из методички).
    """
    print(f"\n  {'№':<5} {'Элемент ОПЗ':<20} Вид")
    print(f"  {'─'*5} {'─'*20} {'─'*20}")
    for idx, e in enumerate(elements, 1):
        print(f"  {idx:<5} {e.display():<20} {e.kind}")