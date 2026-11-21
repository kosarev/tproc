#   tproc - A small yet powerful text processor.
#   https://github.com/kosarev/tproc
#
#   Copyright (C) 2018-2026 Ivan Kosarev.
#   mail@ivankosarev.com
#
#   Published under the MIT license.

import collections.abc
import pathlib

import pytest

import tproc

TESTS_DIR = pathlib.Path(__file__).parent


# Merges adjacent string chunks, so that how the output is split
# into chunks does not matter for comparison. Chunks of other types
# are kept as they are.
def collect(output: collections.abc.Iterable[object]) -> list[object]:
    res: list[object] = []
    for chunk in output:
        if isinstance(chunk, str) and res and isinstance(res[-1], str):
            res[-1] += chunk
            continue

        res.append(chunk)

    return res


# Every .tproc file in this directory is a test: expanding its 'main'
# definition shall give the same output as expanding 'expected'.
@pytest.mark.parametrize('path', sorted(TESTS_DIR.glob('*.tproc')),
                         ids=lambda path: path.stem)
def test_tproc_file(path: pathlib.Path) -> None:
    p = tproc.Processor()
    p.process_file(path)
    assert (collect(p.expand_field('main')) ==
            collect(p.expand_field('expected')))
