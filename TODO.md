# TODO

Planned work for py_maze, a command-line maze generator and game. Items are
grouped into themed roadmap sections below; the next 1 to 5 items to work on
are listed under `## Current`. Completed items are archived automatically
into a `## Complete` section at the bottom of this file.

## Current

- [ ] Resolve the flicker still visible in the play screen and its HUD.
  2.0.1 stopped `render` wiping the terminal and moved to homing the cursor
  and writing the frame in one call, and the flicker a player sees is
  reported as noticeable all the same. Find what is still redrawing more
  than it has to - the status line and the controls line are rewritten
  every frame whether or not they changed, and the hint redraws the whole
  screen twice - and draw only what moved
  - From: UI/UX and Screen Drawing
- [ ] Refuse a loaded maze too small to have an entrance and an exit instead
  of crashing on it. `find_entrance` reads column 1 and `find_exit` the
  second-to-last column, so a file carrying a maze fewer than 3 characters
  wide raises `IndexError` out of `py_maze/grid.py` rather than being
  refused: `py_maze --load tiny.txt --solve` on a one-column picture ends in
  a traceback. `docs/save-format.md` says a rectangle of the allowed
  characters loads, so the check belongs where the maze is used rather than
  where the file is read
  - From: Runtime and Portability Fixes

### Code Review Override - 2.2.1 Load and Document Edges

#### Resolve Issues

- [ ] Refuse a loaded maze too small to have an entrance and an exit instead
  of crashing on it
  - **Issue**: The work is done and shipped, but the queue does not say so.
    `check_ends` in `py_maze/cli.py` refuses the maze, `has_ends` and
    `MIN_GRID_WIDTH` are in `py_maze/grid.py` and on the public surface,
    `TestMazeWithNoEnds` covers it, and the 2.2.1 `CHANGELOG.md` entry
    records it - while the item itself sits unchecked in `## Current` and the
    two override items the same run finished were archived into
    `## Complete`. The next run to read the queue sees implemented work as
    outstanding.
  - **Goal**: Reconcile the record rather than building anything again.
    Check the item off and archive it into `## Complete` where the work above
    is what it asked for; where some part of it is genuinely missing, do only
    that part.
  - From: Runtime and Portability Fixes

#### Found Issues

- [ ] A document may still put a collectible on a wall
  - **Issue**: `json_cells` in `py_maze/saves.py` now refuses a cell outside
    the grid, but takes any cell inside it, wall or not. A document whose
    grid is three rows of `[true, false, true]` and whose collectibles are
    `[[0, 0]]` loads, and `(0, 0)` is a wall: `open_cells` never yields it,
    the player can never stand on it, and `MazeGame` counts it in
    `total_collectibles` all the same, so the summary reads
    `Collected: 0 of 1` however well the maze is played - the very defect the
    off-grid check was written to close. It also breaks the text round trip:
    `save_lines` draws `$` over that wall and `parse_save` reads `$` back as
    an open cell, so loading the document and saving it as a picture yields a
    maze whose wall has turned into a path. `docs/save-format.md` now says
    the document reader refuses such a cell "rather than admitting a maze the
    picture reader could not", and a picture cannot express this one either,
    `$` always being an open cell there.
  - **Goal**: Refuse a collectible that is not on an open cell, in the style
    of the message beside it, and table the refusal in the JSON section of
    `docs/save-format.md`. Then make
    `test_every_pickup_a_document_hands_back_is_one_that_can_be_had` verify
    what its name claims: it reads a generated maze back, where
    `place_collectibles` has already guaranteed open cells, so it passes with
    or without any check in the reader.
  - From: Code Review Override - 2.2.1 Load and Document Edges
