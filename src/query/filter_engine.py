"""
Unified boolean filter engine for text matching.

Supports:
- Exact phrase matching: "machine learning"
- Case-insensitive word matching: python
- Logical operators: AND, OR, NOT
- Parentheses for grouping: ("AI" OR "ML") AND "agents"

This engine is used by both HackerNews and arXiv adapters
for local text filtering.
"""

import re
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod


class TokenType(Enum):
    WORD = "WORD"
    PHRASE = "PHRASE"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    EOF = "EOF"


@dataclass
class Token:
    type: TokenType
    value: str


class FilterLexer:
    """Tokenizer for filter expressions."""

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.current_char = self.text[0] if text else None

    def advance(self):
        """Move to the next character."""
        self.pos += 1
        if self.pos < len(self.text):
            self.current_char = self.text[self.pos]
        else:
            self.current_char = None

    def skip_whitespace(self):
        """Skip whitespace characters."""
        while self.current_char is not None and self.current_char.isspace():
            self.advance()

    def read_phrase(self) -> str:
        """Read a quoted phrase."""
        self.advance()  # skip opening quote
        result = ""
        while self.current_char is not None and self.current_char != '"':
            result += self.current_char
            self.advance()
        if self.current_char == '"':
            self.advance()  # skip closing quote
        return result

    def read_word(self) -> str:
        """Read a word (alphanumeric + some special chars)."""
        result = ""
        while (self.current_char is not None and
               (self.current_char.isalnum() or self.current_char in '-_.')):
            result += self.current_char
            self.advance()
        return result

    def get_next_token(self) -> Token:
        """Get the next token from input."""
        while self.current_char is not None:
            if self.current_char.isspace():
                self.skip_whitespace()
                continue

            if self.current_char == '"':
                return Token(TokenType.PHRASE, self.read_phrase())

            if self.current_char == '(':
                self.advance()
                return Token(TokenType.LPAREN, '(')

            if self.current_char == ')':
                self.advance()
                return Token(TokenType.RPAREN, ')')

            if self.current_char.isalnum() or self.current_char in '-_.':
                word = self.read_word()
                upper_word = word.upper()
                if upper_word == 'AND':
                    return Token(TokenType.AND, 'AND')
                elif upper_word == 'OR':
                    return Token(TokenType.OR, 'OR')
                elif upper_word == 'NOT':
                    return Token(TokenType.NOT, 'NOT')
                else:
                    return Token(TokenType.WORD, word)

            # Skip unknown characters
            self.advance()

        return Token(TokenType.EOF, '')


class FilterNode(ABC):
    """Base class for filter AST nodes."""

    @abstractmethod
    def evaluate(self, text: str) -> bool:
        """Evaluate whether this node matches the given text."""
        pass

    @abstractmethod
    def to_string(self) -> str:
        """Convert the node back to a string expression."""
        pass


class TermNode(FilterNode):
    """Node for a search term (word or phrase)."""

    def __init__(self, term: str, is_phrase: bool = False):
        self.term = term
        self.is_phrase = is_phrase

    def evaluate(self, text: str) -> bool:
        text_lower = text.lower()
        term_lower = self.term.lower()

        if self.is_phrase:
            # Exact phrase match (case-insensitive)
            return term_lower in text_lower
        else:
            # Word boundary match (case-insensitive)
            pattern = r'\b' + re.escape(term_lower) + r'\b'
            return bool(re.search(pattern, text_lower, re.IGNORECASE))

    def to_string(self) -> str:
        if self.is_phrase:
            return f'"{self.term}"'
        return self.term

    def __repr__(self):
        if self.is_phrase:
            return f'Phrase("{self.term}")'
        return f'Word({self.term})'


class NotNode(FilterNode):
    """Node for NOT operation."""

    def __init__(self, operand: FilterNode):
        self.operand = operand

    def evaluate(self, text: str) -> bool:
        return not self.operand.evaluate(text)

    def to_string(self) -> str:
        return f'NOT {self.operand.to_string()}'

    def __repr__(self):
        return f'NOT({self.operand})'


