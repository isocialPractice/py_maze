# <img alt="py_maze" src="https://raw.githubusercontent.com/isocialPractice/py_maze/c50453adc891bc384adb557fc2669c9f0defc35b/logo.svg" width="180px"/>

`Ctrl + click` to view [py_maze documentation](https://isocialpractice.github.io/py_maze/index.html)

A command-line maze generator and game written in Python. Generate random,
solvable mazes and navigate through them using your keyboard!

<div align="left">
  <img src="https://github.com/isocialPractice/py_maze/blob/main/banner.gif?raw=true" 
       alt="Banner Image" width="367px"/>
</div>

## Features

- 🎲 **Random Maze Generation**: Every run carves a fresh maze, at random unless you set a seed
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
- 🔧 **Scriptable**: A quiet mode, JSON output, standard input and output,
  and a status code for each thing that can go wrong
- 📦 **Importable Package**: Generate, solve and draw mazes from your own
  code, with the terminal machinery kept out of the way

## [Installation](docs/installation.md)

```bash
cd py_maze
pip install -e .
py_maze
```

Or run it out of a checkout with no install, from the folder holding the
`py_maze` package:

```bash
python -m py_maze -w 20 -H 30
```

The `py_maze.bat` and `py_maze.sh` launchers do the same from anywhere.
Upgrading from 1.x, or want the full detail?
[Installation](docs/installation.md) has it.

## [Command-Line Options](docs/options.md)

The options a run reaches for most:

| Option | Short | Default | Description |
| --- | --- | --- | --- |
| `--width` | `-w` | from the preset | Width of the maze in cells (minimum 2) |
| `--height` | `-H` | from the preset | Height of the maze in cells (minimum 2) |
| `--difficulty` | `-d` | `normal` | Preset maze size: `easy`, `normal` or `hard` |
| `--algorithm` | `-A` | `backtracker` | How the maze is carved: `backtracker`, `prim` or `division` |
| `--seed` | `-s` | chosen at random | Seed for the maze generator |
| `--collectibles` | `-c` | `0` | Scatter this many pickups through the maze |
| `--save` | `-o` | | Write the maze to a file, or to standard output as `-` |
| `--load` | `-l` | | Play a saved maze instead of generating one, or read `-` |
| `--solve` | `-S` | off | Print the solution path overlaid on the maze |
| `--help` | `-h` | | Show usage and exit |

Note that the short flag for height is a capital `-H`. Lowercase `-h` is
reserved by argparse for `--help`. The same goes for `-S` and `-s`: capital
`-S` solves the maze, lowercase `-s` seeds it.

`--braid`, `--animate`, `--quiet`, `--format`, `--wall-char`, `--open-char`
and `--version` are the rest, and all seventeen are tabled in full under
[Command-line options](docs/options.md).

## [Generating a Maze](docs/generating.md)

```bash
python -m py_maze -d easy --seed 2024 --algorithm prim --braid 0.25
```

Three algorithms carve, `--braid` opens the dead ends so there is more than
one way through, and the seed every run prints brings the same maze back.
[Generating a maze](docs/generating.md) covers all four, with the mazes each
one draws.

## [Solving the Maze](docs/solving.md)

```bash
python -m py_maze -d easy --seed 2024 --solve
```

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

`--animate` steps the same breadth-first search across the screen before the
solved maze is printed. See [Solving the maze](docs/solving.md).

## [How to Play](docs/playing.md)

Arrow keys or **WASD** move your character (`o`) from the **start** at the
top to the **end** at the bottom. **`h`** gives a hint, **`q`** quits, and a
status line under the maze keeps the time, the moves and the collectibles.
[How to play](docs/playing.md) has the rest, the end-of-game summary
included.

## [Saving and Loading](docs/saving.md)

```bash
python -m py_maze --save maze.txt
python -m py_maze --load maze.txt --solve
```

A save file is the maze exactly as it is drawn, under a header recording the
format and the seed. The format is specified in
[docs/save-format.md](docs/save-format.md), so another tool can write a file
py_maze will load.

## [Scripting py_maze](docs/scripting.md)

```bash
python -m py_maze --seed 2024 --save - | python -m py_maze --load - --solve
```

`--quiet`, `--format json`, `-` for standard input and output, a reader for
a maze drawn by something else, and a status code for each thing that can go
wrong: [docs/scripting.md](docs/scripting.md).

## [Using py_maze as a Library](docs/library.md)

```python
import py_maze

grid = py_maze.MazeGenerator(width=6, height=6, seed=2024).generate()
path = py_maze.solve_maze(grid)

for line in py_maze.maze_lines(grid, py_maze.solution_overlay(path)):
    print(line)
```

`import py_maze` reaches every public name whichever module it lives in, and
`msvcrt`, `tty` and `termios` are imported by one module alone, so generating
and solving leave the terminal alone. The grid, a worked example and the whole
tabled surface are in [docs/library.md](docs/library.md).

## Requirements

- Python 3.10 or higher
- No external dependencies required! (Uses only standard library)

The classifiers in `pyproject.toml` list every version the suite is run on:
3.10, 3.11, 3.12 and 3.13, each on Windows, Linux and macOS.

## Documentation

The full documentation is a site built out of [docs/](docs), and every page
of it is a Markdown file that reads on GitHub just as well:

| Page | Covers |
| --- | --- |
| [Quickstart](docs/QUICKSTART.md) | Install it, play it, solve it, in about a minute |
| [Installation](docs/installation.md) | Both ways in, the launchers, upgrading from 1.x |
| [Command-line options](docs/options.md) | Every flag, the presets, fitting the terminal |
| [Generating a maze](docs/generating.md) | Algorithms, braiding, seeds, collectibles |
| [Saving and loading](docs/saving.md) | Save files, and what is refused |
| [Solving the maze](docs/solving.md) | `--solve` and `--animate` |
| [How to play](docs/playing.md) | Keys, the status line, hints, the summary |
| [Scripting py_maze](docs/scripting.md) | Quiet runs, JSON, pipes, status codes |
| [Using py_maze as a library](docs/library.md) | The grid, a worked example, every public name |
| [The save file format](docs/save-format.md) | The specification another tool writes to |
| [Cheat sheet](docs/CHEATSHEET.md) | The lot, dense and scannable |
| [How it works](docs/how-it-works.md) | Carving, braiding and searching, explained |
| [Development](docs/development.md) | The repository map, the layout, the tests |

`DESIGN_LANGUAGE.md` records the site's palette, type scale and spacing, and
what in the repository's own artwork each was derived from.

## Development

```bash
python -m unittest discover -v
```

The suite is standard library only and runs on any platform. The repository
map, the package layout and the single-sourced version are covered in
[docs/development.md](docs/development.md).

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
