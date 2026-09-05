# Changelog

All notable changes to py_maze are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.4] - 2026-09-05

Three corrections to what 2.2.3 wrote down. Two of them are figures and a
sentence in this file, and the third is the helper that reads the site
stylesheet in a different way from the one its own comment describes. The
stylesheet is unchanged, no option behaves differently, and no name entered
or left the public surface.

### Added

- Four tests over the helper that reads a rule out of the site stylesheet:
  that a selector written both inside an at-rule block and at the top level
  answers with the top-level rule, that an at-rule closing on a `;` rather
  than a block leaves the rules after it readable, and that an at-rule
  named in a comment and a brace quoted in one are read as the prose they
  are rather than as CSS. The first fails against the helper as 2.2.3
  shipped it, and the last two against the first draft of the fix.

### Fixed

- The helper reads the rule its comment says it reads. `stylesheet_rule`
  promised the rule "before any at-rule narrows it" and then handed the
  whole file to a single search, which returns the first textual match
  whether or not that match sits inside a block. `.page table` is written
  twice in `docs/assets/css/site.css`, and two
  `@media (prefers-color-scheme: dark)` blocks are written above the base
  rule, so a border colour added to either for the dark theme would have
  become what `test_a_table_fills_the_measure_where_there_is_one_to_fill`
  asserted `width: 100%` against, under a failure message still naming the
  stylesheet. The at-rule blocks are now cut out before the search,
  brace-counted the way `narrow_screen_rule` already counted its own block,
  and the two helpers share that counting rather than each carrying a copy
  of it. The comments come out ahead of the cut, since an `@` and a brace
  read the same in prose as in CSS: the comment above the table rules names
  the narrow-screen block in words today, and naming it
  `@media (max-width: 900px)` the way the rest of the project writes it
  would have taken the rule under the comment out of the stylesheet the
  tests search, while quoting a brace inside the narrow-screen block would
  have reported a block that is closed as one that is never closed. Every
  assertion in both table tests is unchanged.
- The width this file recorded for the key table was two characters short
  of what the page drew. Verifying the 2.2.3 fix meant rendering the pages
  against the 2.2.2 stylesheet first as a control, and the `Key` / `Does`
  table on `docs/CHEATSHEET.md` came back at 605.0px rather than the 588.6px
  recorded. A block table is as wide as its widest row, and the 16.4px
  between the two figures is exactly two characters of the 8.2px monospace
  cell face: the pair of straight quotes in
  `The "would you like to play" prompt, one keypress`. The 2.2.3 entry now
  reads 605.0px and 130.4px apart, and the 2.2.2 entry 92% rather than 90%.
  The 474.6px for the status code table on `docs/scripting.md`, the 72%
  beside it and the 655.5px measure were confirmed against the same
  rendering and stand. Neither the regression nor its fix is affected: the
  table was short of the measure on either figure, and draws the full
  655.5px now.
- The 2.2.3 entry named the wrong box as the one `width: 100%` widens. It
  read that the box widened was "the anonymous one rather than the cells",
  which inverts what happens. The declaration applies to the table's own
  principal box, which `display: block` has made a block box, and widening
  that box is exactly what it does; what keeps a shrink-to-fit width is the
  anonymous table box generated inside it to hold the rows, which no
  selector reaches, and that is why the cells do not follow.
  `DESIGN_LANGUAGE.md`, `CONTRIBUTING.md` and the comment on the test all
  described it that way already, so this file was the one place out of the
  four with it backwards.

## [2.2.3] - 2026-09-04

A follow-up to the site work in 2.2.2, which fixed a table on a phone at the
cost of every table on a desktop screen. The measure is back, the scroll is
kept where it is needed, and two gaps in the suite that let both of these
through are closed. No option behaves differently, and no name entered or
left the public surface.

### Added

- A test that a document putting a collectible on a wall is refused. The
  refusal shipped in 2.2.2 and the page tabled it, but the reader was never
  run against it: it was the one row of that table with no file behind it,
  so a reworded message would have left the page stale without failing
  anything.
- A test reading the refusal tables on `docs/save-format.md` the other way
  round, so every row of them is a message some file the suite holds
  actually raises. That is the direction the missing row slipped through,
  a row being addable to the page without anything reading it back.
- A test that a table fills the measure where there is a measure to fill,
  beside the one that it scrolls where there is not. Each of the two rules
  is now pinned to the width it belongs to rather than to its declarations
  alone, which is what let one replace the other unnoticed.

### Changed

- `DESIGN_LANGUAGE.md` records what a wide table does at each width rather
  than reading as though every table scrolls at every one, and says why the
  scroll is not simply left switched on: a table drawn as a block wraps its
  rows in a box that shrinks to their content and that no selector reaches.
- `CONTRIBUTING.md` records what the suite cannot tell you about the site -
  it reads the stylesheet as text, and a rule that reads as correct is not a
  rule a browser draws as intended - along with the decision not to take a
  browser test dependency for it, and the two widths a layout change is
  checked at by hand instead.

### Fixed

