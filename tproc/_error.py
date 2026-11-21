#   tproc - A small yet powerful text processor.
#   https://github.com/kosarev/tproc
#
#   Copyright (C) 2018-2026 Ivan Kosarev.
#   mail@ivankosarev.com
#
#   Published under the MIT license.

import sys


# Formats a source location for diagnostics.
def format_location(source: str | None, line: int | None) -> str | None:
    if source is None:
        return None
    if line is None:
        return source
    return f'{source}:{line}'


# Raised on malformed inputs, such as unbalanced braces or unknown
# escape sequences. The source and line, when known, refer to where
# the problem is.
class Error(Exception):
    def __init__(self, message: str, source: str | None = None,
                 line: int | None = None) -> None:
        super().__init__(message, source, line)
        self.message = message
        self.source = source
        self.line = line

    def __str__(self) -> str:
        location = format_location(self.source, self.line)
        if location is None:
            return self.message
        return f'{location}: {self.message}'


# Auxiliary Processor-related error info: the stack of files and
# fields being processed when an exception occurred.
class ErrorInfo:
    def __init__(self) -> None:
        self.files: list[str] = []
        self.fields: list[tuple[str, str | None]] = []

    def report(self) -> None:
        for f in reversed(self.files):
            print(f"tproc: In file '{f}':", file=sys.stderr)

        for field, location in reversed(self.fields):
            prefix = 'tproc' if location is None else location
            print(f"{prefix}: In field '{field}':", file=sys.stderr)


# Returns the error info attached to a given exception, attaching a
# new one if there is none yet.
def error_info(e: BaseException) -> ErrorInfo:
    info = getattr(e, 'tproc', None)
    if not isinstance(info, ErrorInfo):
        info = ErrorInfo()
        setattr(e, 'tproc', info)  # noqa: B010
    return info
