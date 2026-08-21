#!/usr/bin/env python3
# test_py_maze
# Unit tests for the py_maze generator, game and command-line parser.

import argparse
import collections
import contextlib
import io
import os
import random
import re
import tempfile
import unittest
from unittest import mock

import py_maze


# A clock that only moves when a test moves it, so timings are exact.
class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds
        return self.now


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
        # 40 rows less the 5 the render spends on markers, the status
        # line and the controls leaves 35, which holds 17 cells
        width, height, warnings = self.fit(5, 30, 120, 40)

        self.assertEqual((width, height), (5, 17))
        self.assertIn('--height 30', warnings)
        self.assertIn('only 35 are available', warnings)

    def test_the_overhead_matches_the_lines_the_render_prints(self):
        # the cap is only right while it counts every line render() puts
        # around the maze itself
        game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE))
        stdout = io.StringIO()
        with mock.patch.object(game, 'clear_screen'), \
                contextlib.redirect_stdout(stdout):
            game.render()

        printed = len(stdout.getvalue().splitlines())
        self.assertEqual(printed - len(TestMazeGame.MAZE),
                         py_maze.RENDER_ROW_OVERHEAD)

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
        # the size now comes from the difficulty preset, so the options
        # themselves default to "not given"
        args = self.parse([])

        self.assertEqual((args.width, args.height), (None, None))
        self.assertEqual(args.difficulty, py_maze.DEFAULT_DIFFICULTY)
        self.assertIsNone(args.seed)
        self.assertFalse(args.solve)
        self.assertFalse(args.animate)

    def test_the_default_maze_is_still_nine_by_eleven(self):
        # the normal preset is the size py_maze has always generated
        self.assertEqual(py_maze.resolve_dimensions(self.parse([])), (9, 11))

    def test_difficulty_chooses_a_preset_size(self):
        for name, size in py_maze.DIFFICULTIES.items():
            args = self.parse(['--difficulty', name])

            self.assertEqual(py_maze.resolve_dimensions(args), size)

    def test_difficulty_short_flag(self):
        args = self.parse(['-d', 'hard'])

        self.assertEqual(args.difficulty, 'hard')

    def test_an_unknown_difficulty_is_rejected(self):
        message = self.parse_error(['-d', 'nightmare'])

        self.assertIn('nightmare', message)

    def test_seed_is_a_number_when_it_reads_as_one(self):
        for flag in ['--seed', '-s']:
            self.assertEqual(self.parse([flag, '2024']).seed, 2024)

    def test_seed_can_be_text(self):
        self.assertEqual(self.parse(['--seed', 'winter']).seed, 'winter')

    def test_solve_and_animate_are_off_until_asked_for(self):
        for flags, solve, animate in [(['--solve'], True, False),
                                      (['-S'], True, False),
                                      (['--animate'], False, True),
                                      (['-a'], False, True),
                                      (['-S', '-a'], True, True)]:
            args = self.parse(flags)

            self.assertEqual((args.solve, args.animate), (solve, animate))

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


class TestSeed(unittest.TestCase):
    def generate(self, seed):
        return py_maze.MazeGenerator(5, 6, seed=seed).generate()

    def test_the_same_seed_carves_the_same_maze(self):
        self.assertEqual(self.generate(2024), self.generate(2024))

    def test_different_seeds_carve_different_mazes(self):
        # a 5 by 6 maze has far too many shapes for two seeds to collide
        self.assertNotEqual(self.generate(2024), self.generate(2025))

    def test_a_text_seed_is_repeatable_too(self):
        self.assertEqual(self.generate('winter'), self.generate('winter'))
        self.assertNotEqual(self.generate('winter'), self.generate('summer'))

    def test_the_generator_records_its_seed(self):
        self.assertEqual(py_maze.MazeGenerator(3, 3, seed=7).seed, 7)
        self.assertIsNone(py_maze.MazeGenerator(3, 3).seed)

    def test_a_seeded_generator_leaves_the_shared_random_alone(self):
        # seeding the module would make every later maze repeat as well
        py_maze.random.seed(11)
        expected = py_maze.random.random()

        py_maze.random.seed(11)
        self.generate(2024)

        self.assertEqual(py_maze.random.random(), expected)

    def test_without_a_seed_the_shared_random_is_used(self):
        py_maze.random.seed(3)
        first = py_maze.MazeGenerator(5, 6).generate()
        py_maze.random.seed(3)
        second = py_maze.MazeGenerator(5, 6).generate()

        self.assertEqual(first, second)


class TestMazeSeed(unittest.TestCase):
    def test_whole_numbers_are_read_as_numbers(self):
        self.assertEqual(py_maze.maze_seed('0'), 0)
        self.assertEqual(py_maze.maze_seed('-12'), -12)

    def test_anything_else_is_kept_as_text(self):
        self.assertEqual(py_maze.maze_seed('winter'), 'winter')
        self.assertEqual(py_maze.maze_seed('1.5'), '1.5')


class TestDifficulty(unittest.TestCase):
    def resolve(self, difficulty=py_maze.DEFAULT_DIFFICULTY,
                width=None, height=None):
        args = argparse.Namespace(
            difficulty=difficulty, width=width, height=height)
        return py_maze.resolve_dimensions(args)

    def test_the_presets_run_from_easy_to_hard(self):
        self.assertEqual(list(py_maze.DIFFICULTIES),
                         ['easy', 'normal', 'hard'])

    def test_harder_presets_are_larger(self):
        sizes = [width * height for width, height
                 in py_maze.DIFFICULTIES.values()]

        self.assertEqual(sizes, sorted(sizes))

    def test_every_preset_meets_the_minimum(self):
        for width, height in py_maze.DIFFICULTIES.values():
            self.assertGreaterEqual(min(width, height), py_maze.MIN_DIMENSION)

    def test_the_preset_supplies_both_dimensions(self):
        self.assertEqual(self.resolve('easy'), py_maze.DIFFICULTIES['easy'])
        self.assertEqual(self.resolve('hard'), py_maze.DIFFICULTIES['hard'])

    def test_width_and_height_override_the_preset(self):
        preset_width, preset_height = py_maze.DIFFICULTIES['hard']

        self.assertEqual(self.resolve('hard', width=3),
                         (3, preset_height))
        self.assertEqual(self.resolve('hard', height=4),
                         (preset_width, 4))
        self.assertEqual(self.resolve('hard', width=3, height=4), (3, 4))

    def test_the_summary_names_every_preset(self):
        summary = py_maze.difficulty_summary()

        for name, (width, height) in py_maze.DIFFICULTIES.items():
            self.assertIn(name, summary)
            self.assertIn('%d by %d' % (width, height), summary)


