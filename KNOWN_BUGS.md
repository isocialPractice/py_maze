# Known Bugs

Defects that are understood but not yet fixed. Each section records how to
reproduce the bug, what is known about it and what is not.

## 2026-09-06: the partial redraw draws on the wrong rows

Found reviewing 2.2.5, which changed `MazeGame.render` from writing every
frame whole to writing only the lines that changed.

### What happens

`frame_diff` addresses every line it writes by an absolute screen row, on the
understanding that line 1 of the frame is sitting on row 1 of the screen.
Nothing holds that understanding true. The first frame is written by
`frame_text`, which ends *every* line with a newline, including the last one.
When the frame is as tall as the terminal, that final newline lands on the
bottom row and scrolls the screen up by one. Frame line `k` now sits on row
`k - 1`, and every partial redraw after it writes frame line `k` onto row `k`
instead - one row below the line it is replacing.

The result is a maze with rows from older frames left between the rows that
were redrawn. Nothing repairs it, because only changed lines are ever written
again.

### Reproducing it

Play the default maze in a terminal 28 rows tall or shorter:

```console
py_maze --play
```

The default `normal` difficulty is 11 cells high, which draws as a 28 line
play screen: 23 maze rows plus the `start` and `end` markers, the tally, the
blank spacer and the controls line. On a 28 row terminal the frame fills the
screen exactly.

This is not an unlucky size. `fit_to_terminal` caps a maze against
`RENDER_ROW_OVERHEAD`, which is 5 - exactly the number of lines the frame
adds around the maze, leaving no row for the cursor to rest on below it. On
every terminal with an even number of rows, a maze capped to fit produces a
frame exactly as tall as the screen:

| Terminal rows | Maze height it caps to | Play screen lines |
| --- | --- | --- |
| 24 | 9 | 24 |
| 26 | 10 | 26 |
| 28 | 11 | 28 |
| 30 | 12 | 30 |

### What is known

Verified with a model terminal that scrolls when a newline is written on its
bottom row, replaying everything a scripted play session sends to standard
output and reading the screen back:

- On a 29 row terminal the 28 line frame is intact and correct.
- On a 28 row terminal the screen holds rows belonging to no frame at all,
  at frame rows 1 and 25. On a 27 row terminal, at frame row 24.
- Under 2.2.4 the same scroll happened, but the screen still showed **one
  intact frame**, merely shifted off the top by one row or two. Writing every
  line of every frame from the home position is what repaired it each time.

So the scroll itself is older than 2.2.5. What 2.2.5 changed is that the
scroll is no longer corrected, turning a cosmetic shift into a picture that
stays wrong for the rest of the game.

### What is not known

- Whether a terminal resized smaller mid-game hits the same fault. It almost
  certainly does, and there is no `SIGWINCH` handling to notice it, but that
  path has not been measured.
- Which of the three candidate fixes the project wants:
  1. Stop `frame_text` ending its last line with a newline, parking the
     cursor with `ANSI_ROW` the way `frame_diff` already does. This treats
     the cause, but changes the output of a public, documented function and
     the "645 characters" figure the 2.2.5 changelog quotes.
  2. Raise `RENDER_ROW_OVERHEAD` from 5 to 6, so a fitted maze always leaves
     a spare row below the frame. One constant, but it shrinks every maze
     that was capped, and does nothing when `terminal_size()` is
     unavailable or the window is resized during play.
  3. Draw the first frame through `frame_diff([], lines)`, which writes no
     newlines at all. Confined to `render`, but it drops the `ANSI_HOME`
     that `test_the_first_frame_puts_the_cursor_back_at_the_top_left`
     asserts on.

### What a fix needs

A regression test cannot be written against the suite's current
`TerminalScreen`: it models a screen of unbounded height and so never
scrolls. It needs a height and the scroll behaviour before it can pin this.
