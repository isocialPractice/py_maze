# Changelog

All notable changes to py_maze are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the version is a [PEP 440](https://peps.python.org/pep-0440/) pre-release
counter: `1.0.0aN`, counting up to the first published release. Every entry
from `## [3.0.4]` down is a
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) number, which is
what the project numbered itself with until 2026-10-09, and those numbers are
left as they were written.

**The old scheme reached `1.0.0` first**, on 2025-12-25, so that entry is
headed `## [1.0.0 under semver]` rather than `## [1.0.0]`. The counter is
climbing to a `1.0.0` of its own, and a reader and the pattern the suite
reads these headings with both have to be able to tell the two apart. The
entry below that heading is unchanged; only the heading says which scheme
its number belongs to.

Work that earns no version at all - documentation and repository chores - is
recorded under a dateless `## [Unreleased]` heading above the entries, which
is where Keep a Changelog puts it, and folds into the next version's entry
when one is written.

> 25 earlier entries in `CHANGELOG-2026.md`, newest first.

> 1 earlier entry in `CHANGELOG-2025.md`, newest first.

## [1.0.0a19] - 2026-11-23

Three readings of the style work, and the one of them that was a test
passing for the wrong reason. The mode screen's subset assertion took the
whole marker table off the screen before comparing it against the style,
which is every fallback that assertion existed to catch; nothing settled a
style against the one half of `can_display` a real console was measured
refusing on; and the sentence corrected in `1.0.0a18` still told a reader
on a `cp437` console that the code page decided a fallback it does not
decide.

### Fixed

- **The mode screen subtracts the four markers a mode draws, not all
  twelve.** `test_every_mode_draws_its_whole_play_screen_from_the_style`
  closed with
  `assertLessEqual(set(''.join(rows)) - self.MARKERS, set(self.STYLE))`.
  Eight of the twelve markers in `MARKERS` - seven distinct characters
  among them, `FRONTIER_MARKER` and `HINT_MARKER` both being `?` - are
  exactly what a style field falls back to, so every fallback the reading
  exists to catch came off the set before the comparison ran. Measured
  against the eleven mutations the `1.0.0a18` entry lists and the wall read
  beside them: the test caught one of those twelve, `self.style.player`,
  and passed both `maze_lines` reads and the other two of
  `MazeGame.frame`'s. It now subtracts `MODE_MARKERS` alone -
  `CHASER_MARKER`, `DOOR_MARKER`, `BOX_MARKER` and `GUIDE_MARKER`, the four
  a mode lays over the maze itself - and the screen it reads carries five
  of the eight fields rather than three, the pickups arriving with the game
  and the hint cells set the way `show_hint` sets them. Re-measured, it
  fails on five of the twelve: both `maze_lines` reads and all three of
  `MazeGame.frame`'s. The seven it still passes are the overlay and solver
  reads, which a mode's play screen does not go through, and each of those
  is read by a test of its own
- **The legacy stdio writer names the process's ANSI code page, and the
  Drawing Styles section now says so.** The paragraph corrected in
  `1.0.0a18` closed "and there `cp437` and `cp850` carry both of these
  walls while `cp1252` carries neither", which is true of a stream
  redirected under such a locale and misleading about the other
  destination the same sentence named. Read off a real console: at
  `chcp 437` with `PYTHONLEGACYWINDOWSSTDIO=1`, `sys.stdout.encoding` is
  `cp1252` and both `--style box` and `--style block` fall back to `*`,
  though `cp437` carries both walls - and the same run on a `chcp 1252`
  console reports `cp1252` as well, so the console's output code page is
  not being read at all. The child reported `isatty` true in both, so the
  handle really was a console rather than a reopened descriptor. The
  fallback is the right answer either way, the writer being what cannot
  encode the wall, but a reader was told `chcp` decided it one paragraph
  after being told `chcp` decides nothing on a console. The section now
  separates the two destinations, keeps the `cp437` and `cp850` clause for
  the redirected one it is true of, and says the writer reads the ANSI code
  page rather than the console's. The `drawable_style` docstring said "a
  stream naming a code page of its own" and needed no change

- **The checks that read the repository root for documents leave a rolled
  changelog out, the way they already left the TODO archive out.** This
  run's archive step moved 26 changelog entries older than the retention
  window into `CHANGELOG-2026.md` and `CHANGELOG-2025.md` beside
  `CHANGELOG.md`, and three tests failed on them at once: both subtests of
  `TestDevelopmentFileTree.test_it_lists_the_files_the_repository_carries`,
  because a new root document has to be drawn on the project structure map,
  and
  `TestRepositoryTextShape.test_the_prose_read_here_is_every_document_the_root_carries`,
  because `DOCUMENTS` is held against what the root carries. `root_documents`
  already excluded `TODO-archive.md` for the reason that covers these word
  for word - a document a tool writes holds text verbatim under a heading
  the tool wrote, so its shape is the roll's and not this repository's to
  keep - so the exclusion is now the two of them, the changelog's matched on
  `CHANGELOG-<year>.md` rather than named. Naming them would be a list that
  falls behind on a January 1st, and what it would fail is the check holding
  the root against `DOCUMENTS`: the new year would be reported as an unread
  document rather than as a list wanting a line. Putting them on the map
  instead fails the other way round, since
  `test_every_entry_it_draws_is_really_there` holds every entry to being on
  disk and a year file need not be. The claim both `docs/development.md` and
  `CONTRIBUTING.md` make - that the list is every Markdown document the root
  carries - now says "that a person writes" and names the two the rolls
  write

### Added

- **A style settled against a console, which is the half of
  `can_display` the fallback was never driven through.** Every stream in
  `TestDrawableStyle` came from `stream_with`, a mock whose `fileno()` is
  not a descriptor, so `is_a_terminal` answered False and the whole class
  settled on the encoding half. Measured at `chcp 437`, `1252` and
  `65001`, that is the half that never fires: `sys.stdout.encoding` is
  `utf-8` on all three and `can_encode` passed everything asked of it,
  while the only refusal in 18 console runs was the cell half turning down
  the win banner's party popper on every one of the three code pages.
  `TestCanDisplay` covers that branch for `can_display` itself and nothing
  paired it with a style. Two tests now do: a style holding a character
  above the basic multilingual plane falls back to `ascii` against a
  console stand-in reporting `utf-8`, built the way
  `TestCanDisplay.on_windows` builds one, with `can_encode` asserted to
  pass the same style so the refusal is read as the cell half's; and the
  same console keeps every shipped style, which is the control a stand-in
  that refused everything would have passed without reading a style at
  all. Both are stdlib-only and run wherever the suite runs, unlike the
  console harness that measured this. The first is the only test of the
  1,318 that catches `drawable_style` asking `can_encode` in place of
  `can_display`
- **The corrected sentence is pinned where it was rewritten.** The
  Drawing Styles section has now been corrected twice for saying the
  console's code page decides something it does not, so the shape of the
  mistake - naming the legacy writer without naming the code page it reads
  - is held by a test: the section names `PYTHONLEGACYWINDOWSSTDIO` and
  names the ANSI code page. Reverting the paragraph to either earlier
  wording fails it

### Changed

- **`TestRedrawInAStyle.LINES` counts the widths the class actually
  takes.** Its comment read "rows enough that `fit_frame` never cuts the
  frame, at either width" while `WIDTHS` holds three - `WIDE = 100`,
  `NARROW = 40` and `TIGHT = 15`. The substance was right and only the
  count was wrong: `frame_height` of the `seed=2024` play frame is 18, 19
  and 22 rows at those widths against `LINES = 24`, so `fit_frame` hands
  all 18 lines back untouched at every one of them and the pin compares
  two screens rather than two windows. The comment now says that, with the
  three figures, so a reader checking whether the tightest width was
  allowed for is not told it was never considered

## [1.0.0a18] - 2026-11-16

What `--style` says about its own fallback, corrected against a real
console, and the seven fields of a style that nothing was reading. The
fallback itself is sound and was measured firing; what was wrong is the
trigger every one of its five prose locations named. Beside that, a style
whose eight fields are eight distinct characters, which is the first thing
in the suite that can tell a field being read from a field being ignored.

### Fixed

- **The `--style` fallback is read off the stream's encoding, not off the
  console's code page.** The Drawing Styles section of `docs/options.md`
  said "A Windows console on a legacy code page is the usual case:
  `cp437` and `cp850` carry both of these walls and `cp1252` carries
  neither", the `drawable_style` docstring said "a console on a legacy
  code page cannot carry the light cross", and `--help` told every reader
  that "A style the terminal cannot draw falls back to ascii". Read back
  off a real console, none of the three holds: at `chcp 1252` both
  `--style box` and `--style block` draw their own wall, every cell of
  the maze holding U+253C or U+2588 and none holding U+FFFD. CPython
  writes to a Windows console through `_WindowsConsoleIO`, which is
  `WriteConsoleW` and UTF-16, so `sys.stdout.encoding` is `utf-8` on
  every code page and `can_encode` is never asked the question the
  documentation described. What does fire the fallback is a stream whose
  encoding really is a legacy code page - output redirected to a file or
  a pipe under such a locale, or a run with
  `PYTHONLEGACYWINDOWSSTDIO=1`, which puts the legacy writer back in
  front of the console - and both were measured doing it, silently and
  exit 0. All three locations now name that, and the one-line summaries
  in `README.md`, `docs/index.md` and `docs/CHEATSHEET.md` say "where the
  destination cannot carry them" rather than naming the terminal: a
  bullet of that length does not owe the distinction, but it must not
  name the wrong half of it. The `box` note `--help` prints beside the
  corrected sentence is reworded with it, for the same reason
- **The win banner's paragraph in `docs/playing.md` tells the same story
  about the same two cases.** It opened "A legacy code page cannot encode
  the glyph at all; a classic console window ... encodes it perfectly
  well and still cannot draw it", which reads as a console at `chcp 1252`
  being the first of the two when it is always the second. The paragraph
  now says which destination is which and why a console cannot be the
  first. What the banner prints is unaffected either way: the party
  poppers are above the basic multilingual plane, so a classic console
  falls back on the cell half whatever its code page carries

### Added

- **A style whose eight fields are eight distinct characters, so the
  seven that were unexercised stop being unexercised.** All three shipped
  styles are `ASCII_STYLE._replace(wall=...)`, so `open_cell`, `player`,
  `solution`, `frontier`, `visited`, `hint` and `collectible` hold the
  same character in every one of them, and every test that read a field
  compared it against `BLOCK_STYLE.<field>` - which is that same ASCII
  constant. Measured by mutation before the change: reverting
  `style.open_cell` in `maze_lines`, `style.solution` in
  `solution_overlay`, `style.collectible` in `collectible_overlay`,
  `style.frontier` and `style.visited` in `animate_search`'s overlays,
  those two and `style.solution` in its legend, and `self.style.player`,
  `self.style.hint` and `self.style.collectible` in `MazeGame.frame`,
  each to the constant it replaced, left the whole suite green.
  `TestEveryFieldOfAStyleDraws` draws the fixed `seed=2024` maze with a
  `MazeStyle` of eight characters no module defines, through
  `maze_lines`, both overlays, `animate_search` and `MazeGame.frame` in
  every mode, and asserts each field's character lands in the cells that
  field draws. Re-run against it, all eleven of those mutations now fail
  at least one test. Two of its tests are guards rather than readings -
  that the style shares no character with any module marker, and that no
  shipped style could have done this job - because without the first
  every assertion holds whether the field was read or not
- **The redraw pinned against a style in the suite's own screen.** No
  test walked a game through a move in a style at all: the style tests
  read `maze_lines`, the overlays, the solver's legend and which style a
  game was handed, and every redraw test ran in `ascii`, so the one
  thing a style could break about the redraw was checked only by a
  harness needing a Windows console. `TestRedrawInAStyle` plays a fixed
  dozen moves - two turns and a backtrack among them, every one landing
  on a new cell - once per style, at the three widths the console
  reading was taken at, and asserts the block screen with U+2588 put
  back to `*` equals the `ascii` screen row for row. 100 columns wraps
  nothing, so a move writes the rows it changed; 40 and 15 carry the
  controls line onto the row below, so every frame is drawn whole. A
  third test holds the two widths to being those two halves, since a pin
  taken at one of them says nothing about the other. `PlaySession` takes
  a `style` to make this possible, passing it to the `MazeGame` it
  builds the way a run hands one over

### Changed

- **The two style tests that read wider than they are say so.**
  `test_the_overlays_draw_what_the_style_they_are_given_draws` and
  `test_the_solver_names_the_markers_its_frames_were_drawn_with` both
  pass against code that ignores the style it was handed, because the
  fields they compare are `BLOCK_STYLE`'s and `BLOCK_STYLE`'s are the
  constants. Both are kept - they pin the shape of what an overlay and
  a legend return - and each now carries a comment saying what it cannot
  tell apart and where those fields are actually read

## [1.0.0a17] - 2026-11-14

What a maze is drawn with is a choice now. The eight markers a picture is
made of are one object, three styles are built out of it, and `--style`
picks between them, with the two that leave ASCII giving way wherever the
terminal cannot draw them. A bare run draws exactly what it drew before the
option existed. The comment correction that was waiting under
`## [Unreleased]` ships here as well, written reviewing `1.0.0a16` after it
was tagged.

### Fixed

- **The comment on the heading pin says what both of its subtests do.**
  The `1.0.0a16` entry below records that the block swap keys each of the
  two statement shapes under the older entry, and the comment on
  `test_a_heading_below_a_statement_keys_it_under_the_entry_above` still
  read the other way: that the loop fails the two shapes differently, a
  paragraph by the order alone and a bullet by its own opener, and that
  one shape passing said nothing about the other. Both subtests report
  the same keying failure under the reordering the pin names - the
  `version = heads[number]` assignment lifted over the flush - and under
  the `statements.setdefault(heads.get(number, version), [])` keying
  mutation, because a bullet's opener flushes the statement above it
  rather than the one it starts, so an entry carrying one statement
  never flushes early and the heading is what reaches both shapes. The
  comment names the second mutation too, exchanging the two blocks
  whole, which carries the append up as well and does key the bullet
  correctly: that edit is the one the earlier wording was describing, and
  leaving the two unnamed is what let the rationale be rewritten twice.
  Both shapes are kept: the pin holds, and its rationale was what was
  wrong. The `1.0.0a16` wording stands as released; this entry is the
  correction to it
- **The usage block on the options page is the usage the parser prints.**
  It showed `--mode {plain,chase}` and no `--quest-stages` at all, so it
  had been stale since quest mode shipped. Nothing read it: the examples
  the suite runs as written are named one at a time on the generating and
  scripting pages, and this block is on neither
- **The README counts the options there are.** It said twenty-one and
  listed ten of them as "the rest", leaving `--quest-stages` out of both
  the count and the list while the options page tabled it. With `--style`
  there are twenty-three, which is what it now says

