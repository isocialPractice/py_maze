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

Each move redraws the whole screen. The cursor is put back at the top left
with an ANSI escape sequence and the new frame is written over the old one in
a single call, so the maze, the status line and the controls are replaced
together and the screen never stands empty part-way through a redraw.

Terminals that read escape sequences are drawn on this way, which is every
terminal on Linux and macOS and every Windows console that takes virtual
terminal processing (Windows 10 and later). Where the escapes would be
printed as text instead, py_maze falls back to clearing the screen through
`cls` or `clear`, exactly as it always did. Setting `TERM=dumb` forces the
fallback.

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
