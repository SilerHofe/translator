"""
Лабораторная работа №1: Лексический анализатор
Транслятор с языка JavaScript на язык R  |  Вариант 10

Классы лексем (Таблица 1.1 методички):
  W - служебные слова       (постоянная таблица)
  I - идентификаторы        (временная таблица 1.6)
  O - операции              (постоянная таблица)
  R - разделители           (постоянная таблица)
  N - числовые константы    (временная таблица 1.5)
  C - строковые константы   (временная таблица)

Таблица идентификаторов строится по образцу Таблицы 1.6 методички:
  Код | Идентификатор | Номер процедуры | Уровень процедуры |
  Номер идент. в процедуре | Тип идентификатора | Объём памяти

ВАЖНО (методичка стр. 13): лексер только ЗАВОДИТ записи в таблице 1.6
(заполняет Код и Имя). Остальные поля заполняются на этапе
синтаксического анализа (Лабораторная работа №2).
"""

# ============================================================
#  ПОСТОЯННЫЕ ТАБЛИЦЫ (определяются входным языком — JS)
# ============================================================

# Таблица служебных слов W
KEYWORDS = {
    'var':      1,
    'function': 2,
    'return':   3,
    'if':       4,
    'else':     5,
    'while':    6,
    'for':      7,
    'new':      8,
    'true':     9,
    'false':    10,
    'null':     11,
    'console':  12,
    'log':      13,
}

# Таблица операций O
OPERATIONS = {
    '+':  1,
    '-':  2,
    '*':  3,
    '/':  4,
    '%':  5,
    '<':  6,
    '>':  7,
    '==': 8,
    '!=': 9,
    '<=': 10,
    '>=': 11,
    '=':  12,
    '^':  13,
}

# Вспомогательная таблица: символы, начинающие двулитерную операцию
PART_OF_TWO_LIT = {
    '/': 1,
    '=': 2,
    '<': 3,
    '>': 4,
    '!': 5,
}

# Таблица разделителей R
SEPARATORS = {
    ' ':  1,
    ',':  2,
    ';':  3,
    '(':  4,
    ')':  5,
    '.':  6,
    '[':  7,
    ']':  8,
    '{':  9,
    '}':  10,
    '\t': 1,   # табуляция = пробел (код 1)
}


# ============================================================
#  ЗАПИСЬ ТАБЛИЦЫ ИДЕНТИФИКАТОРОВ — Таблица 1.6 методички
# ============================================================

class IdRecord:
    """
    Одна строка таблицы идентификаторов (Таблица 1.6).

    Лексер (Лаба 1) заполняет:
        code            — порядковый номер в таблице
        name            — имя идентификатора
        nesting_level   — уровень вложенности в момент первого появления
                          (0 = глобальный, 1 = внутри первого блока {...}, и т.д.)
        id_type         — тип: 'unknown' (уточняется в Лабе 2)

    Лаба 2 дополнит:
        proc_num    — номер процедуры/функции
        proc_level  — уровень процедуры
        id_in_proc  — порядковый номер идентификатора в процедуре
        mem_size    — объём памяти
    """
    def __init__(self, code: int, name: str, nesting_level: int = 0):
        # ── заполняет Лаба 1 ──
        self.code           = code
        self.name           = name
        self.nesting_level  = nesting_level  # уровень вложенности { }
        self.id_type        = 'unknown'      # variable | function | parameter | unknown

        # ── заполнит Лаба 2 ──
        self.proc_num   = None
        self.proc_level = None
        self.id_in_proc = None
        self.mem_size   = None

    def __repr__(self):
        return (f"IdRecord(code={self.code}, name={self.name!r}, "
                f"level={self.nesting_level}, type={self.id_type!r})")


# ============================================================
#  ТОКЕН
# ============================================================

class Token:
    def __init__(self, token_class: str, code: int, value: str):
        self.token_class = token_class  # W I O R N C
        self.code = code
        self.value = value

    def to_internal(self) -> str:
        return f"{self.token_class}{self.code}"

    def __repr__(self):
        return f"{self.token_class}{self.code}({self.value!r})"


# ============================================================
#  БАЗОВЫЙ КЛАСС СОСТОЯНИЯ
# ============================================================

