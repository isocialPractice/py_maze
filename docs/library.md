---
title: Using py_maze as a library
summary: >-
  Every part of the game is a function or a class you can call. The grid it
  all passes around, a worked example, and the whole public surface tabled.
---

Every part of the game is a function or a class that can be called from your
own code. `import py_maze` reaches every public name whichever module it
lives in, so nothing has to be imported out of a submodule:

```python
import py_maze

grid = py_maze.MazeGenerator(width=6, height=6, seed=2024).generate()
```

`msvcrt`, `tty` and `termios` are imported by `py_maze.keys` alone, so
every module that generates, solves, draws or saves a maze leaves the
terminal alone. Importing the package re-exports the game as well, so it
brings that one module with it, but no console is read or written at
import time, and a script that wants none of the terminal at all can
import `py_maze.generation` and `py_maze.solving` on their own.

## The Grid

One type is passed between every name below. A maze is a **grid**: a list of
rows, each row a list of booleans, `True` for a wall and `False` for a cell
the player can stand on. `grid[y][x]` addresses row `y`, column `x`, and a
cell is always the pair `(x, y)`.

A maze of `W` by `H` cells is carved into `H * 2 + 1` rows of `W * 2 + 1`
booleans, the extra line in each direction being the wall between one cell
and the next. Every row is the same length: a ragged grid is not a maze.

```python
>>> grid = py_maze.MazeGenerator(width=2, height=2, seed=1).generate()
>>> len(grid), len(grid[0])     # rows, then columns
(5, 5)
>>> grid[0][1]                  # the entrance, carved into the top row
False
```

The grid is built from nothing but lists and booleans, so it can be copied,
compared, pickled or written out with `json.dumps` as it stands. A maze
carved by `MazeGenerator` is the same object the solver walks, the renderer
draws and the save file writer writes, so nothing is converted between one
step and the next.

The entrance and the exit are not stored beside the grid, they are found in
it: `find_entrance` returns the open cell in the top row and `find_exit` the
one in the bottom row. That is why a maze read back from a file is used
exactly like a carved one, having nothing but its grid to go on.

## A Worked Example

Generating a maze, solving it and drawing the solution, with no game and no
keyboard involved:

```python
import py_maze

# carve a 6 by 6 maze from a seed, so the same maze comes back every run
grid = py_maze.MazeGenerator(width=6, height=6, seed=2024).generate()

# the entrance and the exit are read out of the grid, not stored beside it
entrance = py_maze.find_entrance(grid)
exit_cell = py_maze.find_exit(grid)

# breadth-first search from the entrance to the exit, shortest route first
path = py_maze.solve_maze(grid)
print("%s to %s in %d cells" % (entrance, exit_cell, len(path)))

# draw the maze with the solution laid over it, one string per row
for line in py_maze.maze_lines(grid, py_maze.solution_overlay(path)):
    print(line)
```

**Output:**

```
(1, 0) to (11, 12) in 35 cells
*.***********
*.*     *   *
*.*** * *** *
*...* *     *
***.* *******
*...*       *
*.*** ***** *
*...* *   * *
***.* * *** *
*...*   *...*
*.*******.*.*
*.........*.*
***********.*
```

That is the maze `python -m py_maze -d easy --seed 2024 --solve` prints,
since `easy` is 6 by 6 cells and the seed decides the rest.

`solve_maze` takes `start` and `end` cells too, each defaulting to the
entrance and the exit, so a route can be solved from wherever a player has
wandered to. It returns `None` when there is no way through rather than
raising, which is worth checking on a maze that came from a file:

```python
path = py_maze.solve_maze(grid)
if path is None:
    print("no way through")
```

## Carving and Braiding

`MazeGenerator` looks the algorithm up by name and holds the seed, but a
carver can be called on its own: a width, a height and a random number
generator in, a carved grid out.

```python
import random
import py_maze

# the names --algorithm reads from: ['backtracker', 'division', 'prim']
print(sorted(py_maze.ALGORITHMS))

# a carver on its own, and the same maze through the generator
grid = py_maze.carve_prim(8, 8, random.Random(7))

generator = py_maze.MazeGenerator(width=8, height=8, seed=7, algorithm='prim')
grid = generator.generate()
print(len(py_maze.solve_maze(grid)))    # 35 cells, the only way through

# open every dead end, so there is more than one way through
py_maze.braid_maze(grid, 1.0, generator.random)
print(len(py_maze.solve_maze(grid)))    # 31 cells, the shortest of them
```

