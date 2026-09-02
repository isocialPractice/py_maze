---
title: Command-line options
summary: >-
  Every flag py_maze takes, the short form beside it, what it defaults to and
  what it changes.
---

| Option | Short | Default | Description |
| --- | --- | --- | --- |
| `--width` | `-w` | from the preset | Width of the maze in cells (minimum 2) |
| `--height` | `-H` | from the preset | Height of the maze in cells (minimum 2) |
| `--difficulty` | `-d` | `normal` | Preset maze size: `easy`, `normal` or `hard` |
| `--algorithm` | `-A` | `backtracker` | How the maze is carved: `backtracker`, `prim` or `division` |
| `--braid` | `-b` | `0` | Open this share of the dead ends, from `0` for none to `1` for all |
| `--seed` | `-s` | chosen at random | Seed for the maze generator |
| `--collectibles` | `-c` | `0` | Scatter this many pickups through the maze |
| `--save` | `-o` | | Write the maze to a file so it can be played again, or to standard output as `-` |
| `--load` | `-l` | | Play the maze saved in a file instead of generating one, or in standard input as `-` |
| `--wall-char` | | `*` | Character a wall is drawn with in a loaded file that carries no py_maze header |
| `--open-char` | | space | Character an open cell is drawn with in the same |
| `--format` | `-f` | `text` | How the maze is written: `text`, the picture, or `json`, a document |
| `--solve` | `-S` | off | Print the solution path overlaid on the maze |
| `--animate` | `-a` | off | Step through the solver's search on screen |
| `--quiet` | `-q` | off | Print the maze and nothing else: no banner, no seed line, no prompt |
| `--version` | `-V` | | Show the installed version and exit |
| `--help` | `-h` | | Show usage and exit |

Note that the short flag for height is a capital `-H`. Lowercase `-h` is
reserved by argparse for `--help`. The same goes for `-S` and `-s`: capital
`-S` solves the maze, lowercase `-s` seeds it, and capital `-A` picks the
algorithm. The short flag for `--save` is `-o`, as in an output file, since
`-s` is already the seed. `--wall-char` and `--open-char` have no short
flags: they are read by a loader rather than typed at a prompt.

A maze is drawn with walls between cells, so a maze of `W` by `H` cells
renders as `W * 2 + 1` characters wide and `H * 2 + 1` characters tall.

Values below 2 cells cannot produce a maze with an interior path, so they
are rejected:

```bash
python -m py_maze -w 1
```

**Output:**

```
usage: py_maze [-h] [--width WIDTH] [--height HEIGHT]
               [--difficulty {easy,normal,hard}]
               [--algorithm {backtracker,prim,division}] [--braid [SHARE]]
               [--seed SEED] [--collectibles COUNT] [--save FILE]
               [--load FILE] [--wall-char CHAR] [--open-char CHAR]
               [--format {text,json}] [--solve] [--animate] [--quiet]
               [--version]
py_maze: error: argument --width/-w: maze dimensions must be at least 2 cells, got 1
```

## Difficulty Presets

Each preset is just a maze size, so picking one is a shorter way of passing
`--width` and `--height`:

| Preset | Size in cells | Rendered size |
| --- | --- | --- |
| `easy` | 6 by 6 | 13 by 13 characters |
| `normal` | 9 by 11 | 19 by 23 characters |
| `hard` | 16 by 20 | 33 by 41 characters |

```bash
python -m py_maze --difficulty hard
```

`normal` is the size py_maze has always generated, so a run with no options
is unchanged. Either dimension can still be set by hand, and doing so
overrides that half of the preset:

```bash
# a hard maze, but only 8 cells tall
python -m py_maze -d hard -H 8
```

## Fitting the Terminal

A maze larger than the screen scrolls out of view and cannot be played, so
sizes are measured against the terminal before the maze is generated. When a
requested size does not fit, it is capped to the largest one that does and a
warning explains the change:

```bash
python -m py_maze -w 60 -H 60
```

**Output (on an 80 by 24 terminal):**

```
warning: --width 60 needs 121 columns but only 80 are available; using 39
warning: --height 60 needs 121 rows but only 19 are available; using 9
```

Five rows are reserved for the `start` and `end` markers, the status line, the
spacer and the controls line, which is why the height allowance is smaller
than the terminal is tall.

Two limits apply to the capping:

- Mazes are never capped below the 2 cell minimum. If the terminal cannot
  hold even the smallest maze, the requested size is generated as asked and
  the warning says the maze will not fit on screen.
- Nothing is capped when the output is piped or redirected, since there is no
  terminal to fit. Writing a large maze to a file works exactly as before:

```bash
python -m py_maze -w 60 -H 60 > maze.txt
```

A difficulty preset is capped the same way, so `--difficulty hard` on a small
terminal generates the largest hard-ish maze that fits.

## Status codes

A run that could not do what it was asked exits with a code naming what went
wrong. Those are tabled under
[Scripting py_maze](scripting.md#status-codes), along with everything else a
script needs.
