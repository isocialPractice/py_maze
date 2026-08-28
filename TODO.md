# TODO

Planned work for py_maze, a command-line maze generator and game. Items are
grouped into themed roadmap sections below; the next 1 to 5 items to work on
are listed under `## Current`. Completed items are archived automatically
into a `## Complete` section at the bottom of this file.

## Current

- [ ] Put the generators behind one interface - a size and a seeded random
  generator in, a carved grid out - so a new algorithm is one module and one
  name in an option rather than a change to `MazeGenerator`
  - From: Generation Algorithms
- [ ] Add an `--algorithm`/`-A` option choosing the generator, defaulting to
  recursive backtracking so a bare run is unchanged
  - From: Generation Algorithms
- [ ] Add Prim's algorithm as a second generator, which carves shorter dead
  ends and a more open maze than backtracking does
  - From: Generation Algorithms
- [ ] Add recursive division as a third generator, which carves long straight
  corridors and rooms rather than a winding single route
  - From: Generation Algorithms
- [ ] Add a `--braid` option removing a share of the dead ends, so the maze
  has more than one way through and the breadth-first solver picks a shortest
  path rather than the only path
  - From: Generation Algorithms

### Create and Deploy GitHub Pages Override

- Line count over 1500

## Fixes and Hardening

Bug fixes and robustness improvements to the existing game. Completing
items in this section is a patch version update.

No items are currently queued in this section.

## Project Infrastructure

Tooling, packaging, and documentation groundwork. Completing items in
this section is a patch version update.

No items are currently queued in this section.

## Gameplay Enhancements

New player-facing features from the README's future-enhancements list.
Completing items in this section is a minor version update.

No items are currently queued in this section.

## Maze Solver and Visualization

Algorithmic features around solving and displaying mazes. Completing
items in this section is a minor version update.

No items are currently queued in this section.

## Library Packaging and Public API

Turning the flat module into an importable package with a documented
surface. `python py_maze.py` gives way to `python -m py_maze`, so completing
items in this section is a major version update.

No items are currently queued in this section.

## Generation Algorithms

More than one way to carve a maze, selectable from the command line. New
options with the current behaviour unchanged, so completing items in this
section is a minor version update.

- [ ] Put the generators behind one interface - a size and a seeded random
  generator in, a carved grid out - so a new algorithm is one module and one
  name in an option rather than a change to `MazeGenerator`
- [ ] Add an `--algorithm`/`-A` option choosing the generator, defaulting to
  recursive backtracking so a bare run is unchanged
- [ ] Add Prim's algorithm as a second generator, which carves shorter dead
  ends and a more open maze than backtracking does
- [ ] Add recursive division as a third generator, which carves long straight
  corridors and rooms rather than a winding single route
- [ ] Add a `--braid` option removing a share of the dead ends, so the maze
  has more than one way through and the breadth-first solver picks a shortest
  path rather than the only path

## Machine-Readable Output and Interop

Letting another program call py_maze and read what comes back, with no
dependencies and no network service. New options with the current output
unchanged, so completing items in this section is a minor version update.

- [ ] Add a `--format` option choosing how the maze is written: `text`, the
  picture it prints today and the default, or `json`, carrying the grid, the
  entrance, the exit, the collectibles, the seed and the solution when one
  was asked for
- [ ] Accept `-` as the file name for `--load` and `--save`, reading from
  standard input and writing to standard output, so py_maze can sit in the
  middle of a shell pipeline
- [ ] Load a plain maze picture that carries no `# py_maze save` header, with
  the wall and open characters given by `--wall-char` and `--open-char`, so a
  maze drawn by another tool can be played, solved and re-saved
- [ ] Exit with distinct status codes for a refused save file, an unreadable
  file and a maze with no way through, so a script can tell the three apart
  without reading the message
- [ ] Add a `--quiet` flag suppressing the banners, the seed line and the
  play prompt, so a run that only wants the maze on standard output gets
  nothing else

## Runtime and Portability Fixes

Faults found while evaluating the finished project, none of which change an
interface. Completing items in this section is a patch version update.

No items are currently queued in this section.

## Documentation and Chores

Files the project is expected to carry and the prose the library half needs.
None of these move the version.

No items are currently queued in this section.

## Complete

- [x] Create `CHANGELOG.md` recording the existing 1.0.0 release as the
  baseline entry, following the Keep a Changelog format
  - From: Project Infrastructure
- [x] Fix the README usage example: argparse reserves `-h` for help, so
  `python py_maze.py -w 20 -h 30` fails; document the real short flag
  (`-H`) or rename the height option
  - From: Fixes and Hardening
- [x] Validate `--width` and `--height` arguments: reject values less
  than 2 with a clear error message instead of generating a degenerate
  or crashing maze
  - From: Fixes and Hardening
- [x] Fix the Windows input loop: sleep briefly when `msvcrt.kbhit()`
  reports no key (currently a 100% CPU busy-wait) and handle the
  `b'\x00'` arrow-key prefix in addition to `b'\xe0'`
  - From: Fixes and Hardening
- [x] Add unit tests covering `MazeGenerator` (solvability, dimensions,
  entrance and exit placement) and `MazeGame` (movement, wall
  collision, win detection)
  - From: Project Infrastructure
- [x] Add a `.gitignore` for Python artifacts (`__pycache__/`,
  `*.egg-info/`, `build/`, `dist/`)
  - From: Project Infrastructure