class BaseState:
    def __init__(self, lexeme: str, analyzer):
        self.lexeme   = lexeme
        self.analyzer = analyzer

    def execute(self, symbol: str):
        raise NotImplementedError

    def execute_last(self):
        """Вызывается в конце каждой строки входного текста."""
        pass

    def _add_char(self, symbol: str):
        self.lexeme += symbol


# ============================================================
#  СОСТОЯНИЯ СКАНЕРА (диаграмма состояний — раздел 1.4)
# ============================================================

class StartState(BaseState):
    """Начальное состояние S."""

    def execute(self, symbol: str):
        a = self.analyzer
        if symbol.isalpha() or symbol == '_':
            s = WordState('', a); a.set_state(s); s.execute(symbol)
        elif symbol == '$':
            s = IdentificatorState('', a); a.set_state(s); s.execute(symbol)
        elif symbol.isdigit():
            s = DigitState('', a); a.set_state(s); s.execute(symbol)
        elif symbol == '.':
            a.set_state(DotState('.', a))
        elif symbol in ('"', "'"):
            a.set_state(CharConstState(symbol, a))
        elif symbol in PART_OF_TWO_LIT:
            a.set_state(PartTwoLitState(symbol, a))
        elif symbol in SEPARATORS:
            s = SeparatorState('', a); a.set_state(s); s.execute(symbol)
        elif symbol in OPERATIONS:
            s = OperationState('', a); a.set_state(s); s.execute(symbol)
        # иначе — неизвестный символ, остаёмся в S (или можно добавить ошибку)

    def execute_last(self):
        pass


class WordState(BaseState):
    """
    Чтение буквенного слова.
    Семантическая процедура 2 (методичка стр. 17-18):
      ищем в таблице служебных слов;
      если не найдено — выполняем сем. процедуру 1 (таблица идентификаторов).
    """

    def execute(self, symbol: str):
        a = self.analyzer
        if symbol.isalpha():
            self._add_char(symbol)
        elif symbol.isdigit() or symbol == '_':
            self._add_char(symbol)
            a.set_state(IdentificatorState(self.lexeme, a))
        elif (symbol in SEPARATORS or symbol in PART_OF_TWO_LIT
              or symbol in OPERATIONS or symbol in ('"', "'")):
            self._sem2()
            s = StartState('', a); a.set_state(s); s.execute(symbol)
        else:
            self._add_char(symbol)

    def execute_last(self):
        if self.lexeme:
            self._sem2()
            self.analyzer.set_state(StartState('', self.analyzer))

    def _sem2(self):
        """Сем. процедура 2: поиск в таблице служебных слов."""
        a = self.analyzer
        word = self.lexeme
        if word in KEYWORDS:
            a.add_token(Token('W', KEYWORDS[word], word))
        else:
            self._sem1(word)

    def _sem1(self, word: str):
        """Сем. процедура 1: занести в таблицу идентификаторов."""
        a = self.analyzer
        rec = a.get_or_add_id(word)
        a.add_token(Token('I', rec.code, word))


class IdentificatorState(BaseState):
    """
    Чтение идентификатора (буквы + цифры + _).
    Семантическая процедура 1.
    """

    def execute(self, symbol: str):
        a = self.analyzer
        if symbol.isalnum() or symbol == '_':
            self._add_char(symbol)
        elif (symbol in SEPARATORS or symbol in PART_OF_TWO_LIT
              or symbol in OPERATIONS or symbol in ('"', "'")):
            self._sem1()
            s = StartState('', a); a.set_state(s); s.execute(symbol)
        else:
            self._add_char(symbol)

    def execute_last(self):
        if self.lexeme:
            self._sem1()
            self.analyzer.set_state(StartState('', self.analyzer))

    def _sem1(self):
        """Сем. процедура 1: занести в таблицу идентификаторов."""
        a = self.analyzer
        rec = a.get_or_add_id(self.lexeme)
        a.add_token(Token('I', rec.code, self.lexeme))