### Added

- **The markers a maze is drawn with are one object.** `MazeStyle` is a
  named tuple of the eight the picture is made of - the wall, the open
  cell, the player, the solution, the frontier, the visited cell, the hint
  and the collectible - so a second way of drawing a maze is a second
  object rather than a branch inside `maze_lines`. The chaser, the door,
  the box and the guide stay module constants: each belongs to one mode
  and was picked to say something a glyph had to argue for, the door
  having to read heavier than the wall beside it, so a style re-picking
  them would be making those arguments again against a wall it knows
  nothing about
- **The markers py_maze has always drawn with are a style under a name.**
  `ASCII_STYLE` is built out of `WALL_MARKER` and the seven beside it
  rather than repeating their characters, so a marker a caller imports by
  name and the style that draws it cannot drift apart. It is what
  `DEFAULT_STYLE` names and what every drawing function falls back on
  when it is handed no style, which is why a run with no options draws
  what it drew before and the suite's fixed mazes still match
- **A box-drawing style, drawn only where it can be.**
  `BOX_DRAWING_STYLE` draws its wall with the light cross: a wall here is
  a whole cell rather than the edge of one, and that is the one character
  in the set that joins to the cell beside it on all four sides, so a run
  of them reads as the lattice a maze is. `drawable_style` settles a name
  against the stream before the maze is drawn and hands back
  `ASCII_STYLE` where the destination cannot draw every character of the
  one asked for, the way `win_banner` falls back to its plain wording.
  The whole style gives way rather than the character that failed, so a
  picture is never half in one style and half in another
- **A block style, for a font the asterisk reads poorly in.**
  `BLOCK_STYLE` draws a full block for a wall and leaves the cell a
  space, so the maze reads as one wall with the corridors cut out of it
  rather than as a grid of characters. Both of these walls are in `cp437`
  and `cp850` and in neither `cp1252` nor ASCII, so the fallback is a
  measurement of the destination rather than a rule about Unicode
- **`--style` picks between them**, defaulting to `ascii`, with the names
  and what each draws listed in its help text the way `--algorithm` lists
  its own. It has no short flag, both `s` letters being spoken for. The
  style is settled once for the run and handed to the picture, the
  solver's frames and the play screen alike, so a fallback reaches all
  three or none of them, and every mode names it rather than reading it
  out of the settings a mode reads one each of. A maze is saved in
  `ascii` whatever it is drawn in: the format fixes the characters a
  picture is read back from, so `save_lines` passes no style at all
- **The option is documented where the others are.** A `Drawing Styles`
  section on the options page draws the same maze in all three and says
  the two things a terminal hides - the silent fallback, and the save
  file being written in `ascii` regardless - with the option tabled on
  the options page and the cheat sheet and a feature line in the README
  and on the site's front page. The style names are on the public surface
  as `STYLES`, `STYLE_NOTES`, `named_style` and `drawable_style`; the
  table `docs/library.md` owes them is still queued

## [1.0.0a16] - 2026-11-10

Four of the pins `1.0.0a15` added or reworded held less than they named: a
block order nothing read, an empty entry reported as the wrong failure, a
blank-line rule the Python files stood outside, and a fixture whose own
margin was recorded nowhere. Found reviewing `1.0.0a15` after it was tagged.

### Added

- **A statement is pinned to the heading it was written below.**
  `changelog_statements()` flushes the statement it is holding before it
  moves to the heading it has just reached, and nothing read that order.
  Every changelog the suite reads puts a blank line above a heading, which
  flushes the statement a line earlier and leaves the order making no
  difference, so the shape that reads it is the one none of them writes. A
  heading directly below a paragraph keys that paragraph under the entry the
  heading opens once the two blocks are swapped, which is the newer entry's
  prose answering for the older entry. Both statement shapes are written,
  and the swap keys each of them under the older entry: a bullet's own
  opener flushes the statement above it rather than itself, so where an
  entry carries one statement the heading is what reaches both shapes
- **A run of three blank lines is reported in the Python files.** `1.0.0a15`
  records a run of three before a class becoming two, and nothing held that.
  The pair check reads the Markdown documents and the published pages, so
  the run could come back to either Python file unreported. PEP 8 asks two
  blank lines between top-level definitions and names no shape that takes
  three, so the Python files are read for the run where the documents are
  read for the pair: `test_py_maze.py` and every module under `py_maze/`,
  both already in reach of the width checks beside it

### Changed

- **Every entry carrying a version is read for prose, not every dated
  one.** The dateless `## [Unreleased]` heading is the one this project adds
  by hand between releases, and an empty one was the single shape the check
  could not see, so the keying pin failed in its place and reported the
  order of the entries when what was wrong was an entry missing from them.
  The check named for an entry read as no prose reports it now
- **The keying pin fails for the order alone.** It compared the versions
  keyed against every version the file heads, so an entry read as no prose
  was a list the wrong length rather than prose nobody could read. Only the
  versions that were keyed are compared now, and the check above reports the
  rest

### Fixed

- **The split-statement test's own margin was recorded nowhere.** The test
  fails under the span widening it was rewritten for only because its two
  statements, once joined, stand 71 characters apart, which is inside a
  spread of 120 characters. The margin is 49 of them: a first statement 49
  longer still pairs once joined and 50 longer does not, so a rewording of
  that size would send the test back to passing for the span being too
  narrow while it still read as a test of the statement boundary. The joined
  pair is asserted in the same test, which holds the fixture's own gap
  inside the spread

## [1.0.0a15] - 2026-11-08

One of the pairing tests added in `1.0.0a14` could not fail for the rule it
named, and the order the entries they read are keyed in was held by nothing.
Found reviewing `1.0.0a14` after it was tagged.

### Added

- **The order `changelog_statements()` keys its entries in is pinned where it
  is produced.** The earliest entry to state a pairing is read off the end of
  that dict, so its keys have to run in the order the file writes its entries.
  Both ends of that were already held - the file's own order through
  `changelog_entries()`, and the reader of the dict against a dict written by
  hand - and the reader between them was held by nothing. Keying its entries
  by a text sort of the version left the whole suite passing, because the
  three versions this file carries reach the right answer under a text sort by
  luck. Reversing the order was caught, so what was missing was the general
  pin rather than any pin at all

### Fixed

- **The test naming the one-statement span could not fail for it.** A pair
  split across two statements is no claim, and neither statement the test
  passed held the constant at all - so the reader answered no because the name
  was absent rather than because the span is one statement. Widening the span
  to the joined statements left every test passing, which is to say the span
  the class comment opens by describing was exercised by nothing. One
  statement now names the constant and the next carries the count, near enough
  to pair once joined, and the widening fails here
- **A comment credited another test with catching a lowered span figure.** The
  test it named reads the one pairing this file really carries, and that
  statement writes its two ends a handful of characters apart, so it fails
  only for a span narrower than that handful. Most of the range below the
  figure is caught by the equality the comment was attached to, and the
  comment read that equality as guarding one direction where it guards both
- **Three blank lines stood before a class.** Every other top-level definition
  in the suite is preceded by two, and that run of three was the only one in
  the file

## [1.0.0a14] - 2026-11-06

What settles a claim about a constant's length, the fenced example that could
have answered for one by accident, and tests for the three pairing rules this
project's own prose never reached. Found reviewing `1.0.0a13` after it was
tagged, alongside the two corrections that were already waiting here for a
number.

The reader added in `1.0.0a13` held a comment's credited version against that
version's entry and took any entry stating the pair as an answer. Three
entries here state the one pairing the suite credits, because a length gets
restated whenever new wording is written to fit inside it and again whenever a
correction has to quote it - so the check could be satisfied by re-dating the
comment to an entry that records no change to the constant at all, which is
the failure the reader exists to catch.

### Added

- **The three rules the pairing check rests on are exercised.** The pattern
  reads the count written before the constant as well as after it; the two
  have to stand within a fixed span of each other inside one statement; and
  the entries stating a pair are reported in the changelog's own order. A
  passing run reached none of the three - every statement in this file names
  the constant first, nothing in it stands anywhere near the edge of that
  span, and the list of entries is only built once a claim has already failed.
  Each was taken out in turn and the whole suite still passed. The span's own
  figure is held to its value as well, since the boundary tests read the
  constant and would otherwise follow it anywhere
- **The changelog reader is tested against changelogs written for the
  purpose.** `changelog_entries()` and `changelog_statements()` take the path
  they read, defaulting to this file, so a test can write a synthetic entry
  the way the comment reader's tests already write synthetic Python. This file
  carries no fenced block anywhere, which is why the reading below could be
  pinned no other way

### Changed

- **The entry that settles a credited claim is the one recording the change**,
  not every entry that mentions the pairing. The earliest entry stating it is
  the one held to, and a comment crediting a later one is reported even though
  that entry does say the words. Earliest is read off this file's own order,
  which runs newest first and is already held to that, rather than by sorting
  the version strings. A text sort reaches the right entry for the three
  versions this file happens to carry and the wrong one for any two whose
  counters are a single digit, so what is held is the order rather than one
  answer it produced. The entry's own `### Added` or `### Fixed` section was
  the other candidate and is wrong here: the entry recording the shortening
  writes it under `### Changed`, which is where a constant losing a word
  belongs, while both entries that only restate it write it under
  `### Fixed`. What the rule chosen cannot see is a constant reaching the
  same length twice, and the class comment says so rather than leaving the
  limit to be discovered in a green run

### Fixed

- **A figure a sentence wrapped onto a line of its own split the entry it
  was in.** Found reviewing `1.0.0a13` after it was tagged.
  `changelog_statements()` read every line opening with a number and a full
  stop as a numbered list item, and the `1.0.0a9` entry ends a sentence on a
  column count that the wrap carried onto a line by itself, so one paragraph
  of that entry was reported as two statements broken mid-sentence. The join
  is what the reader exists for: a constant named on one side of such a break
  and its count written on the other reads as unpaired, and an unpaired read
  is reported as a comment crediting the wrong version, which would be a
  correct comment called wrong. Markdown lets a numbered item interrupt a
  paragraph only where it is numbered 1, and that is the rule the reader
  keeps now: inside a list any number opens the next statement, inside a
  paragraph only a bullet or a `1.` does. The entries are otherwise read
  exactly as before, that one paragraph being the only statement anywhere in
  the file whose span changed
- **The note on reading comments described the join backwards.** The
  `1.0.0a13` entry said the four labels written from the ends of the
  tree-drawing constant lines would otherwise open the comment block below
  them. Two blank lines and a `def` stand below them; what they would have
  joined is the block above, as its closing lines, and that block introduces
  the constants rather than labelling any one of them
- **An example inside a fenced block was read as the prose of the entry round
  it.** `changelog_statements()` did not know where the fences were, unlike
  the `changelog_entries()` it keys off, which skips a fenced `## ` heading on
  purpose. Reading them on that side only was worse than reading them on
  neither: in a worked entry of the shape `CONTRIBUTING.md` shows a
  contributor - a fence holding a version heading with a bullet under it - the
  heading was skipped while the bullet was appended to the entry the fence
  sits inside, so that entry answered for a count no entry here ever stated. A
  fence now closes the statement running into it and none of its lines joins
  one
- **Two comments described the comment join backwards.** The note on reading
  comments and the test holding it both said the four labels written from the
  ends of the tree-drawing constant lines would otherwise be read as the
  opening lines of the block below them. Two blank lines and a `def` stand
  below those four; the block they would have joined is the one above them,
  which introduces the constants rather than labelling any one of them. The
  `1.0.0a13` entry said it the same way round and is corrected above, so these
  two were the places left

## [1.0.0a13] - 2026-11-04

A reader for the one claim the suite's comments make that the repository can
check itself, and the two corrections to 1.0.0a12 that were waiting for a
number.

The comment corrected below was found by reading the prose, after 1.0.0a12
was tagged and with the wrong pairing already shipped inside it. Nothing in
the suite read a claim of that shape, and the claim is mechanically
checkable: the count is in the module and this file holds one entry per
version. What stopped a reader being kept the first time was scope - one
written against a block of prose failed on the entry that had to restate the
wrong pairing in order to correct it, and was dropped rather than narrowed.

### Added

- **A comment that dates a constant's length is read against the entry it
  credits.** A sentence of a `#` comment in `test_py_maze.py` that names one
  of the package's string constants, counts its characters and names a
  version is a claim about that version's entry here, and the entry has to
  state the same count for the same constant. The shape is one count and one
  constant to a sentence: a count that cannot be tied to one name is a claim
  nothing can check, and the answer to one of those is to write it as two
  sentences rather than to have a reader guess which number belongs to which
  name. Several versions are allowed and one of them carrying the claim is
  enough, which is what lets a comment say what a wrong pairing was by naming
  the right version beside it. The comments come from the tokenizer rather
  than from lines whose first character is a `#`, because a line of a string
  can open with one and say everything a comment says. Only the suite's
  comments are read: a correction here necessarily restates the wrong
  pairing, which is what sank the reader written during the fix for it
- **The sentence is the span, rather than the comment.** The comment on
  `TestPlayScreenOnANarrowTerminal` counts `CONTROLS_LINE` in its first
  sentence and dates a different change in its last, and the one on
  `TestAFrameLineAsWideAsTheConsole` reads its widths off a real console at a
  version without counting characters at all. Both are the shape from a
  distance and neither is a claim, so both are left alone. A line of nothing
  but `#` ends a paragraph rather than joining the two either side of it,
  the suite ending most of its paragraphs without a full stop, and a comment
  with code in front of it stands alone and joins nothing - the four that
  label the tree-drawing constants from the end of their own lines would
  otherwise be read as the closing lines of the block above them, which
  introduces the constants rather than labelling any one of them
- **The entries here are read as statements rather than as lines.** One
  bullet or one paragraph, its wrapped lines joined back into a line, ending
  at the next bullet, the next blank line or the next heading. The file wraps
  at the width it is read to, so a constant and its count are as likely to
  straddle a break as not, and the two have to stand within 120 characters of
  each other inside one statement to read as the same claim - the two ends of
  a long bullet say nothing about each other

### Fixed

- **A test comment credited the wrong version with the quest line's
  shortening.** Found reviewing `1.0.0a12` after it was tagged. The class
  comment on `TestTheGuideAnswerLeavesTheFrameAlone` named `1.0.0a7` as where
  `QUEST_CONTROLS_LINE` lost the word "Press" to reach 79 characters, which is
  the 1.0.0a6 change - 1.0.0a7 is where `CONTROLS_LINE` went from 66
  characters to 60, and its entry says as much in as many words. A reader sent
  to 1.0.0a7 for the precedent the guide's answer follows found the plain
  line's change instead. The comment now names 1.0.0a6 and says "the quest
  controls line", the two being the same claim from either side.
  `KNOWN_BUGS.md` and the `1.0.0a12` entry had the pairing right already, so
  the comment was the one place the repository disagreed with itself about it
