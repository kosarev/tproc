#   tproc - A small yet powerful text processor.
#   https://github.com/kosarev/tproc
#
#   Copyright (C) 2018-2026 Ivan Kosarev.
#   mail@ivankosarev.com
#
#   Published under the MIT license.

import argparse
import contextlib
import pathlib
import sys
import typing

from ._error import Error
from ._error import error_info
from ._processor import Processor
from ._version import __version__


def main(args: list[str] | None = None) -> None:
    # Parse command-line arguments.
    args_parser = argparse.ArgumentParser(
        prog='tproc', description='A small yet powerful text processor.')
    args_parser.add_argument('input_file', nargs='?', default='-',
                             help="the input file; '-' or none for stdin")
    args_parser.add_argument('output_file', nargs='?', default='-',
                             help="the output file; '-' or none for stdout")
    args_parser.add_argument('-e', '--expand', type=str, default='main',
                             metavar='definition',
                             help="the definition to expand; 'main' by "
                                  'default')
    args_parser.add_argument('-d', '--define', metavar='name[=value]',
                             action='append', default=[],
                             help='define an option available to input '
                                  'code as tproc.opts[name]; repeatable')
    args_parser.add_argument('--version', action='version',
                             version=f'%(prog)s {__version__}')
    parsed = args_parser.parse_args(args)

    # Parse options.
    p = Processor()
    for opt in parsed.define:
        name, _, value = opt.partition('=')
        p.opts[name] = value

    try:
        # Process input.
        input_name = parsed.input_file
        if input_name == '-':
            input_name = '<stdin>'
            p.process_input(sys.stdin, input_name)
        else:
            p.process_file(input_name)

        # Expand the definition.
        with contextlib.ExitStack() as stack:
            output: typing.TextIO = sys.stdout
            if parsed.output_file != '-':
                output = stack.enter_context(
                    pathlib.Path(parsed.output_file).open(
                        'w', encoding='utf-8'))

            try:
                for chunk in p.expand_field(parsed.expand):
                    output.write(str(chunk))
            except Exception as e:
                error_info(e).files.append(input_name)
                raise
    except Error as e:
        error_info(e).report()
        sys.exit(f'{e.source or "tproc"}:'
                 f'{"" if e.line is None else f"{e.line}:"} '
                 f'error: {e.message}')
    except Exception as e:
        error_info(e).report()
        raise