class DigitState(BaseState):
    """
    Чтение целого числа.
    Семантическая процедура 3.
    """

    def execute(self, symbol: str):
        a = self.analyzer
        if symbol.isdigit() or symbol in ('e', 'E', '+', '-'):
            self._add_char(symbol)
        elif symbol == '.':
            a.set_state(DotDigitState(self.lexeme + '.', a))
        elif (symbol in SEPARATORS or symbol in PART_OF_TWO_LIT
              or symbol in OPERATIONS):
            self._sem3()
            s = StartState('', a); a.set_state(s); s.execute(symbol)
        else:
            self._add_char(symbol)

    def execute_last(self):
        if self.lexeme:
            self._sem3()
            self.analyzer.set_state(StartState('', self.analyzer))

    def _sem3(self):
        """Сем. процедура 3: занести в таблицу числовых констант."""
        a = self.analyzer
        code = a.get_or_add_num(self.lexeme)
        a.add_token(Token('N', code, self.lexeme))


class DotState(BaseState):
    """
    Промежуточное состояние после '.':
      следующая цифра → начало числа (.25) → DotDigitState
      иначе           → разделитель R6 (console.log)
    """

    def execute(self, symbol: str):
        a = self.analyzer
        if symbol.isdigit():
            a.set_state(DotDigitState('.' + symbol, a))
        else:
            # Точка — разделитель R6
            a.add_token(Token('R', SEPARATORS['.'], '.'))
            s = StartState('', a); a.set_state(s); s.execute(symbol)

    def execute_last(self):
        # Точка в конце строки — разделитель
        a = self.analyzer
        a.add_token(Token('R', SEPARATORS['.'], '.'))
        a.set_state(StartState('', a))


class DotDigitState(BaseState):
    """
    Чтение числа с фиксированной/плавающей точкой.
    Семантическая процедура 3.
    """

    def execute(self, symbol: str):
        a = self.analyzer
        if symbol.isdigit() or symbol in ('e', 'E', '+', '-'):
            self._add_char(symbol)
        elif (symbol in SEPARATORS or symbol in PART_OF_TWO_LIT
              or symbol in OPERATIONS or symbol.isalpha()):
            self._sem3()
            s = StartState('', a); a.set_state(s); s.execute(symbol)
        else:
            self._add_char(symbol)

    def execute_last(self):
        if self.lexeme:
            self._sem3()
            self.analyzer.set_state(StartState('', self.analyzer))

    def _sem3(self):
        a = self.analyzer
        code = a.get_or_add_num(self.lexeme)
        a.add_token(Token('N', code, self.lexeme))


class CharConstState(BaseState):
    """
    Чтение строковой/символьной константы (" " или ' ').
    Семантическая процедура 3 (для констант).
    """

    def execute(self, symbol: str):
        a = self.analyzer
        if symbol == self.lexeme[0]:          # закрывающая кавычка
            content = self.lexeme[1:]
            code = a.get_or_add_str(content)
            a.add_token(Token('C', code, content))
            a.set_state(StartState('', a))
        else:
            self._add_char(symbol)

    def execute_last(self):
        pass


class PartTwoLitState(BaseState):
    """
    Ожидание второго символа двулитерной операции (/ = < > !).
    Семантические процедуры 7 и 8.
    """

    def execute(self, symbol: str):
        a = self.analyzer
        two = self.lexeme + symbol

        if two in OPERATIONS:                 # двулитерная операция: == != <= >=
            a.add_token(Token('O', OPERATIONS[two], two))
            a.set_state(StartState('', a))
        elif two == '//':                     # однострочный комментарий
            a.set_state(CommentsState('', a))
        elif two == '/*':                     # многострочный комментарий
            a.set_state(MultiCommentState('', a))
        else:                                 # первый символ — однолитерная операция
            if self.lexeme in OPERATIONS:
                a.add_token(Token('O', OPERATIONS[self.lexeme], self.lexeme))
            s = StartState('', a); a.set_state(s); s.execute(symbol)

    def execute_last(self):
        a = self.analyzer
        if self.lexeme in OPERATIONS:
            a.add_token(Token('O', OPERATIONS[self.lexeme], self.lexeme))
        a.set_state(StartState('', a))


class CommentsState(BaseState):
    """
    Однострочный комментарий //.
    Семантическая процедура 5: удалить (игнорировать) до конца строки.
    """

    def execute(self, symbol: str):
        pass   # все символы игнорируются

    def execute_last(self):
        self.analyzer.set_state(StartState('', self.analyzer))


