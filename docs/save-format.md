---
title: The py_maze save format
summary: >-
  The header, the seed comment, the markers, the ragged-line rule and what a
  reader refuses, so another tool can write a file py_maze will load.
---

A save file is the maze exactly as it is drawn, under a short header
recording the format and the seed it came from. There is no packing and no
encoding: what `--save` writes is the picture `--load` reads back, so the
file can be opened in any editor, changed by hand and compared like any
other text.

This page specifies the format so another tool can write a file py_maze
will load, and so a reader written elsewhere agrees with the one in
`py_maze/saves.py`. The current format is **1**, the number carried in the
header.

There are three things `--load` will read, and this page covers all of
them. The picture under its header is the one `--save` writes by default
and the one the rest of this page means by "a save file":

| What | Written by | Read by |
| --- | --- | --- |
| The picture under its header | `--save FILE` | `--load FILE` |
| A [JSON document](#the-json-document) | `--save FILE --format json` | `--load FILE` |
| A [picture with no header](#a-picture-with-no-header) | Another tool entirely | `--load FILE --wall-char C --open-char C` |

Every one of them is read from standard input, and the first two written to
standard output, under the file name `-`.

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
| Where it is read from | A file by name, or standard input under the name `-`. A stream read that way is called `<stdin>` in the messages |

## Comment Lines

A line whose first character is `#` is a comment. Three kinds matter:

### The Format Header

```
# py_maze save 1
```

Required of a save file, and required before its first maze line. It is
matched against `^#\s*py_maze save\s+(\d+)\s*$`, so the spacing after `#`
and around the number is free but the wording is not. The number is the
format version: this build reads **1** and refuses anything else rather
than guessing at it, which is what the number is for.

The header is what makes a file a save file, and a file carrying one is
read strictly: the markers below are the only characters its maze may be
drawn with. A file with no header is not refused, but it is not a save
file either. It is read as [a picture with no
header](#a-picture-with-no-header), on whatever terms the reader is given.

A header **below** the first maze line is refused rather than believed. A
reader that has already taken those lines for a picture cannot go back and
read them again as something else.

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

## A Picture With No Header

A maze drawn by something that had never heard of py_maze carries no header
and is unlikely to be drawn with `*` and the space. Such a file is read as
a **plain picture**: the reader is told which character is a wall and which
is a cell, and everything else on this page applies unchanged.

```bash
python -m py_maze --load drawn.txt --wall-char '#' --open-char '.'
```

**`drawn.txt`:**

```
#.#####
#.....#
#####.#
```

The two options default to the characters py_maze itself draws with, so a
save file with its header cut off loads as it stands. Three rules follow
from a picture having no header to speak for it:

- **The characters are the reader's to name, not the file's.** A file that
  does carry the header is read with the three markers above whatever the
  options say, the format having already settled the question.
- **A comment is a line the picture could not have drawn.** `#` opens a
  comment only when `#` is not one of the picture's own characters, so the
  file above is three maze lines rather than three notes. A plain picture
  drawn with `*` and the space still keeps its seed comment.
- **The first line decides whether this is a maze at all.** A character the
  picture cannot be drawn with is `not a py_maze save file` on the first
  maze line, where nothing has read as a maze yet, and
  `unexpected character` on any line after it, where something has.

Nothing about writing changes: a maze is always written with `*`, the space
and `$`, so a plain picture loaded this way is a py_maze save file the
moment it is saved again.

## The JSON Document

`--format json` writes the same maze as a document, for a program that
would rather not read a picture. It says outright what the picture leaves
to be worked out, and it is written on a single line so it pipes into a
reader as it stands:

```bash
python -m py_maze -w 2 -H 3 --seed 2024 -c 2 --solve --format json --save -
```

**Output** (laid out here, written on one line):

```json
{
  "py_maze": 1,
  "seed": 2024,
  "entrance": [1, 0],
  "exit": [3, 6],
  "collectibles": [[1, 3], [1, 5]],
  "solution": [[1, 0], [1, 1], [1, 2], [1, 3], [2, 3], [3, 3], [3, 4], [3, 5], [3, 6]],
  "grid": [
    [true, false, true, true, true],
    [true, false, true, false, true],
    [true, false, true, false, true],
    [true, false, false, false, true],
    [true, true, true, false, true],
    [true, false, false, false, true],
    [true, true, true, false, true]
  ]
}
```

That is the maze `python -m py_maze -w 2 -H 3 --seed 2024 -c 2` prints, as a
picture:

```
* ***
* * *
* * *
*$  *
*** *
*$  *
*** *
```

| Key | Holds |
| --- | --- |
| `py_maze` | The format number, exactly as the header carries it. This build reads **1** |
| `seed` | The seed the maze was generated from, as a number or a word, and `null` when there is none |
| `entrance` | The `(x, y)` of the entrance, as a two-element list |
| `exit` | The `(x, y)` of the exit |
| `collectibles` | Every cell holding a pickup, in reading order. `[]` when there are none |
| `solution` | The route from the entrance to the exit, cell by cell, when `--solve` or `--animate` asked for one. `null` otherwise, and `null` when there is no way through |
| `grid` | The maze itself: a list of rows of `true` and `false`, `true` for a wall |

The grid is the whole of the maze, and the four keys above it are read out
of it every time a picture is loaded. A reader may take them as written or
work them out again; py_maze itself works them out, which is why a document
and a picture of the same maze play identically.

`grid` is required and every other key is optional. `entrance`, `exit` and
`solution` are written for a reader and are not read back: a loaded
document hands back the same three things a loaded picture does, the grid,
the collectibles and the seed. Rows must be lists of `true` and `false`,
all the same length, and each must hold at least one cell. A cell is a list
of two whole numbers, `[x, y]`.

A file is read as a document when it opens with `{`, which no picture does
unless `--wall-char` or `--open-char` says it is drawn with one.

## What a Reader Must Refuse

A file that is not a maze this build reads is refused, with a message
naming what was wrong, rather than being guessed at. The reader in
`py_maze.saves` raises `SaveFileError` for each of these, and the command
line prints it under a `py_maze:` prefix and exits with status **3**.

| The file | The message |
| --- | --- |
| Is not a maze the reader can be reading, on its very first line | `not a py_maze save file` |
| Draws maze lines above its format header | `the save header on line 2 comes after the maze` |
| Carries a format this build does not read | `save format 2 is not supported, this build reads 1` |
| Uses a character the picture is not drawn with | `unexpected character '.' on line 2` |
| Has a maze line of a different length than the first | `line 3 is 4 characters, expected 5` |
| Is a header and nothing else, or holds no maze at all | `the save file has no maze in it` |

And for a document:

| The document | The message |
| --- | --- |
| Is not JSON the parser can read | `the JSON could not be read`, and what the parser made of it |
| Is not an object, or carries no `py_maze` key | `not a py_maze save file` |
| Carries a format this build does not read | `save format 2 is not supported, this build reads 1` |
| Has no `grid`, or an empty one | `the save file has no maze in it` |
| Has a row that is not `true` and `false` | `row 1 is not a row of true and false` |
| Has rows of different lengths | `row 2 is 1 cells, expected 2` |
| Lists something that is not a cell | `collectibles holds [1], which is not an (x, y) cell` |
| Puts a collectible off the maze | `collectibles holds [9, 9], which is outside the maze` |
| Records a seed that is neither | `the seed is not a number or a word` |

A picture cannot express a collectible outside the maze, a `$` being one of
the characters the maze is drawn with, so the document reader refuses one
rather than admitting a maze the picture reader could not. A cell off the
grid is drawn by nothing and can be stepped on by nobody, and it would be
counted in the tally all the same, leaving a summary that reads
`Collected: 0 of 1` however well the maze is played. Every cell from
`[0, 0]` to the bottom right of the grid is inside it.

Line numbers count every line in the file, comments and blank lines
included, and start at 1; a document's rows are counted from 1 as well.
Where a file is read by name, the messages are prefixed with it:
`maze.txt: not a py_maze save file`. A maze read from standard input is
prefixed `<stdin>: ` instead.

Two things are deliberately **not** refused:

- **A maze with no way through.** The reader checks the file, not the maze.
  A grid whose exit cannot be reached loads, plays and can be saved again;
  it is the solver that reports there is no route, by returning `None`.
- **A maze of no particular size.** Any rectangle of the allowed characters
  loads, whether or not its dimensions are the `2n + 1` of a carved maze.
  The command line does draw one line here: a maze fewer than 3 characters
  wide has no column for an entrance and an exit to be cut in, so
  `py_maze --load` refuses it with
  `the maze is too narrow for an entrance and an exit, which need 3
  characters` and exits with status **3**. The reader still hands the maze
  back, `py_maze.has_ends` being what reports whether a grid has room for
  the two.

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

A tool that would rather not draw a picture has two shorter routes. Write
the JSON document instead, which is one object with a `py_maze` of `1` and
a `grid` in it and nothing else required. Or draw the maze however the tool
already draws it and let the reader be told: a rectangle of any two
characters loads under `--wall-char` and `--open-char`, with no header, no
comments and no fixed markers to honour.

## Reading and Writing It in Code

The same format through the public API. `read_save` and `parse_save` hand
back the grid described on [the library page](library.md#the-grid): a list of
rows of booleans, `True` for a wall.

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
| `py_maze.read_save(path, chars=None, stream=None)` | Read a file, returning `(grid, collectibles, seed)` |
| `py_maze.parse_save(text, source=None, chars=None)` | The same, from text already in hand. `source` names the file in the error messages |
| `py_maze.parse_json_save(text, source=None)` | The same again, for a document. `parse_save` calls it for text that opens with `{` |
| `py_maze.write_save(path, grid, collectibles=(), seed=None, solution=None, form='text', stream=None)` | Write a maze to a file, in either form |
| `py_maze.save_lines(grid, collectibles=(), seed=None)` | The lines `write_save` would write, without writing them |
| `py_maze.save_json(grid, collectibles=(), seed=None, solution=None)` | The document it would write instead, under `form='json'` |
| `py_maze.picture_chars(wall, open_cell)` | The `chars` map a headerless picture is read with |
| `py_maze.SaveFileError` | Raised for every refusal above. A `ValueError` |
| `py_maze.SAVE_FORMAT` | The format number this build reads |
| `py_maze.SAVE_HEADER` | The header line for that format |
| `py_maze.SAVE_CHARS` | The three markers, mapped to the boolean each becomes |
| `py_maze.JSON_FORMAT_KEY` | The key a document carries the format number under, `py_maze` |
| `py_maze.FORMATS` | The two forms, `TEXT_FORMAT` and `JSON_FORMAT`, with `DEFAULT_FORMAT` the one written unasked |
| `py_maze.STDIO_PATH` | The file name that means standard input or standard output, `-` |

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
