# tproc

A small yet powerful text processor in Python.

[![Build Status](https://travis-ci.org/kosarev/tproc.svg?branch=master)](https://travis-ci.org/kosarev/tproc)


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

```shell
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


## API

### Processor

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
