# Changelog


## 1.0.0

The first stable release.

Python 3 only, and a refresh of the infrastructure:

- Python 3.10 or later is required; Python 2 is no longer supported.
- tproc is now a typed package (PEP 561), checked with strict mypy and linted with pycodestyle and ruff.
- Packaging moved to `pyproject.toml`; CI moved from Travis to GitHub Actions, testing on Linux and Windows. Tagged versions are published to PyPI automatically.
- Tests moved to pytest. New runnable examples in `examples/`.

Diagnostics:

- Malformed inputs -- unbalanced braces, unknown escape sequences, unterminated comments -- raise the new `tproc.Error` with the source file and line, instead of failing assertions. The command line reports them as `file:line: error: message` with the stack of fields being expanded, and exits with status 1.
- Code blocks and field expressions are compiled with their source file names and line numbers, so Python tracebacks and syntax errors point to the right lines of inputs.
- Fixed source file names in diagnostics having their directory prepended twice.

Also:

- `tproc.__version__` and `tproc --version`.
- `tproc.main()` takes an optional list of arguments; `python -m tproc` works.
- Input and output files are UTF-8 regardless of the locale.
- `Processor.process_input()` and `expand()` take any iterables, not only generators.
- `define_code()` and `define_text()` take optional source names and lines for diagnostics. `process_definition()` is now private.
- Fixed falsy non-text values, such as `0` and `False`, being dropped from outputs. Only `None` values and empty strings are.
- Fixed outputs of fields with format specifiers being re-expanded when passed as arguments.
- Fixed comments not hiding non-text chunks.
- Documented the command line, comments, line splices, includes, errors, escaping `@` in code blocks, and the full API.


## 1.0a2

- Options (`-d NAME[=VALUE]`), include files, line splices, comments and empty replacement fields.
- Callable definitions do not have to be generators.
- `TokenBase` is public, and generators can yield custom tokens.
- `@` characters in code blocks can be escaped, to support decorators.
- Diagnostics report the files and fields being processed.
- Whitespace at the beginning of text definitions is stripped.
- Fixed parsing empty trailing arguments and handling empty chunks.


## 1.0a1

- The first public release.
