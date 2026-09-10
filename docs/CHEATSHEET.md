---
title: Cheat sheet
summary: >-
  The options, the keys, the markers, the codes and the public names, dense
  and without explanation. For a reader who has already read the rest.
---

## Options

| Option | Short | Default | Takes |
| --- | --- | --- | --- |
| `--width` | `-w` | preset | cells, minimum 2 |
| `--height` | `-H` | preset | cells, minimum 2 |
| `--difficulty` | `-d` | `normal` | `easy`, `normal`, `hard` |
| `--algorithm` | `-A` | `backtracker` | `backtracker`, `prim`, `division` |
| `--braid` | `-b` | `0` | `0` to `1`, bare flag means `1` |
| `--seed` | `-s` | random | a number or a word |
| `--collectibles` | `-c` | `0` | a count |
| `--mode` | `-m` | `plain` | `plain`, `chase` |
| `--chase-point` | | `55` | `20` to `90`, chase mode only |
| `--chase-speed` | | `2` | `0` to `5`, chase mode only |
| `--save` | `-o` | | a file, or `-` for standard output |
| `--load` | `-l` | | a file, or `-` for standard input |
| `--wall-char` | | `*` | one character, headerless files only |
| `--open-char` | | space | one character, headerless files only |
| `--format` | `-f` | `text` | `text`, `json` |
| `--solve` | `-S` | off | flag |
| `--animate` | `-a` | off | flag |
| `--quiet` | `-q` | off | flag |
| `--version` | `-V` | | flag |
| `--help` | `-h` | | flag |

Capital `-H` is height, `-S` solves, `-A` is the algorithm, `-o` saves,
`-m` is the mode. Lowercase `-h` is the help and `-s` is the seed.

Both chase options round a decimal to the nearest whole number, resolve a
number outside their range to the nearer end of it, and answer anything that
is not a number at all with a notice on standard error before carrying on
without it.

## Sizes

| Preset | Cells | Characters |
| --- | --- | --- |
| `easy` | 6 by 6 | 13 by 13 |
| `normal` | 9 by 11 | 19 by 23 |
| `hard` | 16 by 20 | 33 by 41 |

`W` by `H` cells renders as `W * 2 + 1` by `H * 2 + 1` characters. Sizes are
capped to the terminal unless the output is piped or redirected.

## Commands worth keeping

```bash
py_maze -d hard --seed winter            # a repeatable hard maze
py_maze -A prim -b 0.25 --solve          # open carving, a quarter braided
py_maze -c 6 --save maze.txt             # six pickups, kept in a file
py_maze --load maze.txt --solve          # play back and print the route
py_maze --load maze.txt --animate        # watch the search instead
py_maze -q -f json                       # a document, nothing else
py_maze --seed 2024 --save - | py_maze --load - --solve
py_maze --load drawn.txt --wall-char '#' --open-char '.' --quiet
py_maze --mode chase                     # something follows you halfway in
py_maze -m chase --chase-point 20 --chase-speed 5
```

## Modes

| Mode | Is | Options of its own |
| --- | --- | --- |
| `plain` | The walk from the entrance to the exit | |
| `chase` | The same walk, with something following you | `--chase-point`, `--chase-speed` |

`--chase-point` is a share of the maze, read off the solution measured as
the straight runs it is made of. `--chase-speed` is a preset: the moves the
chaser makes in a second, `0` for one a second rising to `5` for six. Being
caught ends the run the way the exit does, with an `Outcome` line on the
summary naming which of the two happened.

## Keys, in play

| Key | Does |
| --- | --- |
| Arrows, `W` `A` `S` `D` | Move up, left, down, right |
| `h` | Light the next step for a moment |
| `q` | Quit, with the summary so far |
| `Ctrl+C` | Interrupt, restoring the terminal |
| `y` / `n` | The "would you like to play" prompt, one keypress |

## Markers

| Drawn | Is | Constant |
| --- | --- | --- |
| `*` | Wall | `WALL_MARKER` |
| space | Open cell | `OPEN_MARKER` |
| `o` | The player | `PLAYER_MARKER` |
| `.` | Solution | `SOLUTION_MARKER` |
| `~` | Explored, under `--animate` | `VISITED_MARKER` |
| `?` | Frontier, and a hint | `FRONTIER_MARKER`, `HINT_MARKER` |
| `$` | Collectible | `COLLECTIBLE_MARKER` |
| `X` | The chaser, in chase mode | `CHASER_MARKER` |

## Status codes

| Code | Means |
| --- | --- |
| `0` | Finished |
| `2` | An option the command line will not take |
| `3` | Not a maze this build can read, or fewer than 3 characters wide |
| `4` | A file that could not be read, or written |
| `5` | No way from the entrance to the exit, when one was asked for |

On the package as `EXIT_OK`, `EXIT_USAGE`, `EXIT_SAVE_FILE`,
`EXIT_FILE_ERROR`, `EXIT_NO_WAY_THROUGH`.

## Save file

```
# py_maze save 1
# seed: 2024
* ***********
* *     *   *
...
```

Header first, comments start with `#`, the maze is drawn with `*`, the space
and `$`. `--format json` writes the same maze as a document keyed
`py_maze`, `seed`, `entrance`, `exit`, `collectibles`, `solution`, `grid`.
Specified in full on [the save file format](save-format.md).

## The package, in one screen

```python
import py_maze

grid = py_maze.MazeGenerator(width=6, height=6, seed=2024,
                             algorithm='prim').generate()
py_maze.braid_maze(grid, 0.25, py_maze.MazeGenerator(2, 2).random)

entrance = py_maze.find_entrance(grid)     # (x, y) in the top row
exit_cell = py_maze.find_exit(grid)        # (x, y) in the bottom row
path = py_maze.solve_maze(grid)            # a list of cells, or None

for line in py_maze.maze_lines(grid, py_maze.solution_overlay(path)):
    print(line)

py_maze.write_save('maze.txt', grid, seed=2024)
grid, collectibles, seed = py_maze.read_save('maze.txt')
```

A maze is a **grid**: rows of booleans, `True` for a wall, addressed
`grid[y][x]`, a cell always written `(x, y)`. Every public name is tabled on
[the library page](library.md).

| Want | Call |
| --- | --- |
| Carve | `MazeGenerator(...).generate()`, or `carve_prim(w, h, rng)` |
| Open the dead ends | `braid_maze(grid, share, rng)` |
| Scatter pickups | `place_collectibles(grid, count, rng)` |
| Solve | `solve_maze(grid, start, end)` |
| Watch it solve | `search_frames(grid, start, end)` |
| Measure a route | `solution_runs(path)`, `maze_progress(grid, cell, path)` |
| Play a mode | `game_mode(name)`, `plain_game(...)`, `chase_game(...)` |
| Draw | `maze_lines(grid, overlays)`, `print_maze(...)` |
| Write, read | `write_save(...)`, `read_save(...)`, `save_json(...)` |
| Parse text in hand | `parse_save(text, source, chars)` |
| Play it | `MazeGame(grid, ...)` |
