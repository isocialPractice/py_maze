---
title: Development
summary: >-
  The repository as a map, what each module owns, where the version lives,
  how the tests are run and how this site is built.
---

The project structure:

```
py_maze/
├── py_maze/                # The package itself
│   └── algorithms/         # The ways a maze can be carved, one to a module
├── docs/                   # This site, one Markdown page to a file
│   ├── _layouts/           # The one layout every page is drawn in
│   ├── assets/             # The stylesheet and the one script
│   └── save-format.md      # The save file, for a tool that writes one
├── .github/
│   ├── instructions/       # Editor instructions for this repository
│   └── workflows/
│       ├── tests.yml       # The suite, on every platform and version
│       └── workflow.yml    # This site, built and deployed to Pages
├── py_maze.bat             # Windows launcher, no install needed
├── py_maze.sh              # POSIX launcher, no install needed
├── test_py_maze.py         # Unit tests
├── pyproject.toml          # Packaging and project metadata
├── .gitignore              # Ignored build, cache and editor artifacts
├── CHANGELOG.md            # Version history
├── CONTRIBUTING.md         # The test command and the conventions
├── DESIGN_LANGUAGE.md      # The site's palette, type and spacing
├── LICENSE                 # The MIT text the manifest declares
├── TODO.md                 # Planned work, and what has been done
└── README.md               # The front door, and the way to this site
```

## The Package Layout

Each module owns one job, and `__init__.py` re-exports every public name, so
`import py_maze` reaches all of them whichever module they live in:

```
py_maze/
├── __init__.py         # Re-exports the public names
├── __main__.py         # python -m py_maze
├── grid.py             # The grid, and the helpers that build and read it
├── algorithms/         # The ways a maze can be carved, one to a module
│   ├── __init__.py     # The registry --algorithm reads its names from
│   ├── backtracker.py  # Recursive backtracking, the default
│   ├── prim.py         # Randomized Prim's algorithm
│   └── division.py     # Recursive division
├── generation.py       # Carving a maze, braiding it, scattering its pickups
├── solving.py          # Breadth-first search over a grid
├── rendering.py        # Drawing a maze, and measuring the terminal
├── saves.py            # Reading and writing save files
├── keys.py             # Single keypresses, and the terminal imports
├── game.py             # Playing a maze at the terminal
├── cli.py              # The options, the parser and main()
└── version.py          # The version number, on its own
```

One type is passed between them all: a maze is a **grid**, a list of rows of
booleans with `True` for a wall and `False` for a cell the player can stand
on, addressed as `grid[y][x]`. A maze carved by `generation` is the same
object `solving` walks, `rendering` draws and `saves` writes out, so nothing
is converted along the way. Every module and public name carries a docstring,
so `help(py_maze)` and `help(py_maze.solve_maze)` describe the surface.

`keys.py` is the only module that imports terminal machinery, so `msvcrt`,
`tty` and `termios` stay out of the way of anything that only wants to
generate or solve a maze.

`algorithms/` is the one subpackage, and every module in it is the same
shape: one carving function taking a width, a height and a random number
generator and returning a carved grid. `algorithms/__init__.py` maps the name
`--algorithm` takes to the function that carves it, so a fourth algorithm is
a module there and an entry in that map, with nothing in `generation.py` to
change. `pyproject.toml` lists the subpackage beside the package, which is
what installs it.

## The Version Number

The version lives in one place, `__version__` in `py_maze/version.py`, which
`py_maze/__init__.py` re-exports as `py_maze.__version__`. The manifest reads
it from there, so a release only ever changes that one string:

```toml
# pyproject.toml
dynamic = ["version"]

[tool.setuptools.dynamic]
version = { attr = "py_maze.__version__" }
```

The same value backs the `--version` flag, and the test suite checks that the
changelog has an entry for it.

## Running the Tests

The tests use only the standard library, so no test dependencies are
needed:

```bash
python -m unittest discover -v
```

The suite runs on any platform. Both the Windows and the POSIX keyboard
branches are exercised through fake terminals, so neither is skipped for
running on the other operating system.

That same command is what CI runs. `.github/workflows/tests.yml` runs it on
Windows, Linux and macOS across every supported Python version on each push
and pull request, so the cross-platform promise is checked rather than
asserted.

## This Documentation Site

Every page of this site is a Markdown file in `docs/`, so the same file reads
on GitHub and here. There is no generator to install: GitHub Pages' own
Markdown processing builds it, under the one layout in `docs/_layouts/` and
the stylesheet in `docs/assets/css/`.

`.github/workflows/workflow.yml` builds and deploys it on every push to
`main`. Editing a page is editing its Markdown file, and adding one means
adding the file and a line in `docs/_data/nav.yml`, which is the side menu.

The palette, the type scale and the spacing are recorded in
`DESIGN_LANGUAGE.md` in the repository root, with the contrast ratio measured
for each text and background pair. That file and `docs/assets/css/site.css`
are meant to agree: a value changed in one is changed in the other.

The suite reads these pages as well as the code. The worked example on
[the library page](library.md) is executed and its output compared character
for character, every command line the carving, braiding and scripting pages
show is run, the name tables are checked against `__all__`, and the project
tree above is resolved against the repository. Documentation that drifts from
the package fails the suite rather than a reader's terminal.
