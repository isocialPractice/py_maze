#!/usr/bin/env python3
# test_py_maze
# Unit tests for the py_maze generator, game and command-line parser.

import argparse
import collections
import contextlib
import io
import os
import re
import unittest
from unittest import mock

import py_maze


def terminal_size(columns, lines):
    # build a terminal size for fit_to_terminal to measure against
    #
    # Args:
    #     columns: Characters across
    #     lines: Rows down
    #
    # Returns:
    #     os.terminal_size: The same type shutil.get_terminal_size returns

    return os.terminal_size((columns, lines))


def grid_from_strings(rows):
    # build a maze grid from a picture of the maze
    #
    # Args:
    #     rows: Sequence of equal-length strings, '*' for wall, ' ' for path
    #
    # Returns:
    #     2D list of booleans (True = wall, False = path)

    return [[char == '*' for char in row] for row in rows]


def find_open_cells(grid, x, y):
    # breadth-first flood fill from a starting position
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #     x: Starting column
    #     y: Starting row
    #
    # Returns:
    #     set: Every (x, y) reachable from the start without crossing a wall

    height = len(grid)
    width = len(grid[0])
    seen = {(x, y)}
    queue = collections.deque([(x, y)])

    while queue:
        current_x, current_y = queue.popleft()
        for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            nx, ny = current_x + dx, current_y + dy
            if (0 <= nx < width and 0 <= ny < height and
                    not grid[ny][nx] and (nx, ny) not in seen):
                seen.add((nx, ny))
                queue.append((nx, ny))

    return seen


# Fake stdin used to drive the POSIX keyboard branch on any platform.
class FakeStdin:
    def __init__(self, keys):
        # Args:
        #     keys: The characters read() hands back, in order

        self.keys = keys
        self.position = 0

    def fileno(self):
        return 0

    def read(self, count):
        chunk = self.keys[self.position:self.position + count]
        self.position += count
        return chunk


# Fake termios module recording every terminal setting written back.
class FakeTermios:
    TCSADRAIN = 'tcsadrain'
    SETTINGS = 'saved-terminal-settings'

    def __init__(self):
        self.restored = []

    def tcgetattr(self, fd):
        return self.SETTINGS

    def tcsetattr(self, fd, when, settings):
        self.restored.append((fd, when, settings))


# Fake msvcrt module used to drive the Windows keyboard branch on any platform.
class FakeMsvcrt:
    def __init__(self, keys, idle_polls=0):
        # Args:
        #     keys: Bytes objects getch() hands back, in order
        #     idle_polls: How many times kbhit() reports "no key waiting"
        #     before the first key arrives

        self.keys = list(keys)
        self.idle_polls = idle_polls
        self.kbhit_calls = 0

    def kbhit(self):
        self.kbhit_calls += 1
        if self.idle_polls > 0:
            self.idle_polls -= 1
            return False
        return True

    def getch(self):
        return self.keys.pop(0)


class TestMazeGenerator(unittest.TestCase):
    def test_grid_dimensions_include_walls(self):
        # a maze of W by H cells renders as W*2+1 by H*2+1 characters
        grid = py_maze.MazeGenerator(width=6, height=4).generate()

        self.assertEqual(len(grid), 4 * 2 + 1)
        for row in grid:
            self.assertEqual(len(row), 6 * 2 + 1)

    def test_default_dimensions(self):
        grid = py_maze.MazeGenerator().generate()

        self.assertEqual(len(grid), 11 * 2 + 1)
        self.assertEqual(len(grid[0]), 9 * 2 + 1)

    def test_entrance_and_exit_are_open(self):
        grid = py_maze.MazeGenerator(width=5, height=5).generate()

        self.assertFalse(grid[0][1], "entrance should be open at the top")
        self.assertFalse(grid[-1][-2], "exit should be open at the bottom")

    def test_border_is_sealed_apart_from_entrance_and_exit(self):
        grid = py_maze.MazeGenerator(width=5, height=5).generate()
        top, bottom = grid[0], grid[-1]

        self.assertTrue(all(cell for x, cell in enumerate(top) if x != 1))
        self.assertTrue(
            all(cell for x, cell in enumerate(bottom) if x != len(bottom) - 2))
        for row in grid:
            self.assertTrue(row[0], "left border should be walled")
            self.assertTrue(row[-1], "right border should be walled")

    def test_every_maze_is_solvable(self):
        # the entrance must reach the exit, for a spread of sizes and seeds
        for width, height in [(2, 2), (3, 7), (9, 11), (12, 4)]:
            for seed in range(5):
                py_maze.random.seed(seed)
                grid = py_maze.MazeGenerator(width, height).generate()
                reachable = find_open_cells(grid, 1, 0)

                self.assertIn(
                    (width * 2 - 1, height * 2), reachable,
                    "no path from entrance to exit for %dx%d seed %d"
                    % (width, height, seed))

    def test_every_cell_is_carved(self):
        # recursive backtracking visits every cell, so no cell stays walled
        width, height = 6, 5
        grid = py_maze.MazeGenerator(width, height).generate()
        reachable = find_open_cells(grid, 1, 0)

        for cell_y in range(1, height * 2, 2):
            for cell_x in range(1, width * 2, 2):
                self.assertFalse(grid[cell_y][cell_x])
                self.assertIn((cell_x, cell_y), reachable)

    def test_to_string_matches_grid(self):
        generator = py_maze.MazeGenerator(width=2, height=2)
        generator.grid = grid_from_strings([
            "* ***",
            "*   *",
            "*** *",
            "*   *",
            "*** *",
        ])

        self.assertEqual(
            generator.to_string(),
            "* ***\n*   *\n*** *\n*   *\n*** *")


