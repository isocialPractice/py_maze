# Known Bugs

Defects that are understood but not yet fixed. Each section records how to
reproduce the bug, what is known about it and what is not.

## Resolved in 1.0.0a9: the line after a wrapped one written onto the wrap's row

Found reviewing 1.0.0a8 on a real console. A line carried onto the row below
held that row only until the next line of the frame was written, which was
addressed to it. In quest mode with `--collectibles 9` the tally runs to 47
characters, so every console under 48 columns wraps it - and the blank
spacer that follows it in the frame was written at column 0 of the row the
tally had been carried onto, taking the row with it.

Read off a real conhost at seed 2024.
`python -m py_maze --mode quest --collectibles 9 --seed 2024` on a 39 by 24
console drew the tally whole and the row holding `tems 0/3` came back as 39
spaces. The same run at 29, 24 and 20 columns lost
`ed 0/9   items 0/3`, `llected 0/9   items 0/3` and
`  collected 0/9   items 0/3`; `--mode plain` and `--mode chase` with
`--collectibles 9` lost `ed 0/9` at 29 columns and `   collected 0/9` at 20.
At 29 columns the tally read `collect` with no number on it at all.
Isolated with no game in it, writing the frame's three escapes at the rows
`frame_diff` gave them into an allocated 39 column console, the console did
carry the tail onto the row below and did hold it there until the blank
line's escape was written over it.

`frame_diff` addressed every line by its place in the list -
`ANSI_ROW % row` for `row, line in enumerate(current, start=1)` - so from
the first wrapped line onward the list and the screen had drifted apart by
one. A blank line is not exempt from the clear-line escape:
`line_fills_row` returns False for an empty line by design, because an empty
line occupies its row without writing to any column of it.

Fixed in 1.0.0a9 by addressing a line by the screen row it belongs on, which
is the first row plus the rows every line above it occupies - what
`frame_height` has counted since 1.0.0a6. The rows of a line the difference
path skipped count toward where the next written line goes exactly as a
written line's do, since a line left alone is still occupying the rows it
was drawn on, and a frame with no terminal to measure is addressed by its
line count as before. The wipe at the end of the call is measured in the
rows its dropped lines were occupying and starts on the row below the
frame's own last one, so it and the addressing agree about where the frame
ends however much of it wrapped.

The suite's own screen model reproduced the fault exactly and was never
asked. `TerminalScreen` has modelled width and the pending wrap since
1.0.0a8, so replaying `frame_diff`'s output through it at 39 columns
returned the row empty where `tems 0/3` belonged. The 1183 tests passed on
a fault their one instrument could see, which is the reason worth recording:
an instrument is only worth what is asked of it.

## Resolved in 1.0.0a9: the tally broken inside a word on a console that wrapped it

The fourth round of the wrapped-foot family, and recorded apart from the row
above because the cause is different: nothing was erased, the break simply
fell where the console put it. `MazeGame.render` padded the last line of the
frame out to the end of its row so the break would land on a space, on the
premise named in its own comment - "the last line of the frame is the only
one long enough to be carried onto the row below". The reserve added in
1.0.0a8 disproved that premise in the same version it was written: the tally
reaches 47 characters with a collectible count and an inventory on it, which
is why `fit_to_terminal` reserves a row for it.

So on a 29 column console the tally read `collect` with `ed 0/9   items 0/3`
on the row below, and `docs/playing.md` told a reader the opposite with
nothing qualifying it - "A line carried onto the row below is broken on a
space rather than in the middle of a word".

Fixed in 1.0.0a9 by padding both lines of the foot a console can be narrower
than, which are the two `fit_to_terminal` reserves a wrapped row for.
`wrap_on_spaces` hands a line back unpadded where the padding would need a
row the console's own break does not, so the rows either line occupies are
unchanged, the reserve is the same either way and the maze is fitted exactly
as it was - at 24 columns the quest tally is one such line, and the
console's break inside `collected` stands there. The comment resting the
padding on the last line of the frame went with the fix, and the page says
what a line keeps its own break for.

## Resolved in 1.0.0a8: the clear-line escape eating a line that filled its row

Found reviewing 1.0.0a7 on a real console. A frame line exactly as many
characters long as the console is wide was drawn one character short, and the
character lost was always the last one. At 60 columns the plain controls line
read `... 'q' to quit` with no full stop, and at 79 columns the quest line
read the same way - which are the widths each line had been shortened to fit,
so each landed on the one width that broke it. At 59, 61, 78 and 80 columns
both were correct.

`frame_text` and `frame_diff` wrote `ANSI_CLEAR_LINE` after every line, so
that a shorter line never left the tail of a longer one beside it. On the row
a line fills to the last column there is nothing to clear, and the escape is
not harmless there: a console that has just had its last column written
leaves the cursor *on* that column with the wrap pending rather than past it,
and `\x1b[K` erases from where the cursor stands. Isolated from the game with
a plain `WriteConsoleW` into an allocated 60 column console, 60 characters
read back as 60, and 60 characters followed by `\x1b[K` read back as 59 with
a space in the last cell. A 60 character ruler behaved the same, so it was
the width and not the text.