class TestFindEntranceAndExit(unittest.TestCase):
    def test_they_find_the_openings(self):
        grid = grid_from_strings(TestMazeGame.MAZE)

        self.assertEqual(py_maze.find_entrance(grid), (1, 0))
        self.assertEqual(py_maze.find_exit(grid), (3, 4))

    def test_an_entrance_below_the_top_row_is_found(self):
        grid = grid_from_strings([
            "*****",
            "* * *",
            "*   *",
            "*** *",
        ])

        self.assertEqual(py_maze.find_entrance(grid), (1, 1))

    def test_a_sealed_maze_falls_back_to_the_border(self):
        grid = grid_from_strings(["*****"] * 4)

        self.assertEqual(py_maze.find_entrance(grid), (1, 0))
        self.assertEqual(py_maze.find_exit(grid), (3, 3))


class TestSolveMaze(unittest.TestCase):
    # a maze with two ways round: the right-hand corridor is the short one
    LOOPED = [
        "* *****",
        "*     *",
        "*** * *",
        "*   * *",
        "* *** *",
        "*     *",
        "***** *",
    ]

    def test_the_path_runs_from_the_entrance_to_the_exit(self):
        grid = grid_from_strings(TestMazeGame.MAZE)
        path = py_maze.solve_maze(grid)

        self.assertEqual(
            path,
            [(1, 0), (1, 1), (2, 1), (3, 1), (3, 2), (3, 3), (3, 4)])

    def test_every_step_is_open_and_adjacent(self):
        py_maze.random.seed(5)
        grid = py_maze.MazeGenerator(7, 9).generate()
        path = py_maze.solve_maze(grid)

        for x, y in path:
            self.assertFalse(grid[y][x], "the path crosses a wall")
        for (x, y), (next_x, next_y) in zip(path, path[1:]):
            self.assertEqual(abs(next_x - x) + abs(next_y - y), 1)

    def test_the_shortest_way_round_is_chosen(self):
        grid = grid_from_strings(self.LOOPED)
        path = py_maze.solve_maze(grid)

        self.assertEqual(
            path,
            [(1, 0), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1),
             (5, 2), (5, 3), (5, 4), (5, 5), (5, 6)])

    def test_generated_mazes_are_all_solvable(self):
        for seed in range(5):
            grid = py_maze.MazeGenerator(6, 8, seed=seed).generate()
            path = py_maze.solve_maze(grid)

            self.assertIsNotNone(path, "seed %d produced no solution" % seed)
            self.assertEqual(path[0], py_maze.find_entrance(grid))
            self.assertEqual(path[-1], py_maze.find_exit(grid))

    def test_a_walled_off_exit_has_no_solution(self):
        grid = grid_from_strings([
            "* ***",
            "*   *",
            "*****",
            "*   *",
            "*** *",
        ])

        self.assertIsNone(py_maze.solve_maze(grid))

    def test_a_start_inside_a_wall_has_no_solution(self):
        grid = grid_from_strings(TestMazeGame.MAZE)

        self.assertIsNone(py_maze.solve_maze(grid, start=(0, 0)))

    def test_solving_from_the_exit_is_a_single_cell(self):
        grid = grid_from_strings(TestMazeGame.MAZE)

        self.assertEqual(py_maze.solve_maze(grid, start=(3, 4)), [(3, 4)])

    def test_a_custom_start_and_end_are_honored(self):
        grid = grid_from_strings(TestMazeGame.MAZE)

        self.assertEqual(
            py_maze.solve_maze(grid, start=(1, 1), end=(3, 1)),
            [(1, 1), (2, 1), (3, 1)])


class TestSearchFrames(unittest.TestCase):
    def frames(self, rows, **kwargs):
        grid = grid_from_strings(rows)
        return grid, list(py_maze.search_frames(grid, **kwargs))

    def test_the_search_starts_at_the_entrance(self):
        _, frames = self.frames(TestMazeGame.MAZE)
        visited, frontier, path = frames[0]

        self.assertEqual(visited, {(1, 0)})
        self.assertEqual(frontier, {(1, 0)})
        self.assertIsNone(path)

    def test_the_frontier_grows_one_step_per_frame(self):
        grid, frames = self.frames(TestMazeGame.MAZE)
        previous = set()

        for visited, frontier, _ in frames:
            self.assertTrue(frontier <= visited)
            self.assertTrue(previous <= visited, "cells were forgotten")
            for x, y in visited:
                self.assertFalse(grid[y][x], "a wall was searched")
            previous = visited

    def test_only_the_last_frame_carries_the_path(self):
        _, frames = self.frames(TestMazeGame.MAZE)

        for visited, frontier, path in frames[:-1]:
            self.assertIsNone(path)

        visited, frontier, path = frames[-1]
        self.assertEqual(frontier, set(), "the search should have finished")
        self.assertEqual(path[-1], (3, 4))

    def test_the_search_stops_once_the_exit_is_reached(self):
        # the exit is reached by the wave grown after the last drawn
        # frame, and nothing is searched past it
        _, frames = self.frames(TestMazeGame.MAZE)

        self.assertIn((3, 4), frames[-1][0])
        self.assertNotIn((3, 4), frames[-2][0])
        self.assertTrue(frames[-2][0] < frames[-1][0])

    def test_an_unreachable_exit_ends_without_a_path(self):
        grid, frames = self.frames([
            "* ***",
            "*   *",
            "*****",
            "*   *",
            "*** *",
        ])
        visited, frontier, path = frames[-1]

        self.assertIsNone(path)
        self.assertEqual(visited, {(1, 0), (1, 1), (2, 1), (3, 1)})

    def test_a_search_from_a_wall_draws_nothing(self):
        _, frames = self.frames(TestMazeGame.MAZE, start=(0, 0))

        self.assertEqual(frames, [(set(), set(), None)])


