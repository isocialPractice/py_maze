# TODO

Planned work for py_maze, a command-line maze generator and game. Items are
grouped into themed roadmap sections below; the next 1 to 5 items to work on
are listed under `## Current`. Completed items are archived automatically
into a `## Complete` section at the bottom of this file.

## Current

No items are queued for the next run: every roadmap section below is empty.

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
