#!/usr/bin/env python3
"""Run py_maze from a source checkout with ``python -m py_maze``.

The installed console script calls :func:`py_maze.cli.main` directly, so
this module is what makes the checkout and the installed copy behave the
same way without a `py_maze.py` at the root.
"""

from .cli import main

if __name__ == '__main__':
    main()
