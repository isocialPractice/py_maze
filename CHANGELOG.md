# Changelog

All notable changes to py_maze are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.2] - 2026-08-27

### Changed

- The supported Python versions are the ones that are still supported
  upstream. `requires-python` was `>=3.6`, a release that reached end of life
  in December 2021, and the classifiers stopped at 3.11. The floor is now
  `>=3.10` and the classifiers list 3.10, 3.11, 3.12 and 3.13, every one of
  which the suite is run on. Nothing in the package changes: it is written
  against the standard library alone and uses no syntax newer than the floor
  it declared before.

### Added

- A `LICENSE` file carrying the MIT text that `README.md` and
  `pyproject.toml` have both declared since the first release, so the
  declaration rests on something.
- A GitHub Actions workflow, `.github/workflows/tests.yml`, running
  `python -m unittest discover` on Windows, Linux and macOS across every
  supported Python version on each push and pull request. The cross-platform
  promise is checked now rather than asserted, and the matrix is the
  classifier list, so a version the manifest promises is a version that is
  tested. Nothing is installed to run it: the suite is standard library only.
- `CONTRIBUTING.md`, covering the test command, the comment and docstring
  convention (docstrings on public names, the existing comment style on
  internal helpers), how the version is single-sourced from `__version__`,
  and the grid as the type new code is expected to read and write.
- `docs/save-format.md`, specifying the save file so another tool can write
  one py_maze will load: the header and what it is for, the seed comment, the
  three markers and the on-screen markers that are not part of the format,
  the ragged-line rule and the two ways whitespace catches a writer out, the
  entrance and exit convention, every refusal the reader makes with the
  message it gives, and the two things it deliberately does not refuse.
- Tests covering all of the above: that no classifier falls below
  `requires-python` and the list runs without a gap, that the CI matrix is
  that same list, that the licence the manifest declares is the text the
  repository carries, that the contributing guide gives the command the
  workflow runs, and that the save format document agrees with the reader on
  every marker, every refusal message and the example file it draws.

## [2.0.1] - 2026-08-26

### Fixed

- The play screen no longer flickers on every move. `render` wiped the whole
  terminal and then wrote the maze, the status line and the key legend a line
  at a time, so the screen stood empty between the clear and the last row.
  The cursor is now put back at the top left and the whole frame goes out in
  a single write, over the frame it replaces. Only the first frame of a game
  wipes the screen, to clear what the run printed before play started.
- The screen is cleared with an ANSI escape sequence rather than
  `os.system('cls')` or `os.system('clear')`, so `--animate` no longer starts
  a shell for every frame it draws. Windows consoles are switched to virtual
  terminal processing once per run rather than once per frame. Where the
  escapes are not honoured, including under `TERM=dumb`, the shell call is
  still there as the fallback and the behaviour is exactly what it was.
- The "would you like to play" prompt reads a single keypress on POSIX, as it
  already did on Windows. It set no raw mode, so `sys.stdin.read(1)` waited
  for Enter and left the rest of the line in the buffer, contrary to what the
  function said it did. Ctrl+C at the prompt raises a `KeyboardInterrupt` on
  both platforms now, and an answer piped in rather than typed is read
  straight from the pipe, there being no terminal mode to set.
- The win banner drops the party poppers when the output encoding cannot
  carry them, so a console on a legacy code page shows the congratulations
  instead of raising `UnicodeEncodeError` in place of it.
- `MazeGenerator.generate()` carves from a fresh grid every time. A second
  call on the same generator carved into the maze the first call had already
  made, leaving a grid with more ways through than a maze has. A seeded
  generator also goes back to the same random numbers, so it makes the same
  maze, and scatters the same collectibles, however many times it is asked.

### Added

- `py_maze.ansi_enabled`, `py_maze.clear_screen` and `py_maze.frame_text` for
  drawing over a terminal: whether escape sequences are honoured, wiping the
  screen with one, and joining the lines of a screen into the single string
  that draws it. `ANSI_CLEAR`, `ANSI_HOME` and `ANSI_CLEAR_LINE` are the
  sequences themselves.
- `py_maze.can_encode`, reporting whether a stream's encoding can carry a
  piece of text, and `py_maze.win_banner`, which uses it to choose between
  `WIN_BANNER` and `PLAIN_WIN_BANNER`.
- `py_maze.walled_grid`, the solid block of wall a maze is carved out of, and
  `MazeGame.frame`, the play screen as a list of lines. `CONTROLS_LINE` is
  the key legend that frame ends with.
- Tests covering all of the above: that a frame is one write and homes the
  cursor, that only the first frame wipes the screen, that no shell is
  spawned for an animated search, that the prompt takes one keypress and
  restores the terminal, that a legacy console is given the plain banner, and
  that a generator asked twice hands back the same maze.

### Changed

- `clear_screen`, `MazeGame.clear_screen` and `MazeGame.render` take an
  optional stream, defaulting to standard output as before. `animate_search`
  clears the stream it was given rather than standard output.