class TestMazeLines(unittest.TestCase):
    PICTURE = [
        "* ***",
        "*   *",
        "*** *",
    ]

    def test_a_bare_maze_is_drawn_as_it_is(self):
        grid = grid_from_strings(self.PICTURE)

        self.assertEqual(py_maze.maze_lines(grid), self.PICTURE)

    def test_an_overlay_marks_its_cells(self):
        grid = grid_from_strings(self.PICTURE)
        lines = py_maze.maze_lines(grid, [('.', {(1, 0), (1, 1)})])

        self.assertEqual(lines, ["*.***", "*.  *", "*** *"])

    def test_the_first_overlay_wins(self):
        grid = grid_from_strings(self.PICTURE)
        cell = {(1, 1)}
        lines = py_maze.maze_lines(grid, [('o', cell), ('?', cell)])

        self.assertEqual(lines[1], "*o  *")

    def test_an_overlay_can_cover_a_wall(self):
        # the search marks whole cells, walls included, while it runs
        grid = grid_from_strings(self.PICTURE)
        lines = py_maze.maze_lines(grid, [('~', {(0, 0)})])

        self.assertEqual(lines[0], "~ ***")

    def test_a_solution_overlay_is_empty_without_a_solution(self):
        self.assertEqual(py_maze.solution_overlay(None), [])
        self.assertEqual(py_maze.solution_overlay([]), [])
        self.assertEqual(py_maze.solution_overlay([(1, 0)]),
                         [(py_maze.SOLUTION_MARKER, {(1, 0)})])

    def test_print_maze_wraps_the_maze_in_its_markers(self):
        stream = io.StringIO()
        py_maze.print_maze(grid_from_strings(self.PICTURE), stream=stream)

        self.assertEqual(stream.getvalue().splitlines(),
                         ["start"] + self.PICTURE + ["end"])

    def test_to_string_can_overlay_a_solution(self):
        generator = py_maze.MazeGenerator(width=2, height=2)
        generator.grid = grid_from_strings(TestMazeGame.MAZE)
        path = py_maze.solve_maze(generator.grid)

        self.assertEqual(
            generator.to_string(path),
            "*.***\n*...*\n***.*\n*  .*\n***.*")


# Records the frames an animation draws, in place of a real terminal.
class FakeScreen:
    def __init__(self):
        self.stream = io.StringIO()
        self.clears = 0
        self.pauses = []

    def clear(self):
        self.clears += 1

    def pause(self, delay):
        self.pauses.append(delay)

    def sections(self):
        # Returns:
        #     list: Everything each frame wrote, split on the screen clears
        return self.stream.getvalue().split('Solving...\n')[1:]

    def frames(self):
        # Returns:
        #     list: Just the maze each frame drew, without the markers
        #     around it or the legend below it
        drawn = []
        for section in self.sections():
            lines = section.splitlines()
            drawn.append('\n'.join(
                lines[lines.index('start') + 1:lines.index('end')]))

        return drawn


class TestAnimateSearch(unittest.TestCase):
    def animate(self, rows, **kwargs):
        # Returns:
        #     tuple: (solution path, fake screen it was drawn on)

        grid = grid_from_strings(rows)
        screen = FakeScreen()
        path = py_maze.animate_search(
            grid, stream=screen.stream, clear=screen.clear,
            pause=screen.pause, **kwargs)

        return path, screen

    def test_it_returns_the_same_path_the_solver_finds(self):
        path, _ = self.animate(TestMazeGame.MAZE)

        self.assertEqual(
            path, py_maze.solve_maze(grid_from_strings(TestMazeGame.MAZE)))

    def test_every_frame_is_cleared_and_paused_for(self):
        expected = len(list(py_maze.search_frames(
            grid_from_strings(TestMazeGame.MAZE))))
        _, screen = self.animate(TestMazeGame.MAZE)

        self.assertEqual(screen.clears, expected)
        self.assertEqual(len(screen.pauses), expected)
        self.assertEqual(len(screen.frames()), expected)

    def test_the_frame_delay_can_be_set(self):
        _, screen = self.animate(TestMazeGame.MAZE, delay=0.25)

        self.assertEqual(set(screen.pauses), {0.25})

    def test_the_default_delay_is_the_frame_delay(self):
        _, screen = self.animate(TestMazeGame.MAZE)

        self.assertEqual(set(screen.pauses), {py_maze.FRAME_DELAY})

    def test_the_frontier_leads_and_the_solution_lands_last(self):
        _, screen = self.animate(TestMazeGame.MAZE)
        frames = screen.frames()

        self.assertIn(py_maze.FRONTIER_MARKER, frames[0])
        self.assertNotIn(py_maze.SOLUTION_MARKER, frames[0])
        self.assertIn(py_maze.VISITED_MARKER, frames[-1])
        self.assertIn(py_maze.SOLUTION_MARKER, frames[-1])

    def test_every_frame_explains_its_markers(self):
        _, screen = self.animate(TestMazeGame.MAZE)

        for section in screen.sections():
            self.assertIn('frontier', section)
            self.assertIn('explored', section)
            self.assertIn('solution', section)

    def test_an_unsolvable_maze_still_draws_its_search(self):
        path, screen = self.animate([
            "* ***",
            "*   *",
            "*****",
            "*   *",
            "*** *",
        ])

        self.assertIsNone(path)
        self.assertTrue(screen.clears)
        for frame in screen.frames():
            self.assertNotIn(py_maze.SOLUTION_MARKER, frame)


