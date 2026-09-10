# TODO

Planned work for py_maze, a command-line maze generator and game. Items are
grouped into themed roadmap sections below; the next 1 to 5 items to work on
are listed under `## Current`. Completed items are archived automatically
into a `## Complete` section at the bottom of this file.

## Current

- [ ] Add `dead_ends(grid)` yielding every cell with one open neighbour and
  no way on, which `braid_maze` already finds for itself in
  `py_maze/generation.py` and which nothing else can reach
  - From: Maze Analysis and Statistics
- [ ] Add `junctions(grid)` yielding every cell with three or more open
  neighbours, so the branching of a maze can be counted rather than
  eyeballed
  - From: Maze Analysis and Statistics
- [ ] Add a `maze_stats(grid)` to a new `py_maze/analysis.py` returning the
  measurements the rest of this section reports: the cell count, the open
  cell count, the dead end count, the junction count, the longest corridor
  and the solution length. One call, one dictionary, no terminal
  - From: Maze Analysis and Statistics
- [ ] Add the analysis names to `py_maze/__init__.py`, the module to
  `PACKAGE_MODULES` and `TERMINAL_FREE_MODULES` in the suite, and a table to
  `docs/library.md`, since nothing here touches a terminal
  - From: Maze Analysis and Statistics
- [ ] Add a `--stats` flag printing those measurements under the maze, in
  the style of the status line rather than as a table, and leaving the maze
  itself unchanged
  - From: Maze Analysis and Statistics

### UI/UX Override - Chase Mode on a Real Console and a Real Clock

Chase mode was driven in a real Windows console on 09.10.2026 - the marker
walked onto the screen, the chaser watched with nothing pressed, the run
played to a catch and to an exit - and judged by 107 checks, of which 101
passed. The two that did not are below. Everything else the request asked
to be watched holds: the plain game is unchanged from 2.4.0 frame for
frame, the chaser appears at the entrance at the share of the maze it was
told to, it never crosses a wall and leaves no trail, it moves at 1.00 and
6.02 cells a second on the two extreme presets, and a bad option value is a
notice on standard error that leaves standard output the maze alone.

#### Resolve Issues

- [ ] Chase Mode 1: the ending's extra `Outcome` line scrolls the frame's
  `start` marker off the top of the screen
  - **Issue**: a chased game's summary carries one tally the plain game's
    does not, so its ending is a row taller. On a console where the plain
    ending exactly fits, the chased one scrolls the screen by one row and
    the frame's first line goes with it. Measured on a real console at 100
    by 28 with a 9 by 7 maze, walked to the exit on the same seed twice:
    played plain, `start` is on row 0, `end` on 16 and the controls line on
    19 with nothing scrolled, and 2.4.0 is identical to 2.5.0 there; played
    as a chase, `end` is on 15, the controls line on 18 and there is no
    `start` anywhere. Being caught does the same. No row of the maze itself
    is lost, so what it costs is the marker
  - **Goal**: Resolve to [chase-ending-scrolls-the-start-marker-off.prompt.md](.claude/prompts/chase-ending-scrolls-the-start-marker-off.prompt.md)
  - From: Gameplay Enhancements `->` New Game Modes

#### Found Issues

