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
| `solution_runs(path)` | The straight runs a solution is made of, as their lengths |
| `maze_progress(grid, cell, path)` | How far along the solution a cell stands, from `0` to `1`, or `None` |
| `UNSEARCHED` | The `path` of a caller that has not looked for a route |

A solution is measured as the straight runs it is made of rather than as a
count of cells, which is what lets a share of it be pointed at. A route of
four runs of 4, 2, 5 and 3 totals 14 steps, so 55% of it is 7.7, which falls
in the third run:

```python
>>> grid = py_maze.MazeGenerator(width=6, height=6, seed=2024).generate()
>>> path = py_maze.solve_maze(grid)
>>> sum(py_maze.solution_runs(path)) == len(path) - 1
True
>>> py_maze.maze_progress(grid, path[0]), py_maze.maze_progress(grid, path[-1])
(0.0, 1.0)
```

Every step belongs to exactly one run, so the lengths always sum to the steps
the whole route takes. A cell that is not on the solution has no share of it
and `maze_progress` answers `None`, which is also what it answers for a maze
with no way through.

**How a `path` is read.** The calls that search for one when they are not
handed one - `maze_progress` here, `maze_stats` under **Measuring a maze**
below and `Chaser.chasing` under **Playing, and the Modes** - read it the
same three ways, so a caller says what it is holding once and is believed
by all of them:

- A route: the caller searched and found the way through, and it is measured
  as it stands. Pass it when measuring cell after cell against the one maze
  and it is not solved again for each.
- `None`: the caller searched and there is no way through. That is the answer
  the search came back with rather than the absence of a search, so it is
  taken at its word rather than run again.
- Left out, or `UNSEARCHED`: the caller has not looked, and the maze is solved
  here.

That third reading is why the default is not `None`: a run forwarding a route
it may or may not be holding passes `UNSEARCHED` and pays for one search,
while a run that already knows there is no way through pays for none. The
calls that only measure or draw a route handed to them - `solution_runs`,
`solution_overlay` and `MazeGenerator.to_string` - never search, so they read
`None` as nothing to work on and the sentinel is not theirs to take.

```python
>>> grid = py_maze.MazeGenerator(width=6, height=6, seed=2024).generate()
>>> path = py_maze.solve_maze(grid)
>>> py_maze.maze_progress(grid, path[-1], py_maze.UNSEARCHED)
1.0
>>> py_maze.maze_progress(grid, path[-1], None) is None
True
```

**Measuring a maze** (`py_maze.analysis`)

| Name | What it does |
| --- | --- |
| `maze_stats(grid, path, dead_ends_before)` | Every measurement below as one dictionary |
| `dead_ends(grid)` | Yield each cell inside the maze with one way in and no way on |
| `junctions(grid)` | Yield each cell where three or more ways meet |
| `longest_corridor(grid)` | Cells in the longest straight run, across a row or down a column |
| `solution_share(path, open_count)` | The share of the open cells a route stands on, from 0 to 1 |
| `difficulty_score(open_count, junctions_count, path)` | How hard the maze reads, out of 100 |
| `DIFFICULTY_PARTS` | The three shares that score adds up, by name |
| `JUNCTION_CEILING` | The junctions per open cell at which its decisions part is full |

Nothing here changes the maze: a measurement is taken from the grid as it
stands, so a carved maze and one read out of a file are measured the same
way. `maze_stats` is the whole of it in one call, and the keys are what
`--stats` prints:

```python
>>> grid = py_maze.MazeGenerator(width=6, height=6, seed=2024).generate()
>>> stats = py_maze.maze_stats(grid)
>>> stats['cells'], stats['open']
(169, 73)
>>> stats['dead_ends'] == sum(1 for _ in py_maze.dead_ends(grid))
True
>>> sorted(stats)
['cells', 'dead_ends', 'dead_ends_opened', 'difficulty', 'junctions', 'longest_corridor', 'open', 'solution', 'solution_share']
```

`cells` counts every position of the grid and `open` the ones the player can
stand on, so the second is a share of the first. `solution` is the steps the
shortest route takes, measured as `solution_runs` measures them, and `None`
for a maze with no way through.

`solution_share` is how much of the maze that route stands on, counted in
cells because the maze it is a share *of* is counted in cells. It is the one
measurement held as a fraction rather than a tally, and the printed line
rounds it to a whole percent:

```python
>>> grid = py_maze.MazeGenerator(width=6, height=6, seed=2024).generate()
>>> path = py_maze.solve_maze(grid)
>>> py_maze.solution_share(path, 73) == len(path) / 73
True
>>> round(py_maze.maze_stats(grid)['solution_share'], 3)
0.479
```

`difficulty` reads a score out of the measurements around it, and it is
published as what it is made of rather than as a number to trust.
`DIFFICULTY_PARTS` names the three shares it averages, each worth the same as
the other two, and [Reading a maze](analysis.html) sets out what each one is:

```python
>>> py_maze.DIFFICULTY_PARTS
('wrong turns', 'decisions', 'corners')
>>> grid = py_maze.MazeGenerator(width=6, height=6, seed=2024).generate()
>>> py_maze.difficulty_score(73, 3, py_maze.solve_maze(grid))
36
>>> py_maze.difficulty_score(73, 3, None) is None
True
```

`dead_ends_opened` is the one measurement a grid cannot be asked for. A
braided maze looks exactly like a maze that was carved that way, so only the
caller that braided knows what it opened, and it hands over the count it took
beforehand:

```python
>>> import random
>>> grid = py_maze.MazeGenerator(width=6, height=6, seed=2024).generate()
>>> before = sum(1 for _ in py_maze.dead_ends(grid))
>>> _ = py_maze.braid_maze(grid, 1.0, random.Random(1))
>>> py_maze.maze_stats(grid, dead_ends_before=before)['dead_ends_opened']
3
>>> py_maze.maze_stats(grid)['dead_ends_opened'] is None
True
```

The solution is the one measurement that has to be searched for, and `path` is
read here exactly as **Solving** above reads it - `UNSEARCHED` is re-exported
from `py_maze.analysis` for the callers that import it there - so a caller that
has already searched is believed by this reader too:

```python
>>> grid = py_maze.MazeGenerator(width=6, height=6, seed=2024).generate()
>>> py_maze.maze_stats(grid, py_maze.UNSEARCHED)['solution']
34
>>> py_maze.maze_stats(grid, None)['solution'] is None
True
```

`dead_ends` is the reader `braid_maze` opens a share of, so what a braid acts
on and what `--stats` counts are the one reading. Both it and `junctions`
yield in reading order, left to right and then down the rows.

**Drawing** (`py_maze.rendering`)

| Name | What it does |
| --- | --- |
| `maze_lines(grid, overlays)` | The maze as one string per row |
| `print_maze(grid, overlays, stream)` | The same, written between the `start` and `end` markers |
| `solution_overlay(path)` | The overlay that draws a solution over a maze |
| `collectible_overlay(collectibles)` | The overlay that draws pickups over a maze |
| `quest_overlay(doors, boxes, guide)` | The overlays that draw a quest's shut doors, its boxes and its guide |
| `animate_search(grid, start, end, ...)` | Step the search across a terminal, frame by frame |
| `status_line(...)`, `summary_lines(...)` | The tallies shown during play and at the end |
| `stats_lines(stats)` | What `--stats` prints under a maze, in the status line's style |
| `format_duration(seconds)` | A length of time written the way a stopwatch would |
| `terminal_size()` | The screen the maze will be drawn in |
| `fit_to_terminal(...)`, `fit_dimension(...)` | Cap a maze to the space there is for it, the rows the play screen's foot occupies included |
| `line_fills_row(line, size)` | Whether a line ends flush with the last column, where clearing to the end of the row would erase it |
| `fit_frame(lines, size, focus, reserve)` | Cut a play screen to the rows the terminal has, around a row to keep and any kept back |
| `cut_marker(marker, rows, where)` | An edge marker that names the maze rows the window stops short of |
| `wrap_on_spaces(text, size)` | Pad a line so the console breaks it at a space rather than inside a word |
| `wipe_rows(first, last, size)` | Clear a run of rows a shorter frame gave up, stopping at the bottom of the screen |
| `frame_text(lines, home, stream, size)` | A whole frame as the one string that draws it |
| `frame_diff(previous, current, whole, size)` | The same for the lines that changed, or every row when `whole` |
| `frame_wraps(lines, size)` | Whether a frame runs past the terminal's last column |
| `frame_height(lines, size)` | The screen rows a frame occupies, counting a wrapped line as the rows it is carried onto |
| `can_display(text, stream)` | Whether a destination draws the text as written, the encoding and the screen buffer cell both asked |
| `clear_screen`, `ansi_enabled`, `can_encode` | The rest of the escape sequence machinery behind a redraw |

