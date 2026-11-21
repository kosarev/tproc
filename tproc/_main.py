#   tproc - A small yet powerful text processor.
#   https://github.com/kosarev/tproc
#
#   Copyright (C) 2018-2026 Ivan Kosarev.
#   mail@ivankosarev.com
#
#   Published under the MIT license.

import argparse
import pathlib
import sys

from ._error import error_info
from ._processor import Processor


def main() -> None:
    # Parse command-line arguments.
    args_parser = argparse.ArgumentParser(prog='tproc')
    args_parser.add_argument('input_file', nargs='?',
                             type=argparse.FileType('r'), default=sys.stdin)
    args_parser.add_argument('output_file', nargs='?',
                             type=argparse.FileType('w'), default=sys.stdout)
    args_parser.add_argument('-e', '--expand', type=str, default='main',
                             metavar='definition',
                             help='specify the definition to expand')
    args_parser.add_argument('-d', '--define', metavar='name[=value]',
                             action='append', default=[],
                             help='define option')
    args = args_parser.parse_args()

    # Parse options.
    p = Processor()
    for opt in args.define:
        name, _, value = opt.partition('=')
        p.opts[name] = value

    # Process input.
    input = args.input_file
    try:
        input_dir = (pathlib.Path() if input is sys.stdin
                     else pathlib.Path(input.name).parent)
        p.process_input(input, input.name, input_dir)
    except Exception as e:
        error_info(e).report()
        raise

    # Expand the definition.
    try:
        output = args.output_file
        for chunk in p.expand_field(args.expand):
            output.write(str(chunk))
    except Exception as e:
        info = error_info(e)
        info.files.append(input.name)
        info.report()
        raise
