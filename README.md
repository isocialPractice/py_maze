# py_maze

A command-line maze generator and game written in Python. Generate random, solvable mazes and navigate through them using your keyboard!

## Features

- 🎲 **Random Maze Generation**: Uses recursive backtracking algorithm to create unique, solvable mazes
- 🎮 **Interactive Gameplay**: Navigate through mazes using arrow keys or WASD
- 🖥️ **Cross-Platform**: Works on Windows, Linux, and macOS
- 🎯 **Always Solvable**: Every generated maze is guaranteed to have a path from start to end

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
| `--width` | `-w` | `9` | Width of the maze in cells (minimum 2) |
| `--height` | `-H` | `11` | Height of the maze in cells (minimum 2) |
| `--version` | `-V` | | Show the installed version and exit |
| `--help` | `-h` | | Show usage and exit |

Note that the short flag for height is a capital `-H`. Lowercase `-h` is
reserved by argparse for `--help`.

A maze is drawn with walls between cells, so a maze of `W` by `H` cells
renders as `W * 2 + 1` characters wide and `H * 2 + 1` characters tall.

Values below 2 cells cannot produce a maze with an interior path, so they
are rejected:

```bash
python py_maze.py -w 1
```

**Output:**

```
usage: py_maze.py [-h] [--width WIDTH] [--height HEIGHT] [--version]
py_maze.py: error: argument --width/-w: maze dimensions must be at least 2 cells, got 1
```

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

## How to Play

1. Run `py_maze` from your terminal
2. A random maze will be generated and displayed
3. Choose whether you want to play (press 'y' for yes, 'n' for no)
4. If you choose to play:
   - Use **arrow keys** or **WASD** to move your character (`o`)
   - Navigate from the **start** (top) to the **end** (bottom)
   - Press **'q'** to quit at any time, or **Ctrl+C** to interrupt

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
- Difficulty levels (different maze sizes)
- Timer and move counter
- Maze solver visualization
- Save/load maze feature
- Multiple player characters
- Collectibles and obstacles

Enjoy your maze adventures! 🎉