- [ ] The timed key reader counts its wait down by what it asked for, so
  the loop never waits the chaser's step
  - **Issue**: `read_key_timed_windows` does `left -= nap` with `nap` at
    `KEY_POLL_INTERVAL`, while `time.sleep(0.01)` really costs about 0.0157
    on Windows, so every timed wait overruns by around 57%. Read off the
    game's own writes rather than off a screen poll, `--chase-speed 5`
    redraws every 0.265 s where `MazeGame.tick` asks for 0.167 - 3.95
    frames a second on a small maze and 4.21 on a large one, against the
    six the preset names. The chaser still crosses six cells a second
    because `Chaser.advance` hands back what the clock passed over, so what
    a player sees is not a slow chaser but one covering two cells per
    redraw for 25 of its 42 drawn moves, the catch-up cap paying for the
    loop being late rather than for a stall. The reader predates chase
    mode; shortening the loop's wait to a sixth of a second is what made it
    matter. `TestWindowsTimedInput` cannot catch it, its `FakeTime` sleeping
    by exactly what it was asked for and
    `test_no_poll_of_the_wait_overruns_the_deadline` asserting the
    requested total rather than the elapsed one
  - **Goal**: Resolve to [timed-wait-counts-down-by-what-it-asked-for.prompt.md](.claude/prompts/timed-wait-counts-down-by-what-it-asked-for.prompt.md)
  - From: UI/UX Override - Chase Mode on a Real Console and a Real Clock

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
- [ ] Write `docs/modes.md` covering each mode, its options and its markers,
  add it to `docs/_data/nav.yml` and the README's documentation table, and
  add the new names to `py_maze/__init__.py` and the tables in
  `docs/library.md`

### Further Game Modes

Modes proposed but not yet specified, held apart from the two above so that
"queued and worked out" does not read the same as "an idea worth having".
Each is the game that is already there under a different rule, reachable
through the same `--mode` option and playable with the same keys, and each
names what it reuses so none of them is a second engine. An item here is
worked up into its own items before it is built. Completing items in this
section is a minor version update.

- [ ] Add a time attack mode: the run is against a clock rather than
  against the maze, and the clock running out ends it the way the exit does
  - The timer and the move counter are already drawn on the status line and
    already summarized on the win screen, so what is new is a limit to count
    down to and a second way for the run to end
  - The limit is read off the maze rather than fixed, the solution length
    the breadth-first solver already computes being what a fair one is
    measured from, with an option overruling it as `--chase-point` overrules
    its own reasonable point
  - The summary says which of the two happened, as chase mode's does
- [ ] Add a fog of war mode: only the cells within a few steps of the player
  are drawn, so the maze is walked rather than read
  - `maze_lines` draws every cell it is given, so the mode is a filter on
    what it is handed rather than a second renderer
  - The distance is counted through the maze rather than across it, so a
    wall between two cells hides what is behind it and the solver's own
    breadth-first walk is what measures it
  - Cells already visited stay drawn, so the mode reveals a map rather than
    forgetting one, and `--solve` and the hint are refused rather than
    quietly defeating it
- [ ] Add a collect-all mode: the exit stays shut until every collectible
  has been picked up, so the pickups are the game rather than a tally
  - Collectibles, the tally and the end-of-game summary all exist; what is
    new is the exit refusing to open and saying why
  - The shut exit is drawn with its own marker until the last pickup is
    taken, so a player can see the rule rather than being told it once
  - `place_collectibles` already picks open cells, so every maze it makes is
    winnable in this mode without a second check
- [ ] Add a memory mode: the maze is drawn in full for a few seconds, then
  hidden, and the player walks it from what they remember
  - It is fog of war with the fog arriving late rather than a mode of its
    own, so it is built on whatever that one leaves behind
  - How long the maze is shown is read off its size, with an option
    overruling it, and the countdown is drawn on the status line
  - A wall walked into is reported rather than silently refused, that being
    the only feedback a player has once the drawing is gone
- [ ] Add an endless mode: finishing a maze carves the next one instead of
  ending the run, with the score carried across
  - Each maze is seeded from the one before it, so a whole run is repeatable
    from the seed of its first maze and can be reported as one number
  - The size, or the algorithm, or the braiding steps up as the run goes on,
    so the tenth maze is not the first one again
  - The summary counts the mazes finished, the moves and the pickups across
    the whole run rather than the last maze of it
- [ ] Add a ghost mode: a run recorded to a file is replayed beside the
  player, so a maze can be raced against an earlier attempt
  - The recording is the moves and the times they were made at, written the
    way a save file is written and refused the way one is, so it is a format
    another tool can produce
  - The ghost is drawn with its own marker and walks into nothing, its route
    having already been walked
  - It is the same maze or it is refused: the recording carries the seed and
    the grid it was made on, and a mismatch is reported rather than replayed
    over the wrong maze

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

