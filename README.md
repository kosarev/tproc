# tproc

A small yet powerful text processor written in Python.

[![Build Status](https://travis-ci.org/kosarev/tproc.svg?branch=master)](https://travis-ci.org/kosarev/tproc)

Features:

* Unleashes the full power of Python for organizing, generating,
validating and debugging your data. Supports arbitrary Python
code and modules. No new languages to learn.

* Interleaved text and code. The order of definitions is up to you.

* Text pieces are implicitly defined as functions that can be
called from anywhere in the input file as well as from an
external code having access to the processor object.

* Supports Python 2.7 and 3.

* Available under the MIT license.


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


## API

### tproc.Processor

* `Processor.expand(input)`

   Returns a generator producing a fully expanded input. The
   `input` parameter is a generator of source data.


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
