"""
Лабораторная работа №1: Лексический анализатор
Транслятор с языка JavaScript на язык R
Вариант 10: Входной язык - JavaScript, Выходной язык - R

Классы лексем:
  W - служебные слова
  I - идентификаторы
  O - операции
  R - разделители
  N - числовые константы
  C - символьные/строковые константы

Архитектура: паттерн "Состояние" (State pattern)
Состояния сканера (диаграмма состояний, раздел 1.4 методички):
  StartState            - начальное состояние S
  WordState             - чтение буквенной последовательности
  IdentificatorState    - чтение идентификатора (буквы+цифры+_)
  DigitState            - чтение целой числовой константы
  DotDigitState         - чтение числа с точкой / плавающей точкой
  CharConstState        - чтение строковой/символьной константы
  PartTwoLitState       - начало двулитерной операции (/ = < > !)
  CommentsState         - однострочный комментарий //
  MultiCommentState     - многострочный комментарий /*
  MultiCommentStopState - ожидание закрытия */ 
  SeparatorState        - разделитель
  OperationState        - однолитерная операция
"""

# ============================================================
#  ПОСТОЯННЫЕ ТАБЛИЦЫ ЛЕКСЕМ (определяются входным языком JS)
# ============================================================

# Таблица служебных слов W
# console и log — служебные слова (аналогично System/out/println в Java у коллеги)
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
        self.lexeme = lexeme
        self.analyzer = analyzer

    def execute(self, symbol: str):
        raise NotImplementedError

    def execute_last(self):
        """Вызывается в конце каждой строки."""
        pass

    def _add_char(self, symbol: str):
        self.lexeme += symbol


# ============================================================
#  СОСТОЯНИЯ СКАНЕРА
# ============================================================

class StartState(BaseState):
    """Начальное состояние S."""

    def execute(self, symbol: str):
        a = self.analyzer

        if symbol.isalpha() or symbol == '_':
            state = WordState('', a)
            a.set_state(state)
            state.execute(symbol)

        elif symbol == '$':
            state = IdentificatorState('', a)
            a.set_state(state)
            state.execute(symbol)

        elif symbol.isdigit():
            state = DigitState('', a)
            a.set_state(state)
            state.execute(symbol)

        elif symbol == '.':
            # Может быть разделитель R6 (console.log) или начало числа (.25)
            # Решается в DotState при получении следующего символа
            state = DotState('.', a)
            a.set_state(state)

        elif symbol in ('"', "'"):
            state = CharConstState(symbol, a)
            a.set_state(state)

        elif symbol in PART_OF_TWO_LIT:
            state = PartTwoLitState(symbol, a)
            a.set_state(state)

        elif symbol in SEPARATORS:
            state = SeparatorState('', a)
            a.set_state(state)
            state.execute(symbol)

        elif symbol in OPERATIONS:
            state = OperationState('', a)
            a.set_state(state)
            state.execute(symbol)

    def execute_last(self):
        pass


class WordState(BaseState):
    """
    Чтение слова, начинающегося с буквы.
    Семантическая процедура 1:
      — если слово в таблице служебных слов → W-лексема
      — иначе → занести в таблицу идентификаторов → I-лексема
    """

    def execute(self, symbol: str):
        a = self.analyzer
        if symbol.isalpha():
            self._add_char(symbol)

        elif symbol.isdigit() or symbol == '_':
            self._add_char(symbol)
            a.set_state(IdentificatorState(self.lexeme, a))

        elif symbol in SEPARATORS or symbol in PART_OF_TWO_LIT or symbol in OPERATIONS:
            self._sem1()
            start = StartState('', a)
            a.set_state(start)
            start.execute(symbol)

        elif symbol in ('"', "'"):
            self._sem1()
            start = StartState('', a)
            a.set_state(start)
            start.execute(symbol)

        else:
            self._add_char(symbol)

    def execute_last(self):
        if self.lexeme:
            self._sem1()
            self.analyzer.set_state(StartState('', self.analyzer))

    def _sem1(self):
        a = self.analyzer
        word = self.lexeme
        if word in KEYWORDS:
            a.add_token(Token('W', KEYWORDS[word], word))
        else:
            code = a.get_or_add_id(word)
            a.add_token(Token('I', code, word))


