# py_maze

A command-line maze generator and game written in Python. Generate random, solvable mazes and navigate through them using your keyboard!

## Features

- 🎲 **Random Maze Generation**: Uses recursive backtracking algorithm to create unique, solvable mazes
- 🎮 **Interactive Gameplay**: Navigate through mazes using arrow keys or WASD
- 🖥️ **Cross-Platform**: Works on Windows, Linux, and macOS
- 🎯 **Always Solvable**: Every generated maze is guaranteed to have a path from start to end
- 🎚️ **Difficulty Presets**: Easy, normal and hard maze sizes, or set your own
- 🌱 **Repeatable Mazes**: Every run reports its seed, so a good maze can be generated again
- 🧭 **Built-In Solver**: Print the shortest way through, or watch the search find it
- 💡 **Hints**: Stuck mid-game? One key lights up the next step

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

```bash
python py_maze.py
```

or set custom width and height for the maze like:

```bash
python py_maze.py -w 20 -H 30
```

## Command-Line Options

| Option | Short | Default | Description |
| --- | --- | --- | --- |
| `--width` | `-w` | from the preset | Width of the maze in cells (minimum 2) |
| `--height` | `-H` | from the preset | Height of the maze in cells (minimum 2) |
| `--difficulty` | `-d` | `normal` | Preset maze size: `easy`, `normal` or `hard` |
| `--seed` | `-s` | chosen at random | Seed for the maze generator |
| `--solve` | `-S` | off | Print the solution path overlaid on the maze |
| `--animate` | `-a` | off | Step through the solver's search on screen |
| `--version` | `-V` | | Show the installed version and exit |
| `--help` | `-h` | | Show usage and exit |

Note that the short flag for height is a capital `-H`. Lowercase `-h` is
reserved by argparse for `--help`. The same goes for `-S` and `-s`: capital
`-S` solves the maze, lowercase `-s` seeds it.

A maze is drawn with walls between cells, so a maze of `W` by `H` cells
renders as `W * 2 + 1` characters wide and `H * 2 + 1` characters tall.

Values below 2 cells cannot produce a maze with an interior path, so they
are rejected:

```bash
python py_maze.py -w 1
```

**Output:**

```
usage: py_maze.py [-h] [--width WIDTH] [--height HEIGHT]
                  [--difficulty {easy,normal,hard}] [--seed SEED] [--solve]
                  [--animate] [--version]
py_maze.py: error: argument --width/-w: maze dimensions must be at least 2 cells, got 1
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
python py_maze.py --difficulty hard
```

`normal` is the size py_maze has always generated, so a run with no options
is unchanged. Either dimension can still be set by hand, and doing so
overrides that half of the preset:

```bash
# a hard maze, but only 8 cells tall
python py_maze.py -d hard -H 8
```

### Repeating a Maze

Every run reports the seed its maze was generated from:

```
seed: 2024
```

Passing that seed back generates exactly the same maze, so a maze worth
keeping does not have to be planned for in advance:

```bash
python py_maze.py --seed 2024
```

A seed can be a number or a word, whichever is easier to remember:

```bash
python py_maze.py --seed winter
```

The same seed only reproduces the same maze at the same size, since the size
decides how many turns the generator takes. Pair a seed with `--difficulty`,
or with `--width` and `--height`, to get the identical maze back.

### Fitting the Terminal

A maze larger than the screen scrolls out of view and cannot be played, so
sizes are measured against the terminal before the maze is generated. When a
requested size does not fit, it is capped to the largest one that does and a
warning explains the change:

```bash
python py_maze.py -w 60 -H 60
```

**Output (on an 80 by 24 terminal):**

```
warning: --width 60 needs 121 columns but only 80 are available; using 39
warning: --height 60 needs 121 rows but only 20 are available; using 9
```

Four rows are reserved for the `start` and `end` markers, the spacer and the
controls line, which is why the height allowance is smaller than the terminal
is tall.

Two limits apply to the capping:

- Mazes are never capped below the 2 cell minimum. If the terminal cannot
  hold even the smallest maze, the requested size is generated as asked and
  the warning says the maze will not fit on screen.
- Nothing is capped when the output is piped or redirected, since there is no
  terminal to fit. Writing a large maze to a file works exactly as before:

```bash
python py_maze.py -w 60 -H 60 > maze.txt
```

A difficulty preset is capped the same way, so `--difficulty hard` on a small
terminal generates the largest hard-ish maze that fits.

## Solving the Maze

`--solve` prints the shortest way from the entrance to the exit as a trail of
`.` markers laid over the maze:

```bash
python py_maze.py -d easy --seed 2024 --solve
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
python py_maze.py -d easy --seed 2024 --animate
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
python py_maze.py --animate > solved.txt
```

## How to Play

1. Run `py_maze` from your terminal
2. A random maze will be generated and displayed
3. Choose whether you want to play (press 'y' for yes, 'n' for no)
4. If you choose to play:
   - Use **arrow keys** or **WASD** to move your character (`o`)
   - Navigate from the **start** (top) to the **end** (bottom)
   - Press **'h'** for a hint when you are stuck
   - Press **'q'** to quit at any time, or **Ctrl+C** to interrupt

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
keypresses can be read without waiting for Enter. Raw mode also means Ctrl+C
arrives as an ordinary keypress rather than as an interrupt signal, so the
game handles it itself: the terminal is restored to its normal mode and the
game exits with a goodbye message instead of a traceback.

## Requirements

- Python 3.6 or higher
- No external dependencies required! (Uses only standard library)

Building or installing from source additionally needs pip with setuptools 61
or newer, which is what reads `pyproject.toml`.

## How It Works

The maze generator uses the **recursive backtracking algorithm**:

1. Start with a grid full of walls
2. Begin at the starting cell and mark it as visited
3. Randomly choose an unvisited neighbor
4. Remove the wall between the current cell and chosen neighbor
5. Move to the chosen neighbor and repeat
6. If no unvisited neighbors exist, backtrack to the previous cell
7. Continue until all cells have been visited

This algorithm ensures that every maze generated has exactly one path between any two points, making it both challenging and always solvable!

The solver behind `--solve`, `--animate` and the in-game hints is a
**breadth-first search**: it spreads out from the start one step at a time,
recording the cell each new cell was reached from, until it arrives at the
exit. Following those records back from the exit gives the path, and because
every cell one step away is examined before any cell two steps away, the path
that comes back is always the shortest one. `--animate` draws one frame per
step outward, which is exactly the wave the search is working on.

The generated maze has only one route through, so the shortest route is the
only route, but the same solver still finds the way out from anywhere a player
has wandered to.

## Development

The project structure:

```
py_maze/
├── py_maze.py          # Main game module
├── test_py_maze.py     # Unit tests
├── pyproject.toml      # Packaging and project metadata
├── .gitignore          # Ignored build, cache and editor artifacts
├── CHANGELOG.md        # Version history
└── README.md           # This file
```

### The Version Number

The version lives in one place, `__version__` in `py_maze.py`. The manifest
reads it from there, so a release only ever changes the module:

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

## License

MIT License - Feel free to use and modify as you wish!

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## Future Enhancements

Ideas for future versions:
- Timer and move counter
- Save/load maze feature
- Multiple player characters
- Collectibles and obstacles

Enjoy your maze adventures! 🎉
