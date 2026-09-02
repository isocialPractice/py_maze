---
title: Saving and loading
summary: >-
  Keep a maze in a file and play it back later, and what happens to a file
  that is not a maze py_maze can read.
---

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
do on a generated one, and `--wall-char` and `--open-char` apply to nothing
else: they say how a file that carries no py_maze header was
[drawn](scripting.md#loading-a-maze-drawn-by-something-else).

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

The format is specified in [the save file format](save-format.md): the
header, the seed comment, the markers, the ragged-line rule and what a reader
refuses, so another tool can write a file py_maze will load.