- A table fills the measure again on a desktop screen. 2.2.2 gave every
  table `display: block` at every width to get it scrolling on a phone, and
  a block table shrinks to its content: at 1280px, against a 655.5px
  measure, the key table on `docs/CHEATSHEET.md` drew 605.0px and the status
  code table on `docs/scripting.md` 474.6px, two tables on one page ending
  130.4px apart and both short of the paragraph edge. Most of the site's
  tables are narrower than the measure, so most of them showed it. The
  scroll now belongs to the narrow-screen block alone, below the 900px the
  menu becomes a drawer at, where there is no measure left to fill anyway.
  Putting `width: 100%` back on the block table was measured and does not
  work: it widens the table's own block box, and the anonymous box holding
  the rows inside it keeps a shrink-to-fit width no selector reaches, so the
  cells never follow.

## [2.2.2] - 2026-09-03

The documentation moved out of `README.md` and into a site, and this release
is what carries it. Beside it, one more edge of the JSON document is closed:
a collectible on a wall is refused as one off the grid already was. No
option behaves differently, and no name entered or left the public surface.

### Added

- A documentation site under `docs/`, one Markdown page to a file, built by
  GitHub Pages' own Markdown processing under a layout and stylesheet of the
  project's own. Fourteen pages, a fixed side menu with collapsible groups, a
  light and a dark rendering, and a layout that reads from a phone.
- `QUICKSTART.md` and `CHEATSHEET.md` as pages of that site: the first for a
  reader who wants the game running now, the second for one who has read the
  documentation and wants the options, keys, markers, codes and public names
  back at a glance.
- `DESIGN_LANGUAGE.md`, recording the palette, type scale and spacing the
  site is drawn with, what in the repository's own artwork each was derived
  from, and the contrast ratio measured for every text and background pair.
- `.github/workflows/workflow.yml`, building the site from `docs/` and
  deploying it to GitHub Pages on every push to the default branch. The
  repository's Pages source is set to GitHub Actions.
- A `Documentation` URL in the manifest, pointing at the site.
- Tests covering the site: that every page is published, carries the front
  matter the layout reads and is reachable from the side menu; that the menu
  links the page beside it; that the README stays a front door rather than a
  manual and links every page; that the workflow asks for the permissions a
  Pages deploy needs and runs the Pages action sequence; and that every
  contrast ratio `DESIGN_LANGUAGE.md` writes down is the one recomputed from
  its own hex values, clears 4.5:1, and names a colour the stylesheet
  actually uses. A page's links are checked as well: a raw `href` written in
  a page has to name a page the build actually writes, since the site
  rewrites Markdown links from `.md` to `.html` but leaves an `href`
  untouched.
- Tests covering the site's marks: that every asset the layout draws is one
  the repository carries and every mark the repository carries is one the
  layout draws, that the header holds a mark for each theme and falls back
  to the icon where the menu becomes a drawer, that the brand link is named
  now that its lettering is artwork, and that the tab icon is a file rather
  than a second drawing of itself. A `srcset` is read for the base URL the
  way an `href` and a `src` already were.

### Fixed

- The four cards on the site's home page linked `.md` files, which the build
  does not publish, so each was a 404 on the deployed site. The rewrite that
  fixes this for a Markdown link does not reach a raw `href`, so the cards
  name the built pages directly. The same four pages are still linked as
  Markdown under "Where to go next", which is what a reader on GitHub
  follows.
- A document may no longer put a collectible on a wall. Refusing one off the
  grid was not enough: any cell inside the grid was taken, wall or not, so a
  document whose rows are `[true, false, true]` and whose collectibles are
  `[[0, 0]]` loaded with a pickup on a wall. `open_cells` never yields that
  cell, so the player can never stand on it, while `MazeGame` counted it in
  `total_collectibles` all the same and the summary read `Collected: 0 of 1`
  however well the maze was played - the very thing the off-grid check was
  written to stop. It broke the round trip too: `save_lines` drew `$` over
  the wall and `parse_save` read that `$` back as an open cell, so saving
  the document as a picture turned a wall into a path. The message reads
  `collectibles holds [0, 0], which is a wall`, and the run exits with
  status `3` as the other refusals do.
- A table on the site scrolls on its own rather than taking the page
  sideways with it. `.table-scroll` was written for a wrapper nothing ever
  wore - kramdown emits a bare `<table>` - so the rule applied to nothing
  and a table could not shrink below its widest unbreakable word. The name
  table in `docs/library.md` holds `collectible_overlay(collectibles)`, 33
  characters of the monospace face, which pushed the whole page past a
  360px phone. Every table is now its own scrolling block, header included,
  and `.table-scroll` is gone so the stylesheet has one answer. What this
  release cost for it is the desktop rendering: a table drawn as a block
  hugs its content instead of spanning the measure, so at 1280px the key
  table on `docs/CHEATSHEET.md` draws 92% of the measure and the status code
  table on `docs/scripting.md` 72%, and two tables on one page end 130.4px
  apart. 2.2.3 gives the measure back above the drawer breakpoint.
