---
title: Installation
summary: >-
  Two ways in: install the package and get the py_maze command, or run the
  package straight out of a source checkout.
---

## Option 1: Install with pip (recommended)

```bash
cd py_maze
pip install -e .
```

After installation, you can run the game from anywhere:

```bash
py_maze
```

## Option 2: Run directly with Python

From the folder holding the `py_maze` package:

```bash
python -m py_maze
```

or set custom width and height for the maze like:

```bash
python -m py_maze -w 20 -H 30
```

The `py_maze.bat` and `py_maze.sh` launchers do the same thing from
anywhere, adding their own folder to `PYTHONPATH` first so no install is
needed.

## Requirements

- Python 3.10 or higher
- No external dependencies required! (Uses only standard library)

Building or installing from source additionally needs pip with setuptools 61
or newer, which is what reads `pyproject.toml`.

`requires-python` in `pyproject.toml` is that floor, and the classifiers
beside it list every version the suite is run on: 3.10, 3.11, 3.12 and 3.13.
Each of them is tested on Windows, Linux and macOS by the workflow in
`.github/workflows/tests.yml`, so the versions the manifest promises are the
versions that are actually checked.

## Upgrading from 1.x

py_maze is a package now rather than a single `py_maze.py` file, so
`python py_maze.py` has become `python -m py_maze`. The installed `py_maze`
command, every option and the save file format are all unchanged, and
`import py_maze` still reaches every name it did before. See
[The Package Layout](development.md#the-package-layout) for where each one
now lives.