class TestMazeGame(unittest.TestCase):
    # a hand-built 2x2 cell maze with a single winding path
    MAZE = [
        "* ***",
        "*   *",
        "*** *",
        "*   *",
        "*** *",
    ]

    def setUp(self):
        self.game = py_maze.MazeGame(grid_from_strings(self.MAZE))

    def test_start_position_is_the_entrance(self):
        self.assertEqual((self.game.player_x, self.game.player_y), (1, 0))

    def test_end_position_is_the_exit(self):
        self.assertEqual((self.game.end_x, self.game.end_y), (3, 4))

    def test_game_copies_the_grid(self):
        source = grid_from_strings(self.MAZE)
        game = py_maze.MazeGame(source)
        game.maze[1][1] = True

        self.assertFalse(source[1][1], "original grid should not be mutated")

    def test_move_into_open_space_succeeds(self):
        self.assertTrue(self.game.move_player(0, 1))
        self.assertEqual((self.game.player_x, self.game.player_y), (1, 1))

    def test_move_into_wall_is_blocked(self):
        self.game.move_player(0, 1)

        self.assertFalse(self.game.move_player(-1, 0))
        self.assertEqual((self.game.player_x, self.game.player_y), (1, 1))

    def test_move_outside_the_grid_is_blocked(self):
        self.assertFalse(self.game.move_player(0, -1))
        self.assertEqual((self.game.player_x, self.game.player_y), (1, 0))

    def test_win_requires_reaching_the_exit(self):
        self.assertFalse(self.game.check_win())

        # walk the only path from entrance to exit
        for dx, dy in [(0, 1), (1, 0), (1, 0), (0, 1), (0, 1), (0, 1)]:
            self.assertTrue(self.game.move_player(dx, dy))
            self.assertEqual(
                self.game.check_win(),
                (self.game.player_x, self.game.player_y) == (3, 4))

        self.assertTrue(self.game.check_win())

    def test_generated_maze_is_walkable_end_to_end(self):
        py_maze.random.seed(7)
        grid = py_maze.MazeGenerator(4, 4).generate()
        game = py_maze.MazeGame(grid)
        reachable = find_open_cells(grid, game.player_x, game.player_y)

        self.assertIn((game.end_x, game.end_y), reachable)


