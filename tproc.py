#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import types


# Implements a stream with push-back functionality. Can deal with
# arbitrary types, not just strings.
class _Stream(object):
    def __init__(self, input):
        assert isinstance(input, types.GeneratorType), input
        self._front = []
        self._input = input

    def read(self):
        while True:
            if self._front:
                chunk = self._front.pop()
            else:
                chunk = None
                for chunk in self._input:
                    break

                if not chunk:
                    return

            if chunk:
                yield chunk

    def push_back(self, *chunks):
        self._front.extend(reversed(chunks))

    def __iter__(self):
        return self.read()


# Base class for all tokens.
class TokenBase(object):
    def __init__(self, kind, content):
        self._kind = kind
        self.content = content

    def __repr__(self):
        return '<%s %r>' % (self._kind, self.content)


# Class for delimiters, such as curly braces.
class _DelimiterToken(TokenBase):
    def __init__(self, literal):
        super(_DelimiterToken, self).__init__('delimiter', literal)


# Represents tokens that should be treated as literal data. The content may or
# may not be a string.
class LiteralToken(TokenBase):
    def __init__(self, content):
        super(LiteralToken, self).__init__('literal', content)


# Designates invocations of fields to expand and replace.
class _ReplacementField(TokenBase):
    def __init__(self, content):
        super(_ReplacementField, self).__init__('field', content)


