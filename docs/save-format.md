# The py_maze Save Format

A save file is the maze exactly as it is drawn, under a short header
recording the format and the seed it came from. There is no packing and no
encoding: what `--save` writes is the picture `--load` reads back, so the
file can be opened in any editor, changed by hand and compared like any
other text.

This page specifies the format so another tool can write a file py_maze
will load, and so a reader written elsewhere agrees with the one in
`py_maze/saves.py`. The current format is **1**, the number carried in the
header.

## A Whole File

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

Two comment lines and then the maze. Everything below spells out what each
part means and what a reader does with it.

## The File as a Whole

| Property | Rule |
| --- | --- |
| Encoding | UTF-8. `read_save` opens the file with `encoding='utf-8'`, and every character the format uses is ASCII, so plain ASCII is valid UTF-8 here |
| Line endings | LF or CRLF. Lines are split with `str.splitlines()`, so a file written on either platform reads on both |
| Final newline | Written, not required. `write_save` ends the file with one |
| Line order | Comments and maze lines in any order, except that the format header must come before the first maze line |
| Blank lines | Skipped wherever they appear, including a line of nothing but spaces or tabs |

## Comment Lines

A line whose first character is `#` is a comment. Three kinds matter:

### The Format Header

```
# py_maze save 1
```

Required, and required before the first maze line. It is matched against
`^#\s*py_maze save\s+(\d+)\s*$`, so the spacing after `#` and around the
number is free but the wording is not. The number is the format version:
this build reads **1** and refuses anything else rather than guessing at
it, which is what the number is for.

A file with no header at all is not a save file, and neither is one whose
maze starts above its header.

### The Seed Comment

```
# seed: 2024
```

Optional. Matched against `^#\s*seed:\s*(.+?)\s*$`, with the surrounding
whitespace trimmed off the value. The seed reads as a whole number when it
looks like one and as text otherwise; both regenerate the same maze, and
the number is simply what py_maze reports when it picks a seed itself.

The seed is a record of where the maze came from, not an instruction. A
loaded maze is played exactly as the file draws it, and the seed is never
used to carve it again. A file with no seed comment loads fine and reports
no seed. Where the comment appears more than once, the last one wins.

### Any Other Comment

```
# the long way round is the one on the left
```

Kept for whoever opens the file and ignored by the reader, so a note about
a maze can live alongside it.

## The Maze

Every line that is not blank and does not start with `#` is a row of the
maze, in order from the top.

### The Markers

| Character | Meaning | Constant |
| --- | --- | --- |
| `*` | Wall | `py_maze.WALL_MARKER` |
| (space) | A cell the player can stand on | `py_maze.OPEN_MARKER` |
| `$` | A collectible, on a cell the player can stand on | `py_maze.COLLECTIBLE_MARKER` |

Those three and nothing else. `py_maze.SAVE_CHARS` is the same table in
code, mapping each character to the boolean it becomes.

The markers py_maze draws over a maze on screen are **not** part of a save
file: the player `o`, the solution `.`, the hint, the search frontier and
the cells already visited are all drawn over the grid at the moment of
drawing and are never written to a file. Pasting a solved maze back into
one is refused, which is the point of a fixed character set.

### The Ragged-Line Rule

Every maze line is the same length as the first one. A grid whose rows are
not all the same length is not a maze, and a file carrying one is refused
rather than padded out or trimmed down.

Two things follow from spaces being significant:

- **Trailing spaces are open cells.** An editor that strips trailing
  whitespace on save turns a valid file into a ragged one. py_maze's own
  files never end a line with a space, because the rightmost column of a
  maze is always wall.
- **A line of nothing but open cells cannot be written.** A line with no
  non-whitespace character in it is skipped as a blank line, so a row of
  all spaces disappears rather than loading. This never arises in a maze
  py_maze carves, where the left and right columns are wall.

### The Shape of the Maze

A maze of `W` by `H` cells is `H * 2 + 1` lines of `W * 2 + 1` characters,
the extra line in each direction being the wall between one cell and the
next. The example above is a 6 by 6 maze: 13 lines of 13 characters.

The reader does not require those dimensions, and a rectangle of the
allowed characters loads. What it does not do is make such a maze playable:
the parts of py_maze that walk a maze look for the entrance and the exit
where a carved maze puts them.

- The **entrance** is the first open cell down column 1, which in a carved
  maze is the gap in the top line.