- [x] Handle Ctrl+C cleanly during gameplay: restore the terminal state
  on POSIX and exit with a goodbye message instead of a traceback
  - From: Fixes and Hardening
- [x] Cap maze dimensions to the current terminal size (or warn when
  the maze will not fit) so large `--width`/`--height` values do not
  produce an unreadable render
  - From: Fixes and Hardening
- [x] Migrate packaging from `setup.py` to `pyproject.toml` with a
  single-sourced version so the manifest can be updated in one place
  - From: Project Infrastructure
- [x] Replace placeholder author metadata in `setup.py` with real
  project metadata and add a `--version` flag to the CLI wired to the
  package version
  - From: Fixes and Hardening
- [x] Add a `--seed` option so the same maze can be regenerated
  deterministically
  - From: Gameplay Enhancements
- [x] Add difficulty levels (easy, normal, hard) that map to preset
  maze sizes selectable from the command line
  - From: Gameplay Enhancements
- [x] Implement a maze solver (breadth-first search) that can print the
  solution path overlaid on the maze via a `--solve` flag
  - From: Maze Solver and Visualization
- [x] Add an in-game hint command that briefly highlights the next step
  along the solution path
  - From: Maze Solver and Visualization
- [x] Add an animated solver visualization mode that steps through the
  search frontier in the terminal
  - From: Maze Solver and Visualization
- [x] Add a timer and move counter displayed during play and summarized
  on the win screen
  - From: Gameplay Enhancements
- [x] Add collectibles scattered on the path that are tallied in the
  end-of-game summary
  - From: Gameplay Enhancements
- [x] Add a save/load feature: write the current maze to a file and
  replay a saved maze via a `--load <file>` option
  - From: Gameplay Enhancements
- [x] Split `py_maze.py` into a `py_maze/` package - grid helpers,
  generation, solving, rendering, save files, the game and the command line
  each in their own module - with `__init__.py` re-exporting the public names
  so `import py_maze` and the `py_maze` console script keep working
  - From: Library Packaging and Public API
- [x] Move the `msvcrt`, `tty` and `termios` imports into the module that
  reads keys, so importing the generator or the solver no longer pulls in
  terminal machinery
  - From: Library Packaging and Public API
- [x] Add `__all__` and a docstring to every public function and class, so
  `help(py_maze.solve_maze)` and any generated reference describe the
  surface. Internal helpers keep the existing comment style
  - From: Library Packaging and Public API
- [x] Add `__main__.py` so a source checkout runs with `python -m py_maze`,
  and point `py_maze.bat` and `py_maze.sh` at it
  - From: Library Packaging and Public API
- [x] Keep the grid - a list of rows of booleans, `True` for a wall - as the
  documented interchange type, and add the round-trip tests that pin it, so
  the package can be reorganized later without moving the format
  - From: Library Packaging and Public API
- [x] Clear the screen with an ANSI escape sequence rather than
  `os.system('cls')` or `os.system('clear')`, falling back to the current
  call where the escape is not honoured, so `--animate` stops spawning a
  shell for every frame
  - From: Runtime and Portability Fixes
- [x] Redraw the play screen without the flicker a player sees on every move:
  `render` blanks the whole terminal and then writes the maze, the status
  line and the key legend a line at a time, so the screen stands empty
  between the clear and the last row. Home the cursor instead of clearing,
  and write the frame in a single call
  - From: Runtime and Portability Fixes
- [x] Read a single keypress at the "would you like to play" prompt on POSIX
  as `read_response` already does on Windows: it sets no raw mode, so
  `sys.stdin.read(1)` waits for Enter and leaves the rest of the line in the
  buffer, contrary to what the function says it does
  - From: Runtime and Portability Fixes
- [x] Print the win banner without the emoji when the output encoding cannot
  carry it, so a console on a legacy code page shows the congratulations
  instead of raising `UnicodeEncodeError`
  - From: Runtime and Portability Fixes
- [x] Carve from a fresh grid when `MazeGenerator.generate()` is called a
  second time on the same instance, instead of carving on top of the maze it
  already made
  - From: Runtime and Portability Fixes
- [x] Raise `requires-python` off the end-of-life 3.6 and add the Python 3.12
  and 3.13 classifiers the suite already passes on
  - From: Runtime and Portability Fixes
- [x] Add a `LICENSE` file carrying the MIT text that `README.md` and
  `pyproject.toml` both declare and the repository does not include
  - From: version.control = null
- [x] Add a GitHub Actions workflow running `python -m unittest discover` on
  Windows, Linux and macOS across the supported Python versions, so the
  cross-platform promise is checked rather than asserted
  - From: version.control = null
- [x] Add `CONTRIBUTING.md` covering the test command, the comment and
  docstring convention, and how the version is single-sourced from
  `__version__`
  - From: version.control = null
- [x] Write `docs/save-format.md` specifying the save file - the header, the
  seed comment, the markers, the ragged-line rule and what a reader must
  refuse - so another tool can write a file py_maze will load
  - From: version.control = null
- [x] Write a "Using py_maze as a Library" section in `README.md` covering
  the importable names, the grid format and a worked example that generates,
  solves and renders a maze without playing it
  - From: version.control = null
- [x] Refresh the `Development` file tree in `README.md`, which lists neither
  `TODO.md`, the launcher scripts nor `.github/`
  - From: version.control = null