- **The sentence introducing the quest API table read as the tail of the
  paragraph above it.** Found reviewing `1.0.0a12` after it was tagged.
  Markdown joins consecutive lines into one paragraph, and `docs/library.md`
  had no blank line between the note on which lines of the foot wrap and
  "`place_quest` is the call behind quest mode's entry, and `Quest` is the
  inventory the player fills:", so the line that says what the table below
  it holds was published as the last clause of a paragraph about wrapping.
  The missing break predates `1.0.0a12`: the paragraph on the guide's answer
  added there landed above it rather than causing it, and only moved which
  text the table's own introduction was joined to

## [1.0.0a12] - 2026-10-31

The guide's answer held to the length of the line it is written over, and
taken down by the end of the game.

Both are what six seconds of reading time exposed. 1.0.0a11 gave the answer
long enough to be read, and both of these had been there all along at a
length nobody could catch: a 0.56 second flicker became a sentence a player
sits and looks at. The first is the fourth round of the wrapped-foot family -
a line of the play screen's foot whose rows nothing counted - and the second
is a sentence about an errand outliving the errand, and the game.

**The answer took the controls line's row but not its row count.**
`GUIDE_LINE` said of itself that asking a question "never changes the height
of the frame". The quest controls line is 79 characters and the answer about
a box was 104, so on a console narrow enough to break the answer further the
frame stood a row taller while it was up, and `fit_frame` paid for that row
out of the maze. `fit_to_terminal` reserves rows for the lines it is handed
and is handed the controls line, never the answer. Read off a real Windows
console at seed 2024, `--mode quest`, pressing `n`: at 80 columns the maze
went from 19 rows to 18, the `end` marker read `end 1 row below`, and 6.1
seconds later both came back. 57 of the widths from 15 to 200 columns did the
same, the bands 39 to 51 and 79 to 103 among them, which hold 44, 80 and 100.

**And the answer was still up when the game was over.** No ending cleared
`quest_message`, so `print_ending` redrew the frame with the guide still
naming the box on the row the keys belong on - under a summary for a quest
the player had just quit. That foot is 2 rows at 80 columns against the
controls line's 1, so the ending gave up a maze row for it as well.

### Fixed

- **The guide's answer cost the maze a row for as long as it was up.** Every
  answer is now written to fit inside `QUEST_CONTROLS_LINE`'s 79 characters -
  the box wording is 73, 74 once the item number reaches two digits - so
  there is no console on which the sentence needs a row the controls line did
  not already have. Shortening the wording is what the controls line's own
  wrap was fixed with in 1.0.0a7, and it is the reading that costs no maze
  row anywhere: reserving against the taller of the two lines would have been
  correct at every width too, and would have left a quest maze permanently a
  row shorter than a plain one at 80 columns, which is the asymmetry that
  work removed. The reword is fixed with it - the door wording was 68
  characters against the box's 104, so finding the box gave the maze row back
  halfway through the answer, and both wordings are now inside the controls
  line
- **An ending drew the guide's answer on the row the keys belong on.**
  `print_ending` takes the answer down before it redraws the frame, which is
  the one place a quit, the exit and the chaser all print through, so a
  summary is printed under the keys whatever is left of the six seconds. A
  game that is over has no errand left for a sentence to be about
- **A step that finished the errand drew the sentence saying it had not.**
  `play` aged the answer before the key was dispatched and not after, so the
  move that opened the door the answer pointed at drew one more frame reading
  `you are carrying item 1, and it opens the door ahead` with the door open
  behind it. The answer is aged on both sides of the key now. The call before
  it stays where it is rather than moving down: the turn nothing was pressed
  on returns from its own branch without reaching anything below, and the two
  hint keys draw a frame from inside their own handler
- **The note and `docs/playing.md` both named one width where the padded
  break still parts a field, and there are two.** Found reviewing `1.0.0a11`
  after it was tagged. A run of spaces early enough in the row to cost it a
  row is passed over at 17 columns and at 18, which is the set the sweep over
  `wrap_on_spaces` pins and what the entry below says in its own opening,
  where `moves` is parted from its count at 17 and 18, before the `Fixed`
  note called 17 the only one. The figure is now 17 and 18 in both places

### Added

- `MazeGame.clear_guide_answer`, the one method the ageing and the ending
  both take the answer down with, so the reading it was given at and the
  errand it was given about always come down with the sentence rather than
  being left for a later turn to age an answer that is no longer up

### Changed

- `Quest.task` records why its wordings are the length they are, and
  `GUIDE_LINE`'s comment no longer claims the height of the frame is safe
  without saying what keeps it so. Taking a line's row is not the same as
  taking its row count, and that distinction is the whole of both faults
- `TestTheGuideAnswerLeavesTheFrameAlone` sweeps 15 to 200 columns rather
  than the five widths a console is usually set to, since one width inside a
  band is as good as the band: no answer longer than the line it replaces, no
  answer needing a row the controls line did not, the reword leaving the
  sentence on the row it was on, and the end-to-end one - a maze carved by
  `fit_to_terminal` for a quest console still fitting that console when the
  controls line's row carries the answer instead. The last is what would
  catch a future wording change reopening this, and it fails at 81 of the
  swept widths with the old wording restored
- The tables in `TestFrameHeight` and the console the padding in
  `TestWrapOnSpaces` is measured on both read off `guide_answers`, a helper
  that walks a real quest through its three states, rather than off a copy of
  the sentence. The copies are how those tables came to describe a 104
  character answer the game had stopped saying, and `TestWrapOnSpaces` came
  down from a 100 column console to a 60 column one with the wording: there
  is no longer a width wide enough for the controls line and too narrow for
  the answer, which is the point of the fix
- `docs/modes.md` and `docs/playing.md` record that every answer is written
  to fit inside the controls line it replaces and why, that the reword
  happens on the row the sentence is already on, and that the end of the game
  takes the answer down. `docs/library.md` names the answer as the third line
  of the foot that can wrap and says why `fit_to_terminal` is handed two
  lines rather than three. `KNOWN_BUGS.md` carries both faults as the console
  readings they were found on

## [1.0.0a11] - 2026-10-29

The guide's answer given the six seconds a sentence needs to be read, and the
tally's break taken between two fields rather than inside one.

Both are the play screen's foot again, and both are the same mistake read two
ways: a line the game treats as a label when what is on it is a sentence. The
guide's answer shared the `h` hint's 0.6 seconds, which is the time a lit
cell needs and not the time 104 characters of prose needs. `wrap_on_spaces`
treated the three spaces between two fields and the one space inside a field
as the same space, which is true of the controls line and false of the tally.

**The answer was gone before it could be read.** `show_quest_hint` wrote
`GUIDE_LINE` over the controls line and held it on a `time.sleep` of
`HINT_SECONDS`, so the keys were back under the player's eyes before the
sentence had been got through. Lengthening that sleep was not the answer
either: `play` draws nothing while it sleeps, so the clock on the status line
would have stood still for the whole of it and every key pressed underneath
would have waited to be played.

**The break fell inside a field.** Read off a real Windows console at seed
2024, `--mode quest --collectibles 9` on 44 columns broke the 47 character
tally after `items` and left `0/3` alone on the row below, with the word it
belongs to on the row above. 31 columns parted `collected` from `0/9`, and
the plain tally did the same at 31 to 34 and parted `moves` from its count at
17 and 18.

### Added

- `GUIDE_SECONDS`, the six seconds the guide's answer is given, exported
  beside `HINT_SECONDS` as that one is. `h` keeps its 0.6: a lit cell is read
  at a glance, and the two are no longer the same number because they were
  never the same kind of thing
- `MazeGame.age_guide_answer`, which holds the answer while it is being read
  and takes it down afterwards. The game loop calls it on every turn it
  takes, the turns nothing was pressed on included, so the answer comes down
  on the clock rather than on the next keypress and a player who asks the
  guide and then stands still is given it for as long as one who walks away
  reading it

### Fixed

- **The padded break could fall inside a field, leaving its name on one row
  and its value opening the next.** `wrap_on_spaces` cut on the last space
  that still filled the row and could not tell a field separator from the
  space inside a field, so the cut landed on whichever came last. The run of
  two or more spaces is now the break that is taken wherever the row holds
  one, which is what keeps a name and its value together. A run early enough
  in the row to leave it well short of the last column is the exception:
  breaking there needs a row the console's own break did not, so the single
  space is kept and the field is parted after all - 17 and 18 columns are the
  only widths at or above the 15 column floor where that still happens, and a
  maze row is the worse thing to spend. The controls line separates its words
  with single spaces and has no run to prefer, so nothing about the line it
  is padded to has moved
- **The guide's answer was pinned to the time a lit cell is given.** The cell
  keeps that moment and keeps it on a sleep; the answer is left standing and
  aged on the loop's own tick, so the clock counts and the player walks while
  it is read. It never outlasts what it says either: finding the box it named
  is the same errand still and rewords the line where it stands, and opening
  the door it named finishes that errand and takes the line down with
  whatever is left of its six seconds

### Changed

- The sweep over the widths a padded tally wraps on asks all four shapes
  `mode_status` builds - 19 characters for the plain game, 31 for a quest
  with no collectibles, 35 with a pickup and 47 with both - rather than the
  two it named. It also asks that no row of a padded tally opens on a value
  rather than on the name it belongs to, and pins the widths where one still
  does to the set that cannot be had without a row, so a width joining them
  is caught as well as one leaving
- The comment over that sweep called the two shapes "the two the game
  builds", counted the quest tally's four fields as three, and called it "the
  widest the game has" when `--collectibles` takes any count and ten of them
  draws 48. All three figures are corrected
- `docs/modes.md` and `docs/playing.md` record that the cell and the words
  come down at different times and why, and that an answer never outlasts
  the errand it was about. `docs/playing.md` and `docs/library.md` record
  that a run of spaces is taken over a single one where the row holds both

## [1.0.0a10] - 2026-10-27

The padding that moves a console's break onto a space now takes the rest of
that run of spaces with it, so a line broken inside a separator starts the
row below on its word.

Found reviewing `1.0.0a9`, which is the version that introduced it.
`wrap_on_spaces` cuts on the last space that still fills the row and carries
the rest of the line over from the character after the cut, which is exactly
right for a separator one space wide. The controls line separates its words
that way and showed nothing; the tally separates its fields with three
spaces, and padding the tally in `1.0.0a9` is what first sent a run of them
through the helper.

**The row below opened on a space.** On a 20 column console
`--mode quest --collectibles 9` breaks the 47 character tally on the second
of the three spaces after `moves 0`, so the row under it read
` collected 0/9` with a space in column 1 and the field no longer sat under
the one above it. The test written for this in `1.0.0a9` asked the question
at 29 columns alone, where the cut falls on the last space of the run and
there is nothing left to lead, so the widths that produced the fault were
the ones the assertion did not reach.

### Fixed

- **A break that fell inside a run of spaces left the rest of the run
  leading the row below.** `wrap_on_spaces` takes the spaces still to come
  off with the break, so a row below starts on its word whether its
  separator was one space wide or three. Stripping them can only shorten the
  padded line, so the rows it occupies are never more than before and the
  reserve `fit_to_terminal` counts is unchanged. The widths where the cut
  falls inside a separator are asked now rather than the one width where it
  falls on the separator's last space, and every width either of them wraps
  on is checked against two of the tallies the game builds - the plain tally
  carrying a pickup, and the quest tally carrying both counts
- **A dropped line's row was wiped where the new frame ends rather than
  where that line was drawn.** `frame_diff` measured the rows of
  `previous[len(current):]` and wiped that many starting below `current`,
  which is the same run of rows only while the lines `current` kept occupy
  as many rows as the ones they replace. A line that lost a wrap left the
  count right and the position wrong:
  `frame_diff(['a' * 50, 'b'], ['a'], size=(39, 24))` wiped the row the
  retained line had been carried onto and left `b` standing a row below the
  frame. Both ends are measured as `previous` was drawn now - from below the
  lines `current` kept to the bottom of the older frame - and the wipe still
  starts no higher than the row the addressing counted to, so a row the new
  frame has taken for itself is never erased. `MazeGame.render` cuts
  `previous` to the length of `current` before the call, so nothing is
  dropped there and what it writes is unchanged
- The reproduction of the erased tally in `## [1.0.0a9]` and `KNOWN_BUGS.md`
  read `   collected 0/9` for what `--mode plain` lost at 20 columns. The
  tally the rest of that paragraph is read from carries a one digit move
  count, which leaves two spaces on the row below rather than three

### Changed

- `docs/playing.md` records that a break falling inside a run of spaces
  takes the rest of the run with it, beside what it already says about the
  break being moved onto a space at all

## [1.0.0a9] - 2026-10-25

The lines of a frame addressed by the rows they sit on rather than by their
place in the list, and the tally padded at its break as the controls line
already was.

The fourth fault in the play screen's foot, and the first of them that is
not a figure nobody checked. `frame_height` has measured a frame in screen
rows since `1.0.0a6`, and `fit_frame`, the wipe and both cursor parks were
converted to ask it. The one place still counting lines was the per line
addressing inside `frame_diff` itself, which is the place a wrap actually
costs a row.

**The line after a wrapped one was written on the wrap's row.**
`frame_diff` addressed every line by `ANSI_ROW % row` for
`row, line in enumerate(current, start=1)`, so from the first wrapped line
onward the list and the screen had drifted apart by one.
`MazeGame.frame` ends `['end', self.status(), '', controls]`, which puts
the blank spacer directly after the tally - and a blank line is not exempt
from the clear-line escape, `line_fills_row` returning False for an empty
line by design, so `[K` was written at column 0 of the row the tally
had been carried onto and erased it whole.

Read off a real conhost at seed 2024, `--mode quest --collectibles 9` on a
39 by 24 console: the 47 character tally went out whole and the row holding
`tems 0/3` came back as 39 spaces. The same run at 29, 24 and 20 columns
lost `ed 0/9   items 0/3`, `llected 0/9   items 0/3` and
`  collected 0/9   items 0/3`; `--mode plain` and `--mode chase` with
`--collectibles 9` lost `ed 0/9` at 29 columns and `  collected 0/9` at
20. At 29 columns the tally read `collect` with no number on it at all, and
at 20 the player was given neither count.

**The suite's own screen model reproduced it exactly**, which is the half
worth recording twice over: `TerminalScreen` has modelled width and the
pending wrap since `1.0.0a8`, so replaying `frame_diff`'s output through it
at 39 columns returned the row empty where `tems 0/3` belonged. The 1183
tests passed because nothing asked it the question.