- The reason given for `MIN_GRID_WIDTH` was not the reason that applies. The
  `has_ends` docstring, the `check_ends` comment and the documentation all
  said a maze narrower than three characters put a column off the grid and
  faulted in every reader. At two characters wide nothing faults:
  `find_entrance` reads column 1 and `find_exit` column 0, both on the grid.
  Only a one-column maze faults, and only in `find_entrance`. Refusing a
  two-wide maze is still right - the exit column falls left of the entrance
  column, both on the border - so the behaviour, the message and the status
  code are unchanged and only the explanation is.

### Changed

- The site's header draws the repository's own marks. The wordmark carries
  "py_maze" as artwork above 900px and gives way to the icon below it, the
  width the side menu becomes a drawer at, and each is a file per ink: the
  dark-ink art for the light theme and the light-ink art for the dark. Both
  the mark and its size are settled in the stylesheet and in a `<picture>`
  rather than in the script, so the right one is painted before the first
  frame. The header draws no lettering of its own now, so the brand link is
  named by its `title`, its `aria-label` and the `alt` on each mark.
- The tab icon is `docs/assets/favicon.svg` rather than a maze redrawn
  inline as a data URI, which was a second copy of the mark to keep in step
  with the first.
- `DESIGN_LANGUAGE.md` records both: the marks the site draws and where each
  is drawn, and what a table too wide for the screen does.
- `README.md` is a front door rather than a manual. It went from 1315 lines
  to under 220: what it keeps is what the project is, how to install it, the
  options a run reaches for most, and a short stand-in for each section whose
  detail moved, with that section's heading linking the page it moved to. The
  full text was moved rather than summarized, so nothing was lost in the
  split.
- `docs/save-format.md` is a page of the site rather than a document beside
  it. Its text is unchanged.
- The tests that read the documentation read it where it now lives. The
  worked example is still executed and compared character for character, the
  carving, braiding and quiet-run command lines are still run, the name
  tables are still checked against every `__all__` they cover, and the
  project tree is still resolved against the repository - against
  `docs/library.md`, `docs/generating.md`, `docs/scripting.md` and
  `docs/development.md` rather than against one README.

## [2.2.1] - 2026-09-01

Corrections to the edges of the document 2.2.0 introduced. A document
carrying a maze this build can play is read exactly as it was, and every
option behaves as it did: what changes is that the three documents it should
never have taken are refused rather than misread, crashed on or silently
counted.

### Added

- Repo graphics: [logo.svg](logo.svg), [icon.svg](icon.svg),
  [banner.gif](banner.gif)
- `has_ends` and `MIN_GRID_WIDTH` on the public surface, the first reporting
  whether a grid is wide enough to have an entrance and an exit and the
  second the width the two need, and `STDIN_NAME`, what a message calls
  standard input when there is no file name to give it.

### Fixed

- A maze too narrow to have an entrance and an exit is refused instead of
  ending in a traceback. `find_entrance` reads column 1 and `find_exit` the
  column before the last, so a file drawing a maze fewer than 3 characters
  wide had nowhere to put either, and every reader of the two faulted on it
  in turn: `py_maze --load tiny.txt --solve` raised `IndexError` out of the
  solver, and `py_maze --load tiny.txt --format json` raised it out of the
  document without a solution being asked for at all. The maze is now
  refused once, where the run settles on it, so the solver, the document and
  the game are all covered by the one check, and the run exits with status
  `3` and a message naming the file. The reader is unchanged: any rectangle
  of the allowed characters still loads, as `docs/save-format.md` says it
  does, and it is the command line that draws the line.
- A document may no longer put a collectible outside the maze. Any pair of
  whole numbers was taken, so `"collectibles": [[99, 99]]` or `[[-1, -1]]`
  loaded without complaint: the cell sits off the grid, so nothing draws it
  and nobody can step on it, while `MazeGame` counted it all the same and
  the end-of-game summary read `Collected: 0 of 1` however well the maze was
  played. A picture cannot express one, `$` being a character the maze is
  drawn with, so the document reader was admitting a maze the picture reader
  could not. Such a cell is now refused with
  `collectibles holds [99, 99], which is outside the maze`, and the refusal
  is tabled in `docs/save-format.md` beside the others.
- A JSON document whose `py_maze` key is not the format number is refused
  and named for what it carries. The key was compared to the number without
  being checked for one first, so `"py_maze": "1"` was refused with
  `save format 1 is not supported, this build reads 1`, a message that
  reports the string as the number it is not and so contradicts itself, and
  `"py_maze": true` was accepted as format 1, a boolean being a whole number
  in Python. The value is now shown as the document wrote it, so a word
  reads as `save format "1"` and a boolean as `save format true`. The
  message for a format number this build does not read is unchanged.

## [2.2.0] - 2026-08-31

Letting another program call py_maze and read what comes back, with no
dependencies and no network service. Every option here is new and none
changes what a run without it prints: a bare `py_maze` generates, draws and
plays exactly the maze it did before.

### Added

