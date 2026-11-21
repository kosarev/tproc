#   tproc - A small yet powerful text processor.
#   https://github.com/kosarev/tproc
#
#   Copyright (C) 2018-2026 Ivan Kosarev.
#   mail@ivankosarev.com
#
#   Published under the MIT license.

import collections.abc
import os
import pathlib
import types
import typing

from ._error import error_info
from ._stream import Stream
from ._tokens import DelimiterToken
from ._tokens import LiteralToken
from ._tokens import ReplacementField
from ._tokens import TokenBase


# The type of the processor instances.
class Processor:
    def __init__(self) -> None:
        # The character definitions begin with.
        self._definition_prefix = '@'

        # With this character begin comments within replacement fields.
        self._comment_prefix = '#'

        # Delimiter tokens we recognize in inputs.
        self._delimiters = {x: DelimiterToken(x) for x in ['{', '}', ':']}

        self._left_brace = self._delimiters['{']
        self._right_brace = self._delimiters['}']
        self._colon = self._delimiters[':']

        # Escape sequences start with this character.
        self._escape_char = '\\'

        # These are the standard C escape sequences, which are very common
        # among various kinds of textual sources. We support them for better
        # interchangeability, and to provide a way to represent special
        # characters.
        # TODO: Support numerical escape sequences, including Unicode ones.
        self._escapes = {
            '\\': '\\',     "'": "'",       '"': '"',       'a': '\a',
            'b': '\b',      'f': '\f',      'n': '\n',      'r': '\r',
            't': '\t',      'v': '\v',
        }

        # We also want additional escape sequences for all the delimiter
        # tokens.
        self._escapes.update({x: x for x in self._delimiters})

        # And another escape sequence for the definition prefix.
        self._escapes.update({self._definition_prefix:
                              self._definition_prefix})

        # The namespace where the sources to process define their entities.
        # Here we inject a predefined name through which sources can access
        # their processor objects.
        self._namespace: dict[str, typing.Any] = {'tproc': self}

        # Options.
        self.opts: dict[str, str] = {}

        # Make some token types be visible through processor objects.
        self.TokenBase = TokenBase
        self.LiteralToken = LiteralToken

        # The stack of directories of currently included files.
        self.include_dirs = [pathlib.Path()]

    # Checks if a given chunk begins a definition.
    def _is_header(self, chunk: object) -> bool:
        return (isinstance(chunk, str) and
                chunk.startswith(self._definition_prefix))

    # Reads a single line.
    def _read_line(self, input: Stream) -> collections.abc.Iterator[str]:
        for chunk in input:
            assert isinstance(chunk, str), chunk
            parts = chunk.split('\n', 1)  # maxsplit=1
            yield parts[0]

            if len(parts) > 1:
                input.push_back(parts[1])
                break

    # Returns a single line as a string.
    def _collect_line(self, input: Stream) -> str:
        return ''.join(self._read_line(input))

    # Removes a single line from input.
    def _skip_line(self, input: Stream) -> None:
        for _ in self._read_line(input):
            pass

    # Reads the full body of a definition and returns it as a string.
    def _collect_body(self, input: Stream) -> str:
        body = []
        for chunk in input:
            input.push_back(chunk)

            if self._is_header(chunk):
                break

            body.append(self._collect_line(input))

        return '\n'.join(body)

    # Processes a block of code.
    def define_code(self, code: str) -> None:
        exec(code, self._namespace)

    # Processes a text definition.
    def define_text(self, name: str, text: str) -> None:
        def generator() -> collections.abc.Iterator[object]:
            yield text.strip()

        self._namespace[name] = generator

    # Processes a single definition.
    def process_definition(self, header: str, input: Stream) -> None:
        body = self._collect_body(input)

        if header == '@':
            body = body.replace('\\@', '@')
            self.define_code(body)
        else:
            name = header[1:]
            self.define_text(name, body)

    # Processes a given input.
    def process_input(self, input: collections.abc.Iterable[object],
                      input_name: str = '<input>',
                      input_dir: str | os.PathLike[str] = '') -> None:
        self.include_dirs.append(pathlib.Path(input_dir))
        try:
            stream = Stream(input)
            for chunk in stream:
                stream.push_back(chunk)
                if self._is_header(chunk):
                    header = self._collect_line(stream)
                    self.process_definition(header, stream)
                else:
                    self._skip_line(stream)
        except Exception as e:
            error_info(e).files.append(input_name)
            raise
        finally:
            self.include_dirs.pop()

    # Processes a given input file. If the passed path is
    # relative, it is considered relative to the current
    # directory.
    def process_file(self, path: str | os.PathLike[str]) -> None:
        path = pathlib.Path(path)
        with path.open(encoding='utf-8') as f:
            self.process_input(f, str(path), path.parent)

    # Includes a source file. If the passed path is relative,
    # it is considered relative to the directory of the currently
    # processed file.
    def include(self, path: str | os.PathLike[str]) -> None:
        self.process_file(self.include_dirs[-1] / path)

    # Parses tokens and translates escape sequences.
    def _tokens_parser(self, input: Stream
                       ) -> collections.abc.Iterator[TokenBase]:
        escaped = False
        commented_out = False
        for chunk in input:
            # Handle non-string chunks.
            if not isinstance(chunk, str):
                assert not escaped  # TODO

                if not isinstance(chunk, TokenBase):
                    chunk = LiteralToken(chunk)

                yield chunk
                continue

            # Handle escaped characters.
            if escaped:
                c = chunk[0]
                if c == '\n':
                    # For line splices, just ignore the escape sequence
                    # completely.
                    pass
                else:
                    # TODO: error: Unknown escape sequence.
                    assert c in self._escapes, repr(c)
                    yield LiteralToken(self._escapes[c])

                escaped = False
                input.push_back(chunk[1:])
                continue

            repeat = False
            for delim in set(self._delimiters) | {self._escape_char}:
                segments = chunk.partition(delim)
                if segments[1] and (segments[0] or segments[2]):
                    input.push_back(*segments)
                    repeat = True
                    break

            if repeat:
                continue

            if not commented_out and chunk == self._escape_char:
                escaped = True
                continue

            # Handle comments.
            if commented_out:
                if chunk == self._right_brace.content:
                    commented_out = False
                continue

            if chunk == self._left_brace.content:
                next_chunk = None
                for next_chunk in input:
                    input.push_back(next_chunk)
                    break

                if (isinstance(next_chunk, str) and
                        next_chunk.startswith(self._comment_prefix)):
                    commented_out = True
                    continue

            # Otherwise, return the chunk as a token.
            token: TokenBase | None = self._delimiters.get(chunk, None)
            if not token:
                token = LiteralToken(chunk)

            yield token

    # Parses invocations of replacement fields in a given input.
    def _format_parser(self, input: Stream
                       ) -> collections.abc.Iterator[TokenBase]:
        balance = 0
        field: list[TokenBase] = []
        for token in self._tokens_parser(input):
            if token is self._left_brace:
                balance += 1
                if balance == 1:
                    continue

            if token is self._right_brace:
                # TODO: error: No opening brace for this closing brace.
                assert balance > 0
                balance -= 1
                if balance == 0:
                    # Ignore empty fields.
                    if field:
                        yield ReplacementField(field)
                    field = []
                    continue

            if balance == 0:
                if isinstance(token, DelimiterToken):
                    token = LiteralToken(token.content)

                yield token
                continue

            field.append(token)

        # TODO: error: No closing brace for an opening one.
        assert balance == 0

    # Parses part of a replacement field potentially delimited with colon
    # tokens.
    def _parse_field_component(self, tokens: list[TokenBase]
                               ) -> tuple[bool, list[TokenBase]]:
        component = []
        balance = 0
        last_arg = True
        while tokens:
            token = tokens.pop(0)
            if balance == 0 and token is self._colon:
                last_arg = False
                break

            if token is self._left_brace:
                balance += 1
            elif token is self._right_brace and balance > 0:
                balance -= 1

            component.append(token)

        return last_arg, component

    # Turns a given sequence of tokens into a string.
    def _stringify_tokens(self, tokens: collections.abc.Iterable[object]
                          ) -> str:
        return ''.join(str(typing.cast('TokenBase', x).content)
                       for x in tokens)

    # Takes a sequence of tokens constituting a replacement field and expands
    # it.
    def _parse_and_expand_field(self, tokens: list[TokenBase]
                                ) -> collections.abc.Iterator[object]:
        # Parse field components.
        last_arg, value_tokens = self._parse_field_component(tokens)
        last_arg, format_spec_tokens = self._parse_field_component(tokens)

        args = []
        while not last_arg:
            last_arg, arg = self._parse_field_component(tokens)
            args.append(self._expand_tokens(arg))

        # Evaluate.
        value_string = self._stringify_tokens(value_tokens)
        value = eval(value_string, self._namespace)

        if callable(value):
            value = value(*args)

        if not isinstance(value, types.GeneratorType):
            value = iter([value])

        # Expand.
        expanded = self._expand_tokens(value)

        # Format.
        if not format_spec_tokens:
            # No formatting. In this case we can give away chunks as soon as we
            # get them.
            try:
                yield from expanded
            except Exception as e:
                error_info(e).fields.append(value_string)
                raise
        else:
            # Collect fully expanded field and format it as requested.
            format_spec = self._stringify_tokens(format_spec_tokens)
            yield format(self._stringify_tokens(expanded), format_spec)

    # Expands a sequence of tokens, and keeps the output as a
    # sequence of tokens.
    def _expand_tokens(self, input: collections.abc.Iterable[object]
                       ) -> collections.abc.Iterator[object]:
        for token in self._format_parser(Stream(input)):
            if isinstance(token, ReplacementField):
                yield from self._parse_and_expand_field(token.tokens)
                continue

            yield token

    # Expands a given format input.
    def expand(self, input: collections.abc.Iterable[object]
               ) -> collections.abc.Iterator[object]:
        for chunk in self._expand_tokens(input):
            # All delimiters shall be consumed or converted at this point.
            assert not isinstance(chunk, DelimiterToken)

            if isinstance(chunk, LiteralToken):
                chunk = chunk.content

            yield chunk

    # Expands a replacement field specified as a string.
    def expand_field(self, field: str) -> collections.abc.Iterator[object]:
        yield from self.expand([f'{{{field}}}'])