class TestWindowsInput(unittest.TestCase):
    # the Windows branch is exercised directly so these tests run anywhere

    def setUp(self):
        self.game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE))

    def read_key(self, keys, idle_polls=0):
        # Returns:
        #     tuple: (key returned by the game, fake msvcrt, sleep mock)

        fake = FakeMsvcrt(keys, idle_polls)
        with mock.patch.object(py_maze, 'msvcrt', fake, create=True), \
                mock.patch.object(py_maze.time, 'sleep') as sleep:
            return self.game.get_key_windows(), fake, sleep

    def test_plain_key_is_lowercased(self):
        key, _, _ = self.read_key([b'W'])

        self.assertEqual(key, 'w')

    def test_extended_prefix_e0_maps_arrow_keys(self):
        for code, expected in [(b'H', 'up'), (b'P', 'down'),
                               (b'K', 'left'), (b'M', 'right')]:
            key, _, _ = self.read_key([b'\xe0', code])

            self.assertEqual(key, expected)

    def test_extended_prefix_00_maps_arrow_keys(self):
        # some keyboards and remote consoles send b'\x00' instead of b'\xe0'
        for code, expected in [(b'H', 'up'), (b'P', 'down'),
                               (b'K', 'left'), (b'M', 'right')]:
            key, _, _ = self.read_key([b'\x00', code])

            self.assertEqual(key, expected)

    def test_unmapped_extended_key_falls_back_to_its_character(self):
        key, _, _ = self.read_key([b'\xe0', b'S'])

        self.assertEqual(key, 's')

    def test_idle_polling_sleeps_instead_of_spinning(self):
        key, fake, sleep = self.read_key([b'q'], idle_polls=3)

        self.assertEqual(key, 'q')
        self.assertEqual(sleep.call_count, 3)
        self.assertEqual(fake.kbhit_calls, 4)
        sleep.assert_called_with(py_maze.KEY_POLL_INTERVAL)

    def test_ready_key_does_not_sleep(self):
        _, _, sleep = self.read_key([b'a'])

        self.assertEqual(sleep.call_count, 0)

    def test_ctrl_c_raises_a_keyboard_interrupt(self):
        # getch() swallows Ctrl+C instead of signalling, so the game has
        # to turn the byte back into an interrupt
        with self.assertRaises(KeyboardInterrupt):
            self.read_key([py_maze.WINDOWS_INTERRUPT_KEY])


class TestPosixInput(unittest.TestCase):
    # the POSIX branch is exercised directly so these tests run anywhere

    def setUp(self):
        self.game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE))
        self.termios = FakeTermios()

    def read_key(self, keys):
        # Args:
        #     keys: The characters the fake terminal delivers
        #
        # Returns:
        #     tuple: (key returned by the game, fake tty module)

        tty = mock.Mock()
        with mock.patch.object(py_maze, 'termios', self.termios, create=True), \
                mock.patch.object(py_maze, 'tty', tty, create=True), \
                mock.patch.object(py_maze.sys, 'stdin', FakeStdin(keys)):
            return self.game.get_key_posix(), tty

    def test_plain_key_is_lowercased(self):
        key, _ = self.read_key('W')

        self.assertEqual(key, 'w')

    def test_escape_sequences_map_arrow_keys(self):
        for sequence, expected in [('\x1b[A', 'up'), ('\x1b[B', 'down'),
                                   ('\x1b[D', 'left'), ('\x1b[C', 'right')]:
            key, _ = self.read_key(sequence)

            self.assertEqual(key, expected)

    def test_raw_mode_is_entered_and_left(self):
        _, tty = self.read_key('a')

        tty.setraw.assert_called_once()
        self.assertEqual(
            self.termios.restored,
            [(0, FakeTermios.TCSADRAIN, FakeTermios.SETTINGS)])

    def test_ctrl_c_raises_a_keyboard_interrupt(self):
        # raw mode disables the interrupt signal, so Ctrl+C arrives as a
        # byte that the game has to raise on itself
        with self.assertRaises(KeyboardInterrupt):
            self.read_key(py_maze.INTERRUPT_KEY)

    def test_terminal_is_restored_before_the_interrupt_escapes(self):
        # a traceback over a terminal still in raw mode is what this fixes
        with self.assertRaises(KeyboardInterrupt):
            self.read_key(py_maze.INTERRUPT_KEY)

        self.assertEqual(
            self.termios.restored,
            [(0, FakeTermios.TCSADRAIN, FakeTermios.SETTINGS)])