- `--quiet`, `-q`, keeping standard output to the maze. The
  `Generating maze...` and `Loading maze...` banners, the `seed:` line, the
  `saved:` line, the blank spacers and the "would you like to play" prompt
  are all left out, so what is left is the maze and nothing else. The maze
  itself is untouched, `start` and `end` markers included: the option takes
  lines away and changes none. A quiet run does not offer to play, there
  being nobody at the prompt to answer.
- `--format`, `-f`, choosing how the maze is written. `text` is the picture
  py_maze has always printed and saved and remains the default. `json`
  writes a document instead, carrying the grid as a list of rows of `true`
  and `false`, the entrance, the exit, the cells holding a collectible, the
  seed and the solution when `--solve` or `--animate` asked for one. It is
  written on a single line, so it pipes into a reader as it stands, and the
  same document is what `--save` writes under it. A JSON run is quiet
  whether or not `--quiet` is given, a document with a banner in front of it
  no longer being a document. `--load` reads a document back, so a maze
  written as one can be played, solved and re-saved like any other.
- `-` as the file name for `--save` and `--load`, so py_maze can sit in the
  middle of a shell pipeline:
  `py_maze --save - | py_maze --load - --solve`. `--save -` puts the save
  file on standard output and prints nothing else there, the maze included,
  since the file is already the maze and drawing it again would corrupt what
  the next command reads. `--load -` reads the maze off standard input and
  does not offer to play, that stream being the maze rather than the
  keypress a prompt would read. A stream refused by the reader is named
  `<stdin>` in the message.
- `--wall-char` and `--open-char`, saying how a loaded file that carries no
  `# py_maze save` header was drawn, so a maze drawn by another tool can be
  played, solved and re-saved. A file with no header is now read as a plain
  picture rather than refused, and the two options default to the characters
  py_maze itself draws with, so a save file with its header cut off loads
  with no options at all. They apply to reading alone: a maze is always
  written with `*`, the space and `$`, which is why a picture loaded this
  way comes back in py_maze's own characters. A file that does carry the
  header is read with the characters the format fixes whatever they say, and
  a comment is a line the picture could not have drawn, so a maze drawn with
  `#` is read as rows rather than as notes.
- A status code for each thing that can go wrong, so a script can tell them
  apart without reading the message: `3` for a file that is not a maze this
  build can read, `4` for a file that could not be read or written, and `5`
  for a maze with no way from the entrance to the exit. `0` and argparse's
  `2` are unchanged. Code 5 is reported when a solution was asked for and
  there was none to find, after the maze is printed, so a script gets the
  maze and the news together. `EXIT_OK`, `EXIT_USAGE`, `EXIT_SAVE_FILE`,
  `EXIT_FILE_ERROR` and `EXIT_NO_WAY_THROUGH` are on the package.
- `save_json`, `parse_json_save`, `picture_chars`, `STDIO_PATH`,
  `JSON_FORMAT_KEY`, `FORMATS`, `TEXT_FORMAT`, `JSON_FORMAT` and
  `DEFAULT_FORMAT` on the public surface, along with `is_quiet`,
  `asks_to_play` and `maze_char` from the command line. `write_save` and
  `read_save` both take a `stream` of their own in place of standard input
  and standard output, and `parse_save` takes the `chars` a headerless
  picture is drawn with.
- A "Scripting py_maze" section in `README.md` covering all of the above,
  and two sections in `docs/save-format.md`: one specifying the JSON
  document key by key and one specifying the picture with no header. The
  save format number does not move: a document is a second way to write a
  maze rather than a change to the first.
- Tests holding every one of them. The quiet run is compared to the loud one
  character for character, the document is compared to the grid the picture
  draws and round-trips through the reader, a maze written to standard
  output is read back off standard input, each status code is checked
  against the run that produces it, and a picture drawn with `#` and `.` is
  loaded, solved and re-saved as a py_maze file. Every example the two new
  README sections and the two new save-format sections show is run as it is
  written and compared to the output they draw, so prose that drifts from
  the package fails the suite rather than a reader's terminal.

### Changed

- `--save` is written after the maze is solved rather than before, the JSON
  document having a solution to record. Nothing about the text save file
  changes, and a path that cannot be written is still reported and still
  exits without playing.
- A refusal is printed to standard error and the run exits with the code for
  it, where before every failure exited with 1 and the message was the only
  way to tell them apart.
- `python -m py_maze` exits with what `main` hands back, as the installed
  console script already did, so the two agree on a run's status as well as
  on its output.

### Fixed

- The README's feature list no longer promises that no two mazes are alike.
  The bullet 2.1.1 rewrote to stop naming one carving algorithm went on to
  claim every run carves a maze "no two alike", which the "Repeatable Mazes"
  bullet eight lines below it contradicts and `--seed` disproves:
  `py_maze --seed 2024` carves the same maze every time it is run. The
  bullet now says the carving is random unless a seed is set, so the first
  few lines a reader sees agree with the rest of the list.

## [2.1.1] - 2026-08-30

Corrections to what 2.1.0 says about itself. The two new options carve and
braid exactly as they did; what changes is that the help and the README now
account for them where they were still describing the release before.

### Fixed

