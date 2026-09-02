---
title: Scripting py_maze
summary: >-
  Everything for the run that is not being watched: a quiet maze, a JSON
  document, standard input and output, and a status code per failure.
---

Everything below is for the run that is not being watched: a maze generated
for another program to read, a maze handed in from one, and a status code
that says what happened without anything having to read the message. None
of it needs a dependency and none of it starts a service.

## A Quiet Run

`--quiet` keeps standard output to the maze. The banner, the seed line, the
`saved:` line and the play prompt are all left out, so what is left is the
maze and nothing else:

```bash
python -m py_maze -d easy --seed 2024 --quiet
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
*   * *   * *
*** * * *** *
*   *   *   *
* ******* * *
*         * *
*********** *
end
```

The maze is the one a loud run prints, `start` and `end` markers included:
`--quiet` takes lines away and changes none. A quiet run does not offer to
play, there being nobody at the prompt to answer.

## Writing JSON

`--format json` writes the maze as a document instead of a picture, for a
program that would rather not read characters. It says outright what a
picture leaves to be worked out:

```bash
python -m py_maze -w 2 -H 2 --seed 2024 --solve --format json
```

**Output** (laid out here, written on one line):

```json
{
  "py_maze": 1,
  "seed": 2024,
  "entrance": [1, 0],
  "exit": [3, 4],
  "collectibles": [],
  "solution": [[1, 0], [1, 1], [1, 2], [1, 3], [2, 3], [3, 3], [3, 4]],
  "grid": [
    [true, false, true, true, true],
    [true, false, true, false, true],
    [true, false, true, false, true],
    [true, false, false, false, true],
    [true, true, true, false, true]
  ]
}
```

`grid` is the maze itself, a list of rows of `true` and `false` with `true`
for a wall. `solution` is `null` unless `--solve` or `--animate` asked for
one, and `collectibles` is empty unless `--collectibles` scattered any.
Every key is specified in [the save file format](save-format.md).

A JSON run is quiet whether or not `--quiet` is given, since a document
with `Generating maze...` in front of it is not a document any more. The
same document is what `--save` writes under `--format json`, so a file and
a pipe carry the same bytes.

## Standing in a Pipeline

`-` is standard input to `--load` and standard output to `--save`, as it is
to most of the tools py_maze would be piped into. A maze can be written out
of one run and read into the next without a file in between:

```bash
python -m py_maze --seed 2024 --save - | python -m py_maze --load - --solve
```

Each half is quiet in the way it has to be. `--save -` puts the save file on
standard output and prints nothing else there, the maze included: the file is
already the maze, and drawing it again would corrupt what the next command
reads. `--load -` reads the maze off standard input and does not offer to
play, that stream being the maze rather than the keypress a prompt would
read.

Warnings still go to standard error, so a maze capped to the terminal says so
without anything landing in the pipe.

## Loading a Maze Drawn by Something Else

A maze drawn by another tool carries no `# py_maze save` header and is
unlikely to be drawn with `*` and the space. `--wall-char` and `--open-char`
say how it was drawn, and the rest follows:

```bash
python -m py_maze --load drawn.txt --wall-char '#' --open-char '.' --quiet
```

**`drawn.txt`:**

```
#.#####
#.....#
#####.#
```

**Output:**

```
start
* *****
*     *
***** *
end
```

The two options default to the characters py_maze draws with, so a save file
with its header cut off loads with no options at all. They apply to reading
only: a maze is always written with `*`, the space and `$`, which is why the
picture above comes back in py_maze's own characters and can be re-saved,
solved or played like any other maze.

A file carrying the header is read with the characters the format fixes,
whatever the options say. The header settles the question, and the options
are for the file that has nobody to speak for it.

## Status Codes

A run that could not do what it was asked says so on standard error and exits
with a code for what went wrong, so a script can tell the three apart without
reading the message:

| Code | What happened |
| --- | --- |
| `0` | The run finished |
| `2` | An option the command line will not take |
| `3` | A file that is not a maze this build can read |
| `4` | A file that could not be read, or written |
| `5` | A maze with no way from the entrance to the exit |

Code 3 also covers a loaded maze fewer than 3 characters wide. The entrance
is cut in the second column and the exit in the second from last, so a maze
that narrow has nowhere to put them, and the solver, the JSON document and
the game all read the two out of the grid. The maze is refused once, before
any of them sees it, rather than faulting in whichever the run reaches
first.

Code 5 is reported only when a solution was asked for. A generated maze
always has a way through, so it is a loaded one that can lack it, and
`--solve` or `--animate` is what looks. The maze is still printed before the
run exits, so a script gets the maze and the news together.

The names are on the package too, as `py_maze.EXIT_OK`,
`py_maze.EXIT_USAGE`, `py_maze.EXIT_SAVE_FILE`, `py_maze.EXIT_FILE_ERROR`
and `py_maze.EXIT_NO_WAY_THROUGH`.
