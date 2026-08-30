# py_maze

A command-line maze generator and game written in Python. Generate random, solvable mazes and navigate through them using your keyboard!

## Features

- 🎲 **Random Maze Generation**: Every run carves a fresh maze, no two alike
- 🎮 **Interactive Gameplay**: Navigate through mazes using arrow keys or WASD
- 🖥️ **Cross-Platform**: Works on Windows, Linux, and macOS
- 🎯 **Always Solvable**: Every generated maze is guaranteed to have a path from start to end
- 🎚️ **Difficulty Presets**: Easy, normal and hard maze sizes, or set your own
- 🧱 **Three Carving Algorithms**: Winding backtracker corridors, Prim's more
  open branching, or the straight runs and rooms of recursive division
- 🔀 **Braiding**: Open the dead ends and the maze gains a second way through
- 🌱 **Repeatable Mazes**: Every run reports its seed, so a good maze can be generated again
- 🧭 **Built-In Solver**: Print the shortest way through, or watch the search find it
- 💡 **Hints**: Stuck mid-game? One key lights up the next step
- ⏱️ **Timer and Move Counter**: Both run while you play and are summarized when you finish
- 💰 **Collectibles**: Scatter pickups through the maze and see the tally at the end
- 💾 **Save and Load**: Keep a maze in a file and play it again later
- 📦 **Importable Package**: Generate, solve and draw mazes from your own
  code, with the terminal machinery kept out of the way

## Installation

### Option 1: Install with pip (recommended)

```bash
cd py_maze
pip install -e .
```

After installation, you can run the game from anywhere:

```bash
py_maze
```

### Option 2: Run directly with Python

From the folder holding the `py_maze` package:

```bash
python -m py_maze
```

or set custom width and height for the maze like:

```bash
python -m py_maze -w 20 -H 30
```

The `py_maze.bat` and `py_maze.sh` launchers do the same thing from
anywhere, adding their own folder to `PYTHONPATH` first so no install is
needed.