class IdentificatorState(BaseState):
    """
    Чтение идентификатора (буквы, цифры, _).
    Семантическая процедура 2: занести в таблицу идентификаторов → I-лексема.
    """

    def execute(self, symbol: str):
        a = self.analyzer
        if symbol.isalnum() or symbol == '_':
            self._add_char(symbol)

        elif symbol in SEPARATORS or symbol in PART_OF_TWO_LIT or symbol in OPERATIONS:
            self._sem2()
            start = StartState('', a)
            a.set_state(start)
            start.execute(symbol)

        elif symbol in ('"', "'"):
            self._sem2()
            start = StartState('', a)
            a.set_state(start)
            start.execute(symbol)

        else:
            self._add_char(symbol)

    def execute_last(self):
        if self.lexeme:
            self._sem2()
            self.analyzer.set_state(StartState('', self.analyzer))

    def _sem2(self):
        a = self.analyzer
        code = a.get_or_add_id(self.lexeme)
        a.add_token(Token('I', code, self.lexeme))


class DigitState(BaseState):
    """
    Чтение целой числовой константы.
    Семантическая процедура 3: занести в таблицу чисел → N-лексема.
    """

    def execute(self, symbol: str):
        a = self.analyzer
        if symbol.isdigit() or symbol in ('e', 'E', '+', '-'):
            self._add_char(symbol)

        elif symbol == '.':
            a.set_state(DotDigitState(self.lexeme + '.', a))

        elif symbol in SEPARATORS or symbol in PART_OF_TWO_LIT or symbol in OPERATIONS:
            self._sem3()
            start = StartState('', a)
            a.set_state(start)
            start.execute(symbol)

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


class DotDigitState(BaseState):
    """
    Чтение числа с фиксированной/плавающей точкой.
    Семантическая процедура 3.
    """

    def execute(self, symbol: str):
        a = self.analyzer
        if symbol.isdigit() or symbol in ('e', 'E', '+', '-'):
            self._add_char(symbol)

        elif symbol.isalpha():
            self._sem3()
            start = StartState('', a)
            a.set_state(start)
            start.execute(symbol)

        elif symbol in SEPARATORS or symbol in PART_OF_TWO_LIT or symbol in OPERATIONS:
            self._sem3()
            start = StartState('', a)
            a.set_state(start)
            start.execute(symbol)

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


class DotState(BaseState):
    """
    Промежуточное состояние после символа '.'.
    Если следующий символ — цифра → это начало числа (.25) → DotDigitState.
    Иначе → это разделитель R6 (точка доступа console.log).
    """

    def execute(self, symbol: str):
        a = self.analyzer
        if symbol.isdigit():
            # Начало числа вида .25
            state = DotDigitState('.' + symbol, a)
            a.set_state(state)
        else:
            # Разделитель '.' — R6
            a.add_token(Token('R', SEPARATORS['.'], '.'))
            start = StartState('', a)
            a.set_state(start)
            start.execute(symbol)

    def execute_last(self):
        # Точка в конце строки — разделитель
        a = self.analyzer
        a.add_token(Token('R', SEPARATORS['.'], '.'))
        a.set_state(StartState('', a))


