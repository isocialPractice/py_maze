---
title: Generating a maze
summary: >-
  How a maze is carved, how to open its dead ends, how to get the same maze
  back tomorrow, and how to scatter pickups through it.
---

## Carving Algorithms

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

## Braiding

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

## Repeating a Maze

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

## Collectibles

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
[end-of-game summary](playing.md#the-timer-and-the-move-counter).
