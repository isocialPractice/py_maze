#!/usr/bin/env python3
"""The inventory a quest maze is played with, and what carrying it opens.

A quest turns the walk through a maze into a chain of errands. The way on
is shut by a **door**, the thing that opens it is in a **box**, and the box
is somewhere behind the door in the part of the maze the player can already
reach. Opening door one reaches the part of the maze box two is in, and so
on, so a quest maze is played for what is in it rather than only for the
way out.

Nothing here draws, reads a key or owns a clock. :class:`Quest` is the
inventory and the two sets of cells, :func:`place_quest` lays a chain of
them into a maze that already exists, and :class:`py_maze.MazeGame` is what
asks whether the player may step somewhere.

A door is an ordinary open cell of the grid with a door standing on it, the
way a collectible is an open cell with a pickup on it, so a quest maze is
the same grid :mod:`py_maze.generation` carves and :mod:`py_maze.solving`
walks. What a quest adds is a reason the player cannot walk it yet.

The picture a text save draws has no room for a quest: a marker says there
is a door, and nothing in a picture says which item opens it. So the
picture refuses those markers exactly as it refuses any other character it
was not drawn with, and the JSON document carries the chain under its
``quest`` key instead - see :mod:`py_maze.saves`.
"""

import random

from .grid import open_neighbors
from .solving import solve_maze

__all__ = [
    'DEFAULT_QUEST_STAGES',
    'MAX_QUEST_STAGES',
    'MIN_QUEST_STAGES',
    'Quest',
    'door_cells',
    'place_quest',
    'reachable',
]

# how many door-and-box stages a quest runs to. One is a maze with a
# single errand in it; the ceiling is what a maze the size of the
# largest preset has room to space out along its route
MIN_QUEST_STAGES = 1
MAX_QUEST_STAGES = 9

# the reasonable chain: three errands, so the quest is the shape of the
# maze rather than a single locked door on the way to the exit
DEFAULT_QUEST_STAGES = 3


def reachable(grid, start, blocked=()):
    """Walk every cell reachable from one cell with some of them shut.

    It is the flood fill a door needs: a closed door is a cell the
    player cannot pass through, so the part of the maze beyond it is
    not reachable yet however open the corridors there are.

    Args:
        grid: 2D list of booleans (True = wall, False = path)
        start: The (x, y) to walk out from. A blocked cell is one that
            cannot be walked *into*, so a walk that begins on one
            leaves it the way it leaves any other cell
        blocked: Cells that cannot be walked through, closed doors being
            what this is for

    Returns:
        set: Every (x, y) that can be walked to, the start included.
        Empty for a start that is not an open cell of the maze
    """

    x, y = start
    if not (0 <= y < len(grid) and 0 <= x < len(grid[0])) or grid[y][x]:
        return set()

    shut = set(blocked)
    found = {(x, y)}
    pending = [(x, y)]

    while pending:
        here = pending.pop()
        for cell in open_neighbors(grid, *here):
            if cell in found or cell in shut:
                continue
            found.add(cell)
            pending.append(cell)

    return found


def door_cells(path, stages):
    """Space a quest's doors out along the way through a maze.

    The doors go on the route itself rather than beside it, so each one
    is on the way to the exit rather than on a branch the player can
    walk around. They are spread evenly: a quest of three stages shuts
    the route a quarter, a half and three quarters of the way along.

    Args:
        path: Cells from the entrance to the exit, as
            :func:`py_maze.solving.solve_maze` returns them
        stages: How many doors to place

    Returns:
        list: The cells to shut, in the order they are met. Neither end
        of the route is among them, and a route with no room for as
        many doors as were asked for gets as many as it has room for
    """

    length = len(path)
    chosen = []
    seen = set()

    for stage in range(1, stages + 1):
        index = round(stage * (length - 1) / (stages + 1))
        if not 0 < index < length - 1 or index in seen:
            continue
        seen.add(index)
        chosen.append(path[index])

    return chosen