class TestHint(unittest.TestCase):
    def setUp(self):
        self.game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE))

    def show_hint(self):
        # Returns:
        #     tuple: (highlighted cells, what was drawn, sleep mock)

        stdout = io.StringIO()
        with mock.patch.object(self.game, 'clear_screen'), \
                mock.patch.object(py_maze.time, 'sleep') as sleep, \
                contextlib.redirect_stdout(stdout):
            steps = self.game.show_hint()

        return steps, stdout.getvalue(), sleep

    def test_the_next_step_of_the_solution_is_highlighted(self):
        steps, drawn, _ = self.show_hint()

        self.assertEqual(steps, [(1, 1)])
        self.assertIn("*%s  *" % py_maze.HINT_MARKER, drawn)

    def test_the_hint_is_only_shown_for_a_moment(self):
        _, _, sleep = self.show_hint()

        sleep.assert_called_once_with(py_maze.HINT_SECONDS)
        self.assertEqual(self.game.hint_cells, set(),
                         "the hint should be cleared for the next render")

    def test_a_hint_points_the_way_back_after_a_wrong_turn(self):
        # step off the solution, into the dead end at the top left
        self.game.player_x, self.game.player_y = 1, 1
        self.game.maze = grid_from_strings([
            "* ***",
            "*   *",
            "* * *",
            "*   *",
            "*** *",
        ])
        steps, _, _ = self.show_hint()

        self.assertEqual(steps, [(2, 1)])

    def test_there_is_no_hint_at_the_exit(self):
        self.game.player_x, self.game.player_y = self.game.end_x, self.game.end_y
        steps, _, sleep = self.show_hint()

        self.assertEqual(steps, [])
        self.assertEqual(sleep.call_count, 0)

    def test_there_is_no_hint_when_the_exit_is_walled_off(self):
        self.game.maze[1][1] = True
        steps, _, _ = self.show_hint()

        self.assertEqual(steps, [])

    def test_the_h_key_shows_a_hint_and_the_maze_is_redrawn_without_it(self):
        stdout = io.StringIO()
        with mock.patch.object(self.game, 'clear_screen'), \
                mock.patch.object(self.game, 'get_key',
                                  side_effect=['h', 'q']), \
                mock.patch.object(py_maze.time, 'sleep'), \
                contextlib.redirect_stdout(stdout):
            self.game.play()

        output = stdout.getvalue()
        self.assertIn(py_maze.HINT_MARKER, output)
        self.assertNotIn(py_maze.HINT_MARKER, output.rsplit('start', 1)[-1])
        self.assertEqual((self.game.player_x, self.game.player_y), (1, 0),
                         "a hint should not move the player")

    def test_the_controls_offer_the_hint_key(self):
        stdout = io.StringIO()
        with mock.patch.object(self.game, 'clear_screen'), \
                contextlib.redirect_stdout(stdout):
            self.game.render()

        self.assertIn("'h' for a hint", stdout.getvalue())


class TestFormatDuration(unittest.TestCase):
    def test_seconds_are_padded_under_a_minute(self):
        self.assertEqual(py_maze.format_duration(0), "0:00")
        self.assertEqual(py_maze.format_duration(7), "0:07")

    def test_minutes_and_seconds(self):
        self.assertEqual(py_maze.format_duration(75), "1:15")
        self.assertEqual(py_maze.format_duration(599), "9:59")

    def test_hours_are_shown_once_there_are_any(self):
        self.assertEqual(py_maze.format_duration(3600), "1:00:00")
        self.assertEqual(py_maze.format_duration(3725), "1:02:05")

    def test_part_seconds_are_dropped_rather_than_rounded_up(self):
        # a stopwatch reads the second it is in, not the next one
        self.assertEqual(py_maze.format_duration(9.99), "0:09")


class TestStatusAndSummaryLines(unittest.TestCase):
    def test_the_status_reports_the_time_and_the_moves(self):
        self.assertEqual(py_maze.status_line(75, 12), "time 1:15   moves 12")

    def test_the_status_counts_collectibles_when_there_are_any(self):
        self.assertIn("collected 2/5", py_maze.status_line(0, 0, 2, 5))

    def test_a_maze_without_collectibles_does_not_mention_them(self):
        self.assertNotIn("collected", py_maze.status_line(0, 0, 0, 0))

    def test_the_summary_reports_the_time_and_the_moves(self):
        self.assertEqual(py_maze.summary_lines(75, 12),
                         ["Time:  1:15", "Moves: 12"])

    def test_the_summary_tallies_collectibles_when_there_are_any(self):
        lines = py_maze.summary_lines(0, 4, 1, 3)

        self.assertEqual(lines[-1], "Collected: 1 of 3")

    def test_a_summary_without_collectibles_does_not_mention_them(self):
        self.assertEqual(len(py_maze.summary_lines(0, 4, 0, 0)), 2)


class TestGameClock(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE),
                                     clock=self.clock)

    def test_the_clock_reads_nothing_before_the_game_starts(self):
        self.clock.advance(60)

        self.assertEqual(self.game.elapsed(), 0.0)

    def test_the_clock_runs_from_the_start_of_the_game(self):
        self.game.start_clock()
        self.clock.advance(30)

        self.assertEqual(self.game.elapsed(), 30)

    def test_starting_twice_does_not_restart_the_clock(self):
        self.game.start_clock()
        self.clock.advance(30)
        self.game.start_clock()

        self.assertEqual(self.game.elapsed(), 30)

    def test_the_clock_freezes_when_the_game_ends(self):
        # the summary should read the same however long it is left up
        self.game.start_clock()
        self.clock.advance(45)
        self.game.stop_clock()
        self.clock.advance(600)

        self.assertEqual(self.game.elapsed(), 45)

    def test_stopping_twice_keeps_the_first_reading(self):
        self.game.start_clock()
        self.clock.advance(45)
        self.game.stop_clock()
        self.clock.advance(10)
        self.game.stop_clock()

        self.assertEqual(self.game.elapsed(), 45)

    def test_a_game_that_never_started_cannot_be_stopped(self):
        self.game.stop_clock()

        self.assertIsNone(self.game.stopped)


