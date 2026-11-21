#   tproc - A small yet powerful text processor.
#   https://github.com/kosarev/tproc
#
#   Copyright (C) 2018-2026 Ivan Kosarev.
#   mail@ivankosarev.com
#
#   Published under the MIT license.

import pytest

import tproc


def expand(source: str) -> str:
    p = tproc.Processor()
    p.process_input(source.splitlines(keepends=True), 'test.tproc')
    return ''.join(str(chunk) for chunk in p.expand_field('main'))


@pytest.mark.parametrize('source, message, line', [
    ('@main\nx\n{a\n', "unterminated replacement field; missing '}'", 3),
    ('@main\n{a::{b}\n', "unterminated replacement field; missing '}'", 2),
    ('@main\n\n\n  x }\n', "unmatched '}'", 4),
    ('@main\na \\q\n', "unknown escape sequence '\\q'", 2),
    ('@main\n1\n2{# not closed\n3\n', 'unterminated comment', 3),
])
def test_malformed_text(source: str, message: str, line: int) -> None:
    with pytest.raises(tproc.Error) as e:
        expand(source)
    assert e.value.message == message
    assert e.value.source == 'test.tproc'
    assert e.value.line == line
    assert str(e.value) == f'test.tproc:{line}: {message}'


def test_error_in_definition() -> None:
    # Lines are reported relative to the file, not the definition.
    with pytest.raises(tproc.Error) as e:
        expand('@main\n{x}\n\n@x\n\n\nfirst\n  second {\n')
    assert e.value.line == 8


def test_error_in_argument() -> None:
    with pytest.raises(tproc.Error) as e:
        expand('@main\n{f::\nok\n\\z}\n'
               '@\ndef f(x):\n    yield from x\n')
    assert e.value.message == "unknown escape sequence '\\z'"
    assert e.value.line == 4


def test_error_without_location() -> None:
    p = tproc.Processor()
    with pytest.raises(tproc.Error) as e:
        list(p.expand(['{']))
    assert e.value.source is None
    assert str(e.value) == "unterminated replacement field; missing '}'"


def test_escape_before_non_text() -> None:
    with pytest.raises(tproc.Error, match='non-text data'):
        expand('@main\n{x}\n@\ndef x():\n    yield "\\\\"\n    yield 5\n')


def test_non_text_input() -> None:
    p = tproc.Processor()
    with pytest.raises(tproc.Error, match='non-text data in input'):
        p.process_input(['@main\n', 5])


def test_code_line_numbers() -> None:
    p = tproc.Processor()
    with pytest.raises(SyntaxError) as e:
        p.process_input(['intro\n', '@\n', 'x = 1\n', 'y = (\n'],
                        'test.tproc')
    assert e.value.filename == 'test.tproc'
    assert e.value.lineno == 4


def test_field_line_numbers() -> None:
    with pytest.raises(NameError) as e:
        expand('@main\n\n{undefined}\n')
    tb = e.value.__traceback__
    assert tb is not None
    while tb.tb_next is not None:
        tb = tb.tb_next
    assert tb.tb_frame.f_code.co_filename == 'test.tproc'
    assert tb.tb_lineno == 3


def test_error_info() -> None:
    with pytest.raises(NameError) as e:
        expand('@main\n{a}\n@a\n\nx {undefined}\n')
    info = getattr(e.value, 'tproc')  # noqa: B009
    assert info.files == []
    assert info.fields == [('undefined', 'test.tproc:5'),
                           ('a', 'test.tproc:2'),
                           ('main', None)]


def test_error_info_files() -> None:
    p = tproc.Processor()
    with pytest.raises(SyntaxError) as e:
        p.process_input(['@\n', '(\n'], 'test.tproc')
    assert getattr(e.value, 'tproc').files == ['test.tproc']  # noqa: B009
