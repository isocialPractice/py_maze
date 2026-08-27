#!/usr/bin/env python3
"""The single source of the package version.

`pyproject.toml` reads `py_maze.__version__`, the `--version` flag prints
it and the test suite checks the changelog has an entry for it, so a
release only ever changes the string below. It lives in a module of its
own so both the package and the command line can read it without one
importing the other.
"""

__version__ = '2.0.2'
