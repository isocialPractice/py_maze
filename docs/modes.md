---
title: Game modes
summary: >-
  The three ways a maze can be played, the options belonging to each one and
  the markers each one draws.
---

A mode is the maze that is already there played differently: the same grid,
the same solver, the same picture and the same keys. `--mode` picks one, and
a run naming none plays exactly as py_maze always has.

| Mode | Short | Playing it | Its own options |
| --- | --- | --- | --- |
| `plain` | `-m plain` | Walk from the entrance to the exit. The default | |
| `chase` | `-m chase` | The same walk, with something following you | `--chase-point`, `--chase-speed` |
| `quest` | `-m quest` | The way on is shut until you find what opens it | `--quest-stages` |

An option belonging to a mode is ignored by every other one, so passing
`--chase-point` to a quest does no harm and changes nothing.

## What Each Mode Draws

Every mode draws the same maze with the same `*` walls and the same `o`
player. What a mode adds is its own markers, and no two modes share one:

| Marker | Mode | What it is |
| --- | --- | --- |
| `o` | every mode | The player |
| `$` | every mode | A collectible waiting to be picked up |
| `?` | every mode | The cell a hint is lighting up |
| `X` | `chase` | The chaser, drawn over the player on the step that catches them |
| `+` | `quest` | A door, still shut |
| `&` | `quest` | A box, with an item still in it |
| `@` | `quest` | The guide, who says what the next errand is |

None of the three quest markers is a character a maze is ever saved as. A
picture can draw a door and cannot say which item opens it, so a picture
carrying one is refused exactly as a picture carrying a `.` is, and the JSON
document is the form that round-trips a quest maze. [The save file
format](save-format.html) has the whole of that.

## Plain Mode

The walk from the entrance at the top to the exit at the bottom, with a
timer and a move counter running and `h` lighting up the next step of the
way through. Everything in [how to play](playing.html) is this mode, and
every other mode is this mode with something added.

```bash
python -m py_maze --mode plain
```

## Chase Mode

Nothing follows the player at first. Once they have walked far enough into
the maze, a chaser appears at the entrance and starts after them, drawn with
an `X`. It walks the route the solver finds from itself to wherever the
player is standing, so it never crosses a wall and it turns when they turn.

Being caught ends the run the way the exit does: the same tallies, with a
line naming which of the two happened.

```bash
# start the chase a fifth of the way in, and give it the fastest preset
python -m py_maze --mode chase --chase-point 20 --chase-speed 5
```

`--chase-point` is how far in the chase begins, as a whole percent of the
maze the player has walked, from `20` to `90`. `--chase-speed` names one of
six preset speeds rather than a delay: the preset is the moves the chaser
makes in a second, so `0` is one a second and `5` is six.
[Command-line options](options.html#game-modes) has how each reads a value
it was not expecting.

## Quest Mode

The maze is the same and the way on is shut. A **door**, drawn `+`, stays
closed until the matching item is carried; the item is in a **box**, drawn
`&`, somewhere in the part of the maze the player can already reach. Opening
door one reaches the part of the maze box two is hidden in, and so on, so a
quest maze is played for what is in it rather than only for the way out.

```bash
python -m py_maze --mode quest --quest-stages 4
```

`--quest-stages` is how many door-and-box pairs the chain runs to, from `1`
to `9`, defaulting to `3`. The doors are spaced evenly along the route
through the maze, so a quest of three shuts it a quarter, a half and three
quarters of the way along.

Walking onto a box opens it and the item is yours. Walking into a door whose
item you are not carrying costs nothing: the step is refused the way walking
into a wall is, and no move is counted. Walking into one whose item you are
carrying opens it, and it stays open - nothing is ever spent.

The running tally under the maze gains the inventory, and so does the
end-of-game summary:

```
time 0:42   moves 61   items 2/3
```

### The Guide

A quest maze has somebody in it. The guide waits just inside the entrance,
drawn `@`, and answers from anywhere in the maze: press `n` and it says what
the errand in front of you is and lights up where it is, for the same moment
a solution hint stays up for.

It is a second kind of hint rather than a second way to ask for the first.
`h` points at the next step of the way to the exit; `n` points at the box
you still need, or at the door it opens once you are carrying it, and says
so in words where the controls line usually sits:

```
The guide says: item 2 is still in its box, and the box is in the part of the maze you can already reach
```

Once every door is open it says so, and from there the maze is an ordinary
walk to the exit.

### Braiding Opens a Way Round

A quest holds because a carved maze has exactly one route between any two
cells, which is what makes a door on that route a door the player has to
open. `--braid` opens the dead ends and gives the maze a second way through,
and a door with a way round it gates nothing:

```bash
# a quest that can be walked out of without opening anything
python -m py_maze --mode quest --braid
```

That is a real combination rather than an error, and nothing refuses it.
A quest meant to be played as a quest is carved without `--braid`.

### Saving a Quest

Only the JSON document carries a quest:

```bash
python -m py_maze --mode quest --format json --save quest.json
python -m py_maze --mode quest --load quest.json
```

The document records the doors, the boxes and the guide, so the maze loads
back as the same quest with nothing collected. A text save of the same maze
is the plain maze under it - the picture has no room to say which item opens
which door - and loading that one with `--mode quest` lays a fresh chain
into it instead.

The mode on the loading run is what decides, so the second command above
needs its `--mode quest`. Loading a quest document in any other mode plays
the plain maze under the chain and draws none of it: what is drawn over a
loaded maze is always what is in play on it.
