# tproc

A small yet powerful text processor written in Python.

[![Python package CI](https://github.com/kosarev/tproc/actions/workflows/python-package.yml/badge.svg)](https://github.com/kosarev/tproc/actions/workflows/python-package.yml)
[![PyPI](https://img.shields.io/pypi/v/tproc)](https://pypi.org/project/tproc/)
[![Python](https://img.shields.io/pypi/pyversions/tproc)](https://pypi.org/project/tproc/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](https://github.com/kosarev/tproc/blob/master/LICENSE)

## Features:

* Provides a way to program your documentation.

* Unleashes the full power of Python for organizing, generating,
validating and debugging your data. Supports arbitrary Python
code and modules. No new languages to learn.

* Interleaved text and code. The order of definitions is up to you.

* Text pieces are implicitly defined as functions that can be
called from anywhere in the input file as well as from an
external code having access to the processor object.

* Requires Python 3.10 or later.

* Available under the MIT license.


## Contents

* [Installation](#installation)
* [Hello world](#hello-world)
* [Command line](#command-line)
* [Definitions](#definitions)
* [Replacement fields](#replacement-fields)
* [Format specifiers](#format-specifiers)
* [Passing data to generators](#passing-data-to-generators)
* [Escape sequences](#escape-sequences)
* [Line splices](#line-splices)
* [Comments](#comments)
* [Tokens](#tokens)
* [Generation of non-text data](#generation-of-non-text-data)
* [Namespaces and processor objects](#namespaces-and-processor-objects)
* [Including files](#including-files)
* [Errors](#errors)
* [API](#api)
* [Basic design principles](#basic-design-principles)


## Installation

```shell
pip install tproc
```


## Hello world

```python
# hello.tproc

@hello
Hello {world}

@world
World!

@main
{hello}
```

Processing:

```
$ tproc hello.tproc
Hello World!
```

The input contains three definitions, each expanding into its
body text. The names in curly braces are replaced with the body
of the corresponding definition.

Note that tproc only expands input on request, and not as it
reads and processes the definitions. Because of this, the
definitions may come in any order as seems best for your needs.

Whitespace just before and just after definition bodies is
stripped, so all the three definitions in the example produce
inline output with no new-line characters.

The part of the input before the first definition is ignored, and
supposed to be used for describing the purpose of the input and
other relevant information.

Input files are read as UTF-8.


## Command line

```
tproc [-e DEFINITION] [-d NAME[=VALUE]]... [input_file] [output_file]
```

* `input_file`, `output_file`

  The file to process and the file to write the output to. If
  omitted or `-`, the standard input and output are used.

* `-e DEFINITION`, `--expand DEFINITION`

  The definition to expand. `main` by default.

* `-d NAME[=VALUE]`, `--define NAME[=VALUE]`

  Sets an option that input code can read as
  `tproc.opts['NAME']`. The value is an empty string if not
  specified. May be repeated.

  ```python
  @main
  Hello {tproc.opts['who']}!
  ```

  ```
  $ tproc -d who=World hello.tproc
  Hello World!
  ```

* `--version`

  Prints the version of tproc.

`python -m tproc` works the same way as `tproc`.


## Definitions

tproc translates text definitions into Python generators that
produce the body text in its original form, that is, before any
expansion. This makes it possible to write definitions as normal
Python functions, like this:

```python
#!/usr/bin/env tproc

@
def hello():
    yield 'Hello {'
    yield 'world'
    yield '}'

@world
World!

@main
{hello}
```

Output:

```
Hello World!
```

Custom generators can yield the whole piece of data at once or
generate it by chunks of arbitrary size.

Lines in code blocks cannot start with `@`, as that would begin a
new definition. To use decorators, escape the `@` character:

```python
@
def bold(f):
    def wrapper():
        yield '<b>'
        yield from f()
        yield '</b>'
    return wrapper

\@bold
def main():
    yield 'Hello!'
```

```
<b>Hello!</b>
```


## Replacement fields

Replacement fields are portions of text surrounded with curly
braces that tproc replaces with some other content during
expansion process. For example:

```python
@email
info@{domain}

@domain
example.com
```

Such simplest replacement fields contain the name of a text
definition or of a custom generator (which is the same). But they
in fact can be arbitrary expressions:

```python
@
import time

@main
Happy {time.strftime('%A')}!
```

On Fridays this results into:

```
Happy Friday!
```

Note that the value of a replacement field is evaluated every
time the field is expanded, and it is expanded every time tproc
encounters its invocation, so such values are never cached. This
allows generators to produce different content for different
invocations, like in this example:

```python
@
counter = 0

def count():
    global counter
    yield '%d' % counter
    counter += 1

@main
{count} {count} {count}
```

Output:

```
0 1 2
```

To guarantee reproducible results invocations of replacement
fields are always processed in the left-to-right order.

Empty replacement fields, `{}`, expand to nothing.


## Format specifiers

In addition to value expressions, replacement fields may contain
format specifiers:

```python
@title
ESIO TROT

@main
{title:-^15}
```

Generates:

```
---ESIO TROT---
```

As you may guess, the syntax of format specifiers is the same as
for the lovely `format()` function.


## Passing data to generators

In replacement fields, portions of data delimited with colons may
follow (possibly empty) format specifiers. Each such piece of
data will then be passed as an argument to the generator. For
example:

```python
@
def section(title, body):
    yield '<section>'
    yield '<title>'
    for chunk in title:
        yield chunk
    yield '</title>'
    yield '<body>'
    for chunk in body:
        yield chunk
    yield '</body>'
    yield '</section>'

@main
{section::NAME:tproc - A text processor}
{section::SYNOPSIS:tproc [-e DEFINITION] [infile] [outfile]}
```

This gives:

```
<section><title>NAME</title><body>tproc - A text processor</body></section>
<section><title>SYNOPSIS</title><body>tproc [-e DEFINITION] [infile] [outfile]</body></section>
```

And of course such arguments can nest and each of the nested
arguments gets expanded before passing to the generator:

```python
@
def p(body):
    yield '<p>'
    for chunk in body:
        yield chunk
    yield '</p>'

def i(body):
    yield '<i>'
    for chunk in body:
        yield chunk
    yield '</i>'

@main
{p::It is {i::crucial} to support nested arguments.}
```


## Escape sequences

To support nested arguments it is necessary that curly braces and
colons preserve their special meaning everywhere within bodies of
text definitions. But that also means there should be a way to
specify the brace and colon characters in its literal meaning,
that is, as part of the body text. Escape sequences is the way to
do that.

Escape sequences start with slash (`\`) followed by the character
to escape. For example:

<!-- In 'python' mode this block highlights 'wrong' escape
     sequences. -->
```
@
@main
This example:

{code::
#include <iostream>

int main() \{
    std\:\:cout << "@ Hey! @" << std\:\:endl;
\}
}

just prints:

\@ Hey! \@

@
def code(source):
    yield '```'
    for chunk in source: yield chunk
    yield '```'
```

To represent non-printable characters and for better
interchangeability with other sources and consumers of textual
data, tproc also supports the standard C escape sequences:

`\\` `\'` `\"` `\a` `\b` `\f` `\n` `\r` `\t` `\v`

Unknown escape sequences are errors.


## Line splices

An escape character just before the end of a line removes both
itself and the line break, so long lines can be split:

```python
@main
This is a single \
line.
```

```
This is a single line.
```


## Comments

Replacement fields that start with `#` are comments and expand to
nothing:

```python
@main
1{# This is a comment.}2{#
Comments may span several lines.}3
```

```
123
```

Comments end at the first closing brace and cannot be nested.
Their content is not parsed, so there are no escape sequences or
replacement fields within comments.


## Tokens

Consider this:

```python
@main
'{echo:: {echo:: \: } }'

@
def echo(content):
    return content
```

The code seems obvious: the inner `echo` invocation gets expanded
into a colon character surrounded by spaces, which then becomes
the argument of the outer invocation that too replicates the
colon adding some more spaces around it, resulting in:

```
'  :  '
```

However, if the inner `echo` gets its argument containing the
colon in its literal de-escaped form, which is so, then why that
colon character doesn't work as an argument delimiter when it's
passed to the outer `echo`?

The answer is that before an expansion takes place, all
characters that form the sequence to expand are converted into
tokens. Curly braces designating bounds of replacement fields and
colons separating format specifiers and arguments within them
become delimiter tokens and all other data becomes literal
tokens. Being parsed, tokens preserve their meaning until the
very end of the expansion process, so once the escaped colon
character in the example above becomes part of a literal token,
it will always be considered as part of text, and not as a
delimiter.

Let's change the example a bit to see what the generators
actually get:

```python
@main
{eat:: '{outer:: {inner:: \: } }' }

@
inner_chunks = []
outer_chunks = []

def inner(content):
    for chunk in content:
        inner_chunks.append(chunk)
        yield chunk

def outer(content):
    for chunk in content:
        outer_chunks.append(chunk)
        yield chunk

def eat(content):
    for chunk in content:
        pass

    print('inner: %r' % inner_chunks)
    print('outer: %r' % outer_chunks)
    yield ''
```

The output:

```
inner: [<literal ' '>, <literal ':'>, <literal ' '>]
outer: [<literal ' '>, <literal ' '>, <literal ':'>, <literal ' '>, <literal ' '>]
```

For both the inner and outer invocations the content is a
sequence of literal tokens containing spaces and colon
characters. Curly braces and colons that work as delimiters are
consumed and processed by tproc accordingly to their meaning.

In terms of code, literal tokens are instances of class
`LiteralToken` that have a public member `.content` that stores
the literal as a string.


## Generation of non-text data

As we already said, the value of a replacement field can be any
expression. If it evaluates to something callable, it is called
and the returned value is considered as the field value. Then, if
the value is a generator, it becomes the source of the value
chunks. Any other values are converted into literal tokens with
the `.content` field storing the original value. `None` values and
empty strings produce no data, so the field
`{tproc.include('x.tproc')}`, for example, expands to nothing.

This means that functions do not have to be generators:

```python
@
def main():
    return 'Hello!'
```

```
Hello!
```

Note that string chunks generators yield are subject to expansion,
same as text definitions. To produce text that is not expanded,
yield it as a literal token: `tproc.LiteralToken('{verbatim}')`.
The output of fields with format specifiers is never expanded.

Here's how it works:

```python
@content
{55} {[5, 7, 9]} {tuple(range(3))} {'{year}'}
# {lambda\: [(yield [11] * 5)]}

@year
2018

@main
{dump::{content}}

@
def dump(content):
    for chunk in content:
        print('%r' % chunk)

    yield ''
```

The values of the replacement fields in `content` are evaluated
and expanded, and then passed to `dump` as a sequence of literal
tokens:

```
<literal 55>
<literal ' '>
<literal [5, 7, 9]>
<literal ' '>
<literal (0, 1, 2)>
<literal ' '>
<literal '2018'>
<literal '\n# '>
<literal [11, 11, 11, 11, 11]>
```

On full expansion, tokens are converted back to their literals and appear
in the resulting output in their stringized form:

```python
@main
{55} {[5, 7, 9]} {tuple(range(3))} {'{year}'}
# {lambda\: [(yield [11] * 5)]}

@year
2018
```

```
55 [5, 7, 9] (0, 1, 2) 2018
# [11, 11, 11, 11, 11]
```

Using nested replacements lists that expand into non-text data
makes it possible to translate custom markups directly into
Python data structures. For example:

```python
@main
{section::TITLE:
{p::
First paragraph.}
{p::
Second paragraph.}
}

@
def collect(tokens):
    return [x.content for x in tokens]

def p(body):
    yield ('p', collect(body))

def section(title, body):
    yield ('section', collect(title), collect(body))
```

Results in:

```
('section', ['TITLE'], ['\n', ('p', ['\nFirst paragraph.']), '\n', ('p', ['\nSecond paragraph.']), '\n'])
```


## Namespaces and processor objects

Every processor instance has its own space for global names. This
namespace is independent of the tproc's code namespace so users
are free to name their generators and other global entities as
they like.

The only name that comes predefined in the input's code namespace
is `tproc`. That name refers to the processor object that handles
the input source. Through this name the input code can access the
public API of the processor class described in the corresponding
section below. For example, `tproc.LiteralToken` refers to the
type of tokens passed to generators that have arguments:

```python
@main
{'%r' % tproc.LiteralToken}
```

```
<class 'tproc.LiteralToken'>
```


## Including files

`tproc.include(path)` processes the definitions of another file.
Relative paths are resolved relative to the directory of the file
being processed. Definitions from included files can then be used
in the same way as local ones:

```python
# page.tproc

@
tproc.include('common/header.tproc')

@main
{header}
Content.
```

```python
# common/header.tproc

@header
<h1>Title</h1>
```


## Errors

Malformed inputs, such as unbalanced braces or unknown escape
sequences, raise `tproc.Error`. Its `.message`, `.source` and
`.line` members describe what is wrong and where. On the command
line, errors are reported with the stack of fields that were being
expanded:

```
$ tproc page.tproc
tproc: In file 'page.tproc':
tproc: In field 'main':
page.tproc:7: In field 'header':
common/header.tproc:4: error: unterminated replacement field; missing '}'
```

Exceptions raised by input code propagate as usual. Code blocks
and expressions in replacement fields are compiled with the names
and lines of their source files, so tracebacks refer to the right
places in inputs.


## API

### `tproc.__version__`

The version of tproc as a string.

### `tproc.main(args=None)`

Runs tproc as a command-line tool. `args` is the list of
command-line arguments; `sys.argv[1:]` by default.

### `tproc.Error`

The type of exceptions raised on malformed inputs.

* `Error.message`

  The description of the problem.

* `Error.source`, `Error.line`

  The name of the source and the line where the problem is, or
  `None` if unknown.

### `tproc.TokenBase`

The base class of tokens.

* `TokenBase.content`

  The data the token carries.

### `tproc.LiteralToken(content)`

Tokens that represent literal data, as opposed to delimiters.
Derived from `TokenBase`.

* `LiteralToken.content`

  Contains the literal of the token. A string for text data, and
  the original value for non-text data.

### `tproc.Processor`

* `Processor.process_file(path)`

  Processes definitions in a given file. Relative paths are
  relative to the current directory.

* `Processor.process_input(input, input_name='<input>', input_dir='')`

  Processes definitions in a given input, which is an iterable of
  string chunks of any size, such as an open file. `input_name` is
  used in diagnostics, and `input_dir` is the directory relative to
  which included files are looked up.

* `Processor.include(path)`

  Processes definitions in a given file. Relative paths are
  relative to the directory of the file being processed.

* `Processor.define_code(code, source='<code>', line=1)`

  Executes a given piece of Python code in the processor's
  namespace. `source` and `line` refer to where the code comes
  from, for diagnostics.

* `Processor.define_text(name, text, source=None, line=1)`

  Defines a text definition. Whitespace around the text is
  stripped.

* `Processor.expand(input)`

  Returns a generator producing a fully expanded input. The
  `input` parameter is an iterable of source data.

* `Processor.expand_field(field)`

  Returns a generator producing a fully expanded replacement
  field specified as a string. For example,
  `p.expand_field('main')` expands the `main` definition.

* `Processor.opts`

  The dictionary of options, as set by `-d` on the command line.

* `Processor.TokenBase`, `Processor.LiteralToken`

  The types of tokens. See `tproc.TokenBase` and
  `tproc.LiteralToken`.

How outputs are split into chunks is not specified and may change.

See [examples/api.py](examples/api.py) for using tproc from Python
code.


## Basic design principles

* Input files are Python programs, presented in a form suitable
for text processing. They may import, define and execute
arbitrary Python code as they get processed. They may define a
`main()` function to implement the default action.

* All sources of input data, including text definitions, are
Python generators. Similarly, the `Processor.expand()` method is
a generator producing output data. The data is consumed and
generated in chunks that may be of any type and size. String
chunks are subject to expansion. Chunks of other types are passed
to the output without any additional processing unless the they
constitute an input of a custom generator.
