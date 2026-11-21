#   tproc - A small yet powerful text processor.
#   https://github.com/kosarev/tproc
#
#   Copyright (C) 2018-2026 Ivan Kosarev.
#   mail@ivankosarev.com
#
#   Published under the MIT license.

from ._error import Error
from ._main import main
from ._processor import Processor
from ._tokens import LiteralToken
from ._tokens import TokenBase

__all__ = [
    'Error',
    'LiteralToken',
    'Processor',
    'TokenBase',
    'main',
]

# Present the public classes as members of the package itself, so they
# show up as, e.g., 'tproc.LiteralToken' rather than under the name of
# the private module that defines them.
for _cls in (Error, LiteralToken, Processor, TokenBase):
    _cls.__module__ = __name__