class TestInterruptedGame(unittest.TestCase):
    def setUp(self):
        self.game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE))

    def play(self, keys):
        # run the game loop against a scripted sequence of keypresses
        #
        # Args:
        #     keys: Values get_key() returns, or exceptions it raises
        #
        # Returns:
        #     str: Everything the game printed

        stdout = io.StringIO()
        with mock.patch.object(self.game, 'clear_screen'), \
                mock.patch.object(self.game, 'get_key', side_effect=keys), \
                contextlib.redirect_stdout(stdout):
            self.game.play()

        return stdout.getvalue()

    def test_interrupt_ends_the_game_with_a_goodbye(self):
        output = self.play([KeyboardInterrupt])

        self.assertIn(py_maze.GOODBYE_MESSAGE, output)

    def test_interrupt_mid_game_is_not_a_traceback(self):
        # walk a step first, so the interrupt lands after a real move
        output = self.play(['s', KeyboardInterrupt])

        self.assertIn(py_maze.GOODBYE_MESSAGE, output)
        self.assertEqual((self.game.player_x, self.game.player_y), (1, 1))

    def test_interrupt_on_the_win_screen_is_handled(self):
        # the last get_key() waits for a keypress after the win banner
        moves = ['s', 'd', 'd', 's', 's', 's', KeyboardInterrupt]
        output = self.play(moves)

        self.assertIn('Congratulations', output)
        self.assertIn(py_maze.GOODBYE_MESSAGE, output)

    def test_quitting_still_thanks_the_player(self):
        output = self.play(['q'])

        self.assertIn('Thanks for playing', output)
        self.assertNotIn(py_maze.GOODBYE_MESSAGE, output)


class TestFitDimension(unittest.TestCase):
    def test_a_size_that_fits_is_left_alone(self):
        # 9 cells draw as 19 characters, so 80 is plenty
        self.assertEqual(
            py_maze.fit_dimension(9, 80, 'width', 'columns'), (9, None))

    def test_the_exact_fit_is_not_capped(self):
        # 9 cells need exactly 19 characters
        self.assertEqual(
            py_maze.fit_dimension(9, 19, 'width', 'columns'), (9, None))

    def test_an_oversized_maze_is_capped(self):
        cells, warning = py_maze.fit_dimension(40, 41, 'width', 'columns')

        self.assertEqual(cells, 20)
        self.assertIn('--width 40', warning)
        self.assertIn('needs 81 columns', warning)
        self.assertIn('using 20', warning)

    def test_capping_never_goes_below_the_minimum(self):
        # a terminal this narrow cannot hold even a 2 cell maze, so the
        # request is kept as asked and the warning says it will not fit
        cells, warning = py_maze.fit_dimension(6, 3, 'width', 'columns')

        self.assertEqual(cells, 6)
        self.assertIn('will not fit', warning)

    def test_a_negative_allowance_warns_instead_of_capping(self):
        # a terminal shorter than the lines drawn around the maze
        cells, warning = py_maze.fit_dimension(5, -1, 'height', 'rows')

        self.assertEqual(cells, 5)
        self.assertIn('will not fit', warning)


class TestFitToTerminal(unittest.TestCase):
    def fit(self, width, height, columns, lines):
        # Returns:
        #     tuple: (fitted width, fitted height, warning text)

        stream = io.StringIO()
        fitted = py_maze.fit_to_terminal(
            width, height, size=terminal_size(columns, lines), stream=stream)

        return fitted[0], fitted[1], stream.getvalue()

    def test_a_maze_that_fits_is_untouched_and_silent(self):
        width, height, warnings = self.fit(9, 11, 120, 40)

        self.assertEqual((width, height), (9, 11))
        self.assertEqual(warnings, '')

    def test_width_is_capped_to_the_columns(self):
        width, height, warnings = self.fit(60, 4, 41, 40)

        self.assertEqual((width, height), (20, 4))
        self.assertIn('--width 60', warnings)
        self.assertNotIn('--height', warnings)

    def test_height_allows_for_the_lines_around_the_maze(self):
        # 40 rows less the 4 the render spends on markers and controls
        # leaves 36, which holds 17 cells
        width, height, warnings = self.fit(5, 30, 120, 40)

        self.assertEqual((width, height), (5, 17))
        self.assertIn('--height 30', warnings)
        self.assertIn('only 36 are available', warnings)

    def test_both_dimensions_can_be_capped_at_once(self):
        width, height, warnings = self.fit(60, 60, 41, 40)

        self.assertEqual((width, height), (20, 17))
        self.assertIn('--width 60', warnings)
        self.assertIn('--height 60', warnings)

    def test_a_redirected_stream_is_not_measured(self):
        # piping the maze to a file means there is no terminal to fit
        with mock.patch.object(py_maze, 'terminal_size', return_value=None):
            self.assertEqual(py_maze.fit_to_terminal(500, 500), (500, 500))