class MultiCommentState(BaseState):
    """Многострочный комментарий /* ... */ — ждём *."""

    def execute(self, symbol: str):
        if symbol == '*':
            self.analyzer.set_state(MultiCommentStopState('*', self.analyzer))

    def execute_last(self):
        pass   # комментарий продолжается на следующей строке


class MultiCommentStopState(BaseState):
    """Ждём / после * для закрытия комментария."""

    def execute(self, symbol: str):
        a = self.analyzer
        if symbol == '/':
            a.set_state(StartState('', a))
        else:
            a.set_state(MultiCommentState('', a))

    def execute_last(self):
        pass


class SeparatorState(BaseState):
    """
    Разделитель.
    Сем. процедура 4: пробел/табуляция — не кодируются, в выходную цепочку не попадают.
    Сем. процедура 9: остальные разделители → R-лексема.
    """

    def execute(self, symbol: str):
        a = self.analyzer
        if symbol not in (' ', '\t'):
            a.add_token(Token('R', SEPARATORS[symbol], symbol))
            # Отслеживаем вложенность блоков для таблицы идентификаторов
            if symbol == '{':
                a.increment_nesting()
            elif symbol == '}':
                a.decrement_nesting()
        a.set_state(StartState('', a))

    def execute_last(self):
        pass


class OperationState(BaseState):
    """
    Однолитерная операция.
    Семантическая процедура 6.
    """

    def execute(self, symbol: str):
        a = self.analyzer
        a.add_token(Token('O', OPERATIONS[symbol], symbol))
        a.set_state(StartState('', a))

    def execute_last(self):
        pass


# ============================================================
#  ЛЕКСИЧЕСКИЙ АНАЛИЗАТОР
# ============================================================

