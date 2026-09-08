# Known Bugs

Defects that are understood but not yet fixed. Each section records how to
reproduce the bug, what is known about it and what is not.

## 2026-09-08: the timed key reader strands keys typed inside one tick

Found reviewing 2.3.0, which gave the game loop a reader that waits a moment
for a keypress rather than waiting for one however long it takes. The POSIX
branch waits on one thing and reads from another.

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

### Reproducing it

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
- The suite cannot see it. `TestPosixTimedInput` replaces `select` with a
  mock and `sys.stdin` with a `FakeStdin` handing back one character per
  read, so the wrapper that does the chunking is not in the picture at all,
  and all 626 tests pass with the fault in place.

### What is not known

- Which fix the project wants. Both candidates reach outside the timed
  reader:
  1. Read through the descriptor rather than through `sys.stdin`, so the
     thing waited on and the thing read from agree. `read_key_sequence` is
     shared with `read_key_posix`, so it would have to be told how to read
     rather than assuming `sys.stdin`, and both readers would want
     re-verifying against a real terminal.
  2. Give the terminal the deadline instead of `select`, setting `VMIN` 0 and
     `VTIME` through `termios` so the read itself times out. There is then
     nothing left to be out of step with, but raw mode is entered in
     `in_raw_mode` for every reader, and whatever it sets it sets for all of
     them.
- How it behaves on a real terminal rather than on a model of one.
  Everything above is reasoned from the buffering and measured on a pipe; no
  POSIX console has been driven, the machine reviewing it being Windows.

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