- `from py_maze.algorithms import *` now brings in `carve_backtracker`,
  `carve_prim` and `carve_division`. The subpackage imported all three to
  build its registry and `py_maze` re-exported them, but they were left out
  of `py_maze/algorithms/__init__.py`'s own `__all__`, so the star import
  that `__all__` governs handed back the registry and `carver` alone while
  `py_maze.carve_prim` worked. `CONTRIBUTING.md` now names that `__all__` in
  the steps for adding an algorithm, so a fourth one does not repeat it.
- The `--load` help names every option a loaded maze ignores. It named the
  size, seed and collectible ones, and `--algorithm` and `--braid` joined
  that list in 2.1.0: `build_maze` hands back the saved grid before either
  is read, so `py_maze --load maze.txt -A division --braid 1` printed the
  file untouched and nothing said it would. The README's list of ignored
  options names the two as well, and two tests hold the pair to it, one
  reading the help and one loading a maze twice to check the carving options
  leave it alone.
- The README's feature list no longer contradicts itself on how a maze is
  carved. Its first bullet named recursive backtracking as the way mazes are
  made, written when it was the only way, while a later bullet in the same
  list offered three, so the first few lines a reader sees disagreed with one
  another. That bullet now says what the generator does and leaves the naming
  to the "Three Carving Algorithms" bullet below it. Backtracking is still
  the default, and the guarantee it used to carry is on the "Always Solvable"
  bullet already.

## [2.1.0] - 2026-08-29

More than one way to carve a maze, chosen from the command line, and an
option that opens a carved maze up so it has more than one way through. Both
are new options with the current behaviour unchanged: a run without them
carves the maze py_maze has always carved, from the same seeds.

### Added

- `--algorithm`, `-A`, choosing how the maze is carved. `backtracker` is the
  recursive backtracking py_maze has always used and remains the default, so
  a bare run is unchanged. `prim` grows the maze outward from one cell,
  drawing each step from the whole of the growing edge rather than from
  wherever the last step landed: it branches often and its dead ends are
  short, which reads as a more open maze. `division` works the other way
  about, starting from an empty floor and walling it in two with a single gap
  to cross by, over and over, which leaves straight corridors and squared-off
  rooms. All three carve exactly one route between any two cells, so every
  maze is solvable whichever one made it.
- `--braid`, `-b`, opening a share of the maze's dead ends. A dead end is a
  cell with one way in and no way on; braiding knocks a wall out of one so it
  joins the corridor behind it. The single route through the maze becomes a
  network of routes, and `--solve` then reports a shortest way through rather
  than the only one there is. The share runs from `0` for none of them to `1`
  for all, and `--braid` on its own means `1`. It applies to a maze as it is
  generated, so a maze read back with `--load` is untouched by it.
- A `py_maze/algorithms/` subpackage, one module to an algorithm, behind a
  single interface: a size and a random number generator in, a carved grid
  out. `ALGORITHMS` maps the name `--algorithm` takes to the function that
  carves it, so a fourth algorithm is a module there and an entry in that
  map, with nothing in `MazeGenerator` to change. `carve_backtracker`,
  `carve_prim`, `carve_division`, `carver`, `ALGORITHMS`, `ALGORITHM_NOTES`
  and `DEFAULT_ALGORITHM` are all re-exported from the package.
- `braid_maze(grid, share, rng)` and `open_ends(grid)` on the public surface,
  the first opening the dead ends of any grid it is handed and the second
  cutting the entrance and the exit into a carved one.
- Tests holding every algorithm to the same promises rather than the default
  alone: that it carves the size asked for, seals its border, opens its
  entrance and its exit, leaves every cell standable, carves a solvable maze
  and leaves exactly one route between any two squares, and repeats itself
  from a seed. Prim's is checked to leave more dead ends than backtracking
  and recursive division to build a wall the whole way across the maze, so
  each stays the algorithm it says it is. The maze the default carves is
  pinned to the picture it has always drawn.
- A "Carving Algorithms" section, a "Braiding" section and a "Carving and
  Braiding" library example in `README.md`, and a section in
  `CONTRIBUTING.md` on what adding a carving algorithm takes.
- A "Using py_maze as a Library" section in `README.md`, covering the half of
  the project that is not the game: the grid every name reads and writes and
  the shape it takes, a worked example that generates a maze, solves it and
  draws the solution with no game and no keyboard involved, a second showing
  the collectibles and the save file round trip, and a table of every
  importable name under the module it lives in. The section describes what
  the package already did, so no behaviour changes with it.
- Tests holding that section to the package. The worked example is run as it
  is written and what it prints is compared to the output the README shows,
  the `>>>` block is run as a doctest, every name the tables give a row is
  checked against `__all__`, every name the worked example reaches for is
  checked to come from a module that leaves the terminal alone, and the whole
  public surface of the grid, generation, solving and save file modules is
  checked to have a row, so a name added to one of them fails the suite until
  the README shows it.

### Changed