**The tally was broken inside a word.** `MazeGame.render` padded the last
line of the frame so the console's break would land on a space, on the
premise that it was "the only one long enough to be carried onto the row
below". The reserve added in `1.0.0a8` disproved that premise in the same
version it was written: the tally reaches 47 characters and wraps every
console under 48 columns, which is why a row is reserved for it. Both lines
of the foot are padded now, and `wrap_on_spaces` hands a line back unpadded
where the padding would cost a row, so the rows either line occupies are
unchanged and the maze is fitted exactly as it was.

### Fixed

- **A line carried onto the row below lost that row to the line after it**,
  in every mode, on every console narrow enough to wrap the tally.
  `frame_diff` addresses a line by the screen row it belongs on now - the
  first row plus the rows every line above it occupies, which is what
  `frame_height` already counts - so the rows of a wrapped line are held by
  the console rather than written over. A line left alone by the difference
  path counts the rows it is occupying toward where the next written line
  goes, exactly as a written one does, and a frame with no terminal to
  measure is still addressed by its line count
- The wipe that clears the rows a shorter frame gave up is measured in the
  rows its dropped lines were occupying and starts on the row below the
  frame's own last one, which is the row the addressing above it counts to.
  Both ends of it agreed about where the frame ended while every line fit
  on a row; a frame that wrapped moved only one of them
- **The tally was broken inside a word on every console that wrapped it**,
  reading `collect` with its number on the row below at 29 columns.
  `MazeGame.render` pads both lines of the foot a console can be narrower
  than, which are the two `fit_to_terminal` reserves a wrapped row for, and
  the comment resting the padding on the last line of the frame went with
  it

### Changed

- `docs/playing.md` describes the break both lines of the foot are padded
  at rather than the one, says what a line whose words need more rows than
  the console's own break keeps instead, and records that a line carried
  onto the row below keeps that row

## [1.0.0a8] - 2026-10-23

The two lines of the play screen's foot measured against the console they
are drawn on, rather than against a figure nobody checked.

Both faults here are the same mistake in two places. The foot of the play
screen is the part of the frame the console's width is measured against
nowhere - `fit_dimension` caps a maze row to the terminal's columns, so an
80 column console draws maze rows 79 characters wide against a 60 character
controls line - and both of the foot's long lines had a figure attached to
them that the line had since outgrown.

**A line exactly as wide as the console lost its last character.** At 60
columns the plain controls line read `... 'q' to quit` with no full stop,
and at 79 columns the quest line read the same way; 59, 61, 78 and 80
columns were all correct. Those are the widths each line had been shortened
to fit, so each landed on the one width that broke it. `ANSI_CLEAR_LINE`
followed every line of a frame so that a shorter line never left the tail
of a longer one beside it, and on the row a line fills to the last column
there is nothing to clear and the escape is not harmless: a console that
has just had its last column written leaves the cursor *on* that column
with the wrap pending rather than past it, and `\x1b[K` erases from where
the cursor stands.

**The suite could not see it, and that is the half worth recording.**
`TerminalScreen` modelled the cursor as moving past the last column when a
write filled the row, and its `K` branch then truncated the row to
`self.column - 1`, which for a full row is the whole row - so the model
kept the character the console drops. The model holds a pending wrap now,
so a write ending on the last column leaves the cursor on it and a
following `K` erases it, which is what the fix is measured against.

**A maze was still carved a row too tall, on the line the reserve did not
count.** `fit_to_terminal` reserved the rows the controls line occupies and
ruled the rest of the foot out in its own comment - "the status line runs
to 31 characters with an inventory on it". 31 is the quest tally alone;
`status_line` puts a collectible tally beside it, so
`--mode quest --collectibles 9` draws 47 characters, and 50 once the clock
passes an hour. Swept over 20 to 120 columns, plain and chase carved a row
over from 20 to 29 columns and quest from 20 to 39, two rows over on the
narrowest of them. `python -m py_maze --mode quest --collectibles 9 --seed
2024` on a 39 by 24 console carved 9 by 8 and built a frame standing 25
rows tall, with the exit off screen and no resize anywhere in it.

### Added

- `line_fills_row(line, size)`: whether a line ends flush with the
  terminal's last column, which is the one place the clear-line escape must
  not be written. `frame_text` and `frame_diff` both ask it now and leave
  the escape off for exactly that case - a line with no tail beside it to
  clear has nothing to lose by it and one character to gain. A wrapped line
  is measured by the final row it is carried onto, which is the only row
  the escape ever follows, and a `size` of None keeps every piped frame
  exactly as it was
- `mode_status(name, collectibles, ...)` and `MODE_ITEMS`, the running
  tally a mode's first frame will draw, answered before there is a game to
  ask. It is the companion to `mode_controls`: both name a line of the
  foot, both are settled by the options rather than by play, and both are
  what a maze has to be carved against. A mode is looked up rather than
  branched on, so the step that carves a maze never has to know which mode
  fills an inventory
- `fit_to_terminal` takes a `status` line beside its `controls` one, and
  counts the rows each occupies. Handing over neither reserves
  `RENDER_ROW_OVERHEAD`, exactly as before

### Fixed

- **A frame line exactly as wide as the console lost its last character.**
  Read off a real console at seed 2024, Windows 11 conhost: isolated from
  the game with a plain `WriteConsoleW` into an allocated 60 column
  console, 60 characters read back as 60 and 60 characters followed by
  `\x1b[K` read back as 59 with a space in the last cell. A 60 character
  ruler behaved the same, so it was the width and not the text
- **A maze carved for a console was still a row too tall for it**, on
  every console from 20 to 29 columns in plain and chase mode and from 20
  to 39 in quest. The reserve counts the rows the whole foot occupies now,
  and the comment ruling the status line out went with it. The two lines
  the foot has left are the `end` marker and a blank spacer, and neither
  reaches the edge of a console with room for a maze in it
- **A console dragged wider kept the tail of the line it had wrapped.**
  `MazeGame.render` measures the frame it is drawing and the frame already
  on screen in rows now, and measured both against the console it is
  drawing on - but the frame on screen was wrapped by the console it went
  out on. Widen a 50 column console to 120 and the older frame reads as
  never having wrapped at all, so the wipe spans no rows and the row under
  the redrawn frame keeps `'q' to quit.`, the tail of the padded controls
  line, with the cursor parked on it and the end of the game printed from
  there. The frame on screen is measured against the size it was drawn at.
  Found reviewing `1.0.0a7` and fixed after it was tagged, so it ships here
- The `DOOR_MARKER` comment rested the choice of `#` on a claim that does
  not hold - that a door never sits on the first column of a maze row, so
  the only `#` a reader meets inside a grid is refused as the unexpected
  character it is. A door does reach column 0, and `parse_save` reads a
  line opening with `#` as a comment, so that row would be dropped rather
  than refused. What makes the choice safe is that no marker reaches a
  file at all: `save_lines` draws the grid through `SAVE_CHARS` and lays
  nothing over it but the collectibles

### Documentation

- `docs/library.md` named the five-value shape `build_maze` stopped handing
  back in `1.0.0a7`, so a caller following the page wrote
  `grid, collectibles, seed, before, content = py_maze.build_maze(args)`
  and got `ValueError: too many values to unpack (expected 5)`. The page
  names the six-value shape and says what `chain_seed` is
- The same page claimed the controls line is the longest line of the play
  screen, which holds only while the maze is narrower than the line. It is
  the longest line of the frame's *foot*, and the foot is the part of the
  frame the console's width is measured against nowhere, which is why its
  lines are the ones that wrap
- `docs/options.md` sets out the status line's share of the reserve beside
  the controls line's, with the width at which it costs a row of maze
- `KNOWN_BUGS.md` records both faults, what was measured and how the suite
  missed each

### Tests

- `TerminalScreen` holds a pending wrap, so the model of a full row matches
  what a console does with one. Without it no test could see a line lose
  its last character, and five of the new ones fail against the old model
- A frame whose last line is exactly as wide as the console is asserted
  whole at that width, at one column narrower where it wraps and one wider
  where it does not, with `CONTROLS_LINE` at 60 columns and
  `QUEST_CONTROLS_LINE` at 79 named and measured, so shortening either line
  again moves the test with it. A shorter line redrawn over a longer one
  still has the tail cleared from beside it, which is what the escape is
  there for
- `test_a_maze_carved_for_a_console_is_one_it_can_show_whole` runs on a
  tally carrying both of its counts and over every width from 20 to 100 -
  the shape and the widths the fault came back on. It fails 77 subtests
  against the old reserve
- A door that reaches column 0 is pinned against the picture it was found
  on, beside the file that never carries it

## [1.0.0a7] - 2026-10-21

The rest of the line count taken out of the play screen, and a window that
says it is one.

1.0.0a6 converted `fit_frame` to measure a frame in screen rows. Five other
places were still reading a line count as a row: the wipe that clears the
rows a shorter frame gave up, the rows an ending is reserved, the two cursor
parks under a frame, and the reserve the maze itself is carved against.

**The wipe is the one a player saw.** Quitting a plain game on a 60 column
console left row 17 of the screen holding ` quit.` under `Moves: 4` - the
second row of the wrapped controls line, left behind when the frame was
redrawn shorter to make room for the ending. The suite's 1108 tests missed
it because every narrow-terminal test replays the frames the player was
looking at and stops before the ending, which is the only thing that prints
far enough down to show it.

**The two parks cancelled, which is why nothing else showed.** A park sat
one row high by exactly the rows the frame wrapped, and that handed the
ending back the rows its own wrap cost. Neither site was written as though
it were relying on the other, and the cancellation runs out wherever the
frame and the ending wrap by different amounts - from 37 to 59 columns the
frame wraps and the ending does not.

**A maze is now carved against the rows its foot will occupy.** The reserve
was the frame's five lines, and those five lines stand six rows tall on a
console too narrow for the controls line. So a default run on a 60 by 18
console asked for 21x11, was handed 21x6, and built a frame that stood 19
rows tall: `fit_frame` then cut a maze row out of the very first frame, with
no resize anywhere in it. The reserve counts rows now, and the controls line
it counts is the mode's - the plain line and the quest line differ by a row
of maze at some widths, and `fit_to_terminal` takes no mode, so
`mode_controls` is what answers for one.

**Where a window is still cut, it says so.** `start` and `end` are the only
labels on a play screen and a player reads them as naming the two ends of
the maze. The head and the foot of the frame are kept whole, so a cut window
printed those same two words against whichever interior rows it stopped at -
and the exit is the gap in the bottom wall, which could be off screen for
the whole of a game at 80 by 18, the standard console, with nothing saying
anything was missing. An edge the window does not reach is named with the
rows between the two instead: `end 3 rows below`, `start 2 rows above`. A
frame that fits is returned untouched.

### Added

- `cut_marker(marker, rows, where)`, and the `CUT_FORMAT`, `CUT_ABOVE` and
  `CUT_BELOW` constants behind it: an edge marker that names the maze rows a
  cut window stops short of. `fit_frame` already computes the two distances,
  so this is a change to what is printed on two rows that were being printed
  anyway
- `wrap_on_spaces(text, size)`, which pads a line out to the end of the row
  it wraps on so a console breaks it at a space rather than inside a word.
  The guide's answer at 100 columns read back as `...you can already r` with
  `each` on the row below. The line stays one line of the frame - the foot
  is a fixed number of lines and the maze window is measured off it - and
  the padding is refused outright where it would cost a row
- `mode_controls(name)` and `MODE_CONTROLS`, the controls line a mode will
  print, answered before there is a game to ask. It is the fact that decides
  how many rows the foot of the play screen occupies, and a maze is carved
  for a console before the game exists
- `frame_text` and `frame_diff` take a `size`, so the row they park the
  cursor on is below the frame's height rather than below its line count.
  Both default to the line count, which is the height of a frame nothing
  wrapped
- `fit_to_terminal` takes a `controls` line, with the same default: the five
  lines of the frame, counted as five rows

### Changed

- **A shut door is drawn `#` rather than `+`.** Nothing on the play screen
  names a marker - the screen carries the maze, the tally and the controls
  line, with no room for a legend - so a player meeting a door for the first
  time has only the glyph to read, and `+` is the lighter mark of the two:
  four thin arms centred in the cell against the `*` wall's heavier six, so
  the cell scanned as more passable than the wall it stood in. `#` reads
  heavier than `*`, which is the way round that matches what a door means.
  It is also the character a save file opens a comment with, which costs
  nothing: no marker is written to a file at all, `save_lines` drawing the
  grid through `SAVE_CHARS` alone, so no `#` a reader meets inside a grid
  came from a door
- **`CONTROLS_LINE` is 60 characters rather than 66**, naming its keys
  without the word "Press" that the two quoted keys make obvious.
  `QUEST_CONTROLS_LINE` lost the word in 1.0.0a6 and this one kept it, so
  the two modes worded the same instruction two ways. At 60 characters it
  fits a 60 column console exactly, so the narrowest console anyone still
  runs stops giving up a maze row to carry it
- **A loaded maze reports the seed its chain can be reproduced from.** The
  grid of a loaded maze is in the file and only the chain laid over it can
  still be seeded, so a run naming `--seed` played a chain the file's own
  seed does not reproduce - and the file's seed was the only one reported.
  A second line, `content seed: N`, is written where the two part. The
  file's seed does identify the grid, so it is still the first line

### Fixed

- **The wipe that clears the rows a shorter frame gave up was counted in
  lines.** `MazeGame.render` passed two line counts to `wipe_rows`, which
  addresses screen rows with them, so on a console carrying a wrapped line
  the wipe stopped a row short of the old frame's last row and whatever was
  there survived. On a 60 by 18 console, quitting left ` quit.` on row 17,
  below `Moves: 4`, with nothing above it
- **An ending was reserved the rows its line count claimed.** The win banner
  runs to 41 characters and wraps below 42 columns, and `MazeGame.ending`'s
  docstring stated the premise outright - "The rows an ending needs are the
  lines it has" - which is the sentence `frame_height` was added to disprove
- **Two cursor parks under a frame were a line count as well**, one in
  `MazeGame.render` and one inside `frame_diff`, which is the one that fires
  whenever a redraw wrote anything. The two wrongs cancelled against the
  reserve above at most widths; from 37 to 59 columns they do not, and the
  ending was printed over the row the controls line had been carried onto
- **A maze was carved against a reserve that counted lines**, so a console
  wide enough for the mode being played was still handed a maze a window had
  to be cut out of. A default run at 60 by 18 asked for 21x11, got 21x6, and
  lost a maze row from its first frame; 60 by 24 did the same, carving 21x9
  and building 25 rows for 24
- **A cut window was drawn as though it were the whole maze.** Read off real
  consoles at 60 by 18, seed 2024: with the player at the top the screen
  held maze rows 0 to 11 and `end` sat under an interior corridor row, the
  bottom wall and the exit gap in it off screen; walked 19 moves to the foot
  the screen held rows 1 to 12, the exit came back and `start` sat over
  another interior row with the entrance off screen instead. The same showed
  at 100 by 18 in quest mode: the guide's answer costs the bottom wall, and
  the exit left the screen for as long as the answer was up