`py_maze.carver(name)` returns the function a name stands for and raises
`ValueError` for a name no algorithm answers to, which is the same check
`MazeGenerator` makes when it is built. `braid_maze` modifies the grid it is
given and hands it back, so it can be wrapped around `generate()` or called
on a maze read out of a file.

## Collectibles and Save Files

`place_collectibles` picks the cells to scatter pickups over, and drawing
the places from the generator's own random numbers keeps them wherever the
seed put them. `write_save` and `read_save` round-trip a maze and its
pickups through a file:

```python
import py_maze

generator = py_maze.MazeGenerator(width=6, height=6, seed=2024)
grid = generator.generate()

# the same places --collectibles would pick for this seed
collectibles = py_maze.place_collectibles(grid, 4, generator.random)

py_maze.write_save('maze.txt', grid, collectibles, seed=generator.seed)
grid, collectibles, seed = py_maze.read_save('maze.txt')
```

`read_save` hands back the grid, the cells holding a collectible and the
seed the file records, the seed being `None` for a file that records none. A
file that is not a maze this build can read raises `SaveFileError`, a
subclass of `ValueError`, with a message naming what was wrong. The format
is specified in [the save file format](save-format.md).

## The Names

Every name below is re-exported from the package, so `py_maze.solve_maze`
and `py_maze.solving.solve_maze` are the same function. Each carries a
docstring, so `help(py_maze)` and `help(py_maze.solve_maze)` describe the
surface, and `py_maze.__all__` lists it in full.

**Reading a grid** (`py_maze.grid`)

| Name | What it does |
| --- | --- |
| `walled_grid(width, height)` | Build the solid block of wall a maze is carved out of |
| `find_entrance(grid)` | The `(x, y)` of the entrance, in the top row |
| `find_exit(grid)` | The `(x, y)` of the exit, in the bottom row |
| `open_cells(grid)` | Yield every cell the player can stand on, in reading order |
| `open_neighbors(grid, x, y)` | Yield the open cells one step from `(x, y)` |
| `open_ends(grid)` | Cut the entrance and the exit into a carved maze |
| `has_ends(grid)` | Whether a maze is wide enough to have an entrance and an exit |
| `MOVES` | The four steps a player, and the solver, can make |
| `MIN_DIMENSION` | The smallest maze with an interior path, 2 cells |
| `MIN_GRID_WIDTH` | The narrowest a maze can be drawn and still have both ends, 3 characters |

**Generating** (`py_maze.generation`)

| Name | What it does |
| --- | --- |
| `MazeGenerator(width, height, seed, algorithm)` | Carve a maze; `generate()` returns the grid |
| `braid_maze(grid, share, rng)` | Open a share of the dead ends, for more than one way through |
| `place_collectibles(grid, count, rng)` | The set of cells to scatter pickups over |
| `maze_seed(value)` | Read a seed from text, as `--seed` and a save file both do |
| `MAX_SEED` | The bound a seed is drawn from when none is given |

**Carving** (`py_maze.algorithms`)

Every carver is the same call, `carve(width, height, rng)`, returning a
carved grid with its entrance and exit already opened:

| Name | What it does |
| --- | --- |
| `carve_backtracker(width, height, rng)` | Recursive backtracking: one winding route, long dead ends |
| `carve_prim(width, height, rng)` | Randomized Prim's: a more open maze, short dead ends |
| `carve_division(width, height, rng)` | Recursive division: straight corridors and rooms |
| `carver(name)` | The carving function a name stands for, or `ValueError` |
| `ALGORITHMS` | The name `--algorithm` takes, mapped to the function that carves it |
| `ALGORITHM_NOTES` | What each one carves, in the words the help text uses |
| `DEFAULT_ALGORITHM` | The algorithm a bare run carves with, `backtracker` |

**Solving** (`py_maze.solving`)