- `MazeGenerator` no longer holds the carving itself: it takes an `algorithm`
  name, looks the carver up and hands it the size and its own random numbers.
  An unknown name raises `ValueError` when the generator is built rather than
  at the first `generate()`. The interface is unchanged for a caller that
  does not pass one, and the maze carved from a given seed is the maze that
  seed has always carved.
- The `Development` file tree in `README.md` lists what the repository
  carries. It named neither `TODO.md`, the two launcher scripts nor
  `.github/`, and nothing for `docs/`, `CONTRIBUTING.md` or `LICENSE`, each
  of which arrived after the tree was last written. A test now resolves
  every entry the tree draws against the repository and checks each expected
  file is drawn, so the map and the repository cannot drift apart again.

## [2.0.2] - 2026-08-27

### Changed

- The supported Python versions are the ones that are still supported
  upstream. `requires-python` was `>=3.6`, a release that reached end of life
  in December 2021, and the classifiers stopped at 3.11. The floor is now
  `>=3.10` and the classifiers list 3.10, 3.11, 3.12 and 3.13, every one of
  which the suite is run on. Nothing in the package changes: it is written
  against the standard library alone and uses no syntax newer than the floor
  it declared before.

### Added

- A `LICENSE` file carrying the MIT text that `README.md` and
  `pyproject.toml` have both declared since the first release, so the
  declaration rests on something.
- A GitHub Actions workflow, `.github/workflows/tests.yml`, running
  `python -m unittest discover` on Windows, Linux and macOS across every
  supported Python version on each push and pull request. The cross-platform
  promise is checked now rather than asserted, and the matrix is the
  classifier list, so a version the manifest promises is a version that is
  tested. Nothing is installed to run it: the suite is standard library only.
- `CONTRIBUTING.md`, covering the test command, the comment and docstring
  convention (docstrings on public names, the existing comment style on
  internal helpers), how the version is single-sourced from `__version__`,
  and the grid as the type new code is expected to read and write.
- `docs/save-format.md`, specifying the save file so another tool can write
  one py_maze will load: the header and what it is for, the seed comment, the
  three markers and the on-screen markers that are not part of the format,
  the ragged-line rule and the two ways whitespace catches a writer out, the
  entrance and exit convention, every refusal the reader makes with the
  message it gives, and the two things it deliberately does not refuse.
- Tests covering all of the above: that no classifier falls below
  `requires-python` and the list runs without a gap, that the CI matrix is
  that same list, that the licence the manifest declares is the text the
  repository carries, that the contributing guide gives the command the
  workflow runs, and that the save format document agrees with the reader on
  every marker, every refusal message and the example file it draws.

## [2.0.1] - 2026-08-26

### Fixed

- The play screen no longer flickers on every move. `render` wiped the whole
  terminal and then wrote the maze, the status line and the key legend a line
  at a time, so the screen stood empty between the clear and the last row.
  The cursor is now put back at the top left and the whole frame goes out in
  a single write, over the frame it replaces. Only the first frame of a game
  wipes the screen, to clear what the run printed before play started.
- The screen is cleared with an ANSI escape sequence rather than
  `os.system('cls')` or `os.system('clear')`, so `--animate` no longer starts
  a shell for every frame it draws. Windows consoles are switched to virtual
  terminal processing once per run rather than once per frame. Where the
  escapes are not honoured, including under `TERM=dumb`, the shell call is
  still there as the fallback and the behaviour is exactly what it was.
- The "would you like to play" prompt reads a single keypress on POSIX, as it
  already did on Windows. It set no raw mode, so `sys.stdin.read(1)` waited
  for Enter and left the rest of the line in the buffer, contrary to what the
  function said it did. Ctrl+C at the prompt raises a `KeyboardInterrupt` on
  both platforms now, and an answer piped in rather than typed is read
  straight from the pipe, there being no terminal mode to set.
- The win banner drops the party poppers when the output encoding cannot
  carry them, so a console on a legacy code page shows the congratulations
  instead of raising `UnicodeEncodeError` in place of it.
- `MazeGenerator.generate()` carves from a fresh grid every time. A second
  call on the same generator carved into the maze the first call had already
  made, leaving a grid with more ways through than a maze has. A seeded
  generator also goes back to the same random numbers, so it makes the same
  maze, and scatters the same collectibles, however many times it is asked.

### Added

- `py_maze.ansi_enabled`, `py_maze.clear_screen` and `py_maze.frame_text` for
  drawing over a terminal: whether escape sequences are honoured, wiping the
  screen with one, and joining the lines of a screen into the single string
  that draws it. `ANSI_CLEAR`, `ANSI_HOME` and `ANSI_CLEAR_LINE` are the
  sequences themselves.
- `py_maze.can_encode`, reporting whether a stream's encoding can carry a
  piece of text, and `py_maze.win_banner`, which uses it to choose between
  `WIN_BANNER` and `PLAIN_WIN_BANNER`.
- `py_maze.walled_grid`, the solid block of wall a maze is carved out of, and
  `MazeGame.frame`, the play screen as a list of lines. `CONTROLS_LINE` is
  the key legend that frame ends with.