class AndNode(FilterNode):
    """Node for AND operation."""

    def __init__(self, left: FilterNode, right: FilterNode):
        self.left = left
        self.right = right

    def evaluate(self, text: str) -> bool:
        return self.left.evaluate(text) and self.right.evaluate(text)

    def to_string(self) -> str:
        return f'({self.left.to_string()} AND {self.right.to_string()})'

    def __repr__(self):
        return f'AND({self.left}, {self.right})'


class OrNode(FilterNode):
    """Node for OR operation."""

    def __init__(self, left: FilterNode, right: FilterNode):
        self.left = left
        self.right = right

    def evaluate(self, text: str) -> bool:
        return self.left.evaluate(text) or self.right.evaluate(text)

    def to_string(self) -> str:
        return f'({self.left.to_string()} OR {self.right.to_string()})'

    def __repr__(self):
        return f'OR({self.left}, {self.right})'


class FilterParser:
    """
    Parser for filter expressions.

    Grammar:
        expression  -> or_expr
        or_expr     -> and_expr (OR and_expr)*
        and_expr    -> not_expr (AND not_expr)*
        not_expr    -> NOT not_expr | primary
        primary     -> PHRASE | WORD | LPAREN expression RPAREN
    """

    def __init__(self, text: str):
        self.lexer = FilterLexer(text)
        self.current_token = self.lexer.get_next_token()

    def eat(self, token_type: TokenType):
        """Consume a token of expected type."""
        if self.current_token.type == token_type:
            self.current_token = self.lexer.get_next_token()
        else:
            raise SyntaxError(
                f"Expected {token_type}, got {self.current_token.type}"
            )

    def parse(self) -> Optional[FilterNode]:
        """Parse the expression and return AST."""
        if self.current_token.type == TokenType.EOF:
            return None
        return self.or_expr()

    def or_expr(self) -> FilterNode:
        """Parse OR expression."""
        node = self.and_expr()
        while self.current_token.type == TokenType.OR:
            self.eat(TokenType.OR)
            node = OrNode(node, self.and_expr())
        return node

    def and_expr(self) -> FilterNode:
        """Parse AND expression."""
        node = self.not_expr()
        while self.current_token.type == TokenType.AND:
            self.eat(TokenType.AND)
            node = AndNode(node, self.not_expr())
        return node

    def not_expr(self) -> FilterNode:
        """Parse NOT expression."""
        if self.current_token.type == TokenType.NOT:
            self.eat(TokenType.NOT)
            return NotNode(self.not_expr())
        return self.primary()

    def primary(self) -> FilterNode:
        """Parse primary expression (term or parenthesized expression)."""
        token = self.current_token

        if token.type == TokenType.PHRASE:
            self.eat(TokenType.PHRASE)
            return TermNode(token.value, is_phrase=True)

        if token.type == TokenType.WORD:
            self.eat(TokenType.WORD)
            return TermNode(token.value, is_phrase=False)

        if token.type == TokenType.LPAREN:
            self.eat(TokenType.LPAREN)
            node = self.or_expr()
            self.eat(TokenType.RPAREN)
            return node

        raise SyntaxError(f"Unexpected token: {token}")


def parse_expression(expression: str) -> Optional[FilterNode]:
    """
    Parse a filter expression and return the AST.

    Args:
        expression: Filter expression string

    Returns:
        FilterNode AST or None if expression is empty
    """
    parser = FilterParser(expression)
    return parser.parse()


def evaluate_expression(text: str, expression: str) -> bool:
    """
    Quick check if text matches a filter expression.

    Args:
        text: Text to search in
        expression: Filter expression (e.g., '"AI" AND "agents"')

    Returns:
        True if expression matches text
    """
    node = parse_expression(expression)
    if node:
        return node.evaluate(text)
    return False
