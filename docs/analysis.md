---
title: Reading a maze
summary: >-
  What --stats measures, what each number says about the maze, and how the
  difficulty score is put together.
---

Carving a maze and solving one both leave a grid behind. `--stats` reads that
grid and says what it turned out to be: how much of it the player can walk,
how often it offers a choice, how far the way through is and how much of the
maze that way misses.

Nothing here changes the maze. The picture a run draws with `--stats` is the
picture the same run draws without it, and the measurements go underneath
rather than into it:

```bash
python -m py_maze -d easy --seed 2024 --quiet --stats
```

**Output** (the maze itself left out):

```
cells 169   open 73   dead ends 3   junctions 3
longest corridor 9   solution 34   solution share 48%   difficulty 36
```

Two lines rather than one, so neither runs past a narrow terminal. The first
says what the maze is made of and the second how far through it goes and how
hard that is.

A quiet run still reports them. `--quiet` drops what was never asked for, and
these were asked for, which is how `--solve` is already read.

## What Each Number Says

### `cells` and `open`

`cells` is every position of the drawn picture, walls counted alongside
everything else, and `open` is the positions the player can stand on. The
second is a share of the first, so a maze whose `open` is close to its `cells`
is a cavern and one far below it is a warren of narrow corridors.

Both are counted over the picture rather than over the `W` by `H` that
`--difficulty` or `--width` asked for. A maze is drawn with walls between
cells, so 6 by 6 cells renders as 13 characters each way and reports
`cells 169`. [Command-line options](options.html) has the arithmetic.

### `dead_ends`

A cell with one way in and no way on. The entrance and the exit each have a
single open neighbour too, and neither is counted: they are how the maze is
entered and left rather than somewhere to get stuck.

Dead ends are what a player loses time in, and they are the one measurement
`--braid` acts on directly.

### `junctions`

A cell where three or more ways meet: three is a fork and four a crossroads,
while two is a corridor passing through. Counting them says how often the maze
stops the player and asks which way, which is a different question from how
many of those choices turn out to be wrong.

Braiding makes more of them. Every dead end opened joins its cell to the
corridor behind it, and that corridor gains a branch.

### `longest_corridor`

The longest unbroken straight line of walkable cells, across a row or down a
column, measured in cells rather than in the steps between them. It is how far
the maze can be crossed without turning, so a maze of long corridors is played
in fewer decisions than one of the same size made of corners.

It says nothing on its own about which carver made the maze, and braiding only
ever lengthens it: opening a wall joins two runs, and no run is broken by a
cell becoming walkable.

### `solution`

The steps the shortest route takes from the entrance to the exit. A maze with
no way through has no route to measure, and the tally says so in that word
rather than in a nought that would read as a route of no steps:

```
cells 9   open 2   dead ends 0   junctions 0
longest corridor 1   solution none   solution share none   difficulty none
```

