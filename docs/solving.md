---
title: Solving the maze
summary: >-
  Print the shortest way through as a trail of markers, or watch the search
  spread out and find it.
---

`--solve` prints the shortest way from the entrance to the exit as a trail of
`.` markers laid over the maze:

```bash
python -m py_maze -d easy --seed 2024 --solve
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

## Watching the Search

`--animate` steps that same search across the screen before the solved maze
is printed. Each frame is one wave further from the entrance:

```bash
python -m py_maze -d easy --seed 2024 --animate
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
python -m py_maze --animate > solved.txt
```

A loaded maze can lack a way through, which a generated one never does. When
one does, the run exits with a status code saying so, tabled under
[Scripting py_maze](scripting.md#status-codes).
