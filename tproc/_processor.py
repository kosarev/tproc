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

from ._error import Error
from ._error import error_info
from ._error import format_location
from ._stream import Stream
from ._tokens import DelimiterToken
from ._tokens import LiteralToken
from ._tokens import ReplacementField
from ._tokens import TokenBase


# Text definitions. Calling one gives a generator producing its body
# text. Also remembers where the body comes from, so that problems
# found on expanding it can be reported at their source lines.
class _TextDefinition:
    def __init__(self, text: str, source: str | None, line: int) -> None:
        self.text = text
        self.source = source
        self.line = line

    def __call__(self) -> collections.abc.Iterator[object]:
        yield self.text


# The type of the processor instances.
class Processor:
    def __init__(self) -> None:
        # The character definitions begin with.
        self._definition_prefix = '@'

        # With this character begin comments within replacement fields.
        self._comment_prefix = '#'

        # Delimiters we recognize in inputs.
        self._delimiters = ['{', '}', ':']

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

        # We also want additional escape sequences for all the delimiters.
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

    @staticmethod
    def _is_delimiter(token: object,
                      delim: str) -> typing.TypeGuard[DelimiterToken]:
        return isinstance(token, DelimiterToken) and token.content == delim

    # Checks if a given chunk begins a definition.
    def _is_header(self, chunk: object) -> bool:
        return (isinstance(chunk, str) and
                chunk.startswith(self._definition_prefix))

    # Reads a single line.
    def _read_line(self, input: Stream, source: str,
                   line: int) -> collections.abc.Iterator[str]:
        for chunk in input:
            if not isinstance(chunk, str):
                raise Error(f'non-text data in input: {chunk!r}',
                            source, line)

            parts = chunk.split('\n', 1)  # maxsplit=1
            yield parts[0]

            if len(parts) > 1:
                input.push_back(parts[1])
                break

    # Returns a single line as a string.
    def _collect_line(self, input: Stream, source: str, line: int) -> str:
        return ''.join(self._read_line(input, source, line))

    # Reads the full body of a definition and returns its lines.
    def _collect_body(self, input: Stream, source: str,
                      line: int) -> list[str]:
        body: list[str] = []
        for chunk in input:
            input.push_back(chunk)

            if self._is_header(chunk):
                break

            body.append(self._collect_line(input, source, line + len(body)))

        return body

    # Processes a block of code. The source and line are those of the
    # first line of the code, for diagnostics and tracebacks.
    def define_code(self, code: str, source: str = '<code>',
                    line: int = 1) -> None:
        exec(compile('\n' * (line - 1) + code, source, 'exec'),
             self._namespace)

    # Processes a text definition. The source and line are those of the
    # first line of the text, for diagnostics.
    def define_text(self, name: str, text: str, source: str | None = None,
                    line: int = 1) -> None:
        stripped = text.lstrip()
        line += text[:len(text) - len(stripped)].count('\n')
        self._namespace[name] = _TextDefinition(stripped.rstrip(),
                                                source, line)

    # Processes a single definition.
    def _process_definition(self, header: str, body: list[str],
                            source: str, line: int) -> None:
        text = '\n'.join(body)

        if header == self._definition_prefix:
            # Escaped definition prefixes in code let lines start with
            # decorators.
            text = text.replace(self._escape_char + self._definition_prefix,
                                self._definition_prefix)
            self.define_code(text, source, line)
        else:
            name = header[len(self._definition_prefix):]
            self.define_text(name, text, source, line)

    # Processes a given input.
    def process_input(self, input: collections.abc.Iterable[object],
                      input_name: str = '<input>',
                      input_dir: str | os.PathLike[str] = '') -> None:
        self.include_dirs.append(pathlib.Path(input_dir))
        try:
            stream = Stream(input)
            line = 1
            for chunk in stream:
                stream.push_back(chunk)
                if not self._is_header(chunk):
                    # Skip the line.
                    for _ in self._read_line(stream, input_name, line):
                        pass
                    line += 1
                    continue

                header = self._collect_line(stream, input_name, line)
                body = self._collect_body(stream, input_name, line + 1)
                self._process_definition(header, body, input_name, line + 1)
                line += 1 + len(body)
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

    # Parses tokens and translates escape sequences. If the line is
    # known, tracks the lines the tokens come from.
    def _tokens_parser(self, input: Stream, source: str | None,
                       line: int | None
                       ) -> collections.abc.Iterator[TokenBase]:
        def advance(chunk: str) -> None:
            nonlocal line
            if line is not None:
                line += chunk.count('\n')

        escaped_at: int | None = None
        escaped = False
        commented_out_at: int | None = None
        commented_out = False
        for chunk in input:
            # Handle non-string chunks.
            if not isinstance(chunk, str):
                if escaped:
                    raise Error(
                        f'escape character followed by non-text data: '
                        f'{chunk!r}', source, escaped_at)

                if commented_out:
                    continue

                if not isinstance(chunk, TokenBase):
                    chunk = LiteralToken(chunk)

                yield chunk
                continue

            # Handle escaped characters.
            if escaped:
                c = chunk[0]
                advance(c)
                if c == '\n':
                    # For line splices, just ignore the escape sequence
                    # completely.
                    pass
                elif c in self._escapes:
                    yield LiteralToken(self._escapes[c])
                else:
                    raise Error(
                        f"unknown escape sequence '{self._escape_char}{c}'",
                        source, escaped_at)

                escaped = False
                input.push_back(chunk[1:])
                continue

            repeat = False
            for delim in [*self._delimiters, self._escape_char]:
                segments = chunk.partition(delim)
                if segments[1] and (segments[0] or segments[2]):
                    input.push_back(*segments)
                    repeat = True
                    break

            if repeat:
                continue

            if not commented_out and chunk == self._escape_char:
                escaped = True
                escaped_at = line
                continue

            # Handle comments.
            if commented_out:
                advance(chunk)
                if chunk == '}':
                    commented_out = False
                continue

            if chunk == '{':
                next_chunk = None
                for next_chunk in input:
                    input.push_back(next_chunk)
                    break

                if (isinstance(next_chunk, str) and
                        next_chunk.startswith(self._comment_prefix)):
                    commented_out = True
                    commented_out_at = line
                    continue

            # Otherwise, return the chunk as a token.
            if chunk in self._delimiters:
                yield DelimiterToken(chunk, line)
            else:
                yield LiteralToken(chunk)
                advance(chunk)

        # Escape characters at the very end of input are ignored, which
        # lets text definitions end with line splices.

        if commented_out:
            raise Error('unterminated comment', source, commented_out_at)

    # Parses invocations of replacement fields in a given input.
    def _format_parser(self, input: Stream, source: str | None,
                       line: int | None
                       ) -> collections.abc.Iterator[TokenBase]:
        balance = 0
        field: list[TokenBase] = []
        field_line: int | None = None
        for token in self._tokens_parser(input, source, line):
            if self._is_delimiter(token, '{'):
                balance += 1
                if balance == 1:
                    field_line = token.line
                    continue

            if self._is_delimiter(token, '}'):
                if balance == 0:
                    raise Error("unmatched '}'", source,
                                token.line)

                balance -= 1
                if balance == 0:
                    # Ignore empty fields.
                    if field:
                        yield ReplacementField(field, field_line)
                    field = []
                    continue

            if balance == 0:
                if isinstance(token, DelimiterToken):
                    token = LiteralToken(token.content)

                yield token
                continue

            field.append(token)

        if balance:
            raise Error("unterminated replacement field; missing '}'",
                        source, field_line)

    # Parses part of a replacement field potentially delimited with colon
    # tokens.
    def _parse_field_component(self, tokens: list[TokenBase]
                               ) -> tuple[bool, list[TokenBase]]:
        component = []
        balance = 0
        last_arg = True
        while tokens:
            token = tokens.pop(0)
            if balance == 0 and self._is_delimiter(token, ':'):
                last_arg = False
                break

            if self._is_delimiter(token, '{'):
                balance += 1
            elif self._is_delimiter(token, '}') and balance > 0:
                balance -= 1

            component.append(token)

        return last_arg, component

    # Turns a given sequence of tokens into a string.
    def _stringify_tokens(self, tokens: collections.abc.Iterable[TokenBase]
                          ) -> str:
        return ''.join(str(x.content) for x in tokens)

    # Evaluates the value expression of a replacement field.
    def _evaluate(self, expr: str, source: str | None,
                  line: int | None) -> object:
        # Similarly to eval(), ignore leading spaces and tabs. Then pad
        # the expression so its line numbers match the source ones.
        expr = expr.lstrip(' \t')
        if line is not None:
            expr = '\n' * (line - 1) + expr
        code = compile(expr, '<field>' if source is None else source, 'eval')
        return eval(code, self._namespace)

    # Takes a replacement field and expands it.
    def _parse_and_expand_field(self, field: ReplacementField,
                                source: str | None
                                ) -> collections.abc.Iterator[TokenBase]:
        tokens = list(field.tokens)

        # Parse field components.
        last_arg, value_tokens = self._parse_field_component(tokens)
        last_arg, format_spec_tokens = self._parse_field_component(tokens)

        args = []
        while not last_arg:
            last_arg, arg = self._parse_field_component(tokens)
            args.append(self._expand_tokens(arg, source, None))

        value_string = self._stringify_tokens(value_tokens)
        try:
            # Evaluate.
            value = self._evaluate(value_string, source, field.line)

            value_source: str | None = None
            value_line: int | None = None
            if isinstance(value, _TextDefinition):
                value_source = value.source
                value_line = value.line

            if callable(value):
                value = value(*args)

            if not isinstance(value, types.GeneratorType):
                value = iter([value])

            # Expand.
            expanded = self._expand_tokens(value, value_source, value_line)

            # Format.
            if not format_spec_tokens:
                # No formatting. In this case we can give away chunks as
                # soon as we get them.
                yield from expanded
            else:
                # Collect fully expanded field and format it as requested.
                format_spec = self._stringify_tokens(format_spec_tokens)
                yield LiteralToken(
                    format(self._stringify_tokens(expanded), format_spec))
        except Exception as e:
            error_info(e).fields.append(
                (value_string, format_location(source, field.line)))
            raise

    # Expands a sequence of tokens, and keeps the output as a
    # sequence of tokens.
    def _expand_tokens(self, input: collections.abc.Iterable[object],
                       source: str | None, line: int | None
                       ) -> collections.abc.Iterator[TokenBase]:
        for token in self._format_parser(Stream(input), source, line):
            if isinstance(token, ReplacementField):
                yield from self._parse_and_expand_field(token, source)
                continue

            yield token

    # Expands a given format input.
    def expand(self, input: collections.abc.Iterable[object]
               ) -> collections.abc.Iterator[object]:
        for token in self._expand_tokens(input, None, None):
            # All delimiters shall be consumed or converted at this point.
            assert not isinstance(token, DelimiterToken)

            if isinstance(token, LiteralToken):
                yield token.content
            else:
                yield token

    # Expands a replacement field specified as a string.
    def expand_field(self, field: str) -> collections.abc.Iterator[object]:
        yield from self.expand([f'{{{field}}}'])