- [ ] `MIN_GRID_WIDTH` is explained by something that does not happen
  - **Issue**: The `has_ends` docstring in `py_maze/grid.py` says a maze
    narrower than `MIN_GRID_WIDTH` "has one of those columns off the grid and
    neither function has anything to read", the `check_ends` comment in
    `py_maze/cli.py` says "every one of them faults", and `README.md` says
    such a maze "has nowhere to put them". None of that holds at two
    characters wide: `find_entrance` reads column 1 and `find_exit` column 0,
    both on the grid, and neither raises. Only a one-column maze faults, and
    only in `find_entrance` - `find_exit` reads column `-1` there and quietly
    hands back an `x` of `-1`. Refusing a two-wide maze is right, the exit
    column sitting left of the entrance column with both on the border, but
    the reason given for it is not the one that applies.
  - **Goal**: Restate the reason in `py_maze/grid.py`, `py_maze/cli.py`,
    `README.md` and `docs/save-format.md`: three characters is what it takes
    for the entrance column and the exit column to be distinct and inside the
    maze. Leave the behaviour, the message and the status code as they are.
  - From: Code Review Override - 2.2.1 Load and Document Edges

### Create and Deploy GitHub Pages Override

- [ ] Line count over 1300

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

- [ ] Add more than one player character to choose between, so the marker
  walking the maze is not always `o`
- [ ] Add obstacles that block or slow the way through, scattered like the
  collectibles are and reported in the end-of-game summary

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

No items are currently queued in this section.

## Machine-Readable Output and Interop

Letting another program call py_maze and read what comes back, with no
dependencies and no network service. New options with the current output
unchanged, so completing items in this section is a minor version update.

No items are currently queued in this section.

## UI/UX and Screen Drawing

How the game looks while it is being played: the redraw, the status line and
everything a player watches move. Verifying an item here means watching the
screen rather than reading a test, and completing one is a patch version
update.

- [ ] Resolve the flicker still visible in the play screen and its HUD.
  2.0.1 stopped `render` wiping the terminal and moved to homing the cursor
  and writing the frame in one call, and the flicker a player sees is
  reported as noticeable all the same. Find what is still redrawing more
  than it has to - the status line and the controls line are rewritten
  every frame whether or not they changed, and the hint redraws the whole
  screen twice - and draw only what moved

## Runtime and Portability Fixes

Faults found while evaluating the finished project, none of which change an
interface. Completing items in this section is a patch version update.

- [ ] Refuse a loaded maze too small to have an entrance and an exit instead
  of crashing on it. `find_entrance` reads column 1 and `find_exit` the
  second-to-last column, so a file carrying a maze fewer than 3 characters
  wide raises `IndexError` out of `py_maze/grid.py` rather than being
  refused: `py_maze --load tiny.txt --solve` on a one-column picture ends in
  a traceback. `docs/save-format.md` says a rectangle of the allowed
  characters loads, so the check belongs where the maze is used rather than
  where the file is read

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
- [x] Put the generators behind one interface - a size and a seeded random
  generator in, a carved grid out - so a new algorithm is one module and one
  name in an option rather than a change to `MazeGenerator`
  - From: Generation Algorithms
- [x] Add an `--algorithm`/`-A` option choosing the generator, defaulting to
  recursive backtracking so a bare run is unchanged
  - From: Generation Algorithms
- [x] Add Prim's algorithm as a second generator, which carves shorter dead
  ends and a more open maze than backtracking does
  - From: Generation Algorithms
- [x] Add recursive division as a third generator, which carves long straight
  corridors and rooms rather than a winding single route
  - From: Generation Algorithms
- [x] Add a `--braid` option removing a share of the dead ends, so the maze
  has more than one way through and the breadth-first solver picks a shortest
  path rather than the only path
  - From: Generation Algorithms
- [x] The README feature list contradicts itself on how a maze is carved
  - **Issue**: `README.md` line 7 still reads "Uses recursive backtracking
    algorithm to create unique, solvable mazes", written when that was the
    only algorithm. Line 12 of the same list now reads "Three Carving
    Algorithms", so the first six bullets a reader sees disagree with one
    another about whether py_maze carves one way or three.
  - **Goal**: Reword line 7 so it describes what the generator does rather
    than naming one algorithm, leaving the "Three Carving Algorithms" bullet
    to name them. Backtracking is the default, not the only choice, and the
    "Always Solvable" bullet already carries the guarantee.
  - From: Code Review Override - Carving and Braiding Documentation