- **The guide's answer broke inside a word when it wrapped.** At 100 columns
  the longest answer is 104 characters and the console carried the overflow
  at the column rather than at a space

### Documentation

- The line-ending anecdote now names the figures the commands beside it
  report. `.gitattributes`, `docs/development.md` and the `1.0.0a6` entry
  below all said the 1.0.0a5 commit rewrote 23 files from LF to CRLF and
  that a real 2,741 insertions hid inside its 25,113: `git show v1.0.0a5`
  rewrote 22 tracked files and created 2 more already in CRLF, and
  `git show --ignore-cr-at-eol v1.0.0a5` reports 2,746. The 23 was the
  renormalization's own count - 1.0.0a6 did flip 23 files back to LF - and
  the 2,741 came from `--ignore-all-space` rather than from the flag the
  sentence names
- `docs/playing.md` shows what a cut window reads like and says where a
  wrapped line breaks; `docs/options.md` shows the reserve a narrow terminal
  pays and says the line is the mode's; `docs/saving.md` shows the two seeds
  a loaded run reports and which of them `--seed` takes back. The door glyph
  is updated in `docs/modes.md`, `docs/playing.md`, `docs/options.md`,
  `docs/save-format.md`, `docs/CHEATSHEET.md` and `README.md`, with
  `docs/modes.md` saying why the mark is the heavier one
- `KNOWN_BUGS.md` records what was left of the line count after 1.0.0a6 and
  what the five sites now measure

## [1.0.0a6] - 2026-10-19

A play screen measured in the rows a console actually gives it. A frame is a
list of lines; a console wraps a line longer than it is wide onto the row
below, so eighteen lines can stand nineteen rows tall - and the fitting that
cut the frame to the screen counted lines. On an 80 column console, where
the quest controls line ran to 88 characters, the frame was handed a screen
it was a row too tall for and the write of its last line scrolled the
buffer: `start` went off the top before a key had been pressed, and it
stayed off for the whole game.

**The maze window pays for the wrap, the way it already pays for an
ending.** `frame_height` reports the rows a frame occupies rather than the
lines it holds, and `fit_frame` cuts against that. A frame whose foot wraps
gives up one row of maze to carry it, which is the choice `fit_frame` was
already making for every other row the screen could not spare. Nothing
scrolls, and the start marker keeps the first row of the screen.

**The doubt about where the rows are is carried one frame further than the
wrap.** The rows that moved belong to the frame already on screen, and the
frame replacing it cannot tell from its own lines: the guide's answer is 104
characters and the controls line that takes its row back is 79, so at 100
columns the answer wrapped and its replacement did not. What that left was
two tallies, one stale and frozen, and the guide's answer stranded on the
blank spacer's row - the spacer never changes, so the redraw never wrote it
and never cleared it, and asking again repaired none of it. A frame
following a wrapping one is now drawn whole as well.

The fault predates quest mode. The plain game lost the marker at 60 columns
for the same reason and by the same mechanism, its controls line being 66
characters. What 1.0.0a5 changed was the reach of it, from a console
narrower than 67 columns to the standard one.

### Added

- `frame_height(lines, size)`, the rows a frame occupies on a terminal,
  counting a wrapped line as the rows it is carried onto and a frame with no
  terminal behind it as the lines it holds. `fit_frame` measures against it
  now, and it is public because a caller drawing its own frames needs the
  same answer
- `content_seed(given, recorded)`, the rule that settles which seed governs
  what a mode lays into a loaded maze: the seed the run named, else the seed
  the save file records, else `None` for the fresh randomness a seedless
  picture gets
- A `.gitattributes` naming one line ending for the whole repository,
  `* text=auto eol=lf`, with `docs/development.md` saying which ending the
  repository keeps and why

### Changed

- **`QUEST_CONTROLS_LINE` is 79 characters rather than 88**, naming its keys
  without the word "Press" that the three quoted keys make obvious. At 88 it
  wrapped the standard 80 column console, and a wrapped foot is a maze row
  the frame has to give up, so a quest played at 80 columns showed one row
  less of maze than a plain game did

### Fixed

- **A play screen was fitted by its line count and drawn in screen rows.**
  On a console whose rows the frame exactly filled, a foot that wrapped took
  the screen up a row as it went out and the start marker went with it: gone
  from the first frame at 80 by 18 in quest mode, and from the first guide
  answer at 100 by 18. At 80 by 19, with one row to spare, nothing moved.
  `fit_frame` gives up a maze row for every row a wrap needs now
- **The frame after a wrapping one was repaired a changed line at a time.**
  Only the lines that differed went out, onto rows that had all moved up by
  one, which is what left a quest screen holding two tallies and a stranded
  guide answer that asking again would not clear
- **A quest laid into a loaded maze had no seed to come from.** `build_maze`
  threads the generator's own randomness into `mode_content` for a generated
  maze; the `--load` branch passed no `rng` at all, so `place_quest` fell
  back to the global `random` module and `python -m py_maze --load maze.txt
  --mode quest --seed 5` laid a different chain every run. A loaded picture
  was the only maze in the project whose contents could not be reproduced
- **A quest document loaded in a mode that plays no quest was still drawn
  and still saved.** `build_maze` took the chain off the document whatever
  `--mode` said, so `python -m py_maze --load quest.json` - the save command
  `docs/modes.md` prints, run back without repeating `--mode quest` - drew
  `+`, `&` and `@` over the maze and wrote them out again, while the game it
  then offered to play had no doors, no boxes, no guide and no `items`
  tally. The picture said one thing and the game did another. The document's
  chain is now adopted only by a mode that lays that kind of content, so
  what is drawn over a loaded maze is always what is in play on it
- **`SavedMaze` came back from `copy` and `pickle` with its whole triple
  inside its grid.** A tuple subclass is rebuilt by calling `__new__` with
  whatever `__getnewargs__` hands back, and `tuple`'s own answer is the
  triple as a single argument - which this `__new__` reads as the grid. So
  `copy.deepcopy(py_maze.read_save(path))` returned a `SavedMaze` whose
  `grid` was `(grid, collectibles, seed)`, whose `collectibles` was empty
  and whose `seed` was `None`, with no error raised anywhere. `SavedMaze`
  answers `__getnewargs__` with its own four arguments now, so a copied,
  deep-copied or unpickled maze is the maze that went in, quest included
- **The repository held two line endings inside one release.** The 1.0.0a5
  commit rewrote 22 tracked text files from LF to CRLF while the files it
  did not open stayed LF, so `git show v1.0.0a5` reported 25,113 insertions
  against a real 2,746 and the release could not be read without
  `--ignore-cr-at-eol`. `.gitattributes` settles it on LF and the tree is
  renormalized

### Tests

- The rows a frame occupies are pinned against a table of widths: the quest
  controls line at 79 characters and the guide's longest answer at 104, each
  over 60, 80, 88, 100 and 120 columns, asserting `fit_frame` gives up a
  maze row wherever the foot wraps. Nothing in the suite measured rendered
  height before, so the whole class of fault was invisible to it
- The three narrow-terminal tests that pinned the scroll as the best a
  60 column console could do now pin the frame keeping its start marker and
  giving up a row of maze instead
- The branch that shortens a quest it cannot hide a later box for is
  driven directly, `box_spot` answered `None` at a chosen stage. Over 6,021
  quests laid across seeds 1 to 299, sizes 3x3 to 16x20 and 1, 3, 5 and 9
  stages it had never once run, nor had the fallback region above it. The
  doors left are asserted numbered 1 to n with no gap, each with its box,
  the exit still shut and the chain still walkable to the end
- A picture loaded twice under one seed is asserted to get one chain, two
  seeds two chains, and a picture with no seed on either side a fresh
  generator each run

## [1.0.0a5] - 2026-10-17

A maze played for what is in it rather than only for the way out. `--mode
quest` shuts the route with doors, hides what opens them in boxes behind
those doors, and puts somebody in the maze to say which errand is next. The
same run also puts numbers beside the three phrases `--algorithm` has always
been described in, so "Prim's dead ends are short" is something a reader can
check rather than something to take on trust.

**A quest is a chain rather than a locked door.** Door one shuts the route a
quarter of the way along, and the item that opens it is in a box somewhere in
the part of the maze that can already be reached. Opening it reaches the part
of the maze box two is hidden in, and so on, so the maze is played in stages
and each one is finishable exactly when it is wanted. Nothing is ever spent:
an item is kept and a door that has been opened stays open.

**The guide is a second kind of hint rather than a second way to ask for the
first.** `h` has always lit the next step of the way to the exit. `n` asks
the character waiting just inside the entrance what the errand in front of
you is: it lights up the box you still need, or the door it opens once you
are carrying it, and says which in words on the controls line's own row, so
asking never changes the height of the frame.

**The picture refuses a quest and the document carries one.** A save file can
draw a door; nothing in a picture can say which item opens it, and a door
nobody can tell from another door is not a quest. So `+`, `&` and `@` are
refused by the picture exactly as `.` and `o` already are, and the JSON
document grows a `quest` key holding the doors, the boxes and the guide. A
document round trips a quest maze; a text save of the same maze is the plain
maze under it.

**What a mode puts in the maze is now a registry of its own.** A chaser is
built when the game is, but doors and boxes are laid into the grid before a
word is drawn and are saved and loaded with it, so they belong to the maze
rather than to the game. `MODE_CONTENT` is where a mode says what it lays
there and `mode_content` is what lays it, which keeps `build_maze` free of
any mode's name - the promise `MODES` has made since chase mode shipped.

**The carving comparison is measured rather than asserted.** `docs/analysis.md`
now tables the dead ends, junctions, longest corridor, route length, solution
share and difficulty each of the three carvers averages over twenty mazes of
the same size, and the suite recomputes every figure. Three of the phrases
hold and read better as numbers. One does not: recursive division's longest
straight run averages below randomized Prim's, because a wall running straight
is not a corridor running straight, and the page says so rather than letting
the phrase read as a measurement.

### Added

- `py_maze.quest`, a module of its own: `Quest` holds the doors, the boxes
  and the inventory, and `place_quest` lays a chain into a maze that already
  exists, hiding each box in the part of the maze reachable at the time it is
  wanted. `reachable` is the flood fill a shut door needs and `door_cells`
  spaces the doors along the route
- `--mode quest`, with `--quest-stages` from 1 to 9 and a default of 3.
  Unlike the chase options it is refused rather than settled into its range:
  it shapes the maze before a word is drawn, the way `--collectibles` and
  `--braid` do
- The `n` key, which asks the guide what the next errand is, and
  `QUEST_CONTROLS_LINE`, which says so beside the other keys
- `DOOR_MARKER` (`+`), `BOX_MARKER` (`&`) and `GUIDE_MARKER` (`@`), with
  `quest_overlay` to draw them over a maze
- A `quest` key in the JSON document, and `SavedMaze`, which is the
  `(grid, collectibles, seed)` triple every reader here has always handed
  back with the quest beside it rather than as a fourth item a picture could
  never fill
- `MODE_CONTENT` and `mode_content`, the registry of what each mode lays into
  the maze itself, and `quest_content`, quest mode's entry in it
- `docs/modes.md`, the page the three modes are set out on: what each one
  plays like, what each one draws and the options belonging to each
- A carving comparison in `docs/analysis.md`, with the sample it was taken
  over stated and every figure recomputed by the suite

### Changed

- `status_line` and `summary_lines` take the inventory, so a quest tallies
  `items 2/3` under the maze and `Items: 2 of 3` on the summary. A mode with
  no quest carries neither, exactly as a maze with no pickups carries no
  collectible tally
- `build_maze` hands back what the mode laid into the maze beside the four
  things it already returned
- `docs/playing.md`, `docs/options.md`, `docs/CHEATSHEET.md`,
  `docs/save-format.md`, `docs/library.md` and the README all cover the new
  mode, its option, its markers and its key

### Fixed

- **The `stats_lines` docstring read its own worked example as truncation
  rather than rounding.** It said a stored `0.4794520547945205` prints as
  `47%`, where `round(share * 100)` makes it `48%` - which is what
  `docs/analysis.md`, the `1.0.0a4` entry below and the fixture in
  `TestStatsLines` all say for that same share. The docstring is the whole
  of what a reader of the module is told about the two forms of that one
  number, and it was the only place in the repository naming the wrong one,
  so a caller written off it would have floored the share where the line
  rounds it.

## [1.0.0a4] - 2026-10-15

Reading a maze rather than carving one. `--stats` already said what a maze was
made of and how long the way through it was; it now also says how much of the
maze that way misses, how many dead ends a braid opened, and how hard the
whole thing reads. The same numbers go into the JSON document under a `stats`
key, so a script reads them instead of parsing printed lines, and
`docs/analysis.md` is the page that explains each one.

**The share is the number that separates two mazes the others call equal.** A
maze that is one long winding corridor and a maze of the same size that is
mostly branches can carry the same dead ends, the same junctions and the same
route length: nothing py_maze measured could tell them apart. The share of the
open cells the solution stands on can, and it is the measurement the
difficulty score leans on hardest.

**The difficulty score is published as what it is made of rather than as a
number to trust.** Three shares, each worth exactly as much as the other two,
because nothing here knows which of them a given player finds hard. The three
carvers land between roughly 20 and 65, so a score is read against another
maze rather than against the whole of 0 to 100, and `docs/analysis.md` tables
each part beside where it reaches full marks.

### Added

- **`--stats` reports the share of the maze the solution walks through.**
  `solution_share` is the cells the route stands on over every cell the player
  could stand on, counted in cells because the maze it is a share of is
  counted in cells. It is held as the exact share a script can compare, from 0
  to 1 - the vocabulary `--braid` already reads a share in - and printed as a
  whole percent for a player, so `0.4794520547945205` prints as `48%`. A maze
  with no way through reports the word `none`, as its solution already does.
  `py_maze.solution_share(path, open_count)` is the reader on its own.
- **`--stats` reports a difficulty score out of 100.** `difficulty` averages
  three shares named by `py_maze.DIFFICULTY_PARTS`: **wrong turns**, how much
  of the maze is off the shortest route; **decisions**, junctions per open
  cell over the `JUNCTION_CEILING` of `0.2` and capped there; and **corners**,
  the turns the route makes over the steps it takes, a turn being where one
  straight run meets the next. A maze of one long corridor scores nothing on
  wrong turns and nothing on corners however long it is. The ceiling is above
  anything the three carvers reach - about `0.14` at their busiest, which the
  suite now reads back rather than asserting in prose - so the cap is there
  for a braided maze turned into a network. `py_maze.difficulty_score()` is
  the reader on its own, and a maze with no way through scores `none` rather
  than nought, two of the three parts being read off the route.