# The type of the processor instances.
class Processor:
    def __init__(self):
        # The character definitions begin with.
        self._definition_prefix = '@'

        # With this character begin comments within replacement fields.
        self._comment_prefix = '#'

        # Delimiter tokens we recognize in inputs.
        self._delimiters = dict((x, _DelimiterToken(x))
                                    for x in ['{', '}', ':'])

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
            '\\': '\\',     '\'': '\'',     '\"': '\"',     'a': '\a',
            'b': '\b',      'f': '\f',      'n': '\n',      'r': '\r',
            't': '\t',      'v': '\v',
        }

        # We also want additional escape sequences for all the delimiter
        # tokens.
        self._escapes.update(dict((x, x) for x in self._delimiters))

        # And another escape sequence for the definition prefix.
        self._escapes.update({self._definition_prefix:
                                  self._definition_prefix})

        # The namespace where the sources to process define their entities.
        # Here we inject a predefined name through which sources can access
        # their processor objects.
        self._namespace = { 'tproc': self }

        # Options.
        self.opts = dict()

        # Make some token types be visible through processor objects.
        self.TokenBase = TokenBase
        self.LiteralToken = LiteralToken

        # The stack of directories of currently included files.
        self.include_dirs = ['.']

    # Checks if a given string chunk beings a definition.
    def _is_header(self, chunk):
        return chunk.startswith(self._definition_prefix)

    # Reads a single line.
    def _read_line(self, input):
        for chunk in input:
            chunk = chunk.split('\n', 1)  # maxsplit=1
            yield chunk[0]

            if len(chunk) > 1:
                input.push_back(chunk[1])
                break

    # Returns a single line as a string.
    def _collect_line(self, input):
        return ''.join([x for x in self._read_line(input)])

    # Removes a single line from input.
    def _skip_line(self, input):
        for chunk in self._read_line(input):
            pass

    # Reads the full body of a definition and returns it as a string.
    def _collect_body(self, input):
        body = []
        for chunk in input:
            input.push_back(chunk)

            if self._is_header(chunk):
                break

            body.append(self._collect_line(input))

        return '\n'.join(body)

    # Processes a block of code.
    def define_code(self, code):
        exec(code, self._namespace)

    # Processes a text definition.
    def define_text(self, name, text):
        self._namespace[name] = lambda: [(yield text.strip())]

    # Processes a single definition.
    def process_definition(self, header, input):
        body = self._collect_body(input)

        if header == '@':
            self.define_code(body)
        else:
            name = header[1:]
            self.define_text(name, body)

    # Processes a given input.
    def process_input(self, input, input_name='<input>', input_dir=''):
        input = _Stream(input)

        self.include_dirs.append(input_dir)

        for chunk in input:
            input.push_back(chunk)
            if self._is_header(chunk):
                header = self._collect_line(input)
                self.process_definition(header, input)
            else:
                self._skip_line(input)

        self.include_dirs.pop()

    # Processes a given input file. If the passed path is
    # relative, it is considered relative to the current
    # directory.
    def process_file(self, path):
        with open(path, 'r') as f:
            dir = os.path.dirname(path)
            self.process_input((x for x in f), path, dir)

    # Includes a source file. If the passed path is relative,
    # it is considered relative to the directory of the currently
    # processed file.
    def include(self, path):
        if not os.path.isabs(path):
            path = os.path.join(self.include_dirs[-1], path)

        self.process_file(path)

    # Parses tokens and translates escape sequences.
    def _tokens_parser(self, input):
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
                    assert c in self._escapes, repr(c)  # TODO: error: Unknown escape sequence.
                    yield LiteralToken(self._escapes[c])

                escaped = False
                input.push_back(chunk[1:])
                continue

            repeat = False
            for delim in set(self._delimiters) | set([self._escape_char]):
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
            token = self._delimiters.get(chunk, None)
            if not token:
                token = LiteralToken(chunk)

            yield token

    # Parses invocations of replacement fields in a given input.
    def _format_parser(self, input):
        balance = 0
        field = []
        for token in self._tokens_parser(input):
            if token is self._left_brace:
                balance += 1
                if balance == 1:
                    continue

            if token is self._right_brace:
                assert balance > 0  # TODO: error: No opening brace for this closing brace.
                balance -= 1
                if balance == 0:
                    # Ignore empty fields.
                    if field:
                        yield _ReplacementField(field)
                    field = []
                    continue

            if balance == 0:
                if isinstance(token, _DelimiterToken):
                    token = LiteralToken(token.content)

                yield token
                continue

            field.append(token)

        assert balance == 0  # TODO: error: No closing brace for an opening one.

    # Parses part of a replacement field potentially delimited with colon
    # tokens.
    def _parse_field_component(self, tokens):
        component = []
        balance = 0
        while tokens:
            token = tokens.pop(0)
            if balance == 0 and token is self._colon:
                break

            if token is self._left_brace:
                balance += 1
            elif token is self._right_brace and balance > 0:
                balance -= 1

            component.append(token)

        return component

    # Turns a given sequence of tokens into a string.
    def _stringify_tokens(self, tokens):
        return ''.join([str(x.content) for x in tokens])

    # Takes a sequence of tokens constituting a replacement field and expands
    # it.
    def _parse_and_expand_field(self, tokens):
        # Parse field components.
        value = self._parse_field_component(tokens)
        format_spec = self._parse_field_component(tokens)

        args = []
        while tokens:
            arg = self._parse_field_component(tokens)
            args.append(self._expand_tokens((x for x in arg)))

        # Evaluate.
        value = self._stringify_tokens(value)
        value = eval(value, self._namespace)

        if callable(value):
            value = value(*args)

        if not isinstance(value, types.GeneratorType):
            value = (x for x in [value])

        # Expand.
        value = self._expand_tokens(value)

        # Format.
        if not format_spec:
            # No formatting. In this case we can give away chunks as soon as we
            # get them.
            for chunk in value:
                yield chunk
        else:
            # Collect fully expanded field and format it as requested.
            format_spec = self._stringify_tokens(format_spec)
            # value = ''.join([x for x in value])
            value = self._stringify_tokens(value)
            value = '{0:{1}}'.format(value, format_spec)
            yield value

    # Expands a sequence of tokens, and keeps the output as a
    # sequence of tokens.
    def _expand_tokens(self, input):
        input = _Stream(input)
        for token in self._format_parser(input):
            if isinstance(token, _ReplacementField):
                for chunk in self._parse_and_expand_field(token.content):
                    yield chunk
                continue

            yield token

    # Expands a given format input.
    def expand(self, input):
        for chunk in self._expand_tokens(input):
            # All delimiters shall be consumed or converted at this point.
            assert not isinstance(chunk, _DelimiterToken)

            if isinstance(chunk, LiteralToken):
                chunk = chunk.content

            yield chunk

    # Expands a replacement field specified as a string.
    def expand_field(self, field):
        return self.expand((x for x in ['{%s}' % field]))


def main():
    # Parse command-line arguments.
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument('input_file', nargs='?',
                             type=argparse.FileType('r'), default=sys.stdin)
    args_parser.add_argument('output_file', nargs='?',
                             type=argparse.FileType('w'), default=sys.stdout)
    args_parser.add_argument('-e', '--expand', type=str, default='main',
                             metavar='definition',
                             help='specify the definition to expand')
    args_parser.add_argument('-d', '--define', metavar='name[=value]',
                             action='append', nargs=1,
                             help='define option')
    args = args_parser.parse_args()

    # Parse options.
    p = Processor()
    if args.define:
        for opt in args.define:
            assert len(opt) == 1
            opt = opt[0].split('=', 1)  # maxsplit=1
            name = opt[0]
            value = opt[1] if len(opt) > 1 else ''
            p.opts[name] = value

    # Process input.
    input = args.input_file
    if input == sys.stdin:
        input_dir = ''
    else:
        input_dir = os.path.dirname(input.name)
    p.process_input((x for x in input), input.name, input_dir)

    # Expand the definition.
    output = args.output_file
    for chunk in p.expand_field(args.expand):
        output.write(str(chunk))


if __name__ == '__main__':
    main()