- [ ] Pin the partial redraw against a real Windows console, not against the
  suite's own `TerminalScreen`, so the model and the thing it models are
  checked against each other rather than the model being trusted alone
  - The verification of the 2.2.6 redraw fix drove a console allocated with
    `AllocConsole`, sized to exactly 100x28 with `SetConsoleScreenBufferSize`
    and `SetConsoleWindowInfo`, spawned the game into it with `CONIN$` and
    `CONOUT$` as its streams, pushed keys in as `KEY_EVENT` records through
    `WriteConsoleInputW`, and read the screen back with
    `ReadConsoleOutputCharacterW`. It passed on the fix and failed on the
    code before it, at 28 rows and at 24
  - What it would assert, on a console the frame fills exactly: `start` on
    row 1 and the controls line on the bottom row; exactly one `start`, one
    `end`, one status line and one controls line on screen; exactly one `o`
    on the maze; no `?` left once a hint has gone; and at most two maze
    cells differing between consecutive frames, which is all a step can
    account for
  - It cannot go into `test_py_maze.py` as it stands: that file is 574
    stdlib-only tests running in under a second on ubuntu, windows and macos
    across four Python versions, and this is Win32-only, takes about half a
    minute per size and allocates a console window. It needs either a
    `skipUnless` guard and an opt-in environment variable, or a second
    suite of its own that CI runs on the windows leg only
  - Reading the console back is only half of it, and the 2.3.0 verification
    had to add the other half. A repaint that writes the same characters
    over the same characters leaves a screen indistinguishable from one
    nothing touched, so a screen readback cannot tell a loop that draws once
    a second from one that draws four times a second - which is exactly what
    the timed redraw has to be held to. What decides it is watching the
    writes rather than the screen: run the game under a launcher that wraps
    `sys.stdout` in a passthrough journalling every write with its time,
    leaving `fileno` and `isatty` answering for the console handle so
    `ansi_enabled` still sees a terminal and `sys.__stdout__` still measures
    the real console. Then a write can be read as the rows it addressed, and
    "an idle second wrote the status line and nothing else" becomes an
    assertion. A pseudoconsole cannot stand in for this: ConPTY keeps its
    own screen buffer and emits its own repaints, so it would report the
    wasteful redraw as no output at all
  - The 2.4.0 verification added the event that separates this from anything
    the suite can model: the console is resized while the game is running on
    it. That is `SetConsoleWindowInfo` in, `SetConsoleScreenBufferSize`, then
    `SetConsoleWindowInfo` back out, so a resize is three calls and the game
    can measure the console part way through them; nothing may be asserted
    until the resize has settled and a frame has been drawn on the size that
    was asked for. What it would assert, at 22, 8 and 3 rows and back up to
    28: the controls line whole and alone on the bottom row with the spacer,
    the tally and `end` on the three above it, exactly one `o` on the maze
    rows however few of them there are, no row holding two of the frame's
    lines run together, and no row painted past the last one - the last of
    which is a claim about writes rather than about the screen, since a row
    addressed past the bottom is clamped onto the bottom
  - A route pushed into the console on a timer loses keypresses, and loses
    them silently: 59 keys sent at 0.16s intervals left the player on maze
    row 11 of 23, and the screen afterwards is a perfectly good screen of
    the wrong position. A walk has to wait for the move tally to count each
    step before sending the next, which matters most for the scenario that
    needs the player standing below the fold
  - The driver, its tap and its checker were left at `.tmp/ui-ux/` on the
    machine that ran the verification, and the runs are written up in the
    UI/UX agent's log under 09.07.2026, 09.08.2026 and 09.09.2026