- Tests covering all of the above: that a frame is one write and homes the
  cursor, that only the first frame wipes the screen, that no shell is
  spawned for an animated search, that the prompt takes one keypress and
  restores the terminal, that a legacy console is given the plain banner, and
  that a generator asked twice hands back the same maze.

### Changed

- `clear_screen`, `MazeGame.clear_screen` and `MazeGame.render` take an
  optional stream, defaulting to standard output as before. `animate_search`
  clears the stream it was given rather than standard output.

## [2.0.0] - 2026-08-25

### Added

- `python -m py_maze`, so a source checkout runs the same way an installed
  copy does. `py_maze.bat` and `py_maze.sh` now put their own folder on
  `PYTHONPATH` and run the module, so neither needs the game installed and
  neither depends on the working directory.
- An `__all__` and a docstring on every module and every public function and
  class, so `help(py_maze)`, `help(py_maze.solve_maze)` and any generated
  reference describe the surface rather than an empty signature. Internal
  helpers keep the existing comment style, which is what marks them internal.
- Round-trip tests pinning the grid as the interchange type: that it is a
  list of rows of booleans with `True` for a wall, that a maze survives
  being drawn and read back, that saving what was loaded reproduces the file
  it came from, and that a loaded maze solves and draws exactly as the
  generated one did. Tests also pin the package surface, the module entry
  point and the fact that the generator and the solver pull in no terminal
  machinery.

### Changed

- **BREAKING**: `py_maze.py` is now a `py_maze/` package, with the grid
  helpers, generation, solving, rendering, save files, keyboard input, the
  game and the command line each in their own module. `python py_maze.py`
  no longer works and becomes `python -m py_maze`. Nothing else about the
  command changes: every option, every message and the save file format are
  as they were, and `import py_maze` still reaches every public name,
  because `__init__.py` re-exports all of them.
- The `msvcrt`, `tty` and `termios` imports moved out of the import path and
  into `py_maze.keys`, the one module that reads a keypress. Importing the
  generator, the solver, the renderer or the save files no longer pulls in
  terminal machinery, so a program that only wants a maze is not handed a
  terminal to go with it. `MazeGame.get_key`, `get_key_windows` and
  `get_key_posix` are unchanged and now delegate to that module.
- `__version__` lives in `py_maze/version.py` and is re-exported as
  `py_maze.__version__`, so the manifest, the `--version` flag and the
  changelog still read one string. A module of its own means the package and
  the command line can both read it without one importing the other.
- The usage line and the argument errors now name the program `py_maze`
  rather than the file argparse happened to be started from, so they read
  the same however the game was launched.
- The console script points at `py_maze.cli:main` and the manifest ships a
  package rather than a single module. Installing with `pip install -e .`
  and running `py_maze` are unchanged.

### Removed

- `py_maze.py`. The package replaces it; leaving both in place would have
  made which one runs depend on the import machinery.

## [1.2.0] - 2026-08-21

### Added

- A timer and a move counter. Both run under the maze while the game is
  played, on a status line beside the collectible tally, and both are
  summarized on the win screen. The clock starts at the first render and
  stops the moment the maze is won, so the summary reads the same however
  long it is left on screen, and it is a monotonic clock, so an adjustment to
  the system time mid-game cannot run it backwards. Only steps that moved the
  player are counted, so walking into a wall costs nothing but the time it
  took. Quitting with `q` prints the same summary for the game so far.
- A `--collectibles`/`-c` option scattering that many `$` markers through the
  maze for the player to pick up, tallied as "Collected: 2 of 3" in the
  end-of-game summary. Places are drawn from the seeded generator, so the same
  seed puts them in the same cells every run, and the entrance and the exit
  are left clear so nothing is handed over before the first step or after the
  last. Asking for more than the maze has room for fills every cell there is.
  None are scattered unless the option is given.
- A `--save`/`-o` option writing the maze, and any collectibles, to a file,
  and a `--load`/`-l` option playing a maze back from one. A save file is the
  maze exactly as it is drawn, under a short header recording the format and
  the seed, so it can be read, edited by hand and compared like any other
  text. A loaded maze comes from the file as it was saved, so the size, seed
  and collectible options do not apply to it, and a file that is not a maze
  this build can read is refused with a message naming the line and what was
  wrong with it.

### Changed

- The maze render now reserves five rows around the maze rather than four,
  the new one being the status line. The terminal cap measures against the
  same number, so a maze is capped one row earlier than it was.
- Solved mazes draw collectibles over the solution path, so a maze printed
  with `--solve` still shows what there is to pick up along the way.

## [1.1.0] - 2026-08-20

### Added

- A `--seed`/`-s` option that fixes the maze generator's random numbers, so
  the same seed always produces the same maze. A seed is now chosen for every
  run and printed under the maze, so a maze worth keeping can be generated
  again without having planned ahead. Seeds may be whole numbers or text.
- A `--difficulty`/`-d` option choosing a preset maze size: easy (6 by 6),
  normal (9 by 11) or hard (16 by 20). The normal preset is the size the game
  has always generated, so leaving the option out changes nothing, and
  `--width` and `--height` still override either dimension of a preset.