class TestMoveCounter(unittest.TestCase):
    def setUp(self):
        self.game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE))

    def test_a_new_game_has_taken_no_moves(self):
        self.assertEqual(self.game.moves, 0)

    def test_each_step_counts(self):
        self.game.move_player(0, 1)
        self.game.move_player(1, 0)

        self.assertEqual(self.game.moves, 2)

    def test_walking_into_a_wall_is_not_a_move(self):
        self.game.move_player(0, 1)
        self.assertFalse(self.game.move_player(-1, 0))

        self.assertEqual(self.game.moves, 1)

    def test_stepping_outside_the_grid_is_not_a_move(self):
        self.assertFalse(self.game.move_player(0, -1))

        self.assertEqual(self.game.moves, 0)

    def test_a_hint_is_not_a_move(self):
        with mock.patch.object(self.game, 'clear_screen'), \
                mock.patch.object(py_maze.time, 'sleep'), \
                contextlib.redirect_stdout(io.StringIO()):
            self.game.show_hint()

        self.assertEqual(self.game.moves, 0)


class TestCollectiblePlacement(unittest.TestCase):
    def grid(self):
        return py_maze.MazeGenerator(5, 6, seed=2024).generate()

    def test_no_collectibles_are_placed_when_none_are_asked_for(self):
        self.assertEqual(py_maze.place_collectibles(self.grid(), 0), set())
        self.assertEqual(py_maze.place_collectibles(self.grid(), -3), set())

    def test_the_number_asked_for_is_placed(self):
        placed = py_maze.place_collectibles(self.grid(), 7, random.Random(1))

        self.assertEqual(len(placed), 7)

    def test_they_land_on_cells_the_player_can_stand_on(self):
        grid = self.grid()
        placed = py_maze.place_collectibles(grid, 10, random.Random(1))

        for x, y in placed:
            self.assertFalse(grid[y][x], "a collectible landed in a wall")

    def test_the_entrance_and_exit_are_left_clear(self):
        grid = self.grid()
        # ask for one on every open cell, so only the excluded ones are left
        placed = py_maze.place_collectibles(grid, 10000, random.Random(1))

        self.assertNotIn(py_maze.find_entrance(grid), placed)
        self.assertNotIn(py_maze.find_exit(grid), placed)

    def test_asking_for_more_than_there_is_room_for_fills_the_maze(self):
        grid = self.grid()
        spots = len(list(py_maze.open_cells(grid))) - 2
        placed = py_maze.place_collectibles(grid, 10000, random.Random(1))

        self.assertEqual(len(placed), spots)

    def test_the_same_seed_scatters_them_the_same_way(self):
        def scatter():
            generator = py_maze.MazeGenerator(5, 6, seed=2024)
            grid = generator.generate()
            return py_maze.place_collectibles(grid, 5, generator.random)

        self.assertEqual(scatter(), scatter())

    def test_a_different_seed_scatters_them_differently(self):
        def scatter(seed):
            generator = py_maze.MazeGenerator(8, 8, seed=seed)
            grid = generator.generate()
            return py_maze.place_collectibles(grid, 6, generator.random)

        self.assertNotEqual(scatter(2024), scatter(2025))


class TestOpenCells(unittest.TestCase):
    def test_only_the_open_cells_are_listed(self):
        grid = grid_from_strings(["* ***", "*   *", "*** *"])

        self.assertEqual(
            list(py_maze.open_cells(grid)),
            [(1, 0), (1, 1), (2, 1), (3, 1), (3, 2)])

    def test_a_solid_grid_has_none(self):
        self.assertEqual(list(py_maze.open_cells(grid_from_strings(["***"]))),
                         [])


class TestCollectingThem(unittest.TestCase):
    # the hand-built maze runs (1,0) (1,1) (2,1) (3,1) (3,2) (3,3) (3,4)

    def game(self, collectibles):
        return py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE),
                                collectibles)

    def test_a_new_game_has_collected_nothing(self):
        game = self.game({(2, 1), (3, 3)})

        self.assertEqual((game.collected, game.total_collectibles), (0, 2))

    def test_stepping_onto_one_picks_it_up(self):
        game = self.game({(1, 1)})
        game.move_player(0, 1)

        self.assertEqual(game.collected, 1)
        self.assertEqual(game.collectibles, set())

    def test_walking_past_an_empty_cell_collects_nothing(self):
        game = self.game({(3, 3)})
        game.move_player(0, 1)

        self.assertEqual(game.collected, 0)

    def test_each_one_is_only_collected_once(self):
        game = self.game({(1, 1)})
        game.move_player(0, 1)
        game.move_player(0, -1)
        game.move_player(0, 1)

        self.assertEqual(game.collected, 1)

    def test_one_on_the_entrance_is_picked_up_at_the_start(self):
        # place_collectibles never does this, but a hand-edited save can
        game = self.game({(1, 0)})

        self.assertEqual(game.collected, 1)
        self.assertEqual(game.collectibles, set())

    def test_walking_the_maze_collects_every_one_on_the_route(self):
        game = self.game({(1, 1), (3, 1), (3, 4)})
        for dx, dy in [(0, 1), (1, 0), (1, 0), (0, 1), (0, 1), (0, 1)]:
            game.move_player(dx, dy)

        self.assertEqual(game.collected, 3)
        self.assertTrue(game.check_win())

    def test_they_are_drawn_on_the_maze(self):
        game = self.game({(2, 1)})
        stdout = io.StringIO()
        with mock.patch.object(game, 'clear_screen'), \
                contextlib.redirect_stdout(stdout):
            game.render()

        self.assertIn("* %s *" % py_maze.COLLECTIBLE_MARKER,
                      stdout.getvalue())

    def test_a_collected_one_stops_being_drawn(self):
        game = self.game({(1, 1)})
        game.move_player(0, 1)
        stdout = io.StringIO()
        with mock.patch.object(game, 'clear_screen'), \
                contextlib.redirect_stdout(stdout):
            game.render()

        self.assertNotIn(py_maze.COLLECTIBLE_MARKER, stdout.getvalue())

    def test_the_player_is_drawn_over_a_collectible(self):
        # the player has to stay visible, and stepping on one takes it
        game = self.game({(1, 1)})
        game.player_x, game.player_y = 1, 1
        stdout = io.StringIO()
        with mock.patch.object(game, 'clear_screen'), \
                contextlib.redirect_stdout(stdout):
            game.render()

        self.assertIn("*o  *", stdout.getvalue())

    def test_the_game_does_not_empty_the_set_it_was_given(self):
        collectibles = {(1, 1)}
        game = self.game(collectibles)
        game.move_player(0, 1)

        self.assertEqual(collectibles, {(1, 1)},
                         "the caller's collectibles should not be emptied")


