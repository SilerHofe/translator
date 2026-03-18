"""
Лабораторная работа №4: Синтаксический анализатор
Вариант 10: JavaScript → R

Метод рекурсивного спуска (методичка стр. 54–64).

Входные данные — результат Лабы 1 (output_tokens.txt).

Грамматика JavaScript (Вариант 10, адаптация от методички стр. 54–55):

  <программа>   ::= <текст>
  <текст>       ::= { <элемент> }
  <элемент>     ::= <описание> | <функция> | <оператор>
  <описание>    ::= var <идент> { , <идент> } ;
  <функция>     ::= function <идент> ( <парамы> ) { <текст> }
  <парамы>      ::= [ <идент> { , <идент> } ]
  <оператор>    ::= <идент> [ <метка>: ] <опер_тело>
                  | <условный>
                  | <цикл_while>
                  | <цикл_for>
                  | <возврат>
                  | <вызов_конс>
  <опер_тело>   ::= = <выражение> ;
                  | [ <выраж> ] = <выражение> ;
  <условный>    ::= if ( <условие> ) { <текст> } [ else { <текст> } ]
  <цикл_while>  ::= while ( <условие> ) { <текст> }
  <цикл_for>    ::= for ( <оператор> <условие> ; <оператор_без_; > ) { <текст> }
  <возврат>     ::= return <выражение> ;
  <вызов_конс>  ::= console . log ( <аргументы> ) ;
  <условие>     ::= <выражение> <опер_сравн> <выражение>
  <выражение>   ::= <терм> { ( + | - ) <терм> }
  <терм>        ::= <множитель> { ( * | / | % ) <множитель> }
  <множитель>   ::= <аргумент> | ( <выражение> )
  <аргумент>    ::= <идент> [ ( <аргументы> ) | [ <выражение> ] ]
                  | <константа>
  <аргументы>   ::= <выражение> { , <выражение> }
  <идент>       ::= I (идентификатор, класс I)
  <константа>   ::= N | C | W9(true) | W10(false) | W11(null)
  <опер_сравн>  ::= < | > | == | != | <= | >=

Ключевые принципы метода рекурсивного спуска (методичка стр. 56–58):
  - NXTSYMB — глобальная переменная с текущим токеном
  - SCAN — сдвиг на следующий токен
  - ERROR — обработка ошибки с указанием строки и конструкции
  - Каждый нетерминал — отдельная процедура (таблица 4.1 методички)
"""

import os, sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lexer import Token, KEYWORDS, OPERATIONS, SEPARATORS
from load_tables import load_lab1_results


# ============================================================
#  УЗЕЛ ДЕРЕВА РАЗБОРА
# ============================================================

@dataclass
class ParseNode:
    """Узел дерева разбора."""
    label: str                          # имя нетерминала или значение терминала
    children: List['ParseNode'] = field(default_factory=list)
    token: Optional[Token] = None      # для листьев — исходный токен

    def add(self, child: 'ParseNode') -> 'ParseNode':
        self.children.append(child)
        return child

    def to_dict(self) -> dict:
        """Сериализация для JSON (для GUI)."""
        d = {'label': self.label}
        if self.token:
            d['token'] = f"{self.token.token_class}{self.token.code}"
        if self.children:
            d['children'] = [c.to_dict() for c in self.children]
        return d


# ============================================================
#  ОШИБКА СИНТАКСИЧЕСКОГО АНАЛИЗА
# ============================================================

class SyntaxError4(Exception):
    def __init__(self, msg: str, token: Optional[Token] = None, line: int = 0):
        super().__init__(msg)
        self.token   = token
        self.line    = line
        self.message = msg


# ============================================================
#  СИНТАКСИЧЕСКИЙ АНАЛИЗАТОР
# ============================================================

