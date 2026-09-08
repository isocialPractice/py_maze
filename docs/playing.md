---
title: How to play
summary: >-
  The keys, the status line, the end-of-game summary, and what the screen is
  doing between one move and the next.
---

1. Run `py_maze` from your terminal
2. A random maze will be generated and displayed
3. Choose whether you want to play (press 'y' for yes, 'n' for no). The
   answer is a single keypress on every platform: there is no Enter to press
4. If you choose to play:
   - Use **arrow keys** or **WASD** to move your character (`o`)
   - Navigate from the **start** (top) to the **end** (bottom)
   - Walk over any collectibles (`$`) to pick them up
   - Press **'h'** for a hint when you are stuck
   - Press **'q'** to quit at any time, or **Ctrl+C** to interrupt

## Controls

- **Arrow Keys** or **W/A/S/D**: Move up/left/down/right
- **H**: Show a hint for a moment
- **Q**: Quit the game
- **Ctrl+C**: Interrupt the game

While the game is running, the terminal is put into raw mode so single
keypresses can be read without waiting for Enter. The same goes for the
"would you like to play" prompt, which takes one keypress and leaves nothing
behind in the input buffer. Raw mode also means Ctrl+C arrives as an ordinary
keypress rather than as an interrupt signal, so the game handles it itself:
the terminal is restored to its normal mode and the game exits with a goodbye
message instead of a traceback.

An answer piped in rather than typed has no terminal mode to set, so the
prompt reads it straight from the pipe.

## The Timer and the Move Counter

A status line under the maze reports how long the game has been running and
how many steps have been taken. When the maze holds collectibles, it counts
those too:

```
start
* ***
*o$ *
*** *
*   *
*** *
end
time 0:12   moves 8   collected 1/2

Use arrow keys or WASD to move. Press 'h' for a hint, 'q' to quit.
```

Only steps that moved the player are counted, so walking into a wall costs
nothing but the time it took. Asking for a hint is not a move either.

The two tallies are independent of each other, both ways round. The game
comes back to the screen four times a second whether or not a key was
pressed, so the clock counts on while the player stands still: a second that
passes with nothing pressed is a second and no move, exactly as a step into
a wall is a move that never happened. A screen with nothing new on it is
still written as nothing, so three of those four visits leave the terminal
alone - the status line counts whole seconds, and only the one the second
turns over on has anything to say.

Reaching the exit prints the same tallies as an end-of-game summary:

```
🎉 Congratulations! You solved the maze! 🎉

Time:  1:12
Moves: 84
Collected: 3 of 4

Press any key to exit...
```

The clock stops the moment the maze is won, so the summary reads the same
however long it is left on screen. Quitting with `q` prints the summary for
the game so far, and the `Collected` line is left out of a maze that had no
collectibles in it.

A console whose code page cannot draw the party poppers gets the plain
congratulations instead, so the message arrives whatever the terminal can
encode:

```
Congratulations! You solved the maze!
```

## Hints

Pressing **h** during play lights up the next step along the solution with a
`?`, then redraws the maze without it a moment later:

```
start
* ***
*o? *
*** *
*   *
*** *
end
time 0:04   moves 1

Use arrow keys or WASD to move. Press 'h' for a hint, 'q' to quit.
```

The path is solved from wherever the player is standing rather than from the
entrance, so a hint still points the way after a wrong turn, and asking for
one in a dead end points back out of it. At the exit there is nothing left to
hint at, so nothing is highlighted.

## Redrawing the Screen

The first frame is drawn whole, in a single call, so the maze, the status
line and the controls arrive together and the screen never stands empty
part-way through a redraw.

Every frame after it draws only what moved. The frame that would be shown is
compared line by line against the frame already on screen, and each line that
differs is written on its own, addressed by the row it belongs on. A step
rewrites the maze rows it touched - two for a step up or down, one for a step
left or right - and the tally that counted it; the blank spacer and the
controls line are left standing, because neither has changed since the game
began. A step into a wall changes nothing, so nothing is written at all, and
a hint lights up one row rather than redrawing the screen to show it and
redrawing it again to take it away.

Every line is addressed by the row it belongs on, the first frame's included,
and no newline is written at all. A newline written on the bottom row of the
screen scrolls everything up one, and a frame as tall as the terminal ends on
that row - which is what a maze capped to fit any terminal with an even
number of rows draws, the lines the frame adds around the maze leaving no row
for the cursor below it. Addressing the rows rather than ending the lines is
what keeps the row a line was drawn on true for the rest of the game. A maze
too big for the terminal to hold is drawn as far down the screen as there is
room for, a row addressed below the last one landing on the last one.

### When the Row a Line Sits on Cannot Be Trusted

Addressing a row holds only while the first line of the frame is on the first
row of the screen, and the game not scrolling the screen itself is not the
same as nothing scrolling it. Two things still do, and neither of them shows
up in the lines of a frame:

- **The window is resized.** Shrinking a terminal pushes its content up, and
  nothing tells the game it happened.
- **A line is wider than the screen.** The controls line is 66 characters and
  no option makes it shorter, while only the maze is measured against the
  terminal's columns, so a terminal narrower than that carries the line onto
  the row below it. On a screen the frame fills, that row is the bottom one,
  and the carry takes the whole screen up exactly as a newline would.

So the terminal is measured once a frame. When its size has changed since the
last frame, or when a line of the frame runs past its last column, the whole
frame is drawn rather than the difference: every row is written, so the
picture is put back wherever it drifted to rather than being repaired one
changed line at a time. A frame with nothing new to say is still written as
nothing, so a still screen on a narrow terminal stays still.

A frame too wide for the screen is redrawn whole every time it changes, which
is the best a terminal with no room for the line can be given: the picture is
the frame it ought to be, sitting one row higher than it would on a terminal
wide enough to hold it. Output that is piped or redirected has no size to
compare against and no last column to run past, so it is drawn exactly as it
always was.

Terminals that read escape sequences are drawn on this way, which is every
terminal on Linux and macOS and every Windows console that takes virtual
terminal processing (Windows 10 and later). Where the escapes would be
printed as text instead, py_maze falls back to clearing the screen through
`cls` or `clear` and writing every frame whole, exactly as it always did.
Setting `TERM=dumb` forces the fallback.

The same escape wipes the screen between the frames of `--animate`, so an
animated search no longer starts a shell for every frame it draws.

## Example Maze

```
start
**** ************
*    *     *    *
**** * *** * ****
*      *   *    *
* ****** *** ****
* *    *     *  *
* * **** ***** **
* *      *      *
* ******** ****** 
*                *
**************** *
end
```