class TestEndOfGameSummary(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()

    def play(self, keys, collectibles=()):
        # run the game loop against a scripted sequence of keypresses,
        # with the clock ticking a second per keypress
        #
        # Returns:
        #     tuple: (everything the game printed, the game)

        game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE),
                                collectibles, clock=self.clock)

        def key():
            self.clock.advance(1)
            return keys.pop(0)

        stdout = io.StringIO()
        with mock.patch.object(game, 'clear_screen'), \
                mock.patch.object(game, 'get_key', side_effect=key), \
                contextlib.redirect_stdout(stdout):
            game.play()

        return stdout.getvalue(), game

    def win(self, collectibles=()):
        # the only route out, then the keypress the win screen waits on
        return self.play(['s', 'd', 'd', 's', 's', 's', 'x'], collectibles)

    def test_the_win_screen_summarizes_the_time_and_the_moves(self):
        output, _ = self.win()

        self.assertIn('Congratulations', output)
        self.assertIn('Time:  0:06', output)
        self.assertIn('Moves: 6', output)

    def test_the_win_screen_tallies_the_collectibles(self):
        output, _ = self.win({(2, 1), (3, 3), (1, 1)})

        self.assertIn('Collected: 3 of 3', output)

    def test_collectibles_left_behind_are_still_tallied(self):
        # (1, 3) sits in the dead end the winning route never enters
        output, _ = self.win({(2, 1), (1, 3)})

        self.assertIn('Collected: 1 of 2', output)

    def test_quitting_summarizes_the_game_so_far(self):
        output, _ = self.play(['s', 'd', 'q'])

        self.assertIn('Thanks for playing', output)
        self.assertIn('Time:  0:03', output)
        self.assertIn('Moves: 2', output)

    def test_the_summary_does_not_mention_a_maze_without_collectibles(self):
        output, _ = self.win()

        self.assertNotIn('Collected', output)

    def test_the_clock_stops_at_the_win_rather_than_at_the_last_key(self):
        # the win screen waits for a keypress, which must not be timed
        _, game = self.win()

        self.assertEqual(game.elapsed(), 6)

    def test_the_status_line_is_drawn_under_the_maze_while_playing(self):
        output, _ = self.play(['s', 'q'])

        self.assertIn('time 0:', output)
        self.assertIn('moves 1', output)

    def test_the_status_line_counts_the_collectibles(self):
        output, _ = self.play(['s', 'q'], {(1, 1), (3, 3)})

        self.assertIn('collected 1/2', output)


class TestCollectibleCount(unittest.TestCase):
    def test_accepts_nought_and_above(self):
        self.assertEqual(py_maze.collectible_count('0'), 0)
        self.assertEqual(py_maze.collectible_count('12'), 12)

    def test_rejects_negative_counts(self):
        with self.assertRaises(argparse.ArgumentTypeError) as caught:
            py_maze.collectible_count('-1')

        self.assertIn('cannot be negative', str(caught.exception))

    def test_rejects_non_numeric_counts(self):
        with self.assertRaises(argparse.ArgumentTypeError) as caught:
            py_maze.collectible_count('lots')

        self.assertIn('whole number', str(caught.exception))