- **A braided run says how many dead ends were opened, beside how many are
  left.** `--braid 0.25 --stats` now prints an `opened` tally next to its
  `dead ends` tally, and the two add back up to what the carver made, so
  either can be recovered from the other. This is the one measurement a grid
  cannot be asked for: a braided maze looks exactly like a maze carved that
  way, so the count is taken before the braid and handed to `maze_stats` as
  `dead_ends_before`. A run that braided nothing prints no tally at all,
  rather than a nought that would read as a braid that opened none, and
  neither does a loaded maze, `--braid` not applying to one.
- **`--format json` carries the measurements under a `stats` key.** A document
  run prints no tally lines, a document with text in front of it being no
  longer a document, so `--stats --format json` puts the same numbers in the
  document instead and a script reads them rather than parsing the printed
  lines. `--save FILE --format json` records the key the same way; the picture
  a text save draws has no room for it, which is the reason it has no room for
  a solution either. The key is absent rather than `null` until `--stats` asks
  for it: every key but `grid` is optional, and an absent one says the run
  never measured the maze, which is a different claim from a maze that
  measured nothing.
- **`docs/analysis.md` is the page a reader of the measurements lands on.** It
  sets out what each number says about the maze, tables the three parts of the
  difficulty score beside where each reaches full marks, and shows the `stats`
  key a script reads. It is on the site menu under **Using py_maze** and in
  the README's documentation table, and the suite reads every number it prints
  back against the run that prints it.

### Changed

- **`--stats` prints three tallies it did not print before.** The second line
  carries `solution share` and `difficulty` after `solution`, and the first
  carries `opened` between `dead ends` and `junctions` on a run that braided.
  Both lines still stay inside eighty columns, which the suite now reads for
  the braided run as well as the plain one. Anything parsing those lines by
  position will see more than it did; the `stats` key is there so that nothing
  has to.
- **`py_maze.build_maze()` hands back four values rather than three.**
  `(grid, collectibles, seed, dead_ends_before)`, the last being the count
  `maze_stats` needs to report a braid, and `None` for every loaded maze and
  every run that asked for no braid. The dead-end count has to be taken while
  the maze still has it, and `build_maze` is where the braid happens, so it is
  the only place that can carry the number out.
- **`py_maze.save_json()` and `py_maze.write_save()` take a `stats`
  argument.** Last in both signatures, defaulting to `None`, so every
  positional call that worked before still works. Only the JSON form records
  it.

### Fixed

- **A road map section could borrow the paragraph of a subsection it keeps.**
  `road_map_sections()` grouped prose by level 2 heading alone, so every prose
  line down to the next level 2 heading counted toward the section that
  opened the span - the intro of a `###` subsection under it included. The
  section `Gameplay Enhancements` keeps `New Game Modes`, so deleting the
  paragraph that opens the section left the subsection's intro answering for
  both, and the check added in 1.0.0a3 stayed green on exactly the edit it is
  named for. A subsection is now read as a section of its own and owes a
  paragraph of its own, which is what each one was already written to carry,
  so either intro going missing is reported by its own title. Headings nested
  under `## Current` and `## Complete` stay excluded, which keeps an override
  header written into the queue from being read as a road map section.

## [1.0.0a3] - 2026-10-13

What the new checks do not hold. Every item here is about the suite's own
reading of the repository's documents rather than about the maze: an order the
version check depended on and nothing enforced, two readers of `CHANGELOG.md`
answering one question differently, a guard that passed on an empty result,
and a heading pattern that accepted any text in brackets. Nothing a player can
see has changed.

**A check with one reader is a check that can be satisfied by nothing.**
`road_map_prose()` was compared against `[]` by a single assertion, so an
empty result passed it - and rewriting the thirteen road map intros as
blockquotes, or indenting them under their headings, would have emptied it
while the check reported zero weights and stayed green. The scheme documents
had a second reader all along, because `scheme_prose()` coming back empty
fails the PEP 440 check that reads the same span. The road map has one now.

### Added

- **The dated changelog entries are held to descending by date.** The version
  check reads the newest entry as the first dated one in file order, which it
  is only because Keep a Changelog writes a file newest-first, and nothing
  held `CHANGELOG.md` to that. An entry appended at the bottom instead of the
  top failed the version check with a message about the newest entry not being
  the version, sending a reader after an entry that was present and misplaced;
  two entries swapped anywhere below the first were reported by nothing at
  all. Both are now reported by the line they are on.
- **Every themed road map section is held to opening with a paragraph.** That
  paragraph is the standing instruction a run reads before it writes a
  version, and it is what the weight check reads, so a section whose intro was
  deleted or reshaped now fails by its own title rather than by leaving the
  weight check nothing to disagree with.

### Changed

- **A changelog entry heading is held to a vocabulary, not to brackets.** The
  pattern read any bracketed text as a version, so `## [TBD]`, `## [next]` and
  a real entry whose date was forgotten were all a third shape passing the
  check written to catch a third shape - and a forgotten date was caught only
  while its entry was the newest, because the version check reads the dated
  entries alone. The shapes are named now: a version with its date, the
  dateless `## [Unreleased]`, and `## [1.0.0 under semver]`, which is written
  down rather than allowed by a loose pattern. A fourth label fails until
  somebody adds it beside the three.
- **`CHANGELOG.md` has one reader of what starts an entry.** Two disagreed on
  `## Unreleased`, which is `## [Unreleased]` written from memory: the entry
  reader took any `## ` line and reported it as a heading it could not read,
  while the scheme-prose reader ended the preamble on `## [` and so did not
  end it there - the preamble swallowed that section's body, and the weight
  check failed on whatever the body said about a change. Two checks failed for
  one mistake and the louder one described the wrong thing. Both now ask
  `starts_a_changelog_entry()`.

### Fixed

- **A road map section may deny the three weights the way the two guides do.**
  `test_the_road_map_weighs_no_section_as_a_version_step` read `TODO.md` a line
  at a time, which voided the one allowance `version_weights_named()` exists to
  make rather than narrowing it: the denial sentence both scheme documents are
  written around wraps near the eightieth column, and neither half of a wrapped
  `patch, minor or major` holds the run that allowance looks for. A section
  intro saying the counter has no weight to move would have been reported as
  naming all three. `version_weights_named_by_line()` now takes the triple off
  the joined block first, a space to a character, so that the line structure
  and the line number in the failure message both survive it.
- **The version docstring's third paragraph is wrapped to its own width.**
  Splitting it left one line at 53 characters where the rest of the paragraph
  fills to 70, which read as a break for emphasis that was never meant. The
  wording is unchanged.

## [1.0.0a2] - 2026-10-11

What the new counter left behind: the destination it climbs to was a string
the changelog already carried, the road map still told a run to move numbers
the counter has not got, and the one test guarding the scheme prose passed on
the presence of a link. Nothing a player can see has changed, so this is a
fix that touches no interface.

**The counter's destination was spent.** `1.0.0a1` counts up to `1.0.0`, and
the old scheme reached `1.0.0` on 2025-12-25. Two entries under one heading is
confusing for a reader and invisible to a pattern, and it would have taken the
version check with it: `assertIn` over every heading in the file was satisfied
by the 2025 entry, so the run that finally wrote `__version__ = '1.0.0'` would
have passed without writing the release's own entry. The 2025 entry is now
headed `## [1.0.0 under semver]` and the check reads the newest dated entry.

### Changed

- **`CHANGELOG.md` heads the 2025-12-25 entry `## [1.0.0 under semver]`.**
  It is the one entry of the old scheme that names its scheme, because it is
  the one whose number the counter is climbing to. Nothing under the heading
  changed; the preamble says why the heading does.
- **`CHANGELOG.md`, `CONTRIBUTING.md`, `docs/development.md` and the
  `py_maze/version.py` docstring say what the destination is.** All four said
  the counter was counting up to "a first release that has not happened yet",
  which was true and left out that the string it is counting up to was
  already in the file. Each now says the counter climbs to the first published
  release, and that the plain `## [1.0.0]` heading is left for it.
- `TestVersion.test_the_changelog_documents_the_version` holds `__version__`
  against the newest dated entry rather than against any heading in the file.
  A run that advances the counter and forgets the entry now fails, where
  before it matched an older heading and passed.
- `TestVersion.test_the_documents_name_the_scheme_the_version_is_in` reads the
  span of each document that describes the scheme - the preamble of
  `CHANGELOG.md`, the `## The Version Number` section of the other two -
  rather than the whole file. A scheme section renamed away or deleted is now
  a failure, where reading the whole file meant a PEP 440 link anywhere in it
  was enough.
- **The thirteen road map section intros in `TODO.md` say what finishing a
  section does to the counter.** Each one weighed its items as a patch, a
  minor or a major version update, which is advice `1.0.0aN` has no number for
  - and `TODO.md` is the file a run reads first, so a run finishing a gameplay
  item was told by that section's own paragraph to move something that is not
  there. Each now says the counter advances by one and the size of the change
  goes in the changelog entry. The section headings and every `- From:` line
  are untouched, so the items that name them still match word for word.
- `CONTRIBUTING.md` shows the shape of the `## [Unreleased]` heading it sends
  documentation and chore work to, as a fenced example, and says that it
  carries no version and no date and folds into the next version's entry. The
  advice was there with no shape beside it, and the file had never carried
  such a heading, so the first run to take it would have written something the
  repository had not seen.

### Added

- `test_no_scheme_document_weighs_a_change_as_a_version_step`, holding the
  scheme prose to the absence of the version-weight vocabulary as well as to
  the presence of the PEP 440 link. The drift the old test was written for -
  "bump the minor for a new option", written into the guide out of habit -
  passed it, because the link was still there. The three weights may be named
  together, as the group the version has not got, which is the sentence both
  guides are written around; one named on its own is the failure.
- `test_the_road_map_weighs_no_section_as_a_version_step`, reading the prose
  of `TODO.md`'s road map the same way. It is not one of the scheme documents
  and does not join them - it describes no scheme and carries no link to hold
  it to - but its intros are what a run acts on, which is where this drift
  costs most. Only prose at the left margin is read, so the items under
  `## Current` that quote the drift in order to describe it, and the archived
  ones under `## Complete`, are left alone.
- `test_the_changelog_heads_every_entry_one_of_the_two_shapes` and
  `test_an_unreleased_heading_stands_dateless_above_the_entries`, which are
  what make the `Unreleased` advice real: a heading written some third way is
  reported, and an `Unreleased` heading has to be the first entry, carry no
  date, and be the only one of its kind.
- `changelog_entries()`, `scheme_prose()`, `version_weights_named()` and
  `road_map_prose()` in the suite, each carrying the reading its checks depend
  on and why it stops where it does. `scheme_prose()` reads a heading nested
  inside a section as part of it, so a subsection titled "Bumping the minor"
  is caught, and it skips fenced blocks: the toml example on
  `docs/development.md` opens with the comment `# pyproject.toml`, which any
  pattern that does not know where the fences are reads as a level 1 heading,
  and a span ending there stopped directly above the sentence it is read for.

### Removed

- `SUITE_PATH` from `test_py_maze.py`. The width check moved onto
  `past_the_width('test_py_maze.py', ...)`, which names the file relatively
  and lets `document()` build the path, and nothing has read the constant
  since. It sat in the block of root-file paths looking current, which is
  where a later run reaching for the suite's own path would have found it.

## [1.0.0a1] - 2026-10-09

The version re-expressed, and nothing else. `__version__` read `3.0.4`, a
number that says three major releases of a published package, while py_maze
has never been published to any registry and nothing anywhere depends on it.
It now reads `1.0.0a1`: the first pre-release of the `1.0.0` this is being
built towards.

**The number is smaller than yesterday's on purpose.** `1.0.0a1` sorts below
`3.0.4` and below every tag in the repository, which is what a reader should
expect of a version that has stopped claiming to be released. Nothing was
released, nothing was withdrawn, and no behaviour changed: the same code that
answered to `3.0.4` answers to `1.0.0a1`. The three tags the repository
carries - `v3.0.2`, `v3.0.3` and `v3.0.4` - are untouched, and the entries
they belong to still say what they said.

**The old numbers do not travel into the new scheme**, because PEP 440 has
nowhere to put them. A pre-release segment holds exactly one number, so
`1.0.0-alpha.3.0.4` is not a version Python accepts - it is rejected rather
than normalized. `3.0.4` is recorded here as the version the project is coming
from and nowhere else.

### Changed

- `__version__` in `py_maze/version.py` is now `1.0.0a1`. `pyproject.toml`
  reads that attribute through `version = { attr = "py_maze.__version__" }`,
  so the manifest needed no edit - the one string is still the one place a
  version lives. The normalized spelling is the one written: `1.0.0a1`, not
  `1.0.0-alpha.1`, which is the same version to the tooling and a different
  string to a reader.
- The module docstring in `py_maze/version.py` says what the counter is and
  what it cannot hold: one number after the marker, so the size of a change
  has no room in the version and is carried by the changelog entry instead,
  and the `1.0.0` core does not move until the project releases.
- **`CHANGELOG.md`, `CONTRIBUTING.md` and `docs/development.md` describe the
  scheme the version is actually in.** All three said Semantic Versioning,
  and `CONTRIBUTING.md` told a contributor to weigh a change as a patch, a
  minor or a major - advice that cannot be followed under a single counter,
  because there is no number for it to move. Each now names PEP 440, says the
  counter advances by one for any version-relevant change whatever its size,
  and says the size goes in the changelog entry. The size itself is still
  judged the same way; only where it is written down has changed.
- `TestVersion.test_version_is_a_release_number` is now
  `test_the_version_is_an_unreleased_pre_release`, and it holds the whole
  shape rather than the first three numbers of it. The old assertion was
  `^\d+\.\d+\.\d+` with nothing anchoring the end, so it passed for `1.0.0a1`
  unchanged - and would have passed just as happily for a bare `1.0.0`, which
  is the one thing the version must not say while nothing is published.
- `TestVersion.test_the_manifest_reads_the_module_version` reads
  `pyproject.toml` through `MANIFEST_PATH` rather than opening the name
  relatively, so the suite no longer depends on the working directory it
  is run from. Run from anywhere but the repository root, that one test
  raised `FileNotFoundError` while the three beside it passed.

### Added

- `test_the_documents_name_the_scheme_the_version_is_in`, reading
  `CHANGELOG.md`, `CONTRIBUTING.md` and `docs/development.md` and holding each
  to naming PEP 440. The prose and the version string are the pair that has to
  agree here, and the drift this guards is the easy one: a later run reaching
  for "patch" or "minor" out of habit, writing it into the guide, and leaving a
  contributor instructions the version cannot carry out.

## [3.0.4] - 2026-10-08

The three enumerations 3.0.3 left hand-written, and the two things its
fence reader could not see. Every one of them was clean when it was found,
so nothing failed before this and nothing a player does behaves
differently - what makes them worth closing is that each one is a claim
the repository had written down with nothing holding it. The repository
root is now read back rather than listed, a fence is read inside a
blockquote as well as outside one, and a document that opens a fence it
never closes is reported rather than silently stopping the check.

