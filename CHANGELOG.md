# Changelog

All notable changes to py_maze are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