- [x] `--load` does not say that `--algorithm` and `--braid` are ignored
  - **Issue**: `py_maze/cli.py` lines 224 to 228 tell the user that for a
    loaded maze "the size, seed and collectible options do not apply". Two
    more options joined that list this release: `build_maze` returns the
    saved grid before either is read, so `py_maze --load maze.txt -A
    division --braid 1` prints the file untouched with no warning, and the
    help text names neither. `README.md` line 252 does say it; the help
    does not.
  - **Goal**: Extend the `--load` help so it names the carving and braiding
    options alongside the size, seed and collectible ones, and cover it with
    a test in the `--load` group of `test_py_maze.py`.
  - From: Code Review Override - Carving and Braiding Documentation
- [x] Add a `--quiet` flag suppressing the banners, the seed line and the
  play prompt, so a run that only wants the maze on standard output gets
  nothing else
  - From: Machine-Readable Output and Interop
- [x] Accept `-` as the file name for `--load` and `--save`, reading from
  standard input and writing to standard output, so py_maze can sit in the
  middle of a shell pipeline
  - From: Machine-Readable Output and Interop
- [x] Add a `--format` option choosing how the maze is written: `text`, the
  picture it prints today and the default, or `json`, carrying the grid, the
  entrance, the exit, the collectibles, the seed and the solution when one
  was asked for
  - From: Machine-Readable Output and Interop
- [x] Exit with distinct status codes for a refused save file, an unreadable
  file and a maze with no way through, so a script can tell the three apart
  without reading the message
  - From: Machine-Readable Output and Interop
- [x] Load a plain maze picture that carries no `# py_maze save` header, with
  the wall and open characters given by `--wall-char` and `--open-char`, so a
  maze drawn by another tool can be played, solved and re-saved
  - From: Machine-Readable Output and Interop
- [x] Add a `--format` option choosing how the maze is written: `text`, the
  picture it prints today and the default, or `json`, carrying the grid, the
  entrance, the exit, the collectibles, the seed and the solution when one
  was asked for
  - **Issue**: `save_json` reads `find_entrance` and `find_exit` to write the
    `entrance` and `exit` keys, so `--format json` reaches the crash the
    second `## Current` item above describes, and reaches it without
    `--solve`. On a one-column picture, both `py_maze --load tiny.txt
    --format json` and `py_maze --load tiny.txt --format json --save
    out.json` end in an `IndexError` traceback out of `py_maze/grid.py` line
    88 and exit 1, rather than being refused. `docs/save-format.md` promises
    that any rectangle of the allowed characters loads.
  - **Goal**: Widen the fix for that queued item so it covers `save_json` as
    well as the solver. The item names only `--solve`, `find_entrance` and
    `find_exit`, so a fix written to its letter leaves `--format json`
    tracing back. Refuse the maze once, where it is used, so every reader of
    the entrance and the exit is covered by the one check.
  - From: Machine-Readable Output and Interop
- [x] A document may put a collectible outside the maze
  - **Issue**: `json_cells` in `py_maze/saves.py` takes any pair of whole
    numbers, so a document carrying `"collectibles": [[99, 99]]` or
    `[[-1, -1]]` loads without complaint. The cell is off the grid, so
    `maze_lines` never draws it and the player can never step on it, but
    `MazeGame` counts it in `total_collectibles` all the same and the
    end-of-game summary reads `Collected: 0 of 1` however well the maze is
    played. The picture format cannot express this, a `$` always being
    inside the maze, so the document reader admits a maze the picture reader
    cannot.
  - **Goal**: Refuse a cell outside the grid in `parse_json_save`, with a
    message in the style of the ones beside it, and table the refusal in the
    JSON section of `docs/save-format.md`. Cover it with a test in the JSON
    group of `test_py_maze.py`.
  - From: Code Review Override - JSON Document Edges
