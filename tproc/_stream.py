#   tproc - A small yet powerful text processor.
#   https://github.com/kosarev/tproc
#
#   Copyright (C) 2018-2026 Ivan Kosarev.
#   mail@ivankosarev.com
#
#   Published under the MIT license.

import collections.abc

# Marks the end of the underlying input.
_END = object()


# Implements a stream with push-back functionality. Can deal with
# arbitrary types, not just strings.
class Stream:
    def __init__(self, input: collections.abc.Iterable[object]) -> None:
        self._front: list[object] = []
        self._input = iter(input)

    def read(self) -> collections.abc.Iterator[object]:
        while True:
            if self._front:
                chunk = self._front.pop()
            else:
                chunk = next(self._input, _END)
                if chunk is _END:
                    return

            if chunk:
                yield chunk

    def push_back(self, *chunks: object) -> None:
        self._front.extend(reversed(chunks))

    def __iter__(self) -> collections.abc.Iterator[object]:
        return self.read()
