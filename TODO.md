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

### Create and Deploy GitHub Pages Override

- Line count over 1300

### UI/UX Override - Site Marks, Scrolling Tables and the Favicon

#### Resolve Issues

- [ ] A table on the site has no way to scroll on a narrow screen
  - **Issue**: the narrow-screen half works - at 360px the name table in
    `docs/library.md` scrolls on its own, the page does not
    (`document.documentElement.scrollWidth` stays at 360),
    `collectible_overlay(collectibles)` reads in full once scrolled, each
    heading stays over its column at every scroll position, and nothing is
    ellipsised or broken mid-identifier. What it cost is the desktop
    rendering: `width: 100%` became `width: fit-content`, so a table now
    shrinks to its content instead of spanning the measure. Rendered in
    Chromium at 1280px, where the measure is 655.5px, the `Key` / `Does`
    table in `docs/CHEATSHEET.md` draws 588.6px (90%) and the status code
    table in `docs/scripting.md` draws 474.6px (72%) - two tables on one
    page ending 114px apart from each other and both short of the paragraph
    edge. Most of the site's tables are narrower than `76ch`, so most of
    them show it
  - **Goal**: Resolve to [table-measure-regression.prompt.md](.claude/prompts/table-measure-regression.prompt.md)
  - From: Code Review Override - 2.2.1 Load and Document Edges

#### Found Issues

- [ ] The site's rendered behaviour is pinned by nothing the suite runs
  - **Issue**: `TestDocumentationSite` in `test_py_maze.py` reads
    `docs/assets/css/site.css` and `docs/_layouts/default.html` as text,
    which is why this regression passed the suite - a stylesheet that says
    `display: block` reads as correct whatever a browser then does with it.
    Every claim behind the three site items was verified this run only
    because an agent drove a browser by hand
  - **Goal**: Add a browser test the project runs itself, asserting what
    was checked here: that a table wider than the measure scrolls while the
    page does not at 360px, that its heading stays over its column at every
    scroll position, that two tables of different widths both reach the
    paragraph edge at 1280px, that exactly one brand mark is drawn in each
    of the four width-and-theme states with the ink the theme calls for,
    that a stored dark theme paints the light-ink mark on the first frame,
    and that the brand link still exposes `py_maze` with images blocked.
    Playwright is the natural fit and is already on the machine at user
    scope, but the project has no Node test setup and its suite is
    `unittest`, so decide first whether that dependency is wanted at all -
    if not, say so and close this
  - From: UI/UX Override - Site Marks, Scrolling Tables and the Favicon

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

### New Game Modes

Ways of playing a maze that are not the plain walk from the entrance to the
exit. Each mode is the game that is already there played differently: the
same grid, the same solver, the same renderer and the same key loop, with a
bare run naming no mode playing exactly as it does today. Completing items
in this section is a minor version update.

- [ ] Add a chase mode: an antagonist that starts following the player once
  a reasonable point in the maze has been reached, moving at a reasonable
  speed, drawn with its own marker in `py_maze/rendering.py` and reported in
  the end-of-game summary beside the timer, the moves and the pickups
  - **Reasonable point**: far enough in that the chaser cannot reach the
    player the moment it starts moving
  - **Reasonable speed**: slow enough that a player who keeps moving cannot
    be caught by the chaser alone
  - The chaser walks the solution the breadth-first solver already computes,
    so it never walks into a wall and never needs a second algorithm
  - Being caught ends the run the way the exit does, with a summary saying
    which of the two happened rather than a second screen
- [ ] Add a `maze_progress(grid, cell)` reporting how far along the solution
  a cell is, as a share of the whole, which is what the chase point is read
  off and what a later `--stats` can report as well
  - Measure the solution as the straight runs it is made of rather than as
    a count of cells: sum the length of each run, and a cell's progress is
    the distance walked to it over that sum. A solution of four runs of 4,
    2, 5 and 3 totals 14, so 55% of it is 7.7, which falls in the third run
  - It reads a solved grid and returns a number, so it belongs beside the
    solver rather than in the game and can be tested without a terminal
- [ ] Add a `--chase-point` option overruling the reasonable point with a
  share of the maze the player must have walked before the chase begins
  - Takes a whole number from 20 to 90, read against `maze_progress`, and
    defaults to 55
  - A value under 20 resolves to 20 and one over 90 to 90, so the option
    cannot be set to a value that makes the mode unplayable either way
  - A decimal rounds to the nearest whole number
  - A value that is not a number at all, as in `--chase-point a34`, prints
    a notice of its own naming the option and the value, and the run
    carries on as though the option had not been given