> **Upgrading from 1.x:** py_maze is a package now rather than a single
> `py_maze.py` file, so `python py_maze.py` has become `python -m py_maze`.
> The installed `py_maze` command, every option and the save file format
> are all unchanged, and `import py_maze` still reaches every name it did
> before. See [The Package Layout](#the-package-layout) for where each one
> now lives.

## Command-Line Options

| Option | Short | Default | Description |
| --- | --- | --- | --- |
| `--width` | `-w` | from the preset | Width of the maze in cells (minimum 2) |
| `--height` | `-H` | from the preset | Height of the maze in cells (minimum 2) |
| `--difficulty` | `-d` | `normal` | Preset maze size: `easy`, `normal` or `hard` |
| `--algorithm` | `-A` | `backtracker` | How the maze is carved: `backtracker`, `prim` or `division` |
| `--braid` | `-b` | `0` | Open this share of the dead ends, from `0` for none to `1` for all |
| `--seed` | `-s` | chosen at random | Seed for the maze generator |
| `--collectibles` | `-c` | `0` | Scatter this many pickups through the maze |
| `--save` | `-o` | | Write the maze to a file so it can be played again |
| `--load` | `-l` | | Play the maze saved in a file instead of generating one |
| `--solve` | `-S` | off | Print the solution path overlaid on the maze |
| `--animate` | `-a` | off | Step through the solver's search on screen |
| `--version` | `-V` | | Show the installed version and exit |
| `--help` | `-h` | | Show usage and exit |

Note that the short flag for height is a capital `-H`. Lowercase `-h` is
reserved by argparse for `--help`. The same goes for `-S` and `-s`: capital
`-S` solves the maze, lowercase `-s` seeds it, and capital `-A` picks the
algorithm. The short flag for `--save` is `-o`, as in an output file, since
`-s` is already the seed.

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
               [--load FILE] [--solve] [--animate] [--version]
py_maze: error: argument --width/-w: maze dimensions must be at least 2 cells, got 1
```

### Difficulty Presets

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

### Carving Algorithms

`--algorithm` picks how the maze is carved. All three leave exactly one route
between any two cells, so every maze is solvable whichever one carves it;
what changes is the shape of the corridors:

| Algorithm | Short | What it carves |
| --- | --- | --- |
| `backtracker` | `-A backtracker` | One winding route, with long dead ends. The default |
| `prim` | `-A prim` | A more open maze, with short dead ends |
| `division` | `-A division` | Straight corridors and squared-off rooms |

```bash
python -m py_maze -d easy --seed 2024 --algorithm prim
```

**Output:**

```
start
* ***********
*           *
* ********* *
*         * *
*** *********
*   *       *
*** * *******
*   *       *
*** * *******
*           *
*** * * * ***
*   * * *   *
*********** *
end
```

Prim's grows the maze outward from one cell, drawing each step at random
from the whole of the growing edge rather than from wherever the last step
landed. It spreads evenly, so it branches often and its dead ends are short.

```bash
python -m py_maze -d easy --seed 2024 --algorithm division
```

**Output:**

```
start
* ***********
*   *       *
*** * *** * *
*   *   * * *
*** ******* *
*   *     * *
*** * * * * *
*   * * *   *
*** *** *** *
*   *     * *
* ******* ***
*           *
*********** *
end
```

Recursive division works the other way about from the other two. Rather
than carving passages out of solid wall, it starts from an empty floor and
builds a wall the whole way across it, leaving one gap to cross by, then
divides each half the same way until what is left is a corridor one cell
wide. Each wall runs straight, which is where the long runs and the
squared-off rooms come from.

`backtracker` is the algorithm py_maze has always carved with, so a run
without `--algorithm` is unchanged.

### Braiding

A carved maze is a *perfect* maze: one route between any two cells, and every
wrong turn ends in a dead end. `--braid` opens a share of those dead ends,
knocking out one wall apiece so each joins the corridor behind it. The maze
then has more than one way through, and `--solve` reports a shortest way
rather than the only one:

```bash
python -m py_maze -d easy --seed 2024 --braid --solve
```

**Output:**

```
start
*.***********
*.....  *   *
* ***.* * * *
*   *.*     *
*** *.*******
*   *.......*
* *** *****.*
*   * *    .*
*** * * ***.*
*   *   *  .*
* ******* *.*
*         *.*
***********.*
end
```

That is the same maze `--seed 2024` carves without `--braid`, where the only
route through runs 35 cells. Opening its dead ends leaves a shortest route of
23.

The share runs from `0` for none of the dead ends to `1` for all of them, and
`--braid` on its own means `1`:

```bash
# open a quarter of the dead ends, for a maze with a few loops in it
python -m py_maze --braid 0.25
```

Braiding is applied to a maze as it is generated, so it does not apply to a
maze read back with `--load`: that maze comes out of the file exactly as it
went in, braided or not.

### Repeating a Maze

Every run reports the seed its maze was generated from:

```
seed: 2024
```

Passing that seed back generates exactly the same maze, so a maze worth
keeping does not have to be planned for in advance:

```bash
python -m py_maze --seed 2024
```

A seed can be a number or a word, whichever is easier to remember:

```bash
python -m py_maze --seed winter
```

The same seed only reproduces the same maze at the same size, since the size
decides how many turns the generator takes. The same goes for `--algorithm`
and `--braid`: each draws its own random numbers from the seed, so a seed
reproduces a maze only alongside the options it was carved with. Pair a seed
with `--difficulty`, or with `--width` and `--height`, and with whichever of
those two the run used, to get the identical maze back.

### Collectibles

`--collectibles` scatters that many `$` markers through the maze for the
player to pick up on the way past:

```bash
python -m py_maze -d easy --seed 2024 --collectibles 4
```

**Output:**

```
start
* ***********
* *     *   *
* *** * *** *
*   * *     *
*** * *******
*   *       *
* *** ***** *
*   *$*$  * *
*** * * *** *
*   * $$*   *
* ******* * *
*         * *
*********** *
end
seed: 2024
```

Nothing is scattered unless the option is given, so a run without it is
unchanged. The places are drawn from the same seed as the maze, so the command
above puts the collectibles in those cells every time it is run.

Every cell the player can stand on is a candidate, corridors as well as
junctions, apart from the entrance and the exit. Those two are left clear so
nothing is handed over before the first step or after the last. Asking for
more than the maze has room for simply fills every cell there is.

Collectibles are drawn over a solution path rather than under it, so a maze
printed with `--solve` still shows what there is to pick up along the way.

Picking one up is a matter of walking onto it. The running tally sits under
the maze while the game is played, and the final one is part of the
[end-of-game summary](#the-timer-and-the-move-counter).

### Saving and Loading a Maze

`--save` writes the maze, and any collectibles, to a file:

```bash
python -m py_maze -d easy --seed 2024 -c 4 --save maze.txt
```

**`maze.txt`:**

```
# py_maze save 1
# seed: 2024
* ***********
* *     *   *
* *** * *** *
*   * *     *
*** * *******
*   *       *
* *** ***** *
*   *$*$  * *
*** * * *** *
*   * $$*   *
* ******* * *
*         * *
*********** *
```

A save file is the maze exactly as it is drawn, under a short header recording
the format and the seed it came from. That makes it readable, editable by hand
and comparable like any other text file. Lines starting with `#` are comments,
so a note about the maze can be kept alongside it.

`--load` plays a saved maze back:

```bash
python -m py_maze --load maze.txt
```

The maze comes from the file as it was saved, so the options that generate one
do not apply to it: `--width`, `--height`, `--difficulty`, `--seed`,
`--algorithm`, `--braid` and `--collectibles` are all ignored for a loaded
maze. `--solve`, `--animate` and the in-game hints work on it exactly as they
do on a generated one.

A loaded maze reports the seed its file records, so a maze that turned out to
be worth keeping can still be traced back:

```
Loading maze...

start
...
end
seed: 2024
```

A file that is not a maze this build can read is refused rather than guessed
at, with a message naming what was wrong:

```bash
python -m py_maze --load notes.txt
```

**Output:**

```
py_maze: notes.txt: not a py_maze save file
```

The same goes for a ragged maze (`notes.txt: line 3 is 4 characters, expected
5`), a stray character such as a solution marker pasted back in
(`notes.txt: unexpected character '.' on line 2`), and a file written by a
newer build (`notes.txt: save format 2 is not supported, this build reads 1`).

The format is specified in [docs/save-format.md](docs/save-format.md): the
header, the seed comment, the markers, the ragged-line rule and what a reader
refuses, so another tool can write a file py_maze will load.

### Fitting the Terminal

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

## Solving the Maze

`--solve` prints the shortest way from the entrance to the exit as a trail of
`.` markers laid over the maze:

```bash
python -m py_maze -d easy --seed 2024 --solve
```

**Output:**

```
start
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
end
seed: 2024
```

The solver is a breadth-first search, so the route it draws is always the
shortest one. Mazes built by recursive backtracking have exactly one route
between any two points anyway, which makes the shortest route the only route.

### Watching the Search

`--animate` steps that same search across the screen before the solved maze
is printed. Each frame is one wave further from the entrance:

```bash
python -m py_maze -d easy --seed 2024 --animate
```

**One frame partway through:**

```
Solving...
start
*~***********
*~*     *   *
*~*** * *** *
*~~~* *     *
***~* *******
*~~~*       *
*~*** ***** *
*?  * *   * *
*** * * *** *
*   *   *   *
* ******* * *
*         * *
*********** *
end
frontier ?   explored ~   solution .
```

`?` marks the frontier the search is about to grow from, `~` the cells it has
already explored, and `.` the finished path on the last frame.

Animating needs a screen to draw over. When the output is piped or redirected
there is nothing to animate, so the maze is solved without the frames and only
the solved maze is written:

```bash
python -m py_maze --animate > solved.txt
```

## How to Play

1. Run `py_maze` from your terminal
2. A random maze will be generated and displayed
3. Choose whether you want to play (press 'y' for yes, 'n' for no). The
   answer is a single keypress on every platform: there is no Enter to press
4. If you choose to play:
   - Use **arrow keys** or **WASD** to move your character (`o`)
   - Navigate from the **start** (top) to the **end** (bottom)
   - Walk over any collectibles (`$`) to pick them up
   - Press **'h'** for a hint when you are stuck
   - Press **'q'** to quit at any time, or **Ctrl+C** to interrupt

### The Timer and the Move Counter

A status line under the maze reports how long the game has been running and
how many steps have been taken. When the maze holds collectibles, it counts
those too:

```
start
* ***
*o$ *
*** *
*   *
*** *
end
time 0:12   moves 8   collected 1/2

Use arrow keys or WASD to move. Press 'h' for a hint, 'q' to quit.
```

Only steps that moved the player are counted, so walking into a wall costs
nothing but the time it took. Asking for a hint is not a move either.

Reaching the exit prints the same tallies as an end-of-game summary:

```
🎉 Congratulations! You solved the maze! 🎉

Time:  1:12
Moves: 84
Collected: 3 of 4

Press any key to exit...
```

The clock stops the moment the maze is won, so the summary reads the same
however long it is left on screen. Quitting with `q` prints the summary for
the game so far, and the `Collected` line is left out of a maze that had no
collectibles in it.

A console whose code page cannot draw the party poppers gets the plain
congratulations instead, so the message arrives whatever the terminal can
encode:

```
Congratulations! You solved the maze!
```

### Redrawing the Screen

Each move redraws the whole screen. The cursor is put back at the top left
with an ANSI escape sequence and the new frame is written over the old one in
a single call, so the maze, the status line and the controls are replaced
together and the screen never stands empty part-way through a redraw.

Terminals that read escape sequences are drawn on this way, which is every
terminal on Linux and macOS and every Windows console that takes virtual
terminal processing (Windows 10 and later). Where the escapes would be
printed as text instead, py_maze falls back to clearing the screen through
`cls` or `clear`, exactly as it always did. Setting `TERM=dumb` forces the
fallback.

The same escape wipes the screen between the frames of `--animate`, so an
animated search no longer starts a shell for every frame it draws.

### Hints

Pressing **h** during play lights up the next step along the solution with a
`?`, then redraws the maze without it a moment later:

```
start
* ***
*o? *
*** *
*   *
*** *
end
time 0:04   moves 1

Use arrow keys or WASD to move. Press 'h' for a hint, 'q' to quit.
```

The path is solved from wherever the player is standing rather than from the
entrance, so a hint still points the way after a wrong turn, and asking for
one in a dead end points back out of it. At the exit there is nothing left to
hint at, so nothing is highlighted.

## Example Maze

```
start
**** ************
*    *     *    *
**** * *** * ****
*      *   *    *
* ****** *** ****
* *    *     *  *
* * **** ***** **
* *      *      *
* ******** ****** 
*                *
**************** *
end
```

## Controls

- **Arrow Keys** or **W/A/S/D**: Move up/left/down/right
- **H**: Show a hint for a moment
- **Q**: Quit the game
- **Ctrl+C**: Interrupt the game

While the game is running, the terminal is put into raw mode so single
keypresses can be read without waiting for Enter. The same goes for the
"would you like to play" prompt, which takes one keypress and leaves nothing
behind in the input buffer. Raw mode also means Ctrl+C arrives as an ordinary
keypress rather than as an interrupt signal, so the game handles it itself:
the terminal is restored to its normal mode and the game exits with a goodbye
message instead of a traceback.

An answer piped in rather than typed has no terminal mode to set, so the
prompt reads it straight from the pipe.

## Using py_maze as a Library

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

### The Grid

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

### A Worked Example

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

### Carving and Braiding

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

### Collectibles and Save Files

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
is specified in [docs/save-format.md](docs/save-format.md).

### The Names

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
| `MOVES` | The four steps a player, and the solver, can make |
| `MIN_DIMENSION` | The smallest maze with an interior path, 2 cells |

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
| `write_save(path, grid, collectibles, seed)` | Write a maze to a file |
| `read_save(path)` | Read one back as `(grid, collectibles, seed)` |
| `save_lines(grid, collectibles, seed)` | The file's lines, without writing them |
| `parse_save(text, source)` | The same read, from text already in hand |
| `SaveFileError` | Raised for a file this build cannot read |
| `SAVE_FORMAT`, `SAVE_HEADER`, `SAVE_CHARS` | The format number, its header line and the characters it allows |

The terminal half is public too: `MazeGame` plays a maze at the console,
`read_key` and `read_response` take single keypresses, and `build_parser`,
`build_maze` and `main` are the command line itself. Those are the names
that want a terminal. Everything above runs without one.

## Requirements

- Python 3.10 or higher
- No external dependencies required! (Uses only standard library)

Building or installing from source additionally needs pip with setuptools 61
or newer, which is what reads `pyproject.toml`.

`requires-python` in `pyproject.toml` is that floor, and the classifiers
beside it list every version the suite is run on: 3.10, 3.11, 3.12 and 3.13.
Each of them is tested on Windows, Linux and macOS by the workflow in
`.github/workflows/tests.yml`, so the versions the manifest promises are the
versions that are actually checked.

## How It Works

The maze generator carves with the **recursive backtracking algorithm** by
default:

1. Start with a grid full of walls
2. Begin at the starting cell and mark it as visited
3. Randomly choose an unvisited neighbor
4. Remove the wall between the current cell and chosen neighbor
5. Move to the chosen neighbor and repeat
6. If no unvisited neighbors exist, backtrack to the previous cell
7. Continue until all cells have been visited

This algorithm ensures that every maze generated has exactly one path between any two points, making it both challenging and always solvable!

`--algorithm` swaps in one of the other two, and each holds to that same
promise of one path between any two points:

- **Prim's** grows the maze outward from one cell. Every wall between a
  carved cell and an uncarved one is a candidate, and each step draws one at
  random out of the whole growing edge, so the maze spreads evenly rather
  than wandering: it branches often and its dead ends are short.
- **Recursive division** builds walls instead of carving passages. It starts
  from an empty floor, walls it in two with a single gap to cross by, and
  divides each half the same way until what is left is a corridor one cell
  wide. Each wall runs the whole way across, which is where its straight
  corridors and squared-off rooms come from.

Each algorithm is one module under `py_maze/algorithms/`, and each is the
same function to call: a size and a random number generator in, a carved grid
out. Adding a fourth is a module there and a line in the registry, with
nothing in `MazeGenerator` to change.

Each call to `generate()` starts from step 1 again: the carver is handed a
fresh grid and a seeded generator goes back to the same random numbers, so
one generator asked for its maze twice hands back the same maze twice rather
than carving further into the one it already made.

`--braid` is the one thing that undoes a carver's work. A dead end is a cell
with one way in and no way on; braiding knocks a wall out of a share of them
so each joins the corridor behind it. That turns the single route through the
maze into a network of routes, which is what leaves the solver a shortest way
to find rather than the only way there is.

The solver behind `--solve`, `--animate` and the in-game hints is a
**breadth-first search**: it spreads out from the start one step at a time,
recording the cell each new cell was reached from, until it arrives at the
exit. Following those records back from the exit gives the path, and because
every cell one step away is examined before any cell two steps away, the path
that comes back is always the shortest one. `--animate` draws one frame per
step outward, which is exactly the wave the search is working on.

A carved maze has only one route through, so the shortest route is the only
route, and the same solver still finds the way out from anywhere a player has
wandered to. On a maze braided with `--braid` there is more than one route,
and the one that comes back is the shortest of them.

## Development

The project structure:

```
py_maze/
├── py_maze/                # The package itself
│   └── algorithms/         # The ways a maze can be carved, one to a module
├── docs/
│   └── save-format.md      # The save file, for a tool that writes one
├── .github/
│   ├── instructions/       # Editor instructions for this repository
│   └── workflows/
│       └── tests.yml       # The suite, on every platform and version
├── py_maze.bat             # Windows launcher, no install needed
├── py_maze.sh              # POSIX launcher, no install needed
├── test_py_maze.py         # Unit tests
├── pyproject.toml          # Packaging and project metadata
├── .gitignore              # Ignored build, cache and editor artifacts
├── CHANGELOG.md            # Version history
├── CONTRIBUTING.md         # The test command and the conventions
├── LICENSE                 # The MIT text the manifest declares
├── TODO.md                 # Planned work, and what has been done
└── README.md               # This file
```

### The Package Layout

Each module owns one job, and `__init__.py` re-exports every public name, so
`import py_maze` reaches all of them whichever module they live in:

```
py_maze/
├── __init__.py         # Re-exports the public names
├── __main__.py         # python -m py_maze
├── grid.py             # The grid, and the helpers that build and read it
├── algorithms/         # The ways a maze can be carved, one to a module
│   ├── __init__.py     # The registry --algorithm reads its names from
│   ├── backtracker.py  # Recursive backtracking, the default
│   ├── prim.py         # Randomized Prim's algorithm
│   └── division.py     # Recursive division
├── generation.py       # Carving a maze, braiding it, scattering its pickups
├── solving.py          # Breadth-first search over a grid
├── rendering.py        # Drawing a maze, and measuring the terminal
├── saves.py            # Reading and writing save files
├── keys.py             # Single keypresses, and the terminal imports
├── game.py             # Playing a maze at the terminal
├── cli.py              # The options, the parser and main()
└── version.py          # The version number, on its own
```

One type is passed between them all: a maze is a **grid**, a list of rows of
booleans with `True` for a wall and `False` for a cell the player can stand
on, addressed as `grid[y][x]`. A maze carved by `generation` is the same
object `solving` walks, `rendering` draws and `saves` writes out, so nothing
is converted along the way. Every module and public name carries a docstring,
so `help(py_maze)` and `help(py_maze.solve_maze)` describe the surface.

`keys.py` is the only module that imports terminal machinery, so `msvcrt`,
`tty` and `termios` stay out of the way of anything that only wants to
generate or solve a maze.

`algorithms/` is the one subpackage, and every module in it is the same
shape: one carving function taking a width, a height and a random number
generator and returning a carved grid. `algorithms/__init__.py` maps the name
`--algorithm` takes to the function that carves it, so a fourth algorithm is
a module there and an entry in that map, with nothing in `generation.py` to
change. `pyproject.toml` lists the subpackage beside the package, which is
what installs it.

### The Version Number

The version lives in one place, `__version__` in `py_maze/version.py`, which
`py_maze/__init__.py` re-exports as `py_maze.__version__`. The manifest reads
it from there, so a release only ever changes that one string:

```toml
# pyproject.toml
dynamic = ["version"]

[tool.setuptools.dynamic]
version = { attr = "py_maze.__version__" }
```

The same value backs the `--version` flag, and the test suite checks that the
changelog has an entry for it.

### Running the Tests

The tests use only the standard library, so no test dependencies are
needed:

```bash
python -m unittest discover -v
```

The suite runs on any platform. Both the Windows and the POSIX keyboard
branches are exercised through fake terminals, so neither is skipped for
running on the other operating system.

That same command is what CI runs. `.github/workflows/tests.yml` runs it on
Windows, Linux and macOS across every supported Python version on each push
and pull request, so the cross-platform promise is checked rather than
asserted.

## License

MIT License - Feel free to use and modify as you wish! The full text is in
[LICENSE](LICENSE).

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.
[CONTRIBUTING.md](CONTRIBUTING.md) covers the test command, the comment and
docstring convention and how the version is single-sourced.

## Future Enhancements

Ideas for future versions:
- Multiple player characters
- Obstacles that block or slow the way through

Enjoy your maze adventures! 🎉