def box_spot(grid, candidates, rng):
    # pick the cell a box is hidden on, preferring a dead end
    #
    # A box at the end of a blind corridor is a box the player goes
    # looking for; a box in the middle of the route is one they walk
    # over on the way past. Either is a quest, and the first is the
    # better one, so the dead ends are tried before the rest.
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #     candidates: The cells a box may go on
    #     rng: Random number generator to draw the place from
    #
    # Returns:
    #     tuple: The (x, y) chosen, or None when there is nowhere to
    #     put one

    if not candidates:
        return None

    blind = [cell for cell in candidates
             if sum(1 for _ in open_neighbors(grid, *cell)) == 1]

    # sorted before the draw, a set having no order of its own: the same
    # seed has to hide the box in the same place every run
    return rng.choice(sorted(blind or candidates))


class Quest:
    """The doors of a maze, the boxes that open them and what is carried."""

    def __init__(self, boxes=None, doors=None, guide=None):
        """Hold a chain of doors and boxes, with nothing collected yet.

        Args:
            boxes: Mapping of each box's (x, y) to the item in it, as a
                whole number naming the stage it belongs to
            doors: Mapping of each door's (x, y) to the item that opens
                it, numbered to match the box holding it
            guide: The (x, y) the hint-giving character waits on, or
                None for a quest nobody is there to explain
        """

        self.boxes = dict(boxes or {})
        self.doors = dict(doors or {})
        self.guide = tuple(guide) if guide is not None else None

        # what the player is carrying, and the doors already opened with
        # it. An item is kept once it is picked up: a door that has been
        # opened stays open, so nothing is ever spent
        self.carried = set()
        self.opened = set()

    @property
    def stages(self):
        """How many doors the quest runs to, each with its own box."""

        return len(self.doors)

    def closed_doors(self):
        """List the doors still shut.

        Returns:
            list: Their (x, y), in reading order, so the same quest
            draws the same picture every time
        """

        return sorted((cell for cell in self.doors
                       if cell not in self.opened),
                      key=lambda cell: (cell[1], cell[0]))

    def drawn(self):
        """Report the three things of a quest that are drawn on a maze.

        Returns:
            tuple: (doors, boxes, guide) - the doors still shut, the
            boxes still holding something and the cell the guide waits
            on, ready for :func:`py_maze.quest_overlay`. One call, so
            the picture a run prints and the picture a game draws are
            built from the same reading
        """

        return self.closed_doors(), set(self.boxes), self.guide

    def unlock(self, cell):
        """Open the door on a cell, when the item that opens it is carried.

        Args:
            cell: The (x, y) the player is trying to step onto

        Returns:
            bool: True when the cell may be stepped onto, which is every
            cell with no door on it, every door already opened, and a
            closed door whose item is being carried - that one is opened
            here. False for a closed door whose item is still in its box
        """

        item = self.doors.get(tuple(cell))
        if item is None or tuple(cell) in self.opened:
            return True

        if item not in self.carried:
            return False

        self.opened.add(tuple(cell))
        return True

    def open_box(self, cell):
        """Open the box on a cell and put what is in it in the inventory.

        Args:
            cell: The (x, y) the player is standing on

        Returns:
            The item that was in the box, and None when there was no box
            there. A box is opened once: the cell is empty afterwards
        """

        item = self.boxes.pop(tuple(cell), None)
        if item is not None:
            self.carried.add(item)

        return item

    def stage(self):
        """Report which stage of the quest the player is on.

        Returns:
            int: The lowest-numbered door still shut, which is the one
            the player is working towards. None once every door is open
        """

        shut = [self.doors[cell] for cell in self.doors
                if cell not in self.opened]

        return min(shut) if shut else None

    def finished(self):
        """Report whether every door has been opened.

        Returns:
            bool: True when nothing is left to unlock, so the only thing
            between the player and the exit is the walk to it
        """

        return self.stage() is None

    def target(self):
        """Point at whatever the next step of the quest is at.

        Returns:
            tuple: The (x, y) of the box holding the item the player
            still needs, or of the door that item opens once it is
            carried. None once every door is open, there being nothing
            left to point at
        """

        item = self.stage()
        if item is None:
            return None

        if item not in self.carried:
            for cell, held in self.boxes.items():
                if held == item:
                    return cell

        for cell, needed in self.doors.items():
            if needed == item and cell not in self.opened:
                return cell

        return None

    def task(self):
        """Say what the next step of the quest is, in words.

        Returns:
            str: The errand in front of the player - the box to find,
            the door it opens, or that the way out is clear. It names
            the task rather than the route, so it says nothing about
            where the exit is
        """

        item = self.stage()
        if item is None:
            return "every door is open - the way out is yours to find"

        if item not in self.carried:
            return ("item %d is still in its box, and the box is in the "
                    "part of the maze you can already reach" % item)

        return "you are carrying item %d, and it opens the door ahead" % item


