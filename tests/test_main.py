#   tproc - A small yet powerful text processor.
#   https://github.com/kosarev/tproc
#
#   Copyright (C) 2018-2026 Ivan Kosarev.
#   mail@ivankosarev.com
#
#   Published under the MIT license.

import io
import pathlib

import pytest

import tproc


def test_files(tmp_path: pathlib.Path) -> None:
    input = tmp_path / 'in.tproc'
    output = tmp_path / 'out.txt'
    input.write_text('@main\nGrüße, {who}!\n@who\nWelt ✓\n', encoding='utf-8')
    tproc.main([str(input), str(output)])
    assert output.read_text(encoding='utf-8') == 'Grüße, Welt ✓!'


def test_stdio(monkeypatch: pytest.MonkeyPatch,
               capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr('sys.stdin', io.StringIO('@main\nHello!\n'))
    tproc.main([])
    assert capsys.readouterr().out == 'Hello!'


def test_expand_and_define(tmp_path: pathlib.Path,
                           capsys: pytest.CaptureFixture[str]) -> None:
    input = tmp_path / 'in.tproc'
    input.write_text(
        "@other\n{tproc.opts['a']}/{tproc.opts['b']}\n@main\nmain\n")
    tproc.main(['-e', 'other', '-d', 'a=1=2', '-d', 'b', str(input)])
    assert capsys.readouterr().out == '1=2/'


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        tproc.main(['--version'])
    assert capsys.readouterr().out == f'tproc {tproc.__version__}\n'


def test_error(tmp_path: pathlib.Path,
               capsys: pytest.CaptureFixture[str]) -> None:
    input = tmp_path / 'in.tproc'
    input.write_text('@main\n{x}\n@x\nX\n  {y\n')
    with pytest.raises(SystemExit) as e:
        tproc.main([str(input)])
    assert e.value.code == f'{input}:5: error: unterminated replacement ' \
                           "field; missing '}'"
    assert capsys.readouterr().err == (
        f"tproc: In file '{input}':\n"
        "tproc: In field 'main':\n"
        f"{input}:2: In field 'x':\n")


def test_python_error(tmp_path: pathlib.Path) -> None:
    # Errors in input code propagate with their tracebacks.
    input = tmp_path / 'in.tproc'
    input.write_text('@main\n{1/0}\n')
    with pytest.raises(ZeroDivisionError):
        tproc.main([str(input)])