- [ ] Pin both POSIX key readers against a real terminal rather than against
  the suite's `FakeStdin`, so the buffering the 2.4.0 fix reasons about is
  measured on the thing it reasons about
  - 2.4.0 moved `read_key_posix`, `read_key_timed_posix` and `read_response`
    onto the descriptor `select` polls, because reading through `sys.stdin`
    left a second key typed inside one tick in a wrapper the wait cannot
    see. The fault was measured on a pipe and the fix is measured against a
    `FakeStdin` that chunks the way a wrapper does; no POSIX console has
    been driven, the machine that found it and fixed it being Windows
  - What it would assert, on a pseudoterminal opened with `pty.openpty` and
    the child running the game: two movement keys written to the master
    inside one tick move the player twice; a key held down and repeated is
    read press by press; an arrow key written as its three characters is one
    move rather than three; and the terminal is left out of raw mode when
    the run ends, however it ended
  - It cannot go into `test_py_maze.py` as it stands, for the reason the
    Windows item above gives: `pty` is POSIX-only and the suite runs on
    ubuntu, windows and macos. It wants the same `skipUnless` guard and
    opt-in variable, or the second suite that item proposes, with the
    windows leg running one and the ubuntu and macos legs the other

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
- [x] A table on the site has no way to scroll on a narrow screen
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
- [x] The site's rendered behaviour is pinned by nothing the suite runs
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
- [x] The refusal added to `docs/save-format.md` is the one row of that table
  the suite never runs
  - **Issue**: `TestSaveFormatDocument.REFUSALS` in `test_py_maze.py` holds a
    file for every refusal the page tables, and
    `test_every_documented_refusal_is_one_the_reader_makes` reads each one
    and asserts the message it raises appears in the page. `Puts a
    collectible on a wall`, added this run, has no entry, so it is the only
    row the reader is never run against. The message itself is pinned by
    `test_a_document_may_not_put_a_pickup_on_a_wall`, so reworded it would
    leave the page stale without failing anything
  - **Goal**: Add `('a document with a collectible on a wall', '{"py_maze":
    1, "grid": [[true]], "collectibles": [[0, 0]]}\n')` to `REFUSALS`, in the
    place the table lists it, which raises `collectibles holds [0, 0], which
    is a wall` and is already the text the page shows. Consider pinning the
    other direction too, every row of the table being one some file
    produces, since that is the direction this gap slipped through
  - From: UI/UX Override - Site Marks, Scrolling Tables and the Favicon
- [x] The 2.2.2 entry records the scrolling table without the measure it cost
  - **Issue**: the `Fixed` bullet in `CHANGELOG.md` describes the table fix
    as whole, and the release being cut carries the desktop regression queued
    under **Resolve Issues** above: `width: fit-content` makes a table hug its
    content, so at 1280px the two tables measured this run draw 588.6px and
    474.6px against a 655.5px measure. Whoever reads the released entry is
    told the narrow-screen half and not what it cost
  - **Goal**: Either land the measure fix before 2.2.2 is cut, which makes
    the entry true as written, or add a sentence to that bullet saying a
    table now hugs its content rather than spanning the measure, to be
    dropped again when the follow-up lands
  - From: UI/UX Override - Site Marks, Scrolling Tables and the Favicon
