# Contributing to py_maze

Thanks for taking an interest in py_maze. It is a small project with a
small number of rules, and all of them are here.

## What the Project Is

A command-line maze generator, solver and game written against the standard
library alone. There are no runtime dependencies and no test dependencies,
and a change that would add either needs a reason that could not be met
without it.

One type runs through the whole package. A maze is a **grid**: a list of
rows, each row a list of booleans, with `True` for a wall and `False` for a
cell the player can stand on. `grid[y][x]` addresses row `y`, column `x`,
and a cell is always the pair `(x, y)`. A maze carved by
`py_maze.generation` is the same object `py_maze.solving` walks,
`py_maze.rendering` draws and `py_maze.saves` writes out, so nothing is
converted along the way. New code reads and writes that grid rather than a
format of its own.

## Getting Set Up

Clone the repository and run it in place. Nothing needs installing to work
on it:

```bash
git clone https://github.com/isocialPractice/py_maze.git
cd py_maze
python -m py_maze --help
```

An editable install is only needed to exercise the `py_maze` console
script, and it wants pip with setuptools 61 or newer:

```bash
python -m pip install -e .
```

The project supports Python 3.10 and newer. `requires-python` in
`pyproject.toml` is the floor, and the classifiers beside it list every
version the suite is run on.

## Running the Tests

From the repository root:

```bash
python -m unittest discover -v
```

That is the whole test command. It is what the GitHub Actions workflow in
`.github/workflows/tests.yml` runs on Windows, Linux and macOS across every
supported Python version, so a suite that passes locally on one platform is
still checked on the other two.

The suite runs on any platform without skipping. Both the Windows and the
POSIX keyboard branches are driven through fake terminals, as is the console
mode switching, so no test is passed over for running on the wrong operating
system. Timing is driven through a fake clock rather than a real one, so a
test that measures a duration measures an exact one.

A single test, or a single class, while working on it:

```bash
python -m unittest test_py_maze.TestMazeGenerator -v
python -m unittest test_py_maze.TestMazeGenerator.test_every_maze_is_solvable -v
```

Every change lands with tests. A bug fix gets a test that fails before the
fix, a new option gets tests for what it does and what it refuses, and a
new public name gets a test that reaches it through `import py_maze`.

## The Comment and Docstring Convention

The two are not interchangeable here, and which one a piece of code takes
depends on whether the name is public:

- **Public names take docstrings.** Every module, class and function that
  is exported carries one, because `help(py_maze.solve_maze)` and any
  generated reference are built out of them. Functions use the `Args:`,
  `Returns:`, `Raises:` and `Yields:` sections already in use across the
  package, and describe the maze in the reader's terms rather than the
  implementation's.

  ```python
  def solve_maze(grid, start=None, end=None):
      """Find the shortest way through a maze with breadth-first search.

      Args:
          grid: 2D list of booleans (True = wall, False = path)
          start: Cell to solve from, defaulting to the entrance
          end: Cell to solve for, defaulting to the exit

      Returns:
          list: Cells from start to end inclusive, or None when the exit
          cannot be reached
      """
  ```

- **Internal helpers take comments.** A helper that is not exported keeps
  the existing lowercase comment style: a line or two above the definition
  saying what it is for, and the same `Args:` and `Returns:` wording in
  comment form where the shape is worth spelling out. Test helpers follow
  the same rule, since none of them are public.

  ```python
  def terminal_size(columns, lines):
      # build a terminal size for fit_to_terminal to measure against
      #
      # Args:
      #     columns: Characters across
      #     lines: Rows down
      #
      # Returns:
      #     os.terminal_size: The same type shutil.get_terminal_size returns
  ```

- **Comments say why, not what.** A comment that restates the line under it
  earns nothing. The ones worth writing record the reason a thing is done
  the way it is, such as `-h` being reserved by argparse, or a grid being
  carved fresh so a second call does not carve over the first.

A public name also goes in two more places: the `__all__` of the module it
lives in, and the re-export list in `py_maze/__init__.py`, so
`import py_maze` reaches it whichever module it lives in. There is a test
that checks the two agree.

Beyond that, follow the surrounding code: four-space indentation, lines
under 80 characters, `%` string formatting as the package already uses, and
no em dashes in prose or comments.

## Adding a Carving Algorithm

Every way of carving a maze lives in its own module under
`py_maze/algorithms/`, and every one is the same function to call:

```python
carve(width, height, rng) -> grid
```

A size and a random number generator in, a carved grid out, with the
entrance and the exit already opened by `open_ends`. Nothing is carried
between calls, which is what makes a seeded run repeatable: the carver reads
its size and its random numbers and touches nothing else.

A fourth algorithm is four small edits and nothing in `MazeGenerator`:

1. Write `py_maze/algorithms/<name>.py` with the carving function in it, its
   own `__all__` and a module docstring saying what kind of maze it carves.
2. Add it to `ALGORITHMS` and `ALGORITHM_NOTES` in
   `py_maze/algorithms/__init__.py`. The note is what `--algorithm --help`
   shows, so write it for a player choosing between them.
3. Re-export the function from `py_maze/__init__.py`, as any public name is.
4. Add the module to `PACKAGE_MODULES`, `TERMINAL_FREE_MODULES` and
   `TestLibrarySection.TABLED_MODULES` in `test_py_maze.py`, and give it a
   row in the README's `Carving` table. `TestCarvingAlgorithms` then holds
   the new algorithm to every promise the others keep, without a test of its
   own being written.

An algorithm has to leave a maze that is solvable, that seals its border,
that leaves every cell standable, and that has exactly one route between any
two cells. `--braid` is what opens a maze up beyond that, and it works on
whatever a carver hands back.

## The Version Number

The version lives in exactly one place, `__version__` in
`py_maze/version.py`. Everything else reads it from there:

- `py_maze/__init__.py` re-exports it as `py_maze.__version__`
- `pyproject.toml` reads that attribute, so the manifest carries no number
  of its own:

  ```toml
  dynamic = ["version"]

  [tool.setuptools.dynamic]
  version = { attr = "py_maze.__version__" }
  ```

- the `--version` flag prints the same value
- the test suite checks `CHANGELOG.md` has an entry for it

So a release changes that one string and adds the matching changelog entry.
Do not add a version number anywhere else, and do not edit the version as
part of a feature change: releasing is its own step.

## Changes and Pull Requests

- **`CHANGELOG.md`** follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
  and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
  A user-visible change gets an entry under `Added`, `Changed`, `Fixed` or
  `Removed`, written for someone using py_maze rather than someone reading
  the diff.
- **Version weight.** A bug fix that changes no interface is a patch, a new
  option with the current behaviour unchanged is a minor, and a change to
  how py_maze is run or imported is a major. Documentation and repository
  chores move no version at all.
- **`README.md`** is updated in the same change as the behaviour it
  describes, not afterwards. An option that is not in the README is an
  option nobody finds.
- **`TODO.md`** holds the road map. Planned work is grouped into themed
  sections there, and the next few items are listed under `## Current`.
- Keep a pull request to one thing. A fix and a refactor in one diff is two
  reviews wearing one hat.

## Reporting a Bug

Open an issue with the command that was run, what happened, what was
expected, and the Python version and platform. A maze that misbehaves is
worth including as a seed, since the seed reproduces it exactly:

```bash
python -m py_maze --seed 2024 -d hard
```

If it came from a save file, the file itself is better still: the format is
plain text and is specified in [docs/save-format.md](docs/save-format.md).