- A `--solve`/`-S` flag that prints the shortest way through the maze,
  overlaid on it as a trail of `.` markers. The solver is a breadth-first
  search, so the route it draws is always the shortest one.
- A `--animate`/`-a` flag that steps the solver's search across the screen
  one wave at a time, marking the frontier with `?` and explored cells with
  `~` before the solved maze is printed. Piped or redirected output has no
  screen to animate over, so the maze is solved without the frames.
- An in-game hint: pressing `h` lights up the next step along the solution
  for a moment, then redraws the maze without it. The path is solved from
  wherever the player is standing, so a hint still points the way after a
  wrong turn. The controls line names the key.

### Changed

- `--width` and `--height` now default to "not given" rather than to 9 and
  11, and the difficulty preset supplies whichever of the two is left out.
  The maze generated by a bare `py_maze` is unchanged.
- The maze is drawn by one set of helpers shared by the printed maze, the
  in-game render, the solved maze and the animation, so every overlay marker
  lands the same way in all four.
- The game finds its entrance and exit through the same helpers the solver
  uses, instead of scanning the grid itself.

## [1.0.2] - 2026-08-19

### Added

- A `--version`/`-V` flag that prints the package version and exits. The
  number is read from the module, so the flag, the manifest and an installed
  copy can never disagree.
- Maze sizes are now measured against the terminal before generating. A maze
  wider or taller than the screen is capped to what fits, with a warning
  naming the option, the space it needed and the size being used instead.
  When the terminal cannot hold even the smallest maze, the warning says so
  rather than shrinking below the two cell minimum.
- `pyproject.toml`, declaring the package metadata and reading the version
  from `py_maze.__version__` so it is recorded in exactly one place.
- A `.gitignore` covering Python artifacts (`__pycache__/`, `*.egg-info/`,
  `build/`, `dist/`), test and coverage output, virtual environments, and
  editor and operating system noise.
- Tests for the POSIX keyboard branch, the interrupt handling, the terminal
  fitting helpers and the `--version` flag. The POSIX branch is driven
  through a fake terminal, so the suite still runs on any platform.

### Changed

- Packaging moved from `setup.py` to `pyproject.toml`. Installing with
  `pip install -e .` is unchanged, but building from source now needs
  setuptools 61 or newer.
- The placeholder author metadata left in `setup.py` has been replaced with
  the real project details, and the manifest now records the project's home
  page, repository, changelog and issue tracker.
- Quitting at the "would you like to play" prompt and interrupting the game
  now print the same parting message, from a single constant.

### Fixed

- Ctrl+C during gameplay no longer ends in a traceback over a terminal still
  in raw mode. Raw mode suppresses the usual interrupt signal, so the key
  arrived as an ordinary byte and was ignored on POSIX and swallowed by
  `getch` on Windows. Both key readers now restore the terminal and raise
  the interrupt, and the game loop catches it and exits with a message.

## [1.0.1] - 2026-08-18

### Added

- Unit test suite (`test_py_maze.py`) covering maze generation (dimensions,
  sealed borders, entrance and exit placement, solvability across several
  sizes and seeds) and gameplay (start and end detection, movement, wall
  and boundary collision, win detection), plus the command-line parser and
  the Windows keyboard branch. Run it with `python -m unittest discover`.
- This changelog, recording the 1.0.0 release as the baseline entry.
- A "Command-Line Options" section in the README listing every flag, its
  short form, default value and minimum.
- A minimum size of 2 cells for `--width` and `--height`. Smaller values are
  rejected with a message naming the option and the value that was given,
  rather than producing a degenerate maze.

### Changed

- Windows keyboard input now waits for a keypress by polling with a short
  sleep between checks, instead of spinning in a loop that consumed a full
  CPU core while the game sat idle.
- The "Generating maze..." banner now prints after arguments are parsed, so
  `--help` output and argument errors are no longer preceded by it.
- The cross-platform `get_key` method now delegates to `get_key_windows` and
  `get_key_posix`, so each platform's input path can be tested directly.

### Fixed

- The README usage example passed `-h` for height, which argparse reserves
  for `--help`, so the documented command failed. The example and the new
  options table use the real short flag, `-H`.
- Arrow keys that Windows reports with the `\x00` extended-key prefix are
  now recognized. Previously only the `\xe0` prefix was handled, so on
  keyboards and consoles that send `\x00` the arrow keys did nothing.

## [1.0.0] - 2025-12-25

### Added

- Random maze generation using the recursive backtracking algorithm, so
  every generated maze is solvable and has exactly one path between any two
  points.
- Interactive gameplay: move with the arrow keys or WASD, from the entrance
  at the top of the maze to the exit at the bottom, and quit with `q`.
- Cross-platform keyboard handling for Windows, Linux and macOS, using only
  the standard library.
- `--width`/`-w` and `--height`/`-H` options for setting the maze size in
  cells, defaulting to 9 by 11.
- Packaging via `setup.py`, installing a `py_maze` console script.
- `py_maze.bat` and `py_maze.sh` launcher scripts.
