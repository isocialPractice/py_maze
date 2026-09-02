---
title: Quickstart
summary: >-
  Install it, carve a maze, walk it, and print the way out. Everything else
  is elsewhere.
---

## 1. Get it

py_maze needs Python 3.10 or newer and nothing else.

```bash
cd py_maze
pip install -e .
```

No install? Run it out of the checkout instead, from the folder holding the
`py_maze` package:

```bash
python -m py_maze
```

Every command below works either way. Swap `py_maze` for `python -m py_maze`
if you skipped the install.

## 2. Play a maze

```bash
py_maze
```

A maze is drawn, and you are asked whether you want to play. Press `y`.

- **Arrow keys** or **WASD** move your character, the `o`
- Start at the top, finish at the bottom
- **`h`** lights up the next step when you are stuck
- **`q`** quits, and prints your time and move count

## 3. Pick a size

```bash
py_maze -d easy          # 6 by 6 cells
py_maze -d hard          # 16 by 20 cells
py_maze -w 20 -H 12      # or say it yourself
```

The short flag for height is a capital `-H`. Lowercase `-h` is the help.

## 4. See the way out

```bash
py_maze --solve
```

The shortest route is drawn over the maze as a trail of `.` markers. Add
`--animate` to watch the solver find it a wave at a time.

## 5. Keep a maze worth keeping

Every run prints the seed it carved from:

```
seed: 2024
```

Pass it back with the same size, and the same maze comes out again:

```bash
py_maze -d easy --seed 2024
```

Or write it to a file and play it later:

```bash
py_maze --save maze.txt
py_maze --load maze.txt
```

## That is the whole of it

Six commands and you have used most of py_maze. What is left:

| Next | Where |
| --- | --- |
| Every flag, in one table | [Command-line options](options.md) |
| Other carving algorithms, braiding, collectibles | [Generating a maze](generating.md) |
| Quiet output, JSON, pipes, status codes | [Scripting py_maze](scripting.md) |
| Calling py_maze from Python | [Using py_maze as a library](library.md) |
| The commands at a glance | [Cheat sheet](CHEATSHEET.md) |