A generated maze always has a way through. A loaded one can lack it, and a run
asked to solve such a maze exits with a status code saying so, tabled under
[Scripting py_maze](scripting.html#status-codes).

### `solution_share`

How much of the maze that route stands on: the cells it walks over every cell
the player could stand on. It is counted in cells because the maze it is a
share *of* is counted in cells, and a route of no steps still stands on the
one cell it begins and ends on.

**This is the number that separates two mazes the others call equal.** A maze
that is mostly one long winding corridor and a maze of the same size that is
mostly branches can carry the same dead ends, the same junctions and the same
route length. The share is what says which is which: near 1 and almost every
open cell is on the way through, low and most of the maze is somewhere the
player had no reason to be.

It is held as the exact share a script can compare, from 0 to 1 - the same
vocabulary `--braid` reads a share in - and printed as a whole percent for a
player to read. A stored `0.4794520547945205` prints as `48%`.

### `dead_ends_opened`

How many dead ends `--braid` opened, which is the one thing the grid cannot be
asked. A braided maze looks exactly like a maze that was carved that way, so
the count is taken before the braid and compared against the count after:

```bash
python -m py_maze -d easy --seed 2024 --braid 0.5 --quiet --stats
```

**Output** (the maze itself left out):

```
cells 169   open 75   dead ends 1   opened 2   junctions 5
longest corridor 9   solution 22   solution share 31%   difficulty 40
```

The maze had three dead ends, two were opened, one is left. The two tallies
add back up to what the carver made, so either can be recovered from the
other.

The tally is printed only by a run that braided. A nought would say a braid
opened none of them, which is a different claim from never having been
braided, so an ordinary run leaves the tally off its line altogether. The same
goes for a loaded maze: `--braid` does not apply to one, so there is no before
to compare the file against.

### `difficulty`

A score out of 100, read out of the measurements above it.

**It is a reading rather than a measurement, and it is published as what it is
made of rather than as a number to trust.** Three shares are added up and
averaged, each worth exactly as much as the other two:

| Part | What it is | Full marks at |
| --- | --- | --- |
| **wrong turns** | How much of the maze is not on the shortest route, which is `1 - solution_share` | A maze whose route touches almost none of it |
| **decisions** | Junctions per open cell, over the `JUNCTION_CEILING` of `0.2`, capped at 1 | A junction every five open cells |
| **corners** | The turns the route makes over the steps it takes, a turn being where one straight run meets the next | A route that turns at nearly every step |

Nothing weights one part above another, because nothing here knows which of
them a given player finds hard. A maze of one long corridor scores nothing on
wrong turns and nothing on corners however long it is; a maze of the same size
made of short branches scores highly on both.

`0.2` is above anything py_maze itself carves - the busiest the three carvers
get is about `0.14` - so the cap is there for a braided maze turned into a
network rather than for a generated one.

**Read a score against another maze rather than against the whole of 0 to
100.** The three carvers land between roughly 20 and 65, so a 60 is a hard
maze for this generator and not six tenths of the hardest maze there could be.

A maze with no way through has no difficulty to report. Two of the three parts
are read off the route, so the score is `none` rather than nought.

## Comparing the Carving Algorithms

`--algorithm` is described in one phrase apiece - winding corridors with
long dead ends, a more open maze with short ones, straight runs and
squared-off rooms. Those are claims, and these are the numbers behind them.

Every figure is the mean over the twenty mazes `--seed 1` to `--seed 20`
carve at `--difficulty hard`, which is 16 by 20 cells, 1,353 positions and
641 of them open. One maze says very little - a single seed can hand any
carver a short route - so the comparison is over twenty of them, and it can
be taken again:

```python
import statistics

import py_maze

for name in py_maze.ALGORITHMS:
    measured = [py_maze.maze_stats(
        py_maze.MazeGenerator(16, 20, seed=seed, algorithm=name).generate())
        for seed in range(1, 21)]
    print(name, statistics.mean(row['dead_ends'] for row in measured))
```

| Measurement, mean over 20 mazes | `backtracker` | `prim` | `division` |
| --- | --- | --- | --- |
| Dead ends | 33.5 | 101.1 | 87.5 |
| Junctions | 33.0 | 86.1 | 78.6 |
| Longest corridor | 16.1 | 21.4 | 19.7 |
| Solution steps | 236.4 | 76.0 | 124.0 |
| Solution share | 37.0% | 12.0% | 19.5% |
| Difficulty | 39.9 | 60.1 | 56.9 |

Three of the phrases hold, and read better as numbers than as words.

**Backtracker's route is the long one.** Its shortest way through is 236
steps against Prim's 76, and it walks 37% of the open cells against Prim's
12%. That is what "one winding route" measures as: the maze is mostly the
way through, rather than mostly the branches off it.

**Prim's dead ends are the many short ones.** It leaves 101 of them against
backtracker's 33, in a maze with the same 641 open cells, so each one is a
third as deep on average. "Short dead ends" is three times as many of them
sharing the same floor.

**Branching is what makes a maze score.** Prim's 86 junctions and
backtracker's 33 are the gap the `difficulty` column reads back: 60.1
against 39.9, from mazes identical in size. Recursive division sits just
under Prim's on both.

**One phrase the numbers do not back is "straight corridors".** Recursive
division's longest straight run averages 19.7 cells, below Prim's 21.4.
What division builds is walls that run straight, and a wall running straight
is not a corridor running straight: it leaves many short straight runs
rather than one long one, and `longest_corridor` reports the longest run
rather than how many there are. Take the phrase as a description of the
shape and the column as a measurement of one thing about it, which is not
the same claim.

## Measurements in the JSON Document

A `--format json` run prints the document alone, so nothing is printed
underneath it. `--stats` is not dropped there, only moved: the same numbers go
under a `stats` key, so a script reads them rather than parsing the printed
lines.

```bash
python -m py_maze -w 2 -H 3 --seed 2024 --stats --format json
```

The `stats` key of what that writes, laid out here and written on one line:

```json
{
  "cells": 35,
  "open": 13,
  "dead_ends": 2,
  "dead_ends_opened": null,
  "junctions": 2,
  "longest_corridor": 6,
  "solution": 8,
  "solution_share": 0.6923076923076923,
  "difficulty": 44
}
```

The keys are the ones named above, and every one a line prints `none` for is
`null` here.

**A document carries no `stats` key until `--stats` asks for it.** Every key
but `grid` is optional, so an absent one says the run never measured the maze,
which is a different thing from a maze that measured nothing. A `--save FILE
--format json` run records the key the same way it records the solution;
the picture a text save draws has no room for either.

[The save file format](save-format.html) specifies the whole document, and
[Scripting py_maze](scripting.html) is what a reader of it is written against.

## From a Script or a Library

Every number above comes from one call, and the keys are what `--stats`
prints:

```python
>>> import py_maze
>>> grid = py_maze.MazeGenerator(width=6, height=6, seed=2024).generate()
>>> stats = py_maze.maze_stats(grid)
>>> stats['dead_ends'], stats['junctions'], stats['longest_corridor']
(3, 3, 9)
>>> round(stats['solution_share'], 3), stats['difficulty']
(0.479, 36)
```

The three readers behind it are worth having on their own, and so are the two
calls that read a route:

| Call | What it hands back |
| --- | --- |
| `maze_stats(grid, path, dead_ends_before)` | Every measurement as one dictionary |
| `dead_ends(grid)` | Each dead end, in reading order |
| `junctions(grid)` | Each junction, in reading order |
| `longest_corridor(grid)` | Cells in the longest straight run |
| `solution_share(path, open_count)` | The share of the open cells a route stands on |
| `difficulty_score(open_count, junctions_count, path)` | The score, out of 100 |
| `DIFFICULTY_PARTS` | The three parts of that score, by name |
| `JUNCTION_CEILING` | Where its decisions part reaches full marks |

The solution is the one measurement that has to be searched for. A caller that
has already solved the maze hands the route over rather than paying for a
second search, and a caller whose search found no way through hands over
`None` and is believed:

```python
>>> import py_maze
>>> grid = py_maze.MazeGenerator(width=6, height=6, seed=2024).generate()
>>> py_maze.maze_stats(grid, py_maze.solve_maze(grid))['solution']
34
>>> py_maze.maze_stats(grid, None)['solution'] is None
True
```

[Using py_maze as a library](library.html) covers the rest of the package,
including how `UNSEARCHED` tells a caller that has not looked from one that
looked and found nothing.
