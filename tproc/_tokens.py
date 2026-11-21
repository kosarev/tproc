#   tproc - A small yet powerful text processor.
#   https://github.com/kosarev/tproc
#
#   Copyright (C) 2018-2026 Ivan Kosarev.
#   mail@ivankosarev.com
#
#   Published under the MIT license.


# Base class for all tokens.
class TokenBase:
    def __init__(self, kind: str, content: object) -> None:
        self._kind = kind
        self.content = content

    def __repr__(self) -> str:
        return f'<{self._kind} {self.content!r}>'


# Class for delimiters, such as curly braces.
class DelimiterToken(TokenBase):
    def __init__(self, literal: str) -> None:
        super().__init__('delimiter', literal)


# Represents tokens that should be treated as literal data. The content may or
# may not be a string.
class LiteralToken(TokenBase):
    def __init__(self, content: object) -> None:
        super().__init__('literal', content)


# Designates invocations of fields to expand and replace.
class ReplacementField(TokenBase):
    def __init__(self, content: list[TokenBase]) -> None:
        super().__init__('field', content)
        self.tokens = content
