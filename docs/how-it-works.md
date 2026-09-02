---
title: How it works
summary: >-
  What each carving algorithm actually does, what braiding undoes, and why
  the solver always comes back with the shortest way through.
---

The maze generator carves with the **recursive backtracking algorithm** by
default:

1. Start with a grid full of walls
2. Begin at the starting cell and mark it as visited
3. Randomly choose an unvisited neighbor
4. Remove the wall between the current cell and chosen neighbor
5. Move to the chosen neighbor and repeat
6. If no unvisited neighbors exist, backtrack to the previous cell
7. Continue until all cells have been visited

This algorithm ensures that every maze generated has exactly one path between any two points, making it both challenging and always solvable!

`--algorithm` swaps in one of the other two, and each holds to that same
promise of one path between any two points:

- **Prim's** grows the maze outward from one cell. Every wall between a
  carved cell and an uncarved one is a candidate, and each step draws one at
  random out of the whole growing edge, so the maze spreads evenly rather
  than wandering: it branches often and its dead ends are short.
- **Recursive division** builds walls instead of carving passages. It starts
  from an empty floor, walls it in two with a single gap to cross by, and
  divides each half the same way until what is left is a corridor one cell
  wide. Each wall runs the whole way across, which is where its straight
  corridors and squared-off rooms come from.

Each algorithm is one module under `py_maze/algorithms/`, and each is the
same function to call: a size and a random number generator in, a carved grid
out. Adding a fourth is a module there and a line in the registry, with
nothing in `MazeGenerator` to change.

Each call to `generate()` starts from step 1 again: the carver is handed a
fresh grid and a seeded generator goes back to the same random numbers, so
one generator asked for its maze twice hands back the same maze twice rather
than carving further into the one it already made.

`--braid` is the one thing that undoes a carver's work. A dead end is a cell
with one way in and no way on; braiding knocks a wall out of a share of them
so each joins the corridor behind it. That turns the single route through the
maze into a network of routes, which is what leaves the solver a shortest way
to find rather than the only way there is.

The solver behind `--solve`, `--animate` and the in-game hints is a
**breadth-first search**: it spreads out from the start one step at a time,
recording the cell each new cell was reached from, until it arrives at the
exit. Following those records back from the exit gives the path, and because
every cell one step away is examined before any cell two steps away, the path
that comes back is always the shortest one. `--animate` draws one frame per
step outward, which is exactly the wave the search is working on.

A carved maze has only one route through, so the shortest route is the only
route, and the same solver still finds the way out from anywhere a player has
wandered to. On a maze braided with `--braid` there is more than one route,
and the one that comes back is the shortest of them.