An overlay is a `(marker, cells)` pair, and `maze_lines` takes a sequence of
them running from the most important marker to the least: the first pair
holding a cell decides what is drawn there. The markers themselves are named
constants, so a caller need not repeat the characters: `WALL_MARKER`,
`OPEN_MARKER`, `PLAYER_MARKER`, `SOLUTION_MARKER`, `VISITED_MARKER`,
`FRONTIER_MARKER`, `HINT_MARKER`, `COLLECTIBLE_MARKER`, `CHASER_MARKER`,
`DOOR_MARKER`, `BOX_MARKER` and `GUIDE_MARKER`.

The two labels around the maze are not overlays. `start` and `end` name the
ends of the maze, and `fit_frame` draws a window onto the maze whenever the
console cannot hold all of it, so an edge the window stops short of is named
with the rows past it instead: `cut_marker('end', 3, CUT_BELOW)` reads
`end 3 rows below`. `CUT_FORMAT` is the form it is written in, and
`CUT_ABOVE` and `CUT_BELOW` are the two sides.

**Save files** (`py_maze.saves`)

| Name | What it does |
| --- | --- |
| `write_save(path, grid, collectibles, seed, solution, form, stream, stats, quest)` | Write a maze to a file, in either form |
| `read_save(path, chars, stream)` | Read one back as `(grid, collectibles, seed)` |
| `save_lines(grid, collectibles, seed)` | The file's lines, without writing them |
| `save_json(grid, collectibles, seed, solution, stats, quest)` | The document it would write under `form='json'` |
| `SavedMaze(grid, collectibles, seed, quest)` | What a reader hands back: that triple, with a document's quest beside it |
| `parse_save(text, source, chars)` | The same read, from text already in hand |
| `parse_json_save(text, source)` | The same again for a document, which `parse_save` calls for one |
| `picture_chars(wall, open_cell)` | The `chars` map a picture with no header is read with |
| `SaveFileError` | Raised for a file this build cannot read |
| `SAVE_FORMAT`, `SAVE_HEADER`, `SAVE_CHARS` | The format number, its header line and the characters it allows |
| `FORMATS`, `TEXT_FORMAT`, `JSON_FORMAT`, `DEFAULT_FORMAT` | The two forms a maze is written in, and the one written unasked |
| `JSON_FORMAT_KEY` | The key a document carries the format number under |
| `JSON_QUEST_KEY` | The key a document carries a quest's doors and boxes under |
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

What comes back is a `SavedMaze`: that same triple, with the quest a
document carried on its `quest` attribute. A picture can draw a door and
cannot say which item opens it, so only a document ever writes one and only
a document ever reads one back:

```python
>>> import random
>>> import py_maze
>>> grid = py_maze.MazeGenerator(width=6, height=6, seed=2024).generate()
>>> quest = py_maze.place_quest(grid, 2, random.Random(2024))
>>> py_maze.parse_save(py_maze.save_json(grid, quest=quest)).quest.doors
{(1, 7): 1, (5, 11): 2}
>>> py_maze.parse_save('\n'.join(py_maze.save_lines(grid))).quest is None
True
```

## Playing, and the Modes

A mode is the game that is already there played differently: the same grid,
the same solver, the same renderer and the same key loop. `MODES` maps the
name `--mode` takes to the function that builds the game, exactly as
`ALGORITHMS` maps a carving name to its carver, so calling one is the whole
of setting a mode up:

| Name | What it does |
| --- | --- |
| `MODES` | The name `--mode` takes, mapped to the function that builds that game |
| `MODE_NOTES` | What each one plays like, in the words the help text uses |
| `MODE_OPTIONS` | The options belonging to each mode, for a mode that has any |
| `MODE_CONTENT` | What each mode lays into the maze itself, for the modes that lay anything |
| `MODE_CONTROLS` | The controls line each mode prints, for the modes that print another one |
| `MODE_ITEMS` | Where each mode reads its item count from, for the modes that fill an inventory |
| `DEFAULT_MODE`, `PLAIN_MODE`, `CHASE_MODE`, `QUEST_MODE` | The mode a bare run plays, and the names of the three there are |
| `game_mode(name)` | The building function a name stands for, or `ValueError` |
| `mode_content(name, grid, ...)` | Lay whatever that mode puts in the maze, and `None` for a mode that puts nothing |
| `mode_controls(name)` | The controls line that mode prints, and `CONTROLS_LINE` for a mode adding no key of its own |
| `mode_status(name, collectibles, ...)` | The running tally that mode's first frame will draw, which is what a maze is carved against |
| `plain_game(grid, collectibles, ...)` | The walk from the entrance to the exit |
| `chase_game(grid, collectibles, chase_point, chase_speed)` | The same walk, with a chaser behind it |
| `quest_game(grid, collectibles, content, quest_stages)` | The same walk, with the way on shut until what opens it is found |
| `quest_content(grid, rng, collectibles, quest_stages)` | The chain quest mode lays into a maze before it is played |

Every mode is handed every mode setting and reads the ones that belong to
it, which is why a setting for a mode you are not playing is ignored rather
than refused.

The chaser itself is a cell and a clock. Where it steps comes from the same
breadth-first search everything else uses, solved from the chaser to the
player, so it never walks into a wall and needs no second algorithm:

| Name | What it does |
| --- | --- |
| `Chaser(cell, point, speed)` | An antagonist waiting on a cell until the chase begins |
| `Chaser.chasing(now, grid, cell, path)` | Start it if the player has walked far enough in, and say whether it is running |
| `Chaser.advance(now, grid, target)` | Take every step the clock says it is owed, and report how many of them moved it |
| `Chaser.catches(cell)` | Whether it is standing where the player is |
| `CHASE_SPEEDS` | Each preset speed, as the moves it makes in a second |
| `MIN_CHASE_POINT`, `MAX_CHASE_POINT`, `DEFAULT_CHASE_POINT` | The range a chase point is held inside, and the reasonable point |
| `MIN_CHASE_SPEED`, `MAX_CHASE_SPEED`, `DEFAULT_CHASE_SPEED` | The presets `--chase-speed` takes, and the reasonable speed |
| `MAX_CHASE_CATCH_UP` | The most moves one advance reaches for after a stall |
| `chase_setting(number, low, high)` | Round a chase option's number and hold it inside its range, whatever number it is given |

```python
import py_maze

grid = py_maze.MazeGenerator(width=9, height=11, seed=2024).generate()
game = py_maze.chase_game(grid, chase_point=70, chase_speed=4)
game.play()
```

A chase setting is read the same way wherever it comes from. `chase_setting`
rounds to the nearest whole number and holds the result inside the range, and
`Chaser` reads both its `point` and its `speed` with it, so a front end
reading its numbers out of a file is handed the `int` the table promises
rather than an exception: a value past either end resolves to that end, an
infinity to the end it runs past, and a `nan`, which names no place on the
range in either direction, to the bottom of it. `--chase-point` and
`--chase-speed` never reach that far, naming a value they cannot read in a
notice and carrying on without it.

The range is the chaser's rather than the option's, which is what makes
`chase_game(grid, chase_point=0)` a game that begins at `MIN_CHASE_POINT`
instead of one already caught: the chaser waits on the entrance the player
starts on, so a point of nought would have the chase begun and won before the
first keypress.

`Chaser.advance` reports the steps that moved the chaser rather than the
moves the clock owed it. The two differ when there is nowhere to step - a
chaser standing on the player it has caught - and `MAX_CHASE_CATCH_UP` bounds
the moves reached for, so a stall over a chaser that cannot move is not a
walk through everything the stall passed over.

Some of a mode is in the maze rather than in the game. Quest mode's doors
and boxes are laid into the grid before a word is drawn, written into a JSON
document beside the collectibles and read back out of one, so `MODE_CONTENT`
is where a mode says what it puts there and `mode_content` is what lays it.

`mode_controls` and `mode_status` answer the other two questions asked
before there is a game: which controls line the mode will print, and what
its first tally will say. Those are the two lines of the play screen's foot
that can be longer than the console is wide, so how many rows they occupy
decides how tall a maze the console can show whole, and `fit_to_terminal`
takes them as its `controls` and `status` arguments. A game answers both
questions for itself with `MazeGame.controls` and `MazeGame.status`.