class CharConstState(BaseState):
    """
    Чтение строковой/символьной константы (в " " или ' ').
    Семантическая процедура 5: занести в таблицу строк → C-лексема.
    """

    def execute(self, symbol: str):
        a = self.analyzer
        opening = self.lexeme[0]
        if symbol == opening:
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
    Ожидание второго символа потенциально двулитерной операции.
    Символы-инициаторы: / = < > !
    Семантическая процедура 8.
    """

    def execute(self, symbol: str):
        a = self.analyzer
        two = self.lexeme + symbol

        if two in OPERATIONS:
            # Двулитерная операция: == != <= >=
            a.add_token(Token('O', OPERATIONS[two], two))
            a.set_state(StartState('', a))

        elif two == '//':
            a.set_state(CommentsState('', a))

        elif two == '/*':
            a.set_state(MultiCommentState('', a))

        else:
            # Первый символ — однолитерная операция, второй — заново
            first = self.lexeme
            if first in OPERATIONS:
                a.add_token(Token('O', OPERATIONS[first], first))
            start = StartState('', a)
            a.set_state(start)
            start.execute(symbol)

    def execute_last(self):
        a = self.analyzer
        first = self.lexeme
        if first in OPERATIONS:
            a.add_token(Token('O', OPERATIONS[first], first))
        a.set_state(StartState('', a))


class CommentsState(BaseState):
    """Однострочный комментарий // — всё до конца строки игнорируется."""

    def execute(self, symbol: str):
        pass  # Сем. процедура 7: все символы игнорируются

    def execute_last(self):
        self.analyzer.set_state(StartState('', self.analyzer))


class MultiCommentState(BaseState):
    """Многострочный комментарий /* — ждём *."""

    def execute(self, symbol: str):
        if symbol == '*':
            self.analyzer.set_state(MultiCommentStopState('*', self.analyzer))

    def execute_last(self):
        pass  # комментарий продолжается на следующей строке


class MultiCommentStopState(BaseState):
    """Ждём / после * для закрытия /* комментария."""

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
    Семантическая процедура 4: пробел не кодируется.
    Семантическая процедура 9: не-пробельный разделитель → R-лексема.
    """

    def execute(self, symbol: str):
        a = self.analyzer
        if symbol not in (' ', '\t'):
            a.add_token(Token('R', SEPARATORS[symbol], symbol))
        a.set_state(StartState('', a))

    def execute_last(self):
        pass


class OperationState(BaseState):
    """Однолитерная операция."""

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
    Обрабатывает входной текст построчно,
    формирует таблицы лексем и внутреннее представление.
    """

    def __init__(self):
        self._state: BaseState = None
        self._current_line_tokens: list = []

        # Результаты анализа
        self.tokens: list[Token] = []
        self.tokens_by_line: list[list[Token]] = []
        self.errors: list[str] = []

        # Временные таблицы (создаются в процессе анализа)
        self.id_table: dict[str, int] = {}
        self.num_table: dict[str, int] = {}
        self.str_table: dict[str, int] = {}

        self._id_counter = 0
        self._num_counter = 0
        self._str_counter = 0

    # ── управление состоянием ──

    def set_state(self, state: BaseState):
        self._state = state

    def add_token(self, token: Token):
        self.tokens.append(token)
        self._current_line_tokens.append(token)

    def add_error(self, msg: str):
        self.errors.append(msg)

    # ── временные таблицы ──

    def get_or_add_id(self, name: str) -> int:
        if name not in self.id_table:
            self._id_counter += 1
            self.id_table[name] = self._id_counter
        return self.id_table[name]

    def get_or_add_num(self, value: str) -> int:
        if value not in self.num_table:
            self._num_counter += 1
            self.num_table[value] = self._num_counter
        return self.num_table[value]

    def get_or_add_str(self, value: str) -> int:
        if value not in self.str_table:
            self._str_counter += 1
            self.str_table[value] = self._str_counter
        return self.str_table[value]

    # ── главный метод ──

    def analyze(self, source_code: str) -> list[Token]:
        """Анализирует исходный текст построчно."""
        # Сброс
        self.tokens = []
        self.tokens_by_line = []
        self.errors = []
        self.id_table = {}
        self.num_table = {}
        self.str_table = {}
        self._id_counter = 0
        self._num_counter = 0
        self._str_counter = 0

        self._state = StartState('', self)
        lines = source_code.split('\n')

        for line in lines:
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