- [x] The width `CHANGELOG.md` records for the key table is two characters
  short of what the page drew
  - **Issue**: verifying the 2.2.3 fix meant reproducing the regression
    first, so the four pages were rendered against the 2.2.2 stylesheet
    from `HEAD` as a control. The status code table on `docs/scripting.md`
    came back at 474.6px, the recorded figure to a tenth of a pixel. The
    `Key` / `Does` table on `docs/CHEATSHEET.md` came back at 605.0px, not
    the 588.6px recorded, and the 16.4px is exactly two characters of the
    8.2px monospace cell face. A block table is as wide as its widest row,
    and that table's widest row is `The "would you like to play" prompt,
    one keypress`: deleting the two straight quotes from the cell in the
    browser returns the table to 588.6px exactly. The 09.03.2026 run wrote
    its preview tables by hand and dropped them; this run converted the
    Markdown itself, so 605.0px is what that page drew under 2.2.2. The
    regression and the fix are unaffected - the table was short of the
    measure either way, and now draws the full 655.5px - but three
    published numbers derived from the wrong one
  - **Goal**: In the 2.2.3 `### Fixed` entry, `588.6px` becomes `605.0px`
    and `114px apart` becomes `130.4px apart`. In the 2.2.2 entry, `90% of
    the measure` becomes `92%` and its `114px apart` becomes `130.4px`.
    The 474.6px, the 72% and the 655.5px measure are all confirmed and
    stay. The same figures in the completed item at the foot of this file
    are a record of what that run measured rather than a claim about the
    page, so leave them
  - From: UI/UX Override - The Table Measure Regression
- [x] The 2.2.3 entry names the wrong box as the one `width: 100%` widens
  - **Issue**: the last sentence of the 2.2.3 `### Fixed` bullet in
    `CHANGELOG.md` reads "Putting `width: 100%` back on the block table was
    measured and does not work, the box it widens being the anonymous one
    rather than the cells". That inverts it. `width: 100%` applies to the
    element's own principal box, which `display: block` has made a block
    box, and widening that box is exactly what it does; the anonymous table
    box generated inside it to hold the rows keeps an auto width and stays
    shrink-to-fit, which is why the cells do not follow. The other three
    places this run wrote the same fact all say so - `DESIGN_LANGUAGE.md`
    line 125 "a box that shrinks to their content and that no selector can
    reach", the new "What the suite cannot tell you about the site" section
    of `CONTRIBUTING.md` "wraps the rows in a box no selector reaches", and
    the comment on `test_a_table_fills_the_measure_where_there_is_one_to_fill`
    in `test_py_maze.py` line 5405 "an anonymous box that is shrink-to-fit
    and that no selector reaches". A reader who takes the changelog at its
    word has the anonymous box being reached by a declaration the other
    three say cannot reach it, and the changelog is the one that is wrong
  - **Goal**: Reword that clause so the box `width: 100%` widens is the
    table's own block box and the anonymous box holding the rows is the one
    it does not reach. Leave the measurement claim itself - putting
    `width: 100%` back on the block table genuinely does not work, and the
    reason is that the widened box is not the box the cells are laid out in.
    The sentence carries none of the figures the **Found Issues** item above
    corrects, so the two edits do not collide
  - From: Code Review Override - The 2.2.3 Table Measure Fix
- [x] `stylesheet_rule` does not read the stylesheet the way its comment says
  - **Issue**: the comment added to `stylesheet_rule` in `test_py_maze.py`
    line 5346 says it returns a rule "before any at-rule narrows it", and
    the helper does not do that. It hands the whole file to `declarations`,
    which is one `re.search` returning the first textual match, inside an
    at-rule block or not. It returns the base `.page table` today only
    because that rule is written at line 514 of
    `docs/assets/css/site.css`, above the `@media (max-width: 900px)` block
    at line 642 that this run moved the scroll into. Two
    `@media (prefers-color-scheme: dark)` blocks already sit above it at
    lines 50 and 168: a `.page table` rule added to either - a border colour
    for the dark theme is the obvious one - is returned instead, and
    `test_a_table_fills_the_measure_where_there_is_one_to_fill` then asserts
    `width: 100%` against the dark-mode declarations while its failure
    message still says "the stylesheet". `narrow_screen_rule` has the
    problem solved beside it, brace-counting its block rather than matching
    it, so only the base-rule side is unguarded
  - **Goal**: Make the helper match its comment: read the declarations from
    outside every at-rule block - the counterpart of what `narrow_screen_rule`
    already does - or assert the match it found is not inside one, so a
    selector defined in two places cannot silently return the wrong rule.
    Behaviour today is correct, so no assertion in either table test should
    need to change
  - From: Code Review Override - The 2.2.3 Table Measure Fix
