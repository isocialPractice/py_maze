---
title: py_maze
summary: >-
  A command-line maze generator and game written in Python. Generate random,
  solvable mazes and navigate through them using your keyboard.
---

py_maze carves a fresh maze every run, draws it in the terminal out of
asterisks and spaces, and lets you walk it with the arrow keys. It solves
mazes, saves them, reads them back, writes them as JSON for another program,
and imports as a package when you would rather call it than play it.

It needs Python 3.10 and nothing else. There are no dependencies to install
and no service to start.

```bash
pip install -e .
py_maze
```

<!-- the cards are written as HTML for the grid the stylesheet lays them out
     in, and a raw href is not one of the Markdown links the site rewrites
     from .md to .html, so these name the built page directly. Every one of
     them is linked again as Markdown under "Where to go next" below, which
     is what a reader on GitHub follows. -->
<ul class="cards">
<li>
<a href="QUICKSTART.html">Quickstart</a>
<p>Install it, run it, and win a maze, in about a minute.</p>
</li>
<li>
<a href="options.html">Command-line options</a>
<p>Every flag, its short form, its default and what it does.</p>
</li>
<li>
<a href="library.html">Use it as a library</a>
<p>Generate, solve and draw mazes from your own code.</p>
</li>
<li>
<a href="CHEATSHEET.html">Cheat sheet</a>
<p>The commands, options and shapes, dense and scannable.</p>
</li>
</ul>

## Features

- **Random Maze Generation**: Every run carves a fresh maze, at random unless
  you set a seed
- **Interactive Gameplay**: Navigate through mazes using arrow keys or WASD
- **Cross-Platform**: Works on Windows, Linux, and macOS
- **Always Solvable**: Every generated maze is guaranteed to have a path from
  start to end
- **Difficulty Presets**: Easy, normal and hard maze sizes, or set your own
- **Three Carving Algorithms**: Winding backtracker corridors, Prim's more
  open branching, or the straight runs and rooms of recursive division
- **Braiding**: Open the dead ends and the maze gains a second way through
- **Repeatable Mazes**: Every run reports its seed, so a good maze can be
  generated again
- **Built-In Solver**: Print the shortest way through, or watch the search
  find it
- **Hints**: Stuck mid-game? One key lights up the next step
- **Timer and Move Counter**: Both run while you play and are summarized when
  you finish
- **Collectibles**: Scatter pickups through the maze and see the tally at the
  end
- **Save and Load**: Keep a maze in a file and play it again later
- **Scriptable**: A quiet mode, JSON output, standard input and output, and a
  status code for each thing that can go wrong
- **Importable Package**: Generate, solve and draw mazes from your own code,
  with the terminal machinery kept out of the way

## A maze, solved

```bash
python -m py_maze -d easy --seed 2024 --solve
```

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

## Where to go next

| If you want to | Read |
| --- | --- |
| Get it running now | [Quickstart](QUICKSTART.md) |
| Install it properly | [Installation](installation.md) |
| Know what a flag does | [Command-line options](options.md) |
| Change how a maze is carved | [Generating a maze](generating.md) |
| Keep a maze, or read one back | [Saving and loading](saving.md) |
| Print or watch the solution | [Solving the maze](solving.md) |
| Play, and read the status line | [How to play](playing.md) |
| Call py_maze from a script | [Scripting py_maze](scripting.md) |
| Call py_maze from Python | [Using py_maze as a library](library.md) |
| Write a file py_maze will load | [The save file format](save-format.md) |
| Know how the carving and solving work | [How it works](how-it-works.md) |
| Work on py_maze itself | [Development](development.md) |