def place_quest(grid, stages=DEFAULT_QUEST_STAGES, rng=None, path=None,
                taken=()):
    """Lay a chain of doors and boxes into a maze that already exists.

    Each door shuts the route at a point the one before it opened, and
    each box is hidden in the part of the maze that is reachable at the
    time it is wanted: box one before door one, box two between door one
    and door two, and so on. A quest laid this way can always be
    finished, and never before the stage it belongs to.

    The chain only holds for a maze with one route through it.
    ``--braid`` opens a second way round, and a door with a way round it
    gates nothing, so a braided quest maze can be walked out of without
    opening anything.

    Args:
        grid: 2D list of booleans (True = wall, False = path). It is not
            modified: a door stands on an open cell rather than changing
            one
        stages: How many door-and-box pairs to lay
        rng: Random number generator the boxes are hidden with, so a
            seeded generator hides them in the same places every run.
            Defaults to the shared random module
        path: The route through the maze, when the caller has already
            solved it. Searched for here when it is not given
        taken: Cells something else is already on - the collectibles -
            so a box and a pickup never land on one cell and draw over
            each other

    Returns:
        Quest: The chain, with nothing collected yet. None for a maze
        with no way through, for a route too short to space a door
        along, and for a quest of no stages at all - all three are a
        maze with nothing to do in it rather than a quest of nothing
    """

    if stages <= 0:
        return None
    if rng is None:
        rng = random
    if path is None:
        path = solve_maze(grid)
    if not path or len(path) < 3:
        return None

    spare = set(taken) | {path[0], path[-1]}
    doors = {cell: stage
             for stage, cell in enumerate(door_cells(path, stages), start=1)}
    if not doors:
        return None

    # the guide waits just inside the entrance, so the player meets it
    # on the first step rather than hunting for it
    guide = next((cell for cell in path[1:]
                  if cell not in doors and cell not in spare), None)
    if guide is not None:
        spare.add(guide)

    boxes = {}
    shut = set(doors)
    behind = set()

    for cell in sorted(doors, key=doors.get):
        # what the player can reach with every door up to this one
        # opened, and the part of it the stage before could not
        region = reachable(grid, path[0], shut)
        fresh = region - behind - spare - set(doors) - set(boxes)

        spot = box_spot(grid, fresh or
                        region - spare - set(doors) - set(boxes), rng)
        if spot is None:
            # nowhere left to hide one, so this door and every door
            # after it would never open. The quest is the stages that
            # did fit rather than a chain with a break in it
            missed = doors[cell]
            for later in [door for door in doors
                          if doors[door] >= missed]:
                del doors[later]
            break

        boxes[spot] = doors[cell]
        behind = region
        shut.discard(cell)

    if not doors:
        return None

    return Quest(boxes, doors, guide)