- [ ] Add a `--chase-speed` option overruling the reasonable speed with one
  of six preset speeds, given as a whole number from 0 to 5
  - The presets are the moves the chaser makes in a second: `0` is one,
    rising by one to `5` at six, so the option names a speed rather than a
    delay a player has to reason about
  - A value under 0 resolves to 0 and one over 5 to 5, a decimal rounds to
    the nearest whole number, and a value that is not a number prints the
    same kind of notice `--chase-point` does and is otherwise ignored
- [ ] Add a quest mode: an inventory the player fills from the maze, where
  what is carried is what opens the way on, so a maze is played for what is
  in it rather than only for the way out
  - **Door**: closed until the matching item is carried, and opening one
    reaches the next stage or the next part of the maze
  - **Box**: holds an item, so one pickup leads to another
  - Each is drawn with its own marker, refused by the save format the way
    an unknown character already is, and carried through the JSON document
    so a document round trips a quest maze as it does a plain one
- [ ] Add a non-playable character to quest mode that hands out a hint on
  the task in front of the player, shown on its own key the way the hint
  along the solution already is
  - It says what the next step of the quest is rather than where the exit
    is, so it is a second kind of hint rather than a second way to ask for
    the first
- [ ] Add a `--mode` option choosing between the plain game, chase mode and
  quest mode, defaulting to the plain game, with the names listed in its
  help text as `--algorithm` lists its own, and say plainly which options
  belong to which mode
- [ ] Write `docs/modes.md` covering each mode, its options and its markers,
  add it to `docs/_data/nav.yml` and the README's documentation table, and
  add the new names to `py_maze/__init__.py` and the tables in
  `docs/library.md`

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

No items are currently queued in this section.

## Maze Analysis and Statistics

Reading a maze rather than carving or solving one: what shape it turned out
to be, how hard it is likely to play, and how two mazes compare. Everything
here is measured from a grid that already exists, so it works the same on a
generated maze and on one read out of a file. New options with the current
output unchanged, so completing items in this section is a minor version
update.

- [ ] Add a `maze_stats(grid)` to a new `py_maze/analysis.py` returning the
  measurements the rest of this section reports: the cell count, the open
  cell count, the dead end count, the junction count, the longest corridor
  and the solution length. One call, one dictionary, no terminal
- [ ] Add `dead_ends(grid)` yielding every cell with one open neighbour and
  no way on, which `braid_maze` already finds for itself in
  `py_maze/generation.py` and which nothing else can reach
- [ ] Add `junctions(grid)` yielding every cell with three or more open
  neighbours, so the branching of a maze can be counted rather than
  eyeballed
- [ ] Add a `--stats` flag printing those measurements under the maze, in
  the style of the status line rather than as a table, and leaving the maze
  itself unchanged
- [ ] Carry the same measurements in the JSON document under a `stats` key
  when `--stats` is given, so a script reads them rather than parsing the
  printed lines
- [ ] Report the share of the maze the solution walks through, which is what
  separates a maze that is mostly one long corridor from one that is mostly
  wrong turns
- [ ] Add a difficulty score built from the measurements above, documented
  as what it is made of rather than as a number to trust, so `--stats` says
  something a player understands
- [ ] Compare the three carving algorithms in the documentation with the
  measurements rather than with prose, so "Prim's dead ends are short" is a
  number a reader can check
- [ ] Measure a braided maze before and after braiding in the same run, so
  `--braid 0.25 --stats` says how many dead ends were opened rather than how
  many are left
- [ ] Add the analysis names to `py_maze/__init__.py`, the module to
  `PACKAGE_MODULES` and `TERMINAL_FREE_MODULES` in the suite, and a table to
  `docs/library.md`, since nothing here touches a terminal
- [ ] Write `docs/analysis.md` covering the measurements and what each one
  means for a maze, and add it to `docs/_data/nav.yml` and the README's
  documentation table

## Rendering Styles and Character Sets

What a maze is drawn with, as opposed to when the screen is redrawn. Today
every maze is asterisks and spaces, and every marker is one ASCII character
fixed in `py_maze/rendering.py`. This section makes the drawing a choice
without changing what a bare run draws. New options with the current output
unchanged, so completing items in this section is a minor version update.