- [x] Resolve the flicker still visible in the play screen and its HUD.
  2.0.1 stopped `render` wiping the terminal and moved to homing the cursor
  and writing the frame in one call, and the flicker a player sees is
  reported as noticeable all the same. Find what is still redrawing more
  than it has to - the status line and the controls line are rewritten
  every frame whether or not they changed, and the hint redraws the whole
  screen twice - and draw only what moved
  - From: UI/UX and Screen Drawing
- [x] Resolve the flicker still visible in the play screen and its HUD.
  2.0.1 stopped `render` wiping the terminal and moved to homing the cursor
  and writing the frame in one call, and the flicker a player sees is
  reported as noticeable all the same. Find what is still redrawing more
  than it has to - the status line and the controls line are rewritten
  every frame whether or not they changed, and the hint redraws the whole
  screen twice - and draw only what moved
  - **Issue**: the partial redraw addresses absolute screen rows, but
    nothing keeps frame line 1 on screen row 1. `frame_text` ends its last
    line with a newline, so a frame as tall as the terminal scrolls the
    screen by one row as it is drawn, and every partial redraw after it
    writes each line one row below the line it is replacing. The maze is
    left holding rows from older frames and never repairs, because only
    changed lines are written again. Playing the default `normal` maze in a
    terminal 28 rows tall reaches it with no options at all, and
    `fit_to_terminal` produces the same shape on every terminal with an
    even number of rows, because `RENDER_ROW_OVERHEAD` reserves exactly the
    5 lines the frame adds and no row for the cursor below it
  - **Goal**: keep the row a line is written on true for the whole game.
    Three candidate fixes and their costs were weighed in `KNOWN_BUGS.md`;
    what was measured and what was done about it is in the
    [2.2.6 changelog entry](CHANGELOG.md#226---2026-09-07).
    Pin it first: the suite's `TerminalScreen` models a screen of unbounded
    height and so never scrolls, so it cannot catch this until it is given
    a height and the scroll behaviour
  - From: UI/UX and Screen Drawing
- [x] **Timed Key Reader**: Add a timer and move counter displayed during
  play and summarized on the win screen
  - **Issue**: The timer only increments on arrow-key press
  - **Goal**: Ensure the timer and move counter are independent of each other
  - From: Gameplay Enhancements
- [x] Resolve the flicker still visible in the play screen and its HUD.
  2.0.1 stopped `render` wiping the terminal and moved to homing the cursor
  and writing the frame in one call, and the flicker a player sees is
  reported as noticeable all the same. Find what is still redrawing more
  than it has to - the status line and the controls line are rewritten
  every frame whether or not they changed, and the hint redraws the whole
  screen twice - and draw only what moved
  - **Issue**: 2.2.6 kept the row a line is written on true only against
    the game's own writes. It stopped the game writing the newline that
    scrolled the screen, but nothing re-establishes the origin when
    something else scrolls it, and the picture never repairs because only
    changed lines are ever written again. Two triggers are measured in
    [KNOWN_BUGS.md](KNOWN_BUGS.md#2026-09-07-the-partial-redraw-drifts-once-anything-else-scrolls-the-screen).
    The reachable one needs no resize and no unusual options:
    `CONTROLS_LINE` is 66 characters and is the last line of the frame,
    `fit_to_terminal` measures only the maze against the terminal's
    columns, so any terminal under 66 columns wraps the controls line - and
    on a screen the frame fills, that wrap is on the bottom row and scrolls
    it before a key is pressed. A 60 by 24 terminal caps the maze to 9 by 9
    for a 24 line frame and reaches it on the first frame; after four steps
    21 of the 24 rows hold lines from frames that have gone
  - **Goal**: keep the row a line is written on true for the whole game
    against a scroll from any cause, not only the game's own. Three
    candidates and their costs are in the same `KNOWN_BUGS.md` section, and
    only the third covers a resize: measure the terminal each frame and
    draw the frame whole whenever the size has changed, which is what 2.2.4
    did every frame and why the same scroll was merely cosmetic then. Pin
    it first: the suite's `TerminalScreen` models rows but not columns, so
    it cannot catch the wrap until it is given a width and wraps a line
    past the last column the way a terminal does
  - From: UI/UX and Screen Drawing
- [x] A console shortened below the height of the play screen stacks the
  frame's last lines onto its bottom row, taking the controls line and the
  foot of the maze off screen without saying so
  - **Issue**: the 2.3.0 redraw was verified and passes; this is the case
    next to it. On a 100x28 console the frame is 28 lines. Shrinking the
    console to 22 rows under a running game makes `render` redraw the frame
    whole, which is correct, but 28 lines cannot go on 22 rows: the console
    clamps every row address past the screen onto the bottom row, so the
    last maze rows, the `end` marker, the blank spacer and the controls line
    are each written there in turn and the once-a-second tally write is what
    stays. Read back off the console buffer after shrinking the window
    mid-game. The visible part of the picture is right - one `o`, no rows
    from a frame that has gone - but the foot of the maze and the controls
    line are simply not on screen, and a player standing on one of those
    rows would not be drawn at all
  - **Goal**: fit the frame to the terminal it is being drawn on rather than
    to the one the maze was generated for, drawing at most as many lines as
    the screen has rows and keeping the tally and the controls line on the
    bottom of them, so what a shrunken console costs is maze rather than the
    whole foot of the screen. `fit_to_terminal` in `py_maze/rendering.py`
    already answers this question at generation time and is where the
    redraw-time answer belongs
  - From: UI/UX Override - a console shorter than the frame drawn on it
- [x] A paragraph in `docs/library.md` was left with an orphaned line
  - **Issue**: adding `read_key_timed` to the paragraph listing the public
    terminal names pushed `` `build_parser`, `` onto a line of its own 15
    characters wide, in the middle of a paragraph every other line of which
    is wrapped to the margin
  - **Goal**: reflow the paragraph
  - From: Code Review Override - the POSIX timed key reader
- [x] Timed Key Reader 1: the POSIX reader waits on one thing and reads from
  another, so a key typed inside a tick is never looked at
  - **Issue**: `key_waiting` calls `select.select([sys.stdin], [], [],
    timeout)`, which polls the file descriptor behind standard input, while
    `read_key_sequence` reads with `sys.stdin.read(1)`, which is a
    `TextIOWrapper` reading a chunk at a time and keeping what it does not
    hand back. A raw-mode terminal returns every queued byte in one read, so
    two movement keys typed inside a quarter of a second on Linux or macOS -
    or one key held down while the keyboard repeats - leave the second where
    `select` will never mention it. The player takes one step and stops, and
    the next press plays the stranded key rather than itself for the rest of
    the run. Windows is unaffected, and the suite cannot see it:
    `TestPosixTimedInput` mocks both `select` and `sys.stdin`. Measured in
    [KNOWN_BUGS.md](KNOWN_BUGS.md#resolved-in-240-the-timed-key-reader-stranding-keys-typed-inside-one-tick)
  - **Goal**: make the thing waited on and the thing read from the same
    thing. Two candidates and what each costs are in that section; both
    reach out of `read_key_timed_posix` into readers the untimed path shares,
    which is why this was queued rather than fixed in review. Pin it first:
    the POSIX tests hand `read_key_sequence` a fake standard input returning
    one character per read, so nothing in the suite chunks the way a
    terminal does and a fix cannot be told from no fix
  - From: Gameplay Enhancements
- [x] `read_key_timed(None)` means two different things by platform
  - **Issue**: `MazeGame.get_key` routes `None` to `read_key` rather than to
    `read_key_timed`, so the game never reaches it, but `read_key_timed` is
    public, exported and named in `docs/library.md`. Given `None`,
    `read_key_timed_windows` raises `TypeError` comparing it against 0 while
    `read_key_timed_posix` passes it to `select.select` and waits forever
  - **Goal**: decide what no deadline means for a reader whose whole point
    is having one, and make both branches agree. Reading it as "wait however
    long it takes" is what `MazeGame.get_key` already means by `None` and
    what the POSIX branch already does, so Windows would follow; refusing it
    instead wants one check ahead of the platform split rather than a check
    in each branch. Either way it wants a test beside the ones that already
    drive both branches directly
  - From: Code Review Override - the POSIX timed key reader
- [x] Add a `maze_progress(grid, cell)` reporting how far along the solution
  a cell is, as a share of the whole, which is what the chase point is read
  off and what a later `--stats` can report as well
  - Measure the solution as the straight runs it is made of rather than as
    a count of cells: sum the length of each run, and a cell's progress is
    the distance walked to it over that sum. A solution of four runs of 4,
    2, 5 and 3 totals 14, so 55% of it is 7.7, which falls in the third run
  - It reads a solved grid and returns a number, so it belongs beside the
    solver rather than in the game and can be tested without a terminal
  - From: Gameplay Enhancements `->` New Game Modes
- [x] **Chase Mode**: Add a chase mode: an antagonist that starts following
  the player once a reasonable point in the maze has been reached, moving at
  a reasonable speed, drawn with its own marker in `py_maze/rendering.py` and
  reported in the end-of-game summary beside the timer, the moves and the
  pickups
  - **Reasonable point**: far enough in that the chaser cannot reach the
    player the moment it starts moving
  - **Reasonable speed**: slow enough that a player who keeps moving cannot
    be caught by the chaser alone
  - The chaser walks the solution the breadth-first solver already computes,
    so it never walks into a wall and never needs a second algorithm
  - Being caught ends the run the way the exit does, with a summary saying
    which of the two happened rather than a second screen
  - From: Gameplay Enhancements `->` New Game Modes
- [x] Add a `--mode` option choosing between the plain game, chase mode and
  quest mode, defaulting to the plain game, with the names listed in its
  help text as `--algorithm` lists its own, and say plainly which options
  belong to which mode
  - Quest mode is not built yet, so the option lists the modes that exist:
    build the names as a registry, the way `ALGORITHMS`, `DIFFICULTIES` and
    `FORMATS` already are, so quest mode joins the list rather than editing
    the option
  - It is queued ahead of the two chase options because without it chase
    mode has no entry point, a bare run naming no mode playing exactly as it
    does today by design
  - From: Gameplay Enhancements `->` New Game Modes
- [x] Add a `--chase-point` option overruling the reasonable point with a
  share of the maze the player must have walked before the chase begins
  - Takes a whole number from 20 to 90, read against `maze_progress`, and
    defaults to 55
  - A value under 20 resolves to 20 and one over 90 to 90, so the option
    cannot be set to a value that makes the mode unplayable either way
  - A decimal rounds to the nearest whole number
  - A value that is not a number at all, as in `--chase-point a34`, prints
    a notice of its own naming the option and the value, and the run
    carries on as though the option had not been given
  - From: Gameplay Enhancements `->` New Game Modes
- [x] Add a `--chase-speed` option overruling the reasonable speed with one
  of six preset speeds, given as a whole number from 0 to 5
  - The presets are the moves the chaser makes in a second: `0` is one,
    rising by one to `5` at six, so the option names a speed rather than a
    delay a player has to reason about
  - A value under 0 resolves to 0 and one over 5 to 5, a decimal rounds to
    the nearest whole number, and a value that is not a number prints the
    same kind of notice `--chase-point` does and is otherwise ignored
  - It shares its whole validation shape with `--chase-point`, so whichever
    of the two is written first decides that shape for the other
  - From: Gameplay Enhancements `->` New Game Modes