class TestSaveFile(unittest.TestCase):
    MAZE = [
        "* ***",
        "*   *",
        "*** *",
        "*   *",
        "*** *",
    ]

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = os.path.join(self.directory.name, 'maze.txt')

    def test_a_save_is_the_maze_under_a_header(self):
        lines = py_maze.save_lines(grid_from_strings(self.MAZE))

        self.assertEqual(lines[0], py_maze.SAVE_HEADER)
        self.assertEqual(lines[1:], self.MAZE)

    def test_the_seed_is_recorded_when_it_is_known(self):
        lines = py_maze.save_lines(grid_from_strings(self.MAZE), seed=2024)

        self.assertEqual(lines[1], "# seed: 2024")

    def test_an_unknown_seed_is_left_out(self):
        lines = py_maze.save_lines(grid_from_strings(self.MAZE))

        self.assertNotIn("# seed:", '\n'.join(lines))

    def test_collectibles_are_drawn_into_the_maze(self):
        lines = py_maze.save_lines(grid_from_strings(self.MAZE), {(2, 1)})

        self.assertEqual(lines[2], "* %s *" % py_maze.COLLECTIBLE_MARKER)

    def test_a_maze_survives_a_round_trip(self):
        grid = py_maze.MazeGenerator(6, 7, seed=2024).generate()
        collectibles = py_maze.place_collectibles(grid, 5, random.Random(1))
        py_maze.write_save(self.path, grid, collectibles, 2024)

        self.assertEqual(py_maze.read_save(self.path),
                         (grid, collectibles, 2024))

    def test_a_text_seed_survives_a_round_trip(self):
        grid = grid_from_strings(self.MAZE)
        py_maze.write_save(self.path, grid, seed='winter')

        self.assertEqual(py_maze.read_save(self.path), (grid, set(), 'winter'))

    def test_a_save_without_a_seed_loads_without_one(self):
        py_maze.write_save(self.path, grid_from_strings(self.MAZE))
        _, _, seed = py_maze.read_save(self.path)

        self.assertIsNone(seed)

    def test_a_saved_file_ends_with_a_newline(self):
        py_maze.write_save(self.path, grid_from_strings(self.MAZE))
        with open(self.path, encoding='utf-8') as handle:
            self.assertTrue(handle.read().endswith('\n'))

    def test_blank_lines_and_notes_are_ignored(self):
        text = "%s\n# a maze worth keeping\n\n%s\n" % (
            py_maze.SAVE_HEADER, '\n'.join(self.MAZE))
        grid, collectibles, seed = py_maze.parse_save(text)

        self.assertEqual(grid, grid_from_strings(self.MAZE))
        self.assertEqual((collectibles, seed), (set(), None))

    def test_a_saved_maze_is_playable(self):
        grid, collectibles, _ = py_maze.parse_save(
            "%s\n* ***\n*  $*\n*** *\n" % py_maze.SAVE_HEADER)
        game = py_maze.MazeGame(grid, collectibles)

        self.assertEqual((game.player_x, game.player_y), (1, 0))
        self.assertEqual(game.total_collectibles, 1)
        self.assertTrue(game.move_player(0, 1))

    def test_a_file_without_the_header_is_rejected(self):
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_save('\n'.join(self.MAZE), 'maze.txt')

        self.assertIn('not a py_maze save file', str(caught.exception))
        self.assertIn('maze.txt', str(caught.exception))

    def test_an_empty_file_is_rejected(self):
        with self.assertRaises(py_maze.SaveFileError):
            py_maze.parse_save('')

    def test_a_header_with_no_maze_under_it_is_rejected(self):
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_save("%s\n# seed: 2024\n" % py_maze.SAVE_HEADER)

        self.assertIn('no maze in it', str(caught.exception))

    def test_a_newer_save_format_is_rejected(self):
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_save("# py_maze save 99\n* *\n")

        self.assertIn('99', str(caught.exception))
        self.assertIn('not supported', str(caught.exception))

    def test_a_ragged_maze_is_rejected(self):
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_save("%s\n* ***\n*  *\n" % py_maze.SAVE_HEADER)

        self.assertIn('line 3', str(caught.exception))
        self.assertIn('expected 5', str(caught.exception))

    def test_an_unknown_character_is_rejected(self):
        # a solved maze pasted back in, rather than a saved one
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_save("%s\n*.***\n" % py_maze.SAVE_HEADER)

        self.assertIn("'.'", str(caught.exception))
        self.assertIn('line 2', str(caught.exception))

    def test_a_missing_file_raises_an_os_error(self):
        with self.assertRaises(OSError):
            py_maze.read_save(os.path.join(self.directory.name, 'nowhere'))


# Drives main() end to end, with the keyboard and the animation standing
# in for a real terminal.
class MainRunner:
    def run_main(self, argv=(), response='n', terminal=True):
        # Returns:
        #     tuple: (what main printed, the patched animate_search)

        stdout = io.StringIO()
        size = terminal_size(200, 80) if terminal else None
        with mock.patch.object(py_maze.sys, 'argv', ['py_maze'] + list(argv)), \
                mock.patch.object(py_maze, 'terminal_size',
                                  return_value=size), \
                mock.patch.object(py_maze, 'read_response',
                                  side_effect=[response]), \
                mock.patch.object(py_maze, 'animate_search',
                                  return_value=[(1, 0)]) as animate, \
                contextlib.redirect_stdout(stdout):
            py_maze.main()

        return stdout.getvalue(), animate

    def maze_of(self, output):
        # Returns:
        #     str: The maze main printed, without the markers around it
        lines = output.splitlines()
        return '\n'.join(
            lines[lines.index('start') + 1:lines.index('end')])


class TestMain(MainRunner, unittest.TestCase):
    def test_a_plain_run_prints_an_unsolved_maze(self):
        output, animate = self.run_main()

        self.assertNotIn(py_maze.SOLUTION_MARKER, self.maze_of(output))
        self.assertEqual(animate.call_count, 0)

    def test_the_default_maze_is_the_normal_preset(self):
        width, height = py_maze.DIFFICULTIES[py_maze.DEFAULT_DIFFICULTY]
        output, _ = self.run_main()

        self.assertEqual(len(self.maze_of(output).splitlines()), height * 2 + 1)
        self.assertEqual(len(self.maze_of(output).splitlines()[0]),
                         width * 2 + 1)

    def test_a_difficulty_sets_the_size(self):
        width, height = py_maze.DIFFICULTIES['easy']
        output, _ = self.run_main(['-d', 'easy'])

        self.assertEqual(len(self.maze_of(output).splitlines()), height * 2 + 1)

    def test_solve_overlays_the_solution(self):
        output, animate = self.run_main(['--solve'])

        self.assertIn(py_maze.SOLUTION_MARKER, self.maze_of(output))
        self.assertEqual(animate.call_count, 0)

    def test_animate_runs_the_search_on_a_terminal(self):
        output, animate = self.run_main(['--animate'])

        self.assertEqual(animate.call_count, 1)
        self.assertIn(py_maze.SOLUTION_MARKER, self.maze_of(output))

    def test_animate_falls_back_to_solving_when_the_output_is_piped(self):
        # there is no screen to animate over, but the solution is still
        # worth printing
        output, animate = self.run_main(['--animate'], terminal=False)

        self.assertEqual(animate.call_count, 0)
        self.assertIn(py_maze.SOLUTION_MARKER, self.maze_of(output))

    def test_the_seed_is_reported_so_the_maze_can_be_replayed(self):
        output, _ = self.run_main(['--seed', '2024'])

        self.assertIn('seed: 2024', output)

    def test_the_same_seed_prints_the_same_maze(self):
        first, _ = self.run_main(['--seed', '2024'])
        second, _ = self.run_main(['--seed', '2024'])

        self.assertEqual(self.maze_of(first), self.maze_of(second))

    def test_an_unseeded_run_reports_the_seed_it_chose(self):
        output, _ = self.run_main()
        reported = re.search(r'^seed: (\d+)$', output, re.MULTILINE)

        self.assertIsNotNone(reported, "every run should report its seed")
        self.assertLess(int(reported.group(1)), py_maze.MAX_SEED)

    def test_answering_yes_starts_the_game(self):
        with mock.patch.object(py_maze, 'MazeGame') as game:
            self.run_main(response='y')

        game.return_value.play.assert_called_once_with()

    def test_answering_no_says_goodbye(self):
        output, _ = self.run_main(response='n')

        self.assertIn(py_maze.GOODBYE_MESSAGE, output)

    def test_collectibles_are_scattered_over_the_maze(self):
        output, _ = self.run_main(['-c', '4', '--seed', '2024'])

        self.assertEqual(self.maze_of(output).count(
            py_maze.COLLECTIBLE_MARKER), 4)

    def test_a_plain_run_scatters_none(self):
        output, _ = self.run_main()

        self.assertNotIn(py_maze.COLLECTIBLE_MARKER, self.maze_of(output))

    def test_the_same_seed_scatters_them_the_same_way(self):
        first, _ = self.run_main(['-c', '4', '--seed', '2024'])
        second, _ = self.run_main(['-c', '4', '--seed', '2024'])

        self.assertEqual(self.maze_of(first), self.maze_of(second))

    def test_collectibles_are_still_visible_on_a_solved_maze(self):
        output, _ = self.run_main(['-c', '4', '--seed', '2024', '--solve'])
        maze = self.maze_of(output)

        self.assertEqual(maze.count(py_maze.COLLECTIBLE_MARKER), 4)
        self.assertIn(py_maze.SOLUTION_MARKER, maze)

    def test_the_game_is_handed_the_collectibles(self):
        with mock.patch.object(py_maze, 'MazeGame') as game:
            self.run_main(['-c', '3', '--seed', '2024'], response='y')

        _, collectibles = game.call_args[0]
        self.assertEqual(len(collectibles), 3)