- [ ] Gather the markers into one style object in `py_maze/rendering.py` -
  the wall, the open cell, the player, the solution, the frontier, the
  visited cell, the hint and the collectible - so a second style is a second
  object rather than a change to `maze_lines`
- [ ] Keep the current markers as the default style under a name, so a run
  with no options draws exactly what it draws today and the suite's fixed
  mazes still match
- [ ] Add a box-drawing style using the light box characters, drawn only
  where the output encoding can carry them, falling back to the ASCII style
  the way the win banner already falls back
- [ ] Add a `--style` option choosing between the styles, defaulting to the
  current one, with the names listed in its help text as `--algorithm` lists
  its own
- [ ] Add a heavy-block style for a terminal whose font makes the asterisk
  maze hard to read, using a full block for a wall and a space for a cell
- [ ] Make `--wall-char` and `--open-char` apply to writing as well as
  reading, so a maze can be drawn with the characters it will be read back
  with, and say plainly in the documentation what that costs: a picture
  drawn with anything but the format's own characters is no longer a save
  file
- [ ] Refuse a style whose characters a save file could not be read back
  from, rather than writing a file `parse_save` will turn down
- [ ] Report the style in the JSON document, so a program that reads a
  document knows how the picture beside it was drawn
- [ ] Add the style names to the public surface and a table to
  `docs/library.md`, since a caller drawing a maze with `maze_lines` picks a
  style the same way the command line does
- [ ] Extend `TestCarvingSectionExamples` to run each documented style, so a
  style that stops drawing what the documentation shows fails the suite

## The Documentation Site

The site in `docs/`, now that it exists: the pages it is still missing, the
ways it can be read better, and the checks that keep it honest. None of
these move the version.

- [ ] Add a search over the pages, built from a small index generated at
  build time rather than from a hosted service, so the site keeps its
  promise of no dependency and no network call
- [ ] Add a "copy" control to every code block, so a reader takes a command
  without selecting it, and leave the block readable with the script turned
  off
- [ ] Add anchor links to every heading on a page, so a reader can link to
  the paragraph they mean rather than to the page it is on
- [ ] Add an in-page table of contents to the longer pages, built from their
  own level 2 headings, fixed beside the text on a wide screen and folded
  above it on a narrow one
- [ ] Check every link on the site in the suite: an internal link that names
  no page, and an anchor that names no heading, are both failures worth
  catching before a reader finds them
- [ ] Check that every option `build_parser` defines is tabled on
  `docs/options.md`, the way the library page's tables are already checked
  against `__all__`, so an option added without documentation fails
- [ ] Check that every status code `py_maze.cli` exports is tabled on
  `docs/scripting.md` with the same wording the message uses
- [ ] Add the mazes the site shows as generated images rather than as
  characters, only where the characters are genuinely hard to read, and keep
  the text version beside each so a screen reader still reaches it
- [ ] Give the site a page of worked examples: a maze piped through another
  tool, a maze drawn by a script and played by py_maze, and a maze read out
  of a document, each runnable as written and each run by the suite
- [ ] Record the site's URL in one place rather than in the README, the
  manifest and `docs/_config.yml` separately, and check the three agree

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
- [x] Derive the site's design language from `logo.svg` and `icon.svg` and
  record it in `DESIGN_LANGUAGE.md`, with the contrast ratio checked for
  every text and background pair the stylesheet uses
  - From: Create and Deploy GitHub Pages Override
- [x] Split the documentation out of `README.md` into pages under `docs/`,
  moving the full text rather than summarizing it, and leave the README a
  front door whose section headings link to the pages they came from
  - From: Create and Deploy GitHub Pages Override
- [x] Write `docs/QUICKSTART.md` and `docs/CHEATSHEET.md`, the first for a
  reader who wants the game running now and the second for one who has read
  the documentation and wants the options back at a glance
  - From: Create and Deploy GitHub Pages Override
- [x] Build the site from those pages with GitHub Pages' own Markdown
  processing, under a layout and stylesheet written from
  `DESIGN_LANGUAGE.md`: a fixed side menu, collapsible groups, light and
  dark rendering, and a base URL of `/py_maze` so a project site's links
  resolve
  - From: Create and Deploy GitHub Pages Override