class TestTerminalSize(unittest.TestCase):
    def stdout_with_descriptor(self):
        # a stand-in for sys.stdout that os.isatty can be asked about,
        # whatever the test runner has done with the real one
        stdout = mock.Mock()
        stdout.fileno.return_value = 1
        return mock.patch.object(py_maze.sys, 'stdout', stdout)

    def test_a_terminal_is_measured(self):
        size = terminal_size(100, 30)
        with self.stdout_with_descriptor(), \
                mock.patch.object(py_maze.os, 'isatty', return_value=True), \
                mock.patch.object(py_maze.shutil, 'get_terminal_size',
                                  return_value=size):
            self.assertEqual(py_maze.terminal_size(), size)

    def test_a_redirected_stream_has_no_size(self):
        with self.stdout_with_descriptor(), \
                mock.patch.object(py_maze.os, 'isatty', return_value=False):
            self.assertIsNone(py_maze.terminal_size())

    def test_a_stream_without_a_descriptor_has_no_size(self):
        # io.StringIO raises when asked for a file descriptor
        with mock.patch.object(py_maze.sys, 'stdout', io.StringIO()):
            self.assertIsNone(py_maze.terminal_size())


class TestVersion(unittest.TestCase):
    def test_version_is_a_release_number(self):
        self.assertRegex(py_maze.__version__, r'^\d+\.\d+\.\d+')

    def test_the_changelog_documents_the_version(self):
        # the manifest reads __version__, so the changelog is the one
        # other place the number has to agree
        with open('CHANGELOG.md', encoding='utf-8') as changelog:
            released = re.findall(r'^## \[([^\]]+)\]', changelog.read(),
                                  re.MULTILINE)

        self.assertIn(py_maze.__version__, released)

    def test_the_manifest_reads_the_module_version(self):
        # pyproject.toml single-sources the version from py_maze
        with open('pyproject.toml', encoding='utf-8') as manifest:
            content = manifest.read()

        self.assertIn('dynamic = ["version"]', content)
        self.assertIn('version = { attr = "py_maze.__version__" }', content)


class TestMazeDimension(unittest.TestCase):
    def test_accepts_the_minimum_and_above(self):
        self.assertEqual(py_maze.maze_dimension('2'), 2)
        self.assertEqual(py_maze.maze_dimension('30'), 30)

    def test_rejects_values_below_the_minimum(self):
        for value in ['1', '0', '-5']:
            with self.assertRaises(argparse.ArgumentTypeError) as caught:
                py_maze.maze_dimension(value)

            self.assertIn('at least 2 cells', str(caught.exception))

    def test_rejects_non_numeric_values(self):
        with self.assertRaises(argparse.ArgumentTypeError) as caught:
            py_maze.maze_dimension('wide')

        self.assertIn('whole number', str(caught.exception))


class TestBuildParser(unittest.TestCase):
    def parse(self, argv):
        return py_maze.build_parser().parse_args(argv)

    def parse_error(self, argv):
        # Returns:
        #     str: Whatever argparse wrote to stderr before exiting

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as caught:
                self.parse(argv)

        self.assertEqual(caught.exception.code, 2)
        return stderr.getvalue()

    def test_defaults(self):
        args = self.parse([])

        self.assertEqual((args.width, args.height), (9, 11))

    def test_documented_short_flags(self):
        # the README example: -w for width, capital -H for height
        args = self.parse(['-w', '20', '-H', '30'])

        self.assertEqual((args.width, args.height), (20, 30))

    def test_long_flags(self):
        args = self.parse(['--width', '4', '--height', '6'])

        self.assertEqual((args.width, args.height), (4, 6))

    def test_lowercase_h_is_help_not_height(self):
        # argparse reserves -h, which is why the README uses -H
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as caught:
                self.parse(['-h'])

        self.assertEqual(caught.exception.code, 0)
        self.assertIn('usage:', stdout.getvalue())

    def test_width_below_minimum_is_rejected(self):
        message = self.parse_error(['-w', '1'])

        self.assertIn('at least 2 cells', message)

    def test_height_below_minimum_is_rejected(self):
        message = self.parse_error(['-H', '0'])

        self.assertIn('at least 2 cells', message)

    def test_non_numeric_dimension_is_rejected(self):
        message = self.parse_error(['--width', 'big'])

        self.assertIn('whole number', message)

    def test_version_flag_reports_the_package_version(self):
        # -V, because -v is left free for a future verbose option
        for flag in ['--version', '-V']:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as caught:
                    self.parse([flag])

            self.assertEqual(caught.exception.code, 0)
            self.assertIn(py_maze.__version__, stdout.getvalue())
            self.assertIn('py_maze', stdout.getvalue())


if __name__ == '__main__':
    unittest.main()