### Added

- `root_documents()`, reading the Markdown documents out of the
  repository root, and
  `test_the_prose_read_here_is_every_document_the_root_carries`, holding
  what it finds against `TestRepositoryTextShape.DOCUMENTS`. Three places
  stated that those six names were every document the root carries - the
  comment above the list, `CONTRIBUTING.md` and `docs/development.md` -
  and nothing read the root to keep it true. Both other halves of the same
  change in `## [3.0.3]` got that guard: `docs/` has
  `test_no_page_is_published_without_being_listed_here` holding
  `published_pages()` against `PAGES`, and the package walk got a
  found-nothing guard, which left the root as the one enumeration kept by
  hand under a claim of completeness. The case it guards is a new root
  document arriving from a run rather than from a person, which is how
  `KNOWN_BUGS.md` itself arrived.
- `quoted_depth()`, counting the blockquote markers in front of a line and
  returning what is left of it, and `TestBlockquoteMarkerReading`, seven
  tests over the grammar CommonMark sets for one: up to three spaces of
  indentation, the marker, one optional space after it, and a quote inside
  a quote reading as two deep. Four spaces in front of the marker is an
  indented code block rather than a quote, which is the boundary easiest
  to write a line too loose.
- `fenced_lines()`, which replaces the fence state `doubled_blank_lines()`
  kept inline and answers two questions instead of one: which lines a
  document's fenced blocks cover, and where a block the document never
  closed was opened. `doubled_blank_lines()` reads the first answer and
  reports exactly what it reported before; the second is what
  `test_every_document_closes_every_fence_it_opens` reads.
- `test_every_document_closes_every_fence_it_opens`, holding each of the
  twenty documents to closing every fence it opens. An opening fence with
  nothing to close it reads to the end of its document, which is the
  reading `## [3.0.3]` pinned deliberately - guessing where the code ended
  would report lines that may well be code. What was missing was anybody
  noticing it had happened: one stray fence in `CHANGELOG.md`, the
  document most likely to gain one, and every doubled blank line below it
  goes unreported with the suite still green. A check that stops reading
  is worse than one that reports the wrong line, because the second kind
  gets noticed.
- `TestFencedBlockReading`, ten tests over the two answers
  `fenced_lines()` gives, and two more in `TestDoubledBlankLineReading`
  for the blockquote cases its twelve had none of.

### Changed

- A fence is now read inside a blockquote. The pattern allowed leading
  whitespace and nothing else, so a fence written in a quote opened no
  block and the lines under it were read as prose - and quoted prose is
  the construct this repository writes most of, `CHANGELOG.md` recording
  every correction as a dated blockquote and `TODO.md` and the notes
  beside it carrying long runs of them. The markers now come off before
  the fence is matched, and the depth the fence opened at is kept with it:
  only a fence at that same depth closes it, a line deeper than it is
  content, and a line shallower than it has left the quote, which ends the
  block the way a Markdown reader ends one whose container closed. That
  last rule is what stops the new reading swallowing a document: a fence
  left open inside a quote ends with the quote rather than running on.
  Blankness is still read off the whole line rather than off what is left
  after the markers, which is deliberate and is where this reading stops -
  a quote writes its own blank line as a bare `>`, and that is a line with
  something on it.
- `TestDevelopmentFileTree.EXPECTED` no longer names the root's documents.
  They come from `root_documents()` now, so the map on
  `docs/development.md` and the documents read for their shape cannot
  disagree about what the root holds. The tuple keeps what the helper says
  nothing about - the three folders, the two launchers, the suite, the
  manifest, the ignore file and the licence.
- `KNOWN_BUGS.md` is on the project structure map on
  `docs/development.md`, which drew the other five root documents and not
  that one. The class reading that map promises an entry it draws exists
  and a file the repository carries is on it, and sourcing the documents
  from the root is what turned the second half of that promise into a
  failure rather than a silence.
- `CONTRIBUTING.md` and `docs/development.md` say that the root is read
  back rather than that the list is the thing to keep up to date, and both
  name the two fence rules.

### Fixed

- The second blank line between the end of `TestDoubledBlankLineReading`
  and `if __name__ == '__main__':`, which `## [3.0.3]` left as one. Every
  other top-level construct in the file is separated by two, PEP 8 asks
  for two after a class definition, and the comment that same change wrote
  states that rule as the reason the fence exemption exists at all.
  Nothing lints Python here, so the suite passed either way: what was
  wrong is that the one file arguing the rule was the one file breaking
  it.

## [3.0.3] - 2026-10-06

What the two shape checks 3.0.2 added were not reading. All three gaps
were clean at the time they were found, so nothing failed before this and
nothing a player does behaves differently: what makes them worth closing
is that `CONTRIBUTING.md` and `docs/development.md` had written the
narrower reading down as settled. The blank-line check now reads a fenced
code block the way markdownlint MD012 does, the package is held to its own
width beside the suite, and both prose lists name every document the check
covers.

### Added

- `test_no_line_of_the_package_runs_past_the_width_it_keeps_to`, reading
  every module under `py_maze/` against `PACKAGE_MAX_LINE_LENGTH`. The
  defect the suite's own width check guards is not a property of one file:
  a line continuation that arrives as whitespace leaves a long line of
  valid Python wherever it is written, and the eighteen modules under
  `py_maze/` are edited by the same runs, `## [3.0.0]` having touched six
  of them. The number is 79 rather than the suite's 85 because
  `CONTRIBUTING.md` asks the package for lines under 80 and the suite is a
  file whose test names are sentences; the two are separate constants
  because they are separate numbers.
- `test_the_width_is_read_for_every_module_the_package_carries`, holding
  what the walk found against `PACKAGE_MODULES` plus `__init__.py` and
  `__main__.py`. A walk that found nothing would pass the width check in
  silence, which is the one way a check that reads a directory fails
  without saying so.
- `TestDoubledBlankLineReading`, twelve tests over `doubled_blank_lines()`
  written against text in the test rather than against the repository's
  own documents. Both halves of the change are exercised: a `python` block
  showing two top-level definitions spaced the way PEP 8 asks reports
  nothing, and a doubled blank in the prose on either side of that block
  is still reported. The fence pairing is read too - a shorter run does
  not close a longer fence, tildes are not closed by backticks, a line
  carrying an info string is not a close, a fence indented to a list
  item's content column is still a fence, and an unclosed fence runs to
  the end of the document rather than being guessed at.
- `DESIGN_LANGUAGE.md` and `KNOWN_BUGS.md` to `TestRepositoryTextShape`.
  Both are tracked, both are written by the runs that edit the site -
  `DESIGN_LANGUAGE.md` is the other half of changing how it looks, per
  `CONTRIBUTING.md`, and `KNOWN_BUGS.md` is what a code review appends to -
  and with these two the list is every Markdown document the repository
  root carries. Both were clean when they were added.

### Changed

- `test_no_document_carries_two_blank_lines_in_a_row` reads through
  `doubled_blank_lines()`, which skips what is inside a fenced code block.
  MD012 exempts a fence, and the blank lines in there belong to the code:
  two between top-level definitions is what PEP 8 asks and what every
  module of the package does, so the module `CONTRIBUTING.md` tells a
  contributor to write could not have been shown on a page without failing
  the suite. `docs/library.md` carries 13 fenced blocks and
  `docs/scripting.md` 8, and no page shows a top-level `def` yet, which is
  the only reason this passed. A blank line on each side of a fence is
  still not a pair, since reading the block away would leave two lines
  looking adjacent that are not.
- `published_pages()` is a module-level helper rather than a method of
  `TestDocumentationSite`. `TestRepositoryTextShape.documents()` had
  re-implemented it exactly, so the page enumeration had two definitions;
  `package_modules()` is the equivalent for the package and sits beside it.
- The width paragraph in `CONTRIBUTING.md` and the shape paragraph in
  `docs/development.md` name both widths and all six documents, and both
  say what is left out of the blank-line count and why. Each had written
  the four-document list down as what the suite reads, which read as a
  decision rather than as a gap.
- `py_maze/game.py` describes `maze_grid` in the words the other thirty
  docstrings and comments of the package use for the same argument, which
  brings the one line that was at 80 characters to 70. It is the line the
  new width check found.
- `.gitignore` excludes `blog-posts/`, the folder this repository's
  automation drafts into. A draft there is written for a person to read and
  is not repository history, so it is kept out of commits the way
  `test-results/` and `.tmp/` already are.

## [3.0.2] - 2026-10-04

A review of what 3.0.1 said about itself, and of what it repaired without
leaving anything watching. Two of its entries send a reader to the wrong
place in the repository; both are corrected in a blockquote over the entry
rather than rewritten, since the tag and the release for it are published.
The other two changes are the shapes it fixed by hand, which have tests
now. Nothing a player does behaves differently and nothing is added to the
public surface.

### Added

- `TestRepositoryTextShape`, holding the two shapes 3.0.1 found by reading.
  `test_no_line_of_the_suite_runs_past_the_width_it_keeps_to` reads
  `test_py_maze.py` against the 85 characters it is written to, which is
  what the collapsed continuation broke: the backslash and the newline had
  arrived as seventeen spaces, and the 144-character line they left was
  valid Python that passed the whole suite.
  `test_no_document_carries_two_blank_lines_in_a_row` reads `CHANGELOG.md`,
  `README.md`, `TODO.md`, `CONTRIBUTING.md` and every page under `docs/`
  for the pair markdownlint MD012 names. No markdownlint runs here -
  `.github/workflows/tests.yml` is `python -m unittest discover -v` and is
  the only check either workflow makes - so the suite is where that pair
  can be caught. Both tests name the file and the line they fail on, and
  both were run against the shape they guard: a 142-character comment, and
  a doubled blank line in `CHANGELOG.md` and again in `docs/options.md`,
  each failed the test written for it.
- The paragraph on the suite's own width in `CONTRIBUTING.md`, and the
  sentences on the shape of the documents in `CONTRIBUTING.md` and
  `docs/development.md`, so the two checks are written down beside the rest
  of what the suite reads of its own files.

### Changed

- The comment over
  `test_the_unsearched_sentinel_is_one_object_on_every_path` says why the
  `from py_maze.analysis import UNSEARCHED` under it is there. It is the
  only function-level import in the suite, and the assert it feeds cannot
  disagree with the `py_maze.analysis.UNSEARCHED` assert two lines down,
  both being a `getattr` on the same module at the same moment. The form is
  what 3.0.1 undertook to keep working and what code written against 2.9.0
  carries, so it is asserted as a caller writes it rather than dropped as a
  duplicate path.

### Fixed

- The blockquote over `## [3.0.1]` corrects the two entries that describe
  the repository wrongly. The `maze_stats` call that would raise is the one
  handed the package's sentinel, not the one handed the sentinel
  `py_maze.analysis` holds: that second object is the one `maze_stats`
  compares against, so it is the argument read as "not searched" rather
  than as a route, and the direction is the whole point of the entry. The
  precedent for the re-wrapped `with` is a three-context helper in the
  suite rather than a two-context `with` in `read_key`: the public
  `read_key` holds no `with` and no continuation, and no module under
  `py_maze/` carries one at all.

## [3.0.1] - 2026-10-02

> Corrected 2026-10-04 in 3.0.2: two of the entries below describe the
> repository wrongly, and both are about where a reader is sent rather
> than about what shipped.
>
> The `maze_stats` call named under **Added** is the one that would still
> work. `maze_stats` tests `path is UNSEARCHED` against the sentinel
> `py_maze.analysis` itself holds, so an `analysis` module that built its
> own `_Unsearched()` again would match the argument written there and
> take the solved-here branch. The call that raises the quoted
> `TypeError` out of `solution_runs` is
> `maze_stats(grid, py_maze.UNSEARCHED)`, the package path, which is
> `py_maze.solving`'s object: it is the receiving module that misreads a
> sentinel it did not make, so the caller named has to be the one holding
> the other module's object. The exception text and the test are right;
> only the argument is the wrong one of the two.
>
> The precedent cited under **Fixed** is neither where nor what it says.
> The public `read_key` at `py_maze/keys.py:60` holds no `with` and no
> line continuation, and no module under `py_maze/` carries one at all.
> The two-context reading comes from the `TestPosixInput.read_key` helper
> in `test_py_maze.py`, which wraps three contexts - `termios`, `tty` and
> `standard_input`. What the re-wrap followed is the suite's convention
> rather than any one instance of it: thirty-two `with` statements in
> `test_py_maze.py` open with a trailing backslash and continue eight
> characters further in.
>
> The tag and the release for 3.0.1 are published, so both entries keep
> the text they shipped with and this says what to read instead.

A review of what 3.0.0 left behind in the places nothing but a person
reads. Two of the four were lines that had lost their shape; the other two
were promises the release made in prose with nothing behind them, both of
them about what a reader is told. Every change here is in the suite, the
changelog or the tests' own formatting: nothing a player does behaves
differently and nothing is added to the public surface.

### Added

- `test_the_help_line_names_the_keys_it_sets_out_to_explain` and
  `test_the_options_page_names_them_in_the_row_it_tables` in
  `TestStatsOption`, holding the two places a reader of `--stats` looks
  against the two keys they both undertake to name. This is the second
  time the help line drifted from `docs/options.md` and the second time a
  reader rather than a test caught it: 2.9.0 reworded the line and stopped
  naming the tallies, the review after it found that by reading, and 3.0.0
  put `cells` and `open` back. A run prints `cells 169   open 73`, and a
  third rewording that dropped either word from `python -m py_maze --help`
  left the whole suite passing. The help test asserts the pair is named
  together rather than only present, because "the cells `--difficulty`
  asks for" is still a "cells" and is exactly what 2.9.0's wording was
  left holding.
- `test_the_unsearched_sentinel_is_one_object_on_every_path` in
  `TestPackageSurface`, asserting `py_maze.UNSEARCHED`,
  `py_maze.solving.UNSEARCHED` and `from py_maze.analysis import
  UNSEARCHED` are the one object. That identity is the whole of what keeps
  code written against 2.9.0's import path working, and the major version
  promised it in prose alone. The `__all__` comparison beside it passes on
  sets of names, so an `analysis` module that built its own
  `_Unsearched()` again would satisfy it while the two sentinels compared
  unequal under `is`: `maze_stats(grid, py_maze.analysis.UNSEARCHED)`
  would take the other module's object for a real route and raise
  `TypeError: object of type '_Unsearched' has no len()` out of
  `solution_runs`. The two tests that name the sentinel both reach it as
  `py_maze.UNSEARCHED` and never touched the other two paths.

### Fixed