| Name | What it does |
| --- | --- |
| `solve_maze(grid, start, end)` | The shortest route as a list of cells, or `None` |
| `search_frames(grid, start, end)` | Yield `(visited, frontier, path)`, one wave at a time |

**Drawing** (`py_maze.rendering`)

| Name | What it does |
| --- | --- |
| `maze_lines(grid, overlays)` | The maze as one string per row |
| `print_maze(grid, overlays, stream)` | The same, written between the `start` and `end` markers |
| `solution_overlay(path)` | The overlay that draws a solution over a maze |
| `collectible_overlay(collectibles)` | The overlay that draws pickups over a maze |
| `animate_search(grid, start, end, ...)` | Step the search across a terminal, frame by frame |
| `status_line(...)`, `summary_lines(...)` | The tallies shown during play and at the end |
| `format_duration(seconds)` | A length of time written the way a stopwatch would |
| `terminal_size()` | The screen the maze will be drawn in |
| `fit_to_terminal(...)`, `fit_dimension(...)` | Cap a maze to the space there is for it |
| `clear_screen`, `frame_text`, `ansi_enabled`, `can_encode` | The escape sequence machinery behind a redraw |

An overlay is a `(marker, cells)` pair, and `maze_lines` takes a sequence of
them running from the most important marker to the least: the first pair
holding a cell decides what is drawn there. The markers themselves are named
constants, so a caller need not repeat the characters: `WALL_MARKER`,
`OPEN_MARKER`, `PLAYER_MARKER`, `SOLUTION_MARKER`, `VISITED_MARKER`,
`FRONTIER_MARKER`, `HINT_MARKER` and `COLLECTIBLE_MARKER`.

**Save files** (`py_maze.saves`)

| Name | What it does |
| --- | --- |
| `write_save(path, grid, collectibles, seed, solution, form, stream)` | Write a maze to a file, in either form |
| `read_save(path, chars, stream)` | Read one back as `(grid, collectibles, seed)` |
| `save_lines(grid, collectibles, seed)` | The file's lines, without writing them |
| `save_json(grid, collectibles, seed, solution)` | The document it would write under `form='json'` |
| `parse_save(text, source, chars)` | The same read, from text already in hand |
| `parse_json_save(text, source)` | The same again for a document, which `parse_save` calls for one |
| `picture_chars(wall, open_cell)` | The `chars` map a picture with no header is read with |
| `SaveFileError` | Raised for a file this build cannot read |
| `SAVE_FORMAT`, `SAVE_HEADER`, `SAVE_CHARS` | The format number, its header line and the characters it allows |
| `FORMATS`, `TEXT_FORMAT`, `JSON_FORMAT`, `DEFAULT_FORMAT` | The two forms a maze is written in, and the one written unasked |
| `JSON_FORMAT_KEY` | The key a document carries the format number under |
| `STDIO_PATH` | The file name that means standard input or standard output, `-` |
| `STDIN_NAME` | What a message calls that stream, `<stdin>`, there being no file name |

`write_save` and `read_save` take the file name `-` for standard output and
standard input, or a `stream` of your own in its place, which is what makes
them testable without a pipe. `parse_save` reads a document, a picture under
its header or a picture with no header at all, and hands back the same three
things whichever it was:

```python
import py_maze

grid = py_maze.MazeGenerator(width=6, height=6, seed=2024).generate()

# the same maze as a document, with a route through it recorded
document = py_maze.save_json(grid, seed=2024,
                             solution=py_maze.solve_maze(grid))
grid, collectibles, seed = py_maze.parse_save(document)

# and a picture somebody else drew, on the terms it was drawn on
grid, _, _ = py_maze.parse_save("#.#\n#.#\n",
                                chars=py_maze.picture_chars('#', '.'))
```

The terminal half is public too: `MazeGame` plays a maze at the console,
`read_key` and `read_response` take single keypresses, and `build_parser`,
`build_maze` and `main` are the command line itself, along with the
`EXIT_OK`, `EXIT_USAGE`, `EXIT_SAVE_FILE`, `EXIT_FILE_ERROR` and
`EXIT_NO_WAY_THROUGH` codes it exits with. Those are the names that want a
terminal. Everything above runs without one.
