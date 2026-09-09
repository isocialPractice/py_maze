# Known Bugs

Defects that are understood but not yet fixed. Each section records how to
reproduce the bug, what is known about it and what is not.

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