Fixed in 1.0.0a8 by `line_fills_row`, which both functions now ask before
writing the escape: a line whose length divides by the terminal's width ends
flush with the last column, has no tail beside it to clear, and is written
without it. A wrapped line is measured by the final row it is carried onto,
which is the only row the escape ever follows.

The suite could not see any of it, and that is the half worth recording.
`TerminalScreen` modelled the cursor as moving *past* the last column when a
write filled the row - its `put` said so in a comment, that "a line filling
it exactly wraps nothing" - and its `K` branch truncated the row to
`self.column - 1`, which for a full row is the whole row. The model was right
that a full row does not wrap and wrong that the cursor had left the edge,
and `\x1b[K` reads the cursor rather than the wrap. The model holds a pending
wrap now, so a write ending on the last column leaves the cursor on it and a
following `K` erases it, which is what the fix is measured against.

## Resolved in 1.0.0a8: the maze carved a row too tall for the foot it was measured against

The third round of the wrapped-foot family recorded below, and the same
mistake each time: a line of the play screen's foot was ruled out of the
reserve on a figure that was not the figure it reaches. `fit_to_terminal`
added `frame_height([controls], size) - 1` and ruled the rest of the foot out
in a comment - "the status line runs to 31 characters with an inventory on
it". 31 is the quest tally alone; `status_line` puts a collectible tally
beside it, so `--mode quest --collectibles 9` draws
`time 0:03   moves 4   collected 2/9   items 1/3` at 47 characters, and 50
once the clock passes an hour.

Swept over 20 to 120 columns, plain and chase carved a row over from 20 to 29
columns and quest from 20 to 39, two rows over on the narrowest of them.
`python -m py_maze --mode quest --collectibles 9 --seed 2024` on a 39 by 24
console carved 9 by 8 and built a frame standing 25 rows tall: `fit_frame`
cut it on the very first frame, the `end` marker read `end 1 row below`, and
the exit was off screen with no resize anywhere in it.

Fixed in 1.0.0a8 by reserving the rows the whole foot occupies rather than
the controls line's alone. Both lines of the foot that can outrun the console
are settled before a maze is carved - the mode decides the controls line, and
the mode with `--collectibles` decides how wide the tally beside it will be -
so `mode_status` builds the tally the first frame will draw and
`fit_to_terminal` takes it as its `status` argument beside `controls`. The
comment ruling the status line out went with it. The two lines the foot has
left are the `end` marker and a blank spacer, and neither reaches the edge of
a console with room for a maze in it.

`test_a_maze_carved_for_a_console_is_one_it_can_show_whole` asserts the
property end to end, now with a tally carrying both of its counts and with
the widths carried down to 20 - the shape and the width this came back on.

## Resolved in 2.4.0: the timed key reader stranding keys typed inside one tick

Found reviewing 2.3.0, which gave the game loop a reader that waits a moment
for a keypress rather than waiting for one however long it takes: the POSIX
branch waited on one thing and read from another. Fixed in 2.4.0 by the first
of the two candidates below - the readers take their characters off the
descriptor `select` polls, through `os.read`, rather than through the text
wrapper `sys.stdin` is. What the reader is not asked for is left in the
kernel queue, which is the queue the wait looks at, so there is nowhere left
for a key to be held. The suite models the whole stack now rather than the
top of it: `FakeStdin` chunks the way a wrapper does and answers a descriptor
read separately, so a reader that goes through the wrapper fails the tests
that a reader going to the descriptor passes.

What follows is the fault as it was measured, kept because the reasoning
about the buffering is what the fix was chosen from.

### What happens

`key_waiting` calls `select.select([sys.stdin], [], [], timeout)`, which asks
the kernel whether the file descriptor behind standard input has anything on
it. `read_key_sequence` then reads with `sys.stdin.read(1)`, and `sys.stdin`
is a `TextIOWrapper` over a `BufferedReader`: it does not read one byte, it
reads a chunk, decodes the whole of it and hands back the first character.
Every character after the first stays in the wrapper, in userspace, where
`select` cannot see it.

A terminal in raw mode has `VMIN` 1 and `VTIME` 0, so one read returns every
byte queued rather than one byte. Two keys typed inside the same quarter of a
second are therefore delivered in a single read, and the second is stranded:
`select` reports nothing waiting, `read_key_timed_posix` answers `None`, and
the loop ticks on drawing a clock over a keypress it is holding but will not
look at.

### Reproducing it, before 2.4.0

Play on Linux or macOS and type two movement keys quickly, or simply hold one
down and let the keyboard repeat:

```console
py_maze --play
```

The player takes one step and stops. Nothing more happens until the next key
is pressed, and that press plays the stranded key rather than itself, so from
then on the game is a keypress behind for the rest of the run.

### What is known

The chunking is the wrapper's rather than the terminal's, so it can be
measured without one. Three characters written to a pipe and read back
through the same stack `sys.stdin` is built from:

```python
>>> first = f.read(1)      # what read_key_sequence is handed
'd'
>>> os.read(r, 10)         # what select() has to poll
b''
>>> f.read(1), f.read(1)   # where the other two went
('d', 'a')
```

- The untimed reader never had this. `read_key_posix` blocks in
  `sys.stdin.read(1)`, which answers out of the wrapper's own buffer, so a
  character read ahead is returned on the next call rather than waited for at
  a descriptor that will never mention it.
- The Windows branch is not affected. `read_key_timed_windows` polls
  `msvcrt.kbhit` and `msvcrt.getch` reads the same console buffer, so the
  thing waited on and the thing read from are one thing.
- The suite could not see it. `TestPosixTimedInput` replaced `select` with a
  mock and `sys.stdin` with a `FakeStdin` handing back one character per
  read, so the wrapper that does the chunking was not in the picture at all,
  and all 626 tests passed with the fault in place.

### The two candidates, and which was taken

1. **Read through the descriptor rather than through `sys.stdin`**, so the
   thing waited on and the thing read from agree. `read_key_sequence` is
   shared with `read_key_posix`, so it has to be told how to read rather
   than assuming `sys.stdin`.
2. Give the terminal the deadline instead of `select`, setting `VMIN` 0 and
   `VTIME` through `termios` so the read itself times out. There is then
   nothing left to be out of step with, but raw mode is entered in
   `in_raw_mode` for every reader, and whatever it sets it sets for all of
   them.

The first was taken. `read_key_sequence` takes the reader it should use,
`stdin_reader` builds one from the descriptor behind standard input, and
`read_key_posix`, `read_key_timed_posix` and `read_response` all pass it, so
the three POSIX readers agree with each other as well as with the wait.
Standard input with no descriptor to go to - a `StringIO`, an object
standing in for one - buffers nothing of its own and is read as it always
was. The second was left alone for the reason recorded above: it reaches
`in_raw_mode`, which every reader shares.

### What is still not known

- How it behaves on a real terminal rather than on a model of one. The fault
  was reasoned from the buffering and measured on a pipe, and the fix is
  measured against a `FakeStdin` that chunks the way a wrapper does; no
  POSIX console has been driven, the machine reviewing it being Windows.
  That verification is queued in `TODO.md` under **UI/UX and Screen
  Drawing**, beside the Windows console one already there.

## Resolved in 2.3.0: the partial redraw drifting on a scroll the game did not cause

The partial redraw drifting once anything else scrolled the screen was
recorded here against 2.2.6 and fixed in 2.3.0: the terminal is measured
every frame, and the whole frame is drawn rather than the difference whenever
its size has changed since the last one or a line of it runs past the last
column. Both triggers this file recorded - a window resized mid-game, and a
terminal narrower than the 66 character controls line - are covered by that,
and the suite's `TerminalScreen` was given a width first so the wrap it could
not model before is what the fix is measured against.

What is still missing is a measurement against a real console rather than
against the suite's model of one. That is queued in `TODO.md` under **UI/UX
and Screen Drawing** rather than here, being a verification that has not been
written rather than a defect that has been understood.

**1.0.0a6 finished the narrow-terminal half of it.** Drawing the whole frame
put the picture back; it did not stop the frame being a row too tall for the
screen, because the fitting counted lines and the console draws rows. So the
wrap kept taking the screen up as the last line went out, every frame paying
for a full rewrite and a hardware scroll. `fit_frame` measures the frame with
`frame_height` now and gives up a maze row for every row a wrap needs, and
the frame following a wrapping one is drawn whole as well - the rows that
moved belong to the frame already on screen, which the frame replacing it
cannot tell from its own lines.

**1.0.0a7 took the rest of the line count out.** `fit_frame` was converted
and the four other places reading a line count as a screen row were not: the
wipe that clears the rows a shorter frame gave up, the rows an ending is
reserved, and the two cursor parks under a frame. The wipe is what a player
saw - quitting a game on a 60 column console left the second row of the
controls line under the summary, with nothing above it. The parks cancelled
against each other at most widths, which is why nothing else showed. All
five measure rows now.

**1.0.0a9 found the sixth.** Those five each measure a whole frame, and the
one place left counting lines was `frame_diff` addressing the lines inside
one: a line went out at `ANSI_ROW % index`, so the line after a wrapped one
landed on the row the wrap was sitting on. It is the site where a wrap
actually costs a row, and the only one of the six where two counts cannot
cancel - the drift opens at the first wrapped line and runs to the end of the
frame. The section at the top of this file records what a player saw.

The maze a run carves is sized against those rows as well, so a console wide
enough for the mode being played is handed a maze it can show whole instead
of one `fit_frame` cuts a window out of on every frame. The controls line
itself lost the word "Press" in the same version, bringing it to 60
characters - a 60 column console exactly - so the narrowest console anyone
still runs stops paying a maze row for the wrap. Where a window is still cut,
the `start` and `end` markers name the maze rows off screen past them rather
than sitting against an interior row as though the maze ended there.