class TestMainSaveAndLoad(MainRunner, unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = os.path.join(self.directory.name, 'maze.txt')

    def test_save_writes_a_file_and_says_so(self):
        output, _ = self.run_main(['--save', self.path, '--seed', '2024'])

        self.assertIn('saved: %s' % self.path, output)
        self.assertTrue(os.path.exists(self.path))

    def test_a_saved_maze_loads_back_exactly(self):
        saved, _ = self.run_main(
            ['-o', self.path, '-c', '4', '--seed', '2024'])
        loaded, _ = self.run_main(['--load', self.path])

        self.assertEqual(self.maze_of(loaded), self.maze_of(saved))

    def test_a_loaded_maze_reports_the_seed_it_was_saved_from(self):
        self.run_main(['--save', self.path, '--seed', '2024'])
        output, _ = self.run_main(['-l', self.path])

        self.assertIn('Loading maze...', output)
        self.assertIn('seed: 2024', output)

    def test_a_loaded_maze_ignores_the_generation_options(self):
        # the maze is 6 by 7 whatever --difficulty and --width ask for
        self.run_main(['--save', self.path, '-w', '6', '-H', '7'])
        output, _ = self.run_main(['--load', self.path, '-d', 'hard',
                                   '-w', '20'])

        self.assertEqual(len(self.maze_of(output).splitlines()), 7 * 2 + 1)

    def test_a_loaded_maze_can_be_solved(self):
        self.run_main(['--save', self.path, '--seed', '2024'])
        output, _ = self.run_main(['--load', self.path, '--solve'])

        self.assertIn(py_maze.SOLUTION_MARKER, self.maze_of(output))

    def test_a_loaded_maze_keeps_its_collectibles(self):
        self.run_main(['--save', self.path, '-c', '4', '--seed', '2024'])
        with mock.patch.object(py_maze, 'MazeGame') as game:
            self.run_main(['--load', self.path], response='y')

        _, collectibles = game.call_args[0]
        self.assertEqual(len(collectibles), 4)

    def test_a_maze_with_no_seed_to_report_says_nothing_about_one(self):
        py_maze.write_save(self.path,
                           py_maze.MazeGenerator(3, 3, seed=1).generate())
        output, _ = self.run_main(['--load', self.path])

        self.assertNotIn('seed:', output)

    def test_loading_a_missing_file_exits_with_a_message(self):
        missing = os.path.join(self.directory.name, 'nowhere.txt')
        with self.assertRaises(SystemExit) as caught:
            self.run_main(['--load', missing])

        self.assertIn('py_maze:', str(caught.exception))
        self.assertIn('nowhere.txt', str(caught.exception))

    def test_loading_something_that_is_not_a_maze_exits_with_a_message(self):
        with open(self.path, 'w', encoding='utf-8') as handle:
            handle.write("just some notes\n")

        with self.assertRaises(SystemExit) as caught:
            self.run_main(['--load', self.path])

        self.assertIn('not a py_maze save file', str(caught.exception))

    def test_saving_somewhere_unwritable_exits_with_a_message(self):
        unwritable = os.path.join(self.directory.name, 'no', 'such', 'dir.txt')
        with self.assertRaises(SystemExit) as caught:
            self.run_main(['--save', unwritable])

        self.assertIn('py_maze:', str(caught.exception))


class TestMainInterrupt(unittest.TestCase):
    def test_an_interrupt_at_the_prompt_says_goodbye(self):
        stdout = io.StringIO()
        with mock.patch.object(py_maze.sys, 'argv', ['py_maze']), \
                mock.patch.object(py_maze, 'terminal_size',
                                  return_value=terminal_size(200, 80)), \
                mock.patch.object(py_maze, 'read_response',
                                  side_effect=KeyboardInterrupt), \
                contextlib.redirect_stdout(stdout):
            py_maze.main()

        self.assertIn(py_maze.GOODBYE_MESSAGE, stdout.getvalue())


if __name__ == '__main__':
    unittest.main()