- The **exit** is the last open cell up the second-to-last column, which in
  a carved maze is the gap in the bottom line.

A file that opens neither still loads, and the player starts and finishes
at the fallback corners of those two columns.

### Collectibles

A `$` is an open cell holding a collectible, so a reader records the cell
as both. Cells are counted from the top-left of the **maze picture**, not
of the file: comment and blank lines are not rows, so `(x, y)` is column
`x` of the `y`-th maze line, both counted from nought.

In the example, the `$` on the eighth maze line at column 5 is the cell
`(5, 7)`.

There is no limit on how many a file carries and no requirement that it
carry any. py_maze leaves them off the entrance and the exit, so nothing is
picked up before the player has taken a step or after the maze is won; a
file that puts one on the entrance is loaded all the same, and the game
hands it over as play begins.

## What a Reader Must Refuse

A file that is not a maze this build reads is refused, with a message
naming what was wrong, rather than being guessed at. The reader in
`py_maze.saves` raises `SaveFileError` for each of these, and the command
line prints it under a `py_maze:` prefix.

| The file | The message |
| --- | --- |
| Has no format header, or draws maze lines above it | `not a py_maze save file` |
| Carries a format this build does not read | `save format 2 is not supported, this build reads 1` |
| Uses a character outside the three markers | `unexpected character '.' on line 2` |
| Has a maze line of a different length than the first | `line 3 is 4 characters, expected 5` |
| Is a header and nothing else | `the save file has no maze in it` |

Line numbers count every line in the file, comments and blank lines
included, and start at 1. Where a file is read by name, the messages are
prefixed with it: `maze.txt: not a py_maze save file`.

Two things are deliberately **not** refused:

- **A maze with no way through.** The reader checks the file, not the maze.
  A grid whose exit cannot be reached loads, plays and can be saved again;
  it is the solver that reports there is no route, by returning `None`.
- **A maze of no particular size.** Any rectangle of the allowed characters
  loads, whether or not its dimensions are the `2n + 1` of a carved maze.

## Writing a File py_maze Will Load

The whole checklist, for a tool writing one from scratch:

1. Write `# py_maze save 1` as the first line.
2. Write `# seed: <value>` next when there is a seed worth recording, and
   leave the line out when there is not.
3. Write the maze, one line per row, using only `*`, the space and `$`.
4. Keep every maze line the same length, trailing spaces included, and make
   sure no maze line is entirely whitespace.
5. Open the entrance in column 1 and the exit in the second-to-last column
   if the maze is meant to be played.
6. End the file with a newline, and write it as UTF-8.

## Reading and Writing It in Code

The same format through the public API. `read_save` and `parse_save` hand
back the grid described in [the package docs](../README.md#the-package-layout):
a list of rows of booleans, `True` for a wall.

```python
>>> import py_maze
>>> grid, collectibles, seed = py_maze.read_save('maze.txt')
>>> len(grid), len(grid[0])
(13, 13)
>>> sorted(collectibles)
[(5, 7), (6, 9), (7, 7), (7, 9)]
>>> seed
2024
```

| Name | What it does |
| --- | --- |
| `py_maze.read_save(path)` | Read a file, returning `(grid, collectibles, seed)` |
| `py_maze.parse_save(text, source=None)` | The same, from text already in hand. `source` names the file in the error messages |
| `py_maze.write_save(path, grid, collectibles=(), seed=None)` | Write a maze to a file |
| `py_maze.save_lines(grid, collectibles=(), seed=None)` | The lines `write_save` would write, without writing them |
| `py_maze.SaveFileError` | Raised for every refusal above. A `ValueError` |
| `py_maze.SAVE_FORMAT` | The format number this build reads |
| `py_maze.SAVE_HEADER` | The header line for that format |
| `py_maze.SAVE_CHARS` | The three markers, mapped to the boolean each becomes |

A maze read from a file is the same type as a maze straight from the
generator, so it can be solved, drawn, played and saved again with no
conversion between one step and the next:

```python
>>> grid, collectibles, seed = py_maze.read_save('maze.txt')
>>> py_maze.save_lines(grid, collectibles, seed) == open(
...     'maze.txt', encoding='utf-8').read().splitlines()
True
```

## Changing the Format

The header number exists so that an older build refuses a newer file
instead of misreading it. A change that any current reader would get wrong
is a new number, `py_maze.SAVE_FORMAT` moves with it, and the refusal
message names both. A change an existing reader already handles, such as a
new kind of comment line, keeps the number it has.