The foot is the part of the frame the console's width is measured against
nowhere, which is why its lines are the ones that wrap. `fit_dimension`
caps a maze row to the terminal's columns, so an 80 column console draws
maze rows 79 characters wide against a 60 character controls line - the
controls line is the longest line of the *foot*, not of the screen. The
two lines the foot has left are the `end` marker and a blank spacer, and
neither is wide enough to reach the edge of a console with room for a maze
in it.
`place_quest` is the call behind quest mode's entry, and `Quest` is the
inventory the player fills:

| Name | What it does |
| --- | --- |
| `place_quest(grid, stages, rng, path, taken)` | Lay a chain of doors and boxes into a maze, or `None` for one with no way through |
| `Quest(boxes, doors, guide)` | The doors, the boxes that open them and what is being carried |
| `Quest.unlock(cell)` | Whether the cell may be stepped onto, opening a door whose item is carried |
| `Quest.open_box(cell)` | The item in the box on a cell, which is then in the inventory |
| `Quest.closed_doors()` | The doors still shut, in reading order |
| `Quest.drawn()` | The `(doors, boxes, guide)` triple `quest_overlay` takes |
| `Quest.stage()`, `Quest.finished()` | The errand in front of the player, and whether there is one left |
| `Quest.target()`, `Quest.task()` | Where that errand is, and what it is in words |
| `reachable(grid, start, blocked)` | Flood fill a maze with some of its cells shut, which is what a door needs |
| `door_cells(path, stages)` | Space a quest's doors evenly along the route through a maze |
| `MIN_QUEST_STAGES`, `MAX_QUEST_STAGES`, `DEFAULT_QUEST_STAGES` | The range `--quest-stages` takes, and the reasonable chain |

Each box is hidden in the part of the maze that is reachable at the time it
is wanted - box one before door one, box two between door one and door two -
so a quest laid by `place_quest` can always be finished, and never before
the stage it belongs to. The chain only holds for a maze with one route
through it: `braid_maze` opens a second way round, and a door with a way
round it gates nothing.

```python
>>> import random
>>> import py_maze
>>> grid = py_maze.MazeGenerator(width=6, height=6, seed=2024).generate()
>>> quest = py_maze.place_quest(grid, 3, random.Random(2024))
>>> quest.stages
3
>>> quest.stage()
1
>>> sorted(quest.doors.values())
[1, 2, 3]
>>> quest.unlock(quest.closed_doors()[0])
False
>>> quest.open_box(quest.target())
1
>>> sorted(quest.carried)
[1]
```

The terminal half is public too: `MazeGame` plays a maze at the console,
`read_key` and `read_response` take single keypresses, `read_key_timed` waits
a given moment for one and answers `None` when the moment passes empty, or
waits however long it takes when the moment it is given is `None` itself, and
`build_parser`, `build_maze`, `build_game` and `main` are the command line
itself, along
with the `EXIT_OK`, `EXIT_USAGE`, `EXIT_SAVE_FILE`, `EXIT_FILE_ERROR` and
`EXIT_NO_WAY_THROUGH` codes it exits with. `build_maze` hands back
`(grid, collectibles, seed, dead_ends_before, content, chain_seed)`. The
fourth is what `maze_stats` needs to report a braid, and `None` where
nothing was braided, which is every loaded maze and every run that asked
for no braid. The fifth is whatever the mode laid into the maze - a `Quest`
for quest mode and `None` for every other. The last is the seed that
content was laid from.

The two seeds are one number for a generated maze, which lays its content
from the generator the seed built. They part over a loaded maze: the grid is
in the file and only the chain over it can still be seeded, so a run naming
`--seed` plays a chain the file's own seed does not reproduce. `chain_seed`
is `None` where nothing was laid from a seed at all - a mode that puts
nothing in a maze, a document played back with the chain it was saved with,
and a picture played with no seed on either side, whose chain is fresh
randomness. `content_seed(given, recorded)` is the rule it lays that content
from: the seed the run named, else the seed the save file records, else
`None` for the fresh randomness a seedless picture gets. Those are the names
that want a terminal. Everything above runs without one.
