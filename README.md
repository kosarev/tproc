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


# Generation of non-text data

As we already said, the value of a replacement field can be any
expression. If it evaluates to something callable, it is called
and the returned value is considered as the field value. Then, if
the value is a generator, it becomes the source of the value
chunks. Any other values are converted into literal tokens with
the `.content` field storing the original value.

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


## API

### tproc.Processor

* `Processor.expand(input)`

   Returns a generator producing a fully expanded input. The
   `input` parameter is a generator of source data.

### tproc.LiteralToken

* `LiteralToken.content`

  Contains the literal of the token as a string.


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
