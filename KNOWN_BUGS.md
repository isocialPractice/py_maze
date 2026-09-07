# Known Bugs

Defects that are understood but not yet fixed. Each section records how to
reproduce the bug, what is known about it and what is not.

## 2026-09-07: the partial redraw drifts once anything else scrolls the screen

Found reviewing 2.2.6, which stopped the play screen scrolling itself. The
scroll it removed was the game's own newline. Every other way the screen can
scroll is still there, and the redraw has no way to notice one.

### What happens

`frame_diff` addresses every line it writes by an absolute screen row, on the
understanding that line 1 of the frame is sitting on row 1 of the screen.
2.2.6 stopped the game breaking that understanding: it writes no newline at
all, so nothing it sends can scroll the screen. Nothing re-establishes the
understanding when something else breaks it. A screen that scrolls once, for
any reason, leaves frame line `k` on row `k - 1` while every later redraw
goes on writing it to row `k`, and the picture never repairs because only
changed lines are ever written again.

### Reproducing it: a terminal narrower than the controls line

`CONTROLS_LINE` is 66 characters and is the last line of the frame.
`fit_to_terminal` caps the maze against the terminal's columns, but the
controls line is not part of the maze and is never measured against them, so
a terminal narrower than 66 columns wraps it. On a screen the frame fills,
the controls line is on the bottom row, and wrapping there takes the screen
up one exactly as a newline would.

Play in a terminal 60 columns wide and 24 rows tall:

```console
py_maze --play
```

`fit_to_terminal` caps the maze to 9 by 9 for the 24 rows, which draws a 24
line frame that fills the screen, and the 66 character controls line wraps on
the bottom row of a 60 column screen. The screen has scrolled before a key is
ever pressed.

This is not a narrow edge. Any terminal under 66 columns reaches it, no
option makes the controls line shorter, and the maze being capped to fit the
rows is what puts the controls line on the bottom row in the first place.

### Reproducing it: a terminal resized smaller mid-game

Shrinking the window pushes the content up, and there is no `SIGWINCH`
handling to notice it, so every redraw after the resize writes to rows that
have moved.

### What is known

Measured with the suite's `TerminalScreen`, which 2.2.6 gave a height and the
scroll that goes with it:

- Draw the first frame, scroll the screen once by any means, then walk a
  route. 7 of the 10 rows of the suite's test frame end up holding lines from
  frames that have gone - rows 1, 4 to 7, 9 and 10 - and no later step
  repairs any of them.
- Give the same model a width as well, so a line past the last column wraps
  the way a terminal wraps, and the 60 by 24 terminal above scrolls on its
  first frame. After four steps 21 of its 24 rows disagree with the frame.

The wrap is older than 2.2.6 and older than 2.2.5. What changed in 2.2.5 is
that a scroll is no longer corrected, and what 2.2.6 fixed is the one scroll
the game caused itself.

### What is not known

- How much the resize case differs between terminals. That the content moves
  is certain; which row the cursor is left on afterwards is not, and that
  path has not been measured against a real console.
- Which fix the project wants. None of these addresses a scroll the game did
  not cause except the last:
  1. Reserve a row below the frame, `RENDER_ROW_OVERHEAD` going from 5 to 6,
     so one wrapped line has somewhere to go. It shrinks every maze that was
     capped, it does nothing when `terminal_size()` is unavailable, and a
     terminal under 33 columns wraps the controls line onto two rows anyway.
  2. Measure the frame's widest line rather than the maze alone, so a run on
     too narrow a screen says so. That reports the fault rather than fixing
     it.
  3. Give the assumption up instead of defending it: measure the terminal
     each frame and draw the frame whole whenever the size has changed since
     the last one. That is what 2.2.4 did every frame, and it is why the same
     scroll was merely cosmetic then.