## [2.0.0] - 2026-08-25

### Added

- `python -m py_maze`, so a source checkout runs the same way an installed
  copy does. `py_maze.bat` and `py_maze.sh` now put their own folder on
  `PYTHONPATH` and run the module, so neither needs the game installed and
  neither depends on the working directory.
- An `__all__` and a docstring on every module and every public function and
  class, so `help(py_maze)`, `help(py_maze.solve_maze)` and any generated
  reference describe the surface rather than an empty signature. Internal
  helpers keep the existing comment style, which is what marks them internal.
- Round-trip tests pinning the grid as the interchange type: that it is a
  list of rows of booleans with `True` for a wall, that a maze survives
  being drawn and read back, that saving what was loaded reproduces the file
  it came from, and that a loaded maze solves and draws exactly as the
  generated one did. Tests also pin the package surface, the module entry
  point and the fact that the generator and the solver pull in no terminal
  machinery.

### Changed

- **BREAKING**: `py_maze.py` is now a `py_maze/` package, with the grid
  helpers, generation, solving, rendering, save files, keyboard input, the
  game and the command line each in their own module. `python py_maze.py`
  no longer works and becomes `python -m py_maze`. Nothing else about the
  command changes: every option, every message and the save file format are
  as they were, and `import py_maze` still reaches every public name,
  because `__init__.py` re-exports all of them.
- The `msvcrt`, `tty` and `termios` imports moved out of the import path and
  into `py_maze.keys`, the one module that reads a keypress. Importing the
  generator, the solver, the renderer or the save files no longer pulls in
  terminal machinery, so a program that only wants a maze is not handed a
  terminal to go with it. `MazeGame.get_key`, `get_key_windows` and
  `get_key_posix` are unchanged and now delegate to that module.
- `__version__` lives in `py_maze/version.py` and is re-exported as
  `py_maze.__version__`, so the manifest, the `--version` flag and the
  changelog still read one string. A module of its own means the package and
  the command line can both read it without one importing the other.
- The usage line and the argument errors now name the program `py_maze`
  rather than the file argparse happened to be started from, so they read
  the same however the game was launched.
- The console script points at `py_maze.cli:main` and the manifest ships a
  package rather than a single module. Installing with `pip install -e .`
  and running `py_maze` are unchanged.

### Removed

- `py_maze.py`. The package replaces it; leaving both in place would have
  made which one runs depend on the import machinery.

## [1.2.0] - 2026-08-21

### Added

- A timer and a move counter. Both run under the maze while the game is
  played, on a status line beside the collectible tally, and both are
  summarized on the win screen. The clock starts at the first render and
  stops the moment the maze is won, so the summary reads the same however
  long it is left on screen, and it is a monotonic clock, so an adjustment to
  the system time mid-game cannot run it backwards. Only steps that moved the
  player are counted, so walking into a wall costs nothing but the time it
  took. Quitting with `q` prints the same summary for the game so far.
- A `--collectibles`/`-c` option scattering that many `$` markers through the
  maze for the player to pick up, tallied as "Collected: 2 of 3" in the
  end-of-game summary. Places are drawn from the seeded generator, so the same
  seed puts them in the same cells every run, and the entrance and the exit
  are left clear so nothing is handed over before the first step or after the
  last. Asking for more than the maze has room for fills every cell there is.
  None are scattered unless the option is given.
- A `--save`/`-o` option writing the maze, and any collectibles, to a file,
  and a `--load`/`-l` option playing a maze back from one. A save file is the
  maze exactly as it is drawn, under a short header recording the format and
  the seed, so it can be read, edited by hand and compared like any other
  text. A loaded maze comes from the file as it was saved, so the size, seed
  and collectible options do not apply to it, and a file that is not a maze
  this build can read is refused with a message naming the line and what was
  wrong with it.

### Changed

- The maze render now reserves five rows around the maze rather than four,
  the new one being the status line. The terminal cap measures against the
  same number, so a maze is capped one row earlier than it was.
- Solved mazes draw collectibles over the solution path, so a maze printed
  with `--solve` still shows what there is to pick up along the way.

## [1.1.0] - 2026-08-20

### Added

- A `--seed`/`-s` option that fixes the maze generator's random numbers, so
  the same seed always produces the same maze. A seed is now chosen for every
  run and printed under the maze, so a maze worth keeping can be generated
  again without having planned ahead. Seeds may be whole numbers or text.
- A `--difficulty`/`-d` option choosing a preset maze size: easy (6 by 6),
  normal (9 by 11) or hard (16 by 20). The normal preset is the size the game
  has always generated, so leaving the option out changes nothing, and
  `--width` and `--height` still override either dimension of a preset.
- A `--solve`/`-S` flag that prints the shortest way through the maze,
  overlaid on it as a trail of `.` markers. The solver is a breadth-first
  search, so the route it draws is always the shortest one.
