#   tproc - A small yet powerful text processor.
#   https://github.com/kosarev/tproc
#
#   Copyright (C) 2018-2026 Ivan Kosarev.
#   mail@ivankosarev.com
#
#   Published under the MIT license.

import sys


# Auxiliary Processor-related error info.
class ErrorInfo:
    def __init__(self) -> None:
        self.files: list[str] = []
        self.fields: list[str] = []

    def report(self) -> None:
        for f in reversed(self.files):
            print(f"tproc: In file '{f}':", file=sys.stderr)

        for f in reversed(self.fields):
            print(f"tproc: In field '{f}':", file=sys.stderr)


# Returns the error info attached to a given exception, attaching a
# new one if there is none yet.
def error_info(e: BaseException) -> ErrorInfo:
    info = getattr(e, 'tproc', None)
    if not isinstance(info, ErrorInfo):
        info = ErrorInfo()
        setattr(e, 'tproc', info)  # noqa: B010
    return info