class Parser:
    """
    Синтаксический анализатор методом рекурсивного спуска.
    По методичке стр. 57–64, таблица 4.1.
    """

    def __init__(self):
        self._tokens: List[Token] = []
        self._pos: int = 0
        self.NXTSYMB: Optional[Token] = None  # методичка: переменная NXTSYMB
        self.errors: List[str] = []
        self.parse_steps: List[dict] = []  # трассировка для GUI
        self.tree: Optional[ParseNode] = None

    # ── SCAN и ERROR (методичка стр. 57) ────────────────────

    def SCAN(self):
        """Перейти к следующему токену (методичка стр. 57)."""
        self._pos += 1
        if self._pos < len(self._tokens):
            self.NXTSYMB = self._tokens[self._pos]
        else:
            self.NXTSYMB = None  # конец потока

    def ERROR(self, msg: str):
        """Зафиксировать синтаксическую ошибку (методичка стр. 57)."""
        tok = self.NXTSYMB
        line_info = f" (токен: {tok.token_class}{tok.code}='{tok.value}')" if tok else " (конец файла)"
        full_msg = msg + line_info
        self.errors.append(full_msg)
        raise SyntaxError4(full_msg, tok)

    def _log(self, proc: str, action: str = ''):
        """Трассировка шагов для GUI."""
        self.parse_steps.append({
            'proc': proc,
            'token': f"{self.NXTSYMB.token_class}{self.NXTSYMB.code}='{self.NXTSYMB.value}'" if self.NXTSYMB else 'EOF',
            'action': action,
            'pos': self._pos,
        })

    # ── вспомогательные ─────────────────────────────────────

    def _is(self, tc: str, code: int = None) -> bool:
        """Проверить текущий токен."""
        if self.NXTSYMB is None:
            return False
        if self.NXTSYMB.token_class != tc:
            return False
        if code is not None and self.NXTSYMB.code != code:
            return False
        return True

    def _expect(self, tc: str, code: int, err_msg: str) -> Token:
        """Проверить и потребить токен."""
        if not self._is(tc, code):
            self.ERROR(err_msg)
        tok = self.NXTSYMB
        self.SCAN()
        return tok

    def _consume(self) -> Token:
        """Потребить текущий токен и вернуть его."""
        tok = self.NXTSYMB
        self.SCAN()
        return tok

    # ── главный метод ────────────────────────────────────────

    def parse(self, tokens: List[Token]) -> Tuple[Optional[ParseNode], List[str]]:
        """
        Запускает синтаксический анализ.
        Возвращает (дерево разбора, список ошибок).
        """
        self._tokens   = tokens
        self._pos      = -1
        self.errors    = []
        self.parse_steps = []
        self.SCAN()  # инициализация: первый токен → NXTSYMB

        try:
            self.tree = self.PROGRAM()
        except SyntaxError4:
            pass
        except Exception as e:
            self.errors.append(f"Внутренняя ошибка: {e}")

        return self.tree, self.errors

    # ── PROGRAM (методичка: процедура PROGRAM) ───────────────

    def PROGRAM(self) -> ParseNode:
        """<программа> ::= <текст> EOF"""
        self._log('PROGRAM', 'начало разбора программы')
        node = ParseNode('<программа>')
        node.add(self.TEXT())
        if self.NXTSYMB is not None:
            pass  # допускаем остаток (без PROC/END в JS)
        self._log('PROGRAM', 'программа разобрана успешно')
        return node

    # ── TEXT (методичка: процедура TEXT) ─────────────────────

    def TEXT(self) -> ParseNode:
        """<текст> ::= { <элемент> }"""
        self._log('TEXT', 'начало текста')
        node = ParseNode('<текст>')
        while self.NXTSYMB is not None and not self._is('R', 10):  # не '}'
            try:
                elem = self.ELEMENT()
                if elem:
                    node.add(elem)
            except SyntaxError4:
                # Восстановление: пропускаем до ';' или '}'
                while self.NXTSYMB and not self._is('R', 3) and not self._is('R', 10):
                    self.SCAN()
                if self._is('R', 3):
                    self.SCAN()
                break
        return node

    # ── ELEMENT ──────────────────────────────────────────────

    def ELEMENT(self) -> Optional[ParseNode]:
        """<элемент> ::= <описание> | <функция> | <оператор>"""
        self._log('ELEMENT', f'анализ элемента')
        if self._is('W', 1):        # var
            return self.DECLARE()
        elif self._is('W', 2):      # function
            return self.FUNCTION()
        elif self._is('W', 4):      # if
            return self.IF_OPER()
        elif self._is('W', 6):      # while
            return self.WHILE_OPER()
        elif self._is('W', 7):      # for
            return self.FOR_OPER()
        elif self._is('W', 3):      # return
            return self.RETURN_STMT()
        elif self._is('W', 12):     # console
            return self.CONSOLE_LOG()
        elif self._is('I'):
            return self.STATEMENT()
        elif self._is('R', 3):      # одиночная ;
            self.SCAN()
            return None
        else:
            if self.NXTSYMB:
                self.ERROR(f"Неожиданный токен '{self.NXTSYMB.value}'")
            return None

    # ── DECLARE (методичка: процедура DECLARE) ───────────────

    def DECLARE(self) -> ParseNode:
        """<описание> ::= var <идент> { , <идент> } ;"""
        self._log('DECLARE', 'объявление переменных')
        node = ParseNode('<описание>')
        self._expect('W', 1, "Ожидается 'var'")
        node.add(ParseNode('var'))
        ident = self.IDENT()
        node.add(ident)
        while self._is('R', 2):  # ','
            self.SCAN()
            node.add(self.IDENT())
        if self._is('R', 3):     # ';'
            self.SCAN()
        else:
            self.ERROR("Ожидается ';' после объявления переменных")
        return node

    # ── FUNCTION ─────────────────────────────────────────────

    def FUNCTION(self) -> ParseNode:
        """<функция> ::= function <идент> ( <парамы> ) { <текст> }"""
        self._log('FUNCTION', 'объявление функции')
        node = ParseNode('<функция>')
        self._expect('W', 2, "Ожидается 'function'")
        node.add(ParseNode('function'))
        node.add(self.IDENT())
        self._expect('R', 4, "Ожидается '(' после имени функции")
        params = ParseNode('<параметры>')
        if self._is('I'):
            params.add(self.IDENT())
            while self._is('R', 2):
                self.SCAN()
                params.add(self.IDENT())
        node.add(params)
        self._expect('R', 5, "Ожидается ')' после параметров")
        self._expect('R', 9, "Ожидается '{' начало тела функции")
        node.add(self.TEXT())
        self._expect('R', 10, "Ожидается '}' конец тела функции")
        return node

    # ── STATEMENT (методичка: SEP_OPER + OPERATOR) ───────────

    def STATEMENT(self) -> ParseNode:
        """
        <оператор> ::= <идент> = <выражение> ;
                     | <идент> [ <выраж> ] = <выражение> ;
                     | <идент> ( <аргументы> ) ;  (вызов функции)
        """
        self._log('STATEMENT', 'оператор присваивания/вызова')
        node = ParseNode('<оператор>')
        ident = self.IDENT()
        node.add(ident)

        if self._is('R', 7):        # '['  — обращение к массиву
            self.SCAN()
            node.add(self.EXPRESSION())
            self._expect('R', 8, "Ожидается ']'")
            self._expect('O', 12, "Ожидается '=' после arr[idx]")
            node.add(ParseNode(':='))
            node.add(self.EXPRESSION())
            self._expect('R', 3, "Ожидается ';'")

        elif self._is('O', 12):     # '='  — присваивание
            self.SCAN()
            node.add(ParseNode(':='))
            if self._is('W', 8):    # new (new array(...))
                self.SCAN()
                node.add(self.IDENT())
                self._expect('R', 4, "Ожидается '('")
                args = ParseNode('<аргументы>')
                if not self._is('R', 5):
                    args.add(self.EXPRESSION())
                    while self._is('R', 2):
                        self.SCAN()
                        args.add(self.EXPRESSION())
                node.add(args)
                self._expect('R', 5, "Ожидается ')'")
            else:
                node.add(self.EXPRESSION())
            self._expect('R', 3, "Ожидается ';'")

        elif self._is('R', 4):      # '(' — вызов функции
            self.SCAN()
            args = ParseNode('<аргументы>')
            if not self._is('R', 5):
                args.add(self.EXPRESSION())
                while self._is('R', 2):
                    self.SCAN()
                    args.add(self.EXPRESSION())
            node.add(args)
            self._expect('R', 5, "Ожидается ')' после аргументов")
            self._expect('R', 3, "Ожидается ';'")

        else:
            self.ERROR(f"Ожидается '=', '[' или '(' после идентификатора '{ident.label}'")

        return node

    # ── IF_OPER (методичка: процедура IF_OPER) ───────────────

    def IF_OPER(self) -> ParseNode:
        """<условный> ::= if ( <условие> ) { <текст> } [ else { <текст> } ]"""
        self._log('IF_OPER', 'условный оператор')
        node = ParseNode('<условный оператор>')
        self._expect('W', 4, "Ожидается 'if'")
        node.add(ParseNode('if'))
        self._expect('R', 4, "Ожидается '(' после if")
        node.add(self.CONDITION())
        self._expect('R', 5, "Ожидается ')' после условия")
        self._expect('R', 9, "Ожидается '{' тело if")
        node.add(self.TEXT())
        self._expect('R', 10, "Ожидается '}' конец if")
        if self._is('W', 5):        # else
            self.SCAN()
            node.add(ParseNode('else'))
            self._expect('R', 9, "Ожидается '{' тело else")
            node.add(self.TEXT())
            self._expect('R', 10, "Ожидается '}' конец else")
        return node

    # ── WHILE_OPER ───────────────────────────────────────────

    def WHILE_OPER(self) -> ParseNode:
        """<цикл_while> ::= while ( <условие> ) { <текст> }"""
        self._log('WHILE_OPER', 'цикл while')
        node = ParseNode('<цикл while>')
        self._expect('W', 6, "Ожидается 'while'")
        node.add(ParseNode('while'))
        self._expect('R', 4, "Ожидается '('")
        node.add(self.CONDITION())
        self._expect('R', 5, "Ожидается ')'")
        self._expect('R', 9, "Ожидается '{'")
        node.add(self.TEXT())
        self._expect('R', 10, "Ожидается '}'")
        return node

    # ── FOR_OPER ─────────────────────────────────────────────

    def FOR_OPER(self) -> ParseNode:
        """<цикл_for> ::= for ( <инит> ; <условие> ; <шаг> ) { <текст> }"""
        self._log('FOR_OPER', 'цикл for')
        node = ParseNode('<цикл for>')
        self._expect('W', 7, "Ожидается 'for'")
        node.add(ParseNode('for'))
        self._expect('R', 4, "Ожидается '('")
        # инициализация
        if self._is('W', 1):
            node.add(self.DECLARE())
        elif self._is('I'):
            node.add(self.STATEMENT())
        # условие
        if not self._is('R', 3):
            node.add(self.CONDITION())
        self._expect('R', 3, "Ожидается ';' в for")
        # шаг (оператор без точки с запятой)
        if self._is('I'):
            n = ParseNode('<шаг>')
            ident = self.IDENT(); n.add(ident)
            self._expect('O', 12, "Ожидается '=' в шаге for")
            n.add(self.EXPRESSION())
            node.add(n)
        self._expect('R', 5, "Ожидается ')'")
        self._expect('R', 9, "Ожидается '{'")
        node.add(self.TEXT())
        self._expect('R', 10, "Ожидается '}'")
        return node

    # ── RETURN ───────────────────────────────────────────────

    def RETURN_STMT(self) -> ParseNode:
        """<возврат> ::= return <выражение> ;"""
        self._log('RETURN_STMT', 'оператор return')
        node = ParseNode('<return>')
        self._expect('W', 3, "Ожидается 'return'")
        node.add(ParseNode('return'))
        node.add(self.EXPRESSION())
        self._expect('R', 3, "Ожидается ';'")
        return node

    # ── CONSOLE.LOG ──────────────────────────────────────────

    def CONSOLE_LOG(self) -> ParseNode:
        """<вывод> ::= console . log ( <аргументы> ) ;"""
        self._log('CONSOLE_LOG', 'console.log')
        node = ParseNode('<console.log>')
        self._expect('W', 12, "Ожидается 'console'")
        self._expect('R', 6, "Ожидается '.'")
        self._expect('W', 13, "Ожидается 'log'")
        self._expect('R', 4, "Ожидается '('")
        args = ParseNode('<аргументы>')
        if not self._is('R', 5):
            args.add(self.EXPRESSION())
            while self._is('R', 2):
                self.SCAN()
                args.add(self.EXPRESSION())
        node.add(args)
        self._expect('R', 5, "Ожидается ')'")
        self._expect('R', 3, "Ожидается ';'")
        return node

    # ── CONDITION (методичка: процедура CONDITION) ────────────

    def CONDITION(self) -> ParseNode:
        """<условие> ::= <выражение> <опер_сравн> <выражение>"""
        self._log('CONDITION', 'условие')
        node = ParseNode('<условие>')
        node.add(self.EXPRESSION())
        if self._is('O', 6):   # <
            tok = self._consume(); node.add(ParseNode('<'))
        elif self._is('O', 7): # >
            tok = self._consume(); node.add(ParseNode('>'))
        elif self._is('O', 8): # ==
            tok = self._consume(); node.add(ParseNode('=='))
        elif self._is('O', 9): # !=
            tok = self._consume(); node.add(ParseNode('!='))
        elif self._is('O', 10): # <=
            tok = self._consume(); node.add(ParseNode('<='))
        elif self._is('O', 11): # >=
            tok = self._consume(); node.add(ParseNode('>='))
        else:
            self.ERROR("Ожидается оператор сравнения (<, >, ==, !=, <=, >=)")
        node.add(self.EXPRESSION())
        return node

    # ── EXPRESSION (методичка: процедура EXPRESSION) ─────────

    def EXPRESSION(self) -> ParseNode:
        """<выражение> ::= <терм> { (+ | -) <терм> }"""
        self._log('EXPRESSION', 'выражение')
        node = ParseNode('<выражение>')
        node.add(self.TERM())
        while self._is('O', 1) or self._is('O', 2):  # + или -
            op = self._consume()
            node.add(ParseNode(op.value))
            node.add(self.TERM())
        return node

    # ── TERM (методичка: процедура TERM) ─────────────────────

    def TERM(self) -> ParseNode:
        """<терм> ::= <множитель> { (* | / | %) <множитель> }"""
        self._log('TERM', 'терм')
        node = ParseNode('<терм>')
        node.add(self.FACTOR())
        while self._is('O', 3) or self._is('O', 4) or self._is('O', 5):  # * / %
            op = self._consume()
            node.add(ParseNode(op.value))
            node.add(self.FACTOR())
        return node

    # ── FACTOR (методичка: процедура FACTOR) ─────────────────

    def FACTOR(self) -> ParseNode:
        """<множитель> ::= <аргумент> | ( <выражение> )"""
        self._log('FACTOR', 'множитель')
        if self._is('R', 4):  # '('
            self.SCAN()
            node = ParseNode('<скобки>')
            node.add(self.EXPRESSION())
            self._expect('R', 5, "Ожидается ')' закрывающая скобка")
            return node
        else:
            return self.ARGUMENT()

    # ── ARGUMENT (методичка: процедура ARGUMENT) ─────────────

    def ARGUMENT(self) -> ParseNode:
        """<аргумент> ::= <идент> [ (...) | [...] ] | <константа>"""
        self._log('ARGUMENT', 'аргумент')
        if self._is('I'):
            node = ParseNode('<аргумент>')
            ident = self.IDENT()
            node.add(ident)
            if self._is('R', 4):   # вызов функции
                self.SCAN()
                args = ParseNode('<аргументы>')
                if not self._is('R', 5):
                    args.add(self.EXPRESSION())
                    while self._is('R', 2):
                        self.SCAN()
                        args.add(self.EXPRESSION())
                node.add(args)
                self._expect('R', 5, "Ожидается ')'")
            elif self._is('R', 7): # индекс массива
                self.SCAN()
                node.add(self.EXPRESSION())
                self._expect('R', 8, "Ожидается ']'")
            return node
        elif self.CONST(self.NXTSYMB):
            node = ParseNode('<константа>')
            tok = self._consume()
            node.token = tok
            node.add(ParseNode(tok.value, token=tok))
            return node
        else:
            self.ERROR("Ожидается идентификатор или константа")

    # ── IDENT (методичка: процедура IDENT) ───────────────────

    def IDENT(self) -> ParseNode:
        """Проверяет что NXTSYMB — идентификатор класса I."""
        if not self._is('I'):
            self.ERROR(f"Ожидается идентификатор, получен '{self.NXTSYMB.value if self.NXTSYMB else 'EOF'}'")
        tok = self.NXTSYMB
        self.SCAN()
        node = ParseNode(tok.value, token=tok)
        return node

    # ── CONST (методичка: процедура CONST) ───────────────────

    def CONST(self, tok: Optional[Token]) -> bool:
        """Возвращает True если токен является константой."""
        if tok is None:
            return False
        if tok.token_class == 'N':  # числовая
            return True
        if tok.token_class == 'C':  # строковая
            return True
        if tok.token_class == 'W' and tok.code in (9, 10, 11):  # true/false/null
            return True
        return False


# ============================================================
#  ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

def run_parser(prefix: str = 'output') -> dict:
    """
    Запускает синтаксический анализ.
    Возвращает словарь с результатами для GUI.
    """
    tokens_file = f"{prefix}_tokens.txt"
    try:
        tokens = load_lab1_results(prefix=prefix)
    except FileNotFoundError as e:
        return {'ok': False, 'error': str(e), 'tree': None, 'steps': [], 'errors': []}

    parser = Parser()
    tree, errors = parser.parse(tokens)

    return {
        'ok':     len(errors) == 0,
        'errors': errors,
        'tree':   tree.to_dict() if tree else None,
        'steps':  parser.parse_steps,
        'token_count': len(tokens),
    }


if __name__ == '__main__':
    import json
    prefix = sys.argv[1] if len(sys.argv) > 1 else 'output'
    result = run_parser(prefix)
    if result['ok']:
        print("✓ Синтаксический анализ завершён успешно")
    else:
        print("✗ Найдены ошибки:")
        for e in result['errors']:
            print(f"  {e}")
    print(f"Шагов анализа: {len(result['steps'])}")