- A `--animate`/`-a` flag that steps the solver's search across the screen
  one wave at a time, marking the frontier with `?` and explored cells with
  `~` before the solved maze is printed. Piped or redirected output has no
  screen to animate over, so the maze is solved without the frames.
- An in-game hint: pressing `h` lights up the next step along the solution
  for a moment, then redraws the maze without it. The path is solved from
  wherever the player is standing, so a hint still points the way after a
  wrong turn. The controls line names the key.

### Changed

- `--width` and `--height` now default to "not given" rather than to 9 and
  11, and the difficulty preset supplies whichever of the two is left out.
  The maze generated by a bare `py_maze` is unchanged.
- The maze is drawn by one set of helpers shared by the printed maze, the
  in-game render, the solved maze and the animation, so every overlay marker
  lands the same way in all four.
- The game finds its entrance and exit through the same helpers the solver
  uses, instead of scanning the grid itself.

## [1.0.2] - 2026-08-19

### Added

- A `--version`/`-V` flag that prints the package version and exits. The
  number is read from the module, so the flag, the manifest and an installed
  copy can never disagree.
- Maze sizes are now measured against the terminal before generating. A maze
  wider or taller than the screen is capped to what fits, with a warning
  naming the option, the space it needed and the size being used instead.
  When the terminal cannot hold even the smallest maze, the warning says so
  rather than shrinking below the two cell minimum.
- `pyproject.toml`, declaring the package metadata and reading the version
  from `py_maze.__version__` so it is recorded in exactly one place.
- A `.gitignore` covering Python artifacts (`__pycache__/`, `*.egg-info/`,
  `build/`, `dist/`), test and coverage output, virtual environments, and
  editor and operating system noise.
- Tests for the POSIX keyboard branch, the interrupt handling, the terminal
  fitting helpers and the `--version` flag. The POSIX branch is driven
  through a fake terminal, so the suite still runs on any platform.

### Changed

- Packaging moved from `setup.py` to `pyproject.toml`. Installing with
  `pip install -e .` is unchanged, but building from source now needs
  setuptools 61 or newer.
- The placeholder author metadata left in `setup.py` has been replaced with
  the real project details, and the manifest now records the project's home
  page, repository, changelog and issue tracker.
- Quitting at the "would you like to play" prompt and interrupting the game
  now print the same parting message, from a single constant.

### Fixed

- Ctrl+C during gameplay no longer ends in a traceback over a terminal still
  in raw mode. Raw mode suppresses the usual interrupt signal, so the key
  arrived as an ordinary byte and was ignored on POSIX and swallowed by
  `getch` on Windows. Both key readers now restore the terminal and raise
  the interrupt, and the game loop catches it and exits with a message.

## [1.0.1] - 2026-08-18

### Added

- Unit test suite (`test_py_maze.py`) covering maze generation (dimensions,
  sealed borders, entrance and exit placement, solvability across several
  sizes and seeds) and gameplay (start and end detection, movement, wall
  and boundary collision, win detection), plus the command-line parser and
  the Windows keyboard branch. Run it with `python -m unittest discover`.
- This changelog, recording the 1.0.0 release as the baseline entry.
- A "Command-Line Options" section in the README listing every flag, its
  short form, default value and minimum.
- A minimum size of 2 cells for `--width` and `--height`. Smaller values are
  rejected with a message naming the option and the value that was given,
  rather than producing a degenerate maze.

### Changed

- Windows keyboard input now waits for a keypress by polling with a short
  sleep between checks, instead of spinning in a loop that consumed a full
  CPU core while the game sat idle.
- The "Generating maze..." banner now prints after arguments are parsed, so
  `--help` output and argument errors are no longer preceded by it.
- The cross-platform `get_key` method now delegates to `get_key_windows` and
  `get_key_posix`, so each platform's input path can be tested directly.

### Fixed

- The README usage example passed `-h` for height, which argparse reserves
  for `--help`, so the documented command failed. The example and the new
  options table use the real short flag, `-H`.
- Arrow keys that Windows reports with the `\x00` extended-key prefix are
  now recognized. Previously only the `\xe0` prefix was handled, so on
  keyboards and consoles that send `\x00` the arrow keys did nothing.

## [1.0.0] - 2025-12-25

### Added

- Random maze generation using the recursive backtracking algorithm, so
  every generated maze is solvable and has exactly one path between any two
  points.
- Interactive gameplay: move with the arrow keys or WASD, from the entrance
  at the top of the maze to the exit at the bottom, and quit with `q`.
- Cross-platform keyboard handling for Windows, Linux and macOS, using only
  the standard library.
- `--width`/`-w` and `--height`/`-H` options for setting the maze size in
  cells, defaulting to 9 by 11.
- Packaging via `setup.py`, installing a `py_maze` console script.
- `py_maze.bat` and `py_maze.sh` launcher scripts.