class LexicalAnalyzer:
    """
    Лексический анализатор для подмножества JavaScript.
    Обрабатывает входной текст построчно.

    Строит:
      — Постоянные таблицы: KEYWORDS, OPERATIONS, SEPARATORS (определены выше)
      — Временную таблицу идентификаторов (Таблица 1.6): self.id_records
      — Временную таблицу числовых констант (Таблица 1.5): self.num_table
      — Временную таблицу строковых констант: self.str_table
      — Внутреннее представление: self.tokens_by_line
    """

    def __init__(self):
        self._state: BaseState = None
        self._current_line_tokens: list = []

        # Результаты анализа
        self.tokens: list[Token] = []
        self.tokens_by_line: list[list[Token]] = []
        self.errors: list[str] = []

        # Временная таблица идентификаторов — Таблица 1.6
        # Список IdRecord в порядке первого появления
        self.id_records: list[IdRecord] = []
        self._id_map: dict[str, IdRecord] = {}   # имя → запись (для быстрого поиска)

        # Временная таблица числовых констант — Таблица 1.5
        # Запись: значение → (код, тип)  тип: 'integer' | 'fixed-point' | 'floating-point'
        self.num_table: dict[str, tuple] = {}

        # Временная таблица строковых констант
        # Запись: значение → (код, тип)  тип всегда 'string'
        self.str_table: dict[str, tuple] = {}

        self._id_counter    = 0
        self._num_counter   = 0
        self._str_counter   = 0
        self._nesting_level = 0   # текущий уровень вложенности { }

    # ── управление состоянием ──

    def set_state(self, state: BaseState):
        self._state = state

    def add_token(self, token: Token):
        self.tokens.append(token)
        self._current_line_tokens.append(token)
        # Определяем тип идентификатора по предыдущему токену
        self._resolve_id_type(token)

    def _resolve_id_type(self, token: Token):
        """
        Определяет тип данных переменной по присваиванию (Лаба 1).

        Три типа по условию преподавателя (срез языка):
          integer      — правая часть присваивания — целое число (N, тип integer)
          fixed-point  — правая часть — число с точкой (N, тип fixed-point
                         или floating-point — оба с точкой/экспонентой)
          string       — правая часть — строковая константа (C)

        Паттерн: I  O12(=)  N/C  →  обновляем тип идентификатора слева
        Вызывается после добавления каждого токена; работает когда
        только что добавлен N или C и перед ним стоит O12(=) и I.
        """
        # Нас интересует момент когда добавлена числовая или строковая константа
        if token.token_class not in ('N', 'C'):
            return

        # Нужно минимум 3 токена: I  O12  N/C
        if len(self.tokens) < 3:
            return

        assign = self.tokens[-2]   # должен быть O12 (=)
        ident  = self.tokens[-3]   # должен быть I (идентификатор)

        if not (assign.token_class == 'O' and assign.code == 12):
            return
        if ident.token_class != 'I':
            return

        rec = self._id_map.get(ident.value)
        if rec is None:
            return

        # Тип уже определён — не перезаписываем
        if rec.id_type != 'unknown':
            return

        # Определяем тип по правой части
        if token.token_class == 'C':
            rec.id_type = 'string'
        elif token.token_class == 'N':
            # берём тип из таблицы числовых констант
            entry = self.num_table.get(token.value)
            if entry:
                _, num_type = entry
                if num_type == 'integer':
                    rec.id_type = 'integer'
                else:
                    # fixed-point и floating-point → оба "с точкой"
                    rec.id_type = 'fixed-point' 

    def add_error(self, msg: str):
        self.errors.append(msg)

    # ── Таблица 1.6: идентификаторы ──

    def get_or_add_id(self, name: str) -> IdRecord:
        """
        Сем. процедура 1/2: поиск в таблице идентификаторов.
        Если не найден — создаём запись с текущим уровнем вложенности.
        Тип остаётся 'unknown' — уточняется в Лабе 2.
        """
        if name not in self._id_map:
            self._id_counter += 1
            rec = IdRecord(
                code=self._id_counter,
                name=name,
                nesting_level=self._nesting_level,
            )
            self.id_records.append(rec)
            self._id_map[name] = rec
        return self._id_map[name]

    def increment_nesting(self):
        """Вызывается при встрече '{' — увеличивает уровень вложенности."""
        self._nesting_level += 1

    def decrement_nesting(self):
        """Вызывается при встрече '}' — уменьшает уровень вложенности."""
        if self._nesting_level > 0:
            self._nesting_level -= 1

    # ── Таблица 1.5: числовые константы ──

    @staticmethod
    def _num_type(value: str) -> str:
        """Определяет тип числовой константы по её строковому значению."""
        v = value.lower()
        if 'e' in v:
            return 'floating-point'
        elif '.' in v:
            return 'fixed-point'
        else:
            return 'integer'

    def get_or_add_num(self, value: str) -> int:
        """Сем. процедура 3: занести в таблицу числовых констант с типом."""
        if value not in self.num_table:
            self._num_counter += 1
            self.num_table[value] = (self._num_counter, self._num_type(value))
        return self.num_table[value][0]

    # ── Таблица строковых констант ──

    def get_or_add_str(self, value: str) -> int:
        """Занести строковую константу в таблицу с типом 'string'."""
        if value not in self.str_table:
            self._str_counter += 1
            self.str_table[value] = (self._str_counter, 'string')
        return self.str_table[value][0]

    # ── обратная совместимость ──

    @property
    def id_table(self) -> dict:
        """Возвращает {имя: код} — для обратной совместимости с main.py."""
        return {rec.name: rec.code for rec in self.id_records}

    # ── главный метод ──

    def analyze(self, source_code: str) -> list[Token]:
        """Анализирует исходный текст построчно."""
        # Сброс
        self.tokens          = []
        self.tokens_by_line  = []
        self.errors          = []
        self.id_records      = []
        self._id_map         = {}
        self._nesting_level  = 0
        self.num_table       = {}
        self.str_table       = {}
        self._id_counter     = 0
        self._num_counter    = 0
        self._str_counter    = 0

        self._state = StartState('', self)
        for line in source_code.split('\n'):
            self._current_line_tokens = []
            for symbol in line:
                self._state.execute(symbol)
            self._state.execute_last()
            self.tokens_by_line.append(self._current_line_tokens)

        return self.tokens

    def get_internal_repr(self) -> str:
        return ' '.join(t.to_internal() for t in self.tokens)

    def get_line_repr(self, line_tokens: list) -> str:
        return ' '.join(t.to_internal() for t in line_tokens)