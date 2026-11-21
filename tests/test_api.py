#   tproc - A small yet powerful text processor.
#   https://github.com/kosarev/tproc
#
#   Copyright (C) 2018-2026 Ivan Kosarev.
#   mail@ivankosarev.com
#
#   Published under the MIT license.

import pathlib

import tproc


def expand(p: tproc.Processor, field: str = 'main') -> str:
    return ''.join(str(chunk) for chunk in p.expand_field(field))


def test_process_input() -> None:
    p = tproc.Processor()
    p.process_input(['@main\n', 'Hello {who}!\n', '@who\n', 'World\n'])
    assert expand(p) == 'Hello World!'


def test_process_input_chunks() -> None:
    # Input may be split into chunks anywhere, not just at line ends.
    p = tproc.Processor()
    p.process_input(iter('@main\n{x}{x}\n@x\nab\n'))
    assert expand(p) == 'abab'


def test_expand() -> None:
    p = tproc.Processor()
    p.define_text('who', 'World')
    assert ''.join(str(x) for x in p.expand(['Hello ', '{who}!'])) == (
        'Hello World!')


def test_define_code() -> None:
    p = tproc.Processor()
    p.define_code('def main():\n    yield "code"\n')
    assert expand(p) == 'code'


def test_literal_token() -> None:
    t = tproc.LiteralToken(5)
    assert t.content == 5
    assert repr(t) == '<literal 5>'
    assert isinstance(t, tproc.TokenBase)
    assert repr(tproc.LiteralToken) == "<class 'tproc.LiteralToken'>"


def test_processor_token_types() -> None:
    p = tproc.Processor()
    assert p.LiteralToken is tproc.LiteralToken
    assert p.TokenBase is tproc.TokenBase


def test_namespace() -> None:
    # Input code sees its processor object as 'tproc'.
    p = tproc.Processor()
    p.process_input(['@main\n', "{tproc.opts['x']}\n"])
    p.opts['x'] = 'value'
    assert expand(p) == 'value'


def test_include(tmp_path: pathlib.Path) -> None:
    (tmp_path / 'sub').mkdir()
    (tmp_path / 'main.tproc').write_text(
        '@\ntproc.include("sub/a.tproc")\n\n@main\n{a}\n')
    # Relative includes resolve against the including file.
    (tmp_path / 'sub' / 'a.tproc').write_text(
        '@\ntproc.include("b.tproc")\n\n@a\nA{b}\n')
    (tmp_path / 'sub' / 'b.tproc').write_text('@b\nB\n')

    p = tproc.Processor()
    p.process_file(tmp_path / 'main.tproc')
    assert expand(p) == 'AB'


def test_falsy_values() -> None:
    # Falsy non-text values are data too, but None values and empty
    # strings are not.
    p = tproc.Processor()
    p.process_input(['@main\n', "{0}|{False}|{[]}|{None}|{''}|{nothing}\n",
                     '@\n', 'def nothing():\n',
                     '    yield None\n', "    yield ''\n"])
    assert list(p.expand_field('main')) == [0, '|', False, '|', [], '|',
                                            '|', '|']
