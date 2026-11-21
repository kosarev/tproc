# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

tproc is a small text processor: input files are Python programs written as interleaved `@name` text definitions and `@` code blocks, and the output is produced by expanding a definition (`main` by default). `README.md` is the language reference and the primary user documentation, so update it alongside any behavior change, and add an entry to `CHANGELOG.md` (the release workflow takes the release notes from the section matching the tag's version).

Python 3.10+. The infrastructure follows the author's other projects (kosarev/cpm80, z80, zx): `pyproject.toml`, strict mypy, pycodestyle + ruff, pytest, GitHub Actions. House style, enforced by `.ruff.toml`: single quotes, one imported name per `import` line, 79-column lines, comments rather than docstrings, the MIT header block at the top of every source file.

## Commands

```shell
pip install -e .                                   # development install
pytest                                             # all tests
pytest -k counter                                  # one .tproc test (by file stem) or test function
pycodestyle . && ruff check . && mypy --config-file .mypy.ini tproc tests examples
python -m tproc examples/hello.tproc               # or just `tproc ...` once installed
python -m build                                    # sdist + wheel
```

CI (`.github/workflows/python-package.yml`) runs the linters, the tests and every file in `examples/` on Linux and Windows for Python 3.10–3.14. Pushing a `v*` tag runs `release.yml`, which publishes to PyPI via Trusted Publishing. The version lives only in `tproc/_version.py`.

### Tests

- `tests/test_tproc_files.py` turns every `tests/*.tproc` file into a test case: expanding `main` must equal expanding `expected` (adjacent string chunks are merged first, so chunking doesn't matter; non-string chunks compare as-is). `expected` may be a code-defined generator (see `tests/markup.tproc`). Since both sides go through the same expander, behaviour that would affect both equally (e.g. dropping chunks) must be tested by comparing against literal Python values instead, as in `tests/test_api.py`.
- `test_errors.py` checks `tproc.Error` messages and source lines; `test_main.py` drives `tproc.main(args)` in-process.

## Architecture (`tproc/`)

`__init__.py` re-exports the public API (`Processor`, `Error`, `LiteralToken`, `TokenBase`, `main`, `__version__`) from private modules and sets their `__module__` to `tproc`. Everything is a generator pipeline over chunks of arbitrary type and size; nothing is cached and fields are evaluated lazily, left to right, every time they are expanded.

- **`Stream`** (`_stream.py`) wraps an iterable with `push_back()`. All parsing reads a chunk, splits it, and pushes the remainder back, so chunk boundaries can fall anywhere. Only `''` and `None` chunks are dropped here (other falsy values are data).
- **Definition phase** (`process_input` → `_process_definition`), tracking line numbers: a bare `@` block is compiled with its file name and padded line offset and `exec`'d into the processor's private `_namespace` (with `\@` unescaped so decorators work); `@name` bodies become `_TextDefinition` callables that yield the stripped raw text *unexpanded* and remember the source and line of its first character. Text before the first definition is ignored. `include()` resolves relative paths against the `include_dirs` stack.
- **Expansion phase** (`expand` / `expand_field` → `_expand_tokens`) is three layered stages, each taking the `source`/`line` of the text being expanded (both `None` for code-generated text):
  1. `_tokens_parser` turns string chunks into `DelimiterToken`s (`{`, `}`, `:`, each carrying its line) and `LiteralToken`s, handles `\` escapes (incl. line splices) and `{# ...}` comments, and counts newlines. Non-string chunks become `LiteralToken`s wrapping the value.
  2. `_format_parser` groups brace-balanced token runs into `ReplacementField`s (with the opening brace's line); delimiters outside fields are demoted to literals.
  3. `_parse_and_expand_field` splits a field by top-level colons into `value:format_spec:arg1:arg2...`, compiles and `eval`s the value with the field's source line (`_evaluate`), calls it with the args (each a lazily expanded token generator), and recursively expands the result; a `_TextDefinition` value passes its own location down. Formatted output is yielded as a `LiteralToken` so it is not re-expanded.
- Once a character is tokenized as a literal it never regains delimiter meaning, which is what makes nested arguments with escaped colons work. Strings that generators yield *are* re-tokenized; yield `LiteralToken`s to emit verbatim text.
- `expand()` unwraps `LiteralToken`s at the very end; generators receiving arguments see tokens and must read `.content`.
- Errors (`_error.py`): malformed input raises `tproc.Error(message, source, line)`. Any exception propagating out also gets an `ErrorInfo` attached as `e.tproc`, accumulating the stack of files and `(field, location)` pairs; `main()` prints it, then prints `file:line: error: ...` and exits 1 for `tproc.Error`, or re-raises anything else with its traceback.

## Repository layout notes

The parent directory `../lab/` (outside this git repo) holds the author's scratch notes: `TODO` (planned features/documentation work), `FEATURES`, experiments, and `build.sh`.