- [x] Add `.github/workflows/workflow.yml` deploying `docs/` to GitHub
  Pages from `main`, and switch the repository's Pages source to GitHub
  Actions
  - From: Create and Deploy GitHub Pages Override
- [x] Point the tests that read the README's documentation at the pages the
  documentation moved to, so the worked example, the carving examples, the
  scripting section, the name tables and the project tree are still run
  against the package rather than left unchecked
  - From: Create and Deploy GitHub Pages Override
- [x] Refuse a loaded maze too small to have an entrance and an exit instead
  of crashing on it. `find_entrance` reads column 1 and `find_exit` the
  second-to-last column, so a file carrying a maze fewer than 3 characters
  wide raises `IndexError` out of `py_maze/grid.py` rather than being
  refused: `py_maze --load tiny.txt --solve` on a one-column picture ends in
  a traceback. `docs/save-format.md` says a rectangle of the allowed
  characters loads, so the check belongs where the maze is used rather than
  where the file is read
  - From: Runtime and Portability Fixes
- [x] Verify the documentation site deployed
  - The site work was pushed, which only starts the deployment: GitHub
    builds it afterwards and the build can fail on its own. Confirm the
    workflow run for the commit that carried the site succeeded, then
    check this off. If it failed, fix the cause and leave this open.
  - From: Create and Deploy GitHub Pages Override
- [x] Utilize media files in `docs/assets/` for GitHub Pages, and apply asset
  according to:
  - Light mode: Use `docs/assets/icon-dark.svg` and `docs/assets/logo-dark.svg`
  - Dark mode: Use `docs/assets/icon-light.svg` and `docs/assets/logo-light.svg`
  - Reference: `.support/menu-logo_per-mode.png`
  - Apply logo: Desktop and large tablet display sizes
    - **NOTE**: Both logo SVG files have the text `py_maze` vectorized, so the
      raw string currently in the menu can be removed, but at a `title` and
      `aria` attributes accordingly
    - **IMPORTANT**: Ensure the SVG's are sized correctly. Scale them down to around
      `width=40%`
  - Apply icon: Small tablet and phone display sizes
  - Applying both assets:
    - Use an `img` element to hold the assets, keeping them both in the current
      `<a class="brand" href="/py_maze/index.html">` tag, setting the `src`
      according to the current mode
  - From: User Overrides `->` After GitHub Pages Deployment is Verified and
    Marked Complete
- [x] Use newly added `docs/assets/favicon.svg` as the deployed site's favicon
  - From: User Overrides `->` After GitHub Pages Deployment is Verified and
    Marked Complete
- [x] Refuse a loaded maze too small to have an entrance and an exit instead
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
- [x] A document may still put a collectible on a wall
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
- [x] `MIN_GRID_WIDTH` is explained by something that does not happen
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
- [x] A table on the site has no way to scroll on a narrow screen
  - **Issue**: `docs/assets/css/site.css` defines `.table-scroll` with
    `overflow-x: auto`, and nothing ever carries that class: kramdown writes
    a bare `<table>` for a Markdown table, and no page wraps one by hand. So
    the rule that was written to keep a wide table inside the screen is dead,
    and `.page table { width: 100% }` is what applies instead. A table cannot
    shrink below its widest unbreakable word, and the name table in
    `docs/library.md` holds `collectible_overlay(collectibles)` - 33
    characters set in the monospace face at `--type-sm`, roughly 277px, in a
    cell with 24px of padding, beside two more columns. On a 360px phone the
    shell leaves 328px, so that row pushes the page wider than the viewport
    and the whole page scrolls sideways rather than the table.
    `DESIGN_LANGUAGE.md` says "every page reads from a phone", and
    `docs/save-format.md` and `docs/CHEATSHEET.md` carry tables of the same
    shape.
  - **Goal**: Give the tables the scroll the stylesheet already intends,
    without a wrapper on every table by hand - `.page table { display: block;
    overflow-x: auto }` or an equivalent that keeps the header readable - and
    either use `.table-scroll` or drop it, so the stylesheet has one answer
    rather than two. Then record the behaviour in the "Layout and menu"
    section of `DESIGN_LANGUAGE.md`, which currently promises the phone
    rendering without saying what a wide table does. Confirm it in a browser
    at 360px: this was queued rather than fixed because it cannot be verified
    without rendering the page.
  - From: Code Review Override - 2.2.1 Load and Document Edges