- The two-context `with` in
  `test_a_chase_over_an_unsolvable_maze_pays_for_one_search` is wrapped
  the way the rest of the file wraps one. It was a single 144-character
  line: the backslash and the newline that belonged between
  `mock.patch.object(py_maze.game, 'solve_maze')` and
  `mock.patch.object(py_maze.solving, 'solve_maze')` had arrived as
  seventeen spaces. Every other line in the file is 85 characters or
  under, and the same two-context `with` in `read_key` is written with a
  trailing backslash and the second context on its own line. The test
  passed either way, so nothing reported it.
- `CHANGELOG.md` no longer carries two blank lines between the blockquote
  3.0.0 added over `## [2.9.0]` and the paragraph under it. It was the
  only pair of consecutive blank lines in this file, `README.md`,
  `TODO.md`, `CONTRIBUTING.md` or any page under `docs/`, and it is what
  markdownlint MD012 names.
- `docs/library.md` and `py_maze/solving.py`' module docstring name
  `Chaser.chasing` among the calls that read a `path`. 3.0.0 moved its
  default to `UNSEARCHED` because it reads one exactly as `maze_progress`
  and `maze_stats` do, then stated that reading for those two alone -
  "Every call that takes one ... believed by both" - so the page that
  tables `Chaser.chasing(now, grid, cell, path)` said nothing about the
  `None` it now takes at its word, and a caller handing one over waits on
  a chase that never begins. Read the other way the same sentence
  over-claimed: `solution_runs`, `solution_overlay` and
  `MazeGenerator.to_string` take a `path`, never search, and raise
  `TypeError` on `py_maze.UNSEARCHED`. Both places now name the three
  calls that search and say the sentinel is not the others' to take.

## [3.0.0] - 2026-09-30

The version number the last release needed. 2.9.0 taught `maze_stats` to
read `None` as "searched, no way through" and shipped that under a minor
version, which a caller pinned to a compatible range could not have
expected. This release carries the break under the major version Semantic
Versioning asks for, and settles the half of it that was left behind:
`maze_progress` had gone on reading the same value the old way, so one
package said two opposite things with the one argument.

### Added

- `test_a_search_that_found_no_route_is_not_run_again` and
  `test_a_caller_holding_no_route_at_all_asks_for_the_search` in
  `TestMazeProgress`, the pair `TestMazeStats` already carried for the same
  argument. Nothing held the two readers against each other before, which
  is how they came to disagree.
- `test_a_chase_over_an_unsolvable_maze_pays_for_one_search`, counting the
  searches ten ticks of that chase buy. One, taken when the game was built.
- `test_a_chaser_left_to_measure_the_maze_itself_still_starts`, which is
  what a `path` default of `None` on `Chaser.chasing` would now fail: a
  caller leaving the route out would have had its "not searched" read as
  "no way through", and no chase would ever have begun.

### Changed

- **The major version.** 2.9.0's `maze_stats` change is a
  backwards-incompatible change to a function in `py_maze.__all__` and
  tabled on `docs/library.md`, which Semantic Versioning clause 8 makes a
  major release: a consumer pinned to `py_maze>=2.8,<3` took it
  automatically and read `solution` as `None` for a maze with a 34-step
  route, with nothing raised. The tag and the GitHub release for 2.9.0 are
  published, and clause 3 says a released version is not modified, so its
  entry below keeps its number and this is the version the break belongs
  to. Both halves of it are declared here.
- `maze_progress(grid, cell, None)` now reports `None` rather than solving
  the maze, which is the reading `maze_stats` took in 2.9.0. `None` is the
  answer a caller brings back from a search that found no way through and
  it is taken at its word; asking for the search is done by leaving `path`
  out, or by passing `UNSEARCHED`. This is the second incompatibility the
  major version covers: a caller that passed `None` explicitly to mean
  "solve it for me" wants `UNSEARCHED` or an omitted argument.
- `Chaser.chasing`'s `path` default moved to `UNSEARCHED` with it. It
  forwards the argument to `maze_progress` untouched, so a default of
  `None` would have been believed and a caller that left the route out
  would have watched a chase never start.
- `UNSEARCHED` now lives in `py_maze.solving`, the module that searches for
  a route, and is re-exported from `py_maze.analysis` where it first
  shipped. `py_maze.UNSEARCHED`, `py_maze.solving.UNSEARCHED` and
  `from py_maze.analysis import UNSEARCHED` are all the one object, so
  nothing written against 2.9.0's import path moves.
- The `--stats` help line names `cells` and `open` as the keys it is
  describing, the way the `docs/options.md` row and its paragraph do. 2.9.0
  rewrote the line to say the count is taken over the drawn picture rather
  than over the cells of `--difficulty` and stopped naming the tallies, so
  the only "cells" left in it was the thing the tally is not: a reader who
  saw `cells 169` and went to `--help` for what it counts was pointed at
  `--difficulty`. The picture-rather-than-cells distinction 2.9.0 added is
  kept, and the `docs/options.md` table row now names the two keys as its
  own paragraph already did.

### Fixed

- A chase over a maze with no way through no longer solves it on every
  tick. `MazeGame` searches once when it is built and forwards what that
  search came back with, so a `None` travelled through `Chaser.chasing`
  into `maze_progress`, which read it as "not searched" and searched again;
  measured on a chase-mode game over a three-row unsolvable grid, ten ticks
  ran ten breadth-first searches, each one answering `None`. The chase
  cannot begin on such a maze either way, and paying to find that out again
  every tick was the cost of the two readings disagreeing.
- `docs/library.md` states the reading of `path` once, under **Solving**,
  for both of the calls that take one. It taught the two readings within
  fifteen lines of each other before, and the two paragraphs did not agree.

## [2.9.0] - 2026-09-28

> The `maze_stats` change below is backwards-incompatible and shipped here
> under a minor version. 3.0.0 is the version it belongs to, and declares
> it; this entry keeps its number because the tag and the release for it
> are published.

A review of what 2.8.0 shipped, and of what it said about it. The
measurements themselves were right: every tally `--stats` printed was the
correct reading of the maze it was given. What had drifted was everything
around them - the feature never reached the front page of the site, the two
places a reader of the flag looks never said what `cells` counts, the one
reading `stats_lines` was built to distinguish was only ever tested from one
side, and two comments claimed a second search was avoided in a case where
it was not.

### Added

- `UNSEARCHED`, the default for `maze_stats`' `path`, exported from
  `py_maze.analysis` and from the package. It stands for a caller that has
  not looked for a route, which is what separates it from `None` - the
  answer a caller brings back from a search that found no way through. A run
  forwarding a route it may or may not be holding passes one or the other
  rather than collapsing both into `None`.
- The **Measurements** bullet in the `## Features` list on `docs/index.md`.
  The 2.8.0 run added it to `README.md` alone, so the page a reader of the
  site lands on never mentioned `--stats` while the repository's own front
  page did.
- `test_the_site_lists_the_features_the_readme_does`, holding the two
  `## Features` lists against each other bullet for bullet. The site's list
  carries no emoji and wraps differently, so both are read as text and the
  emoji is taken off the README's - which leaves the wording, and nothing
  else, to agree. Nothing compared the two lists before, which is how one
  could gain a bullet and the other not.
- `test_a_route_of_no_steps_prints_as_a_number`, the other side of the
  reading `stats_lines` exists to make. Three characters across is the
  narrowest grid `has_ends` admits and it leaves one column that is not a
  border, so `find_entrance` and `find_exit` both answer with the single
  open cell in it: the route between them takes no steps and prints
  `solution 0`. Only `solution none` was tested before, by a case asserting
  `solution 0` was absent - the claim read backwards.
- Three tests for the search that is no longer run twice:
  `test_a_search_that_found_no_route_is_not_run_again` and
  `test_a_caller_holding_no_route_at_all_asks_for_the_search` in
  `TestMazeStats`, and
  `test_a_run_reporting_no_route_does_not_search_a_second_time` in
  `TestStatsOption`, which drives `--load <unsolvable> -q -S --stats` and
  counts the searches.

### Changed

- `maze_stats(grid, None)` now reports `solution` as `None` rather than
  solving the maze. `None` is the answer a caller brings back from a search
  that found no way through, and it is taken at its word; asking for the
  search is done by leaving `path` out, or by passing `UNSEARCHED`. This is
  the one incompatibility in this release: a caller written against 2.8.0
  that passes `None` explicitly to mean "solve it for me" gets `None` back
  instead of a measured route, and wants `UNSEARCHED` or an omitted
  argument.
- The `--stats` help line and the `docs/options.md` table row now say that
  `cells` and `open` are counted over the maze as it is drawn rather than
  over the cells `--difficulty` and `--width` are given in, with a paragraph
  on the options page working it through: `python -m py_maze -d easy
  --stats` reports `cells 169` for a maze of 6 by 6 cells, which is 13
  characters each way. The docstring and `docs/library.md` already said
  "every position of the grid"; the two places a reader of the flag looks
  said "how many cells it has" and "cells, open cells", and 169 is neither
  6, nor 36, nor the 13 of the rendered width.

### Fixed

- A run that searched a maze and found no way through no longer searches it
  again to measure it. `solution` was `None` both for a maze `--solve` could
  not cross and for a run that never asked, so `maze_stats` could not tell
  the two apart and solved the maze a second time; measured on `--load
  <unsolvable> -q -S --stats`, that was two breadth-first searches, one in
  `py_maze/cli.py` and one in `py_maze/analysis.py`. The tally printed was
  right either way, and the waste only ever fell on a run about to exit
  `EXIT_NO_WAY_THROUGH`, but the comments in both files said the second
  search was avoided and it was not. `cli` now passes the route it holds
  only when it searched for one, and both comments say what is true.

## [2.8.0] - 2026-09-26

Reading a maze, beside carving one, solving one and drawing one. Every
measurement here is taken from a grid that already exists, so a generated
maze and one read out of a file are measured the same way and nothing about
the maze changes for having been measured. The one reader that already
existed is the reason the rest do: `braid_maze` has always had to find the
dead ends before it could open them, and that reading was locked inside
`py_maze/generation.py` where nothing else could ask for it. It is now the
public `dead_ends`, so what a braid acts on and what a report counts are one
reading rather than two that have to be kept agreeing.

### Added

- `py_maze/analysis.py`, a module for measuring a maze rather than making
  one. It imports the grid and the solver and nothing else, so it joins the
  modules that leave the terminal alone, and it modifies nothing: a
  measurement is taken and handed back.
- `dead_ends(grid)`, yielding every cell inside a maze with one way in and no
  way on, in reading order. This is the reading `braid_maze` takes before it
  opens a share of them, moved out of `py_maze/generation.py` where it was a
  private helper nothing else could reach. The entrance and the exit are left
  out: both sit on the border with a single open neighbour apiece, and
  neither is a dead end to open.
- `junctions(grid)`, yielding every cell where three or more ways meet. Three
  open neighbours is a fork and four a crossroads, while two is a corridor
  passing through, so counting them is what says how much branching a carver
  left rather than eyeballing the picture. Braiding a maze makes more of
  them, every dead end opened joining a cell to the corridor behind it.
- `longest_corridor(grid)`, the cells in the longest unbroken straight run,
  across a row or down a column. It is how far a maze can be crossed without
  turning. It says nothing on its own about which carver made the maze -
  measured across the three, the algorithm with the longest run is not the
  same one from seed to seed - so the comparison between them stays a number
  to be measured rather than one predicted here.
- `maze_stats(grid, path)`, the whole of the above as one dictionary: `cells`
  for every position of the grid, `open` for the ones the player can stand
  on, `dead_ends`, `junctions`, `longest_corridor`, and `solution` for the
  steps the shortest route takes. `cells` and `open` are counted over the
  same positions, so the second reads as a share of the first. The solution
  is the one measurement that has to be searched for, so a caller holding a
  route already passes it as `path` rather than paying for a second search,
  the way `maze_progress` already takes one. A maze with no way through has
  no route to measure and reports `None` for it, the rest of the
  measurements still being there to take.
- `--stats`, printing those measurements under the maze it measured. The
  picture is exactly the one a run without the flag draws: the tallies go
  under it rather than into it, above the seed line, and the flag adds
  nothing to the maze itself. A quiet run reports them too - `--quiet` drops
  what was never asked for, and this was asked for, which is how `--solve`
  is already read - while a `--format json` run prints its document alone.
  There is no short flag: `-s` is the seed and `-S` solves, and no letter
  left reads as this.
- `stats_lines(stats)`, what `--stats` prints, written the way `status_line`
  writes the tally under a maze being played rather than as a table, so the
  two read alike. Two lines rather than one: six tallies on a single line
  runs past an 80 column terminal, and the split falls between what the maze
  is made of and how far through it goes.

### Changed

- `py_maze/generation.py` reads its dead ends from `py_maze.analysis` rather
  than finding them itself. `braid_maze` behaves exactly as it did, taking
  the same random numbers in the same order, so a seed braids the maze it
  always braided.
- The library page checks every `>>>` example on it rather than only the
  first. The new one under **Measuring a maze** would otherwise have been
  prose nothing ran, which is the drift the check exists to catch.

## [2.7.4] - 2026-09-24

A review of the two tests 2.7.3 rewrote: the sweep now has both of its ends
pinned, but neither was read off a screen anything held still, and the two
assertions that replaced a tautology were each a line a sibling test already
made on the same play. Both are test-suite changes. Nothing a player does
behaves differently and nothing is added to the public surface.

### Fixed

- `test_the_sweep_runs_from_a_cut_frame_to_a_whole_one` now checks the start
  marker is still on the top row before it reads an index off the screen,
  the guard every other index-reading test in
  `TestTheEndingIsGivenRowsOfItsOwn` takes in one of its two forms. An index
  says where the game drew something only while nothing has scrolled off the
  top: a frame drawn with `k` maze rows more than the end claims, on a
  console that then scrolls `k` rows to pay for them, leaves the foot on the
  same index and the assertion holds for an end that is not the one the
  comment names. That state is what `fit_frame` reserving a row too few
  reaches at the tightest end of the sweep, which is the defect the class
  exists to catch, and the test passed it. It now fails on the start marker
  at that end.
- `test_the_maze_is_what_the_extra_row_costs` and
  `test_the_maze_is_what_an_interrupt_costs_too` no longer restate an
  assertion a sibling test makes. Each gained one in 2.7.3 in place of the
  tautology it dropped, and each replacement compares the same rows a
  sibling compares on identical keys and an identical console: the ending
  slice in the first is the one `assert_the_frame_survived` checks for
  `test_a_chase_played_to_a_catch_keeps_the_start_marker`, and the goodbye
  slice in the second is the third assertion of
  `test_an_interrupt_is_given_rows_of_its_own_as_well`. Both lines are gone,
  so each fact is stated once and each test carries its own subject. What
  the tautology covered is covered still: `frame_foot_at` matches the
  frame's foot rows against the screen and fails the test outright when they
  are nowhere on it, so the length line above pins a row those rows were
  found on, and both tests now say so where they are read.
