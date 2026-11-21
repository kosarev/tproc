#   tproc - A small yet powerful text processor.
#   https://github.com/kosarev/tproc
#
#   Copyright (C) 2018-2026 Ivan Kosarev.
#   mail@ivankosarev.com
#
#   Published under the MIT license.

# Using tproc from Python code.

import tproc


def main() -> None:
    p = tproc.Processor()

    # Options are visible to input code as tproc.opts.
    p.opts['name'] = 'World'

    p.process_input([
        '@main\n',
        "Hello {tproc.opts['name']}! {count} {count} {count}\n",
        '@\n',
        'counter = 0\n',
        'def count():\n',
        '    global counter\n',
        '    counter += 1\n',
        '    yield str(counter)\n',
    ])

    print(''.join(str(chunk) for chunk in p.expand_field('main')))


if __name__ == '__main__':
    main()
