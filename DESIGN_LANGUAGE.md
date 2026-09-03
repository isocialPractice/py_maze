# Design Language

The look of the py_maze documentation site, derived from the repository's own
artwork rather than chosen. Everything below is what
[docs/assets/css/site.css](docs/assets/css/site.css) implements, and the two
are meant to stay in agreement: a value changed in one is changed in the
other.

## What it was derived from

[logo.svg](logo.svg) is the whole of the source, and the icon is the mark it
opens with, drawn on its own in [docs/assets](docs/assets). Both draw their
lettering as a field of small squares on a fixed pitch, ruled off by straight
vignette lines, which is the same shape a maze has and the same shape a
terminal has.

| Read from the artwork | Value found | What it decides on the site |
| --- | --- | --- |
| `fill` and `stroke` on the letterforms | `#373d42`, `#6c757d` | The two ink tones |
| `fill` on the icon's ground | `#f2f2f2` | The panel tone |
| Letter cell against its pitch | 9.49 on 12.66, a fill of 0.75 | The spacing rhythm, 12px with 9px insets |
| Corner radius anywhere in either file | none, every corner square | Radius 0 on every surface |
| Vignette stroke against pattern stroke | 7.45 against 5, a ratio of 1.49 | Rules at 2px, accent bars at 3px |
| Pattern line spacing | 12 units | The 12px ruled ground behind the header |

The palette that comes back is monochrome, and it was left monochrome. There
is no third hue anywhere in either file to derive one from, and inventing one
would be decoration rather than derivation. Colour interest on the page comes
from the mazes themselves, which is where a reader is looking anyway.

## Palette

Every pair below was measured, and the ratio is written beside it. Body text
needs 4.5:1 and large headings 3:1; both themes clear the higher bar for
every text pair.

### Light

| Role | Hex | On | Ratio |
| --- | --- | --- | --- |
| Page ground | `#ffffff` | - | - |
| Panel, code block, table stripe | `#f2f2f2` | - | - |
| Body text, headings, links | `#373d42` | `#ffffff` | 11.00:1 |
| The same, inside a panel | `#373d42` | `#f2f2f2` | 9.83:1 |
| Muted text, captions, the menu's resting state | `#5a6268` | `#ffffff` | 6.21:1 |
| The same, inside a panel | `#5a6268` | `#f2f2f2` | 5.55:1 |
| Rules, borders, accent bars | `#6c757d` | - | not text |

`#6c757d` is the artwork's own gray and it reaches only 4.19:1 on the panel
tone, so it is kept for rules, borders and the accent bar and never used for
text. `#5a6268` is the same gray darkened until it clears 4.5:1 on both
grounds, and it carries every muted line instead.

### Dark

| Role | Hex | On | Ratio |
| --- | --- | --- | --- |
| Page ground | `#22262a` | - | - |
| Panel, code block, table stripe | `#2b3035` | - | - |
| Body text, headings, links | `#e6e8ea` | `#22262a` | 12.40:1 |
| The same, inside a panel | `#e6e8ea` | `#2b3035` | 10.84:1 |
| Muted text, captions, the menu's resting state | `#a8b0b6` | `#22262a` | 6.93:1 |
| The same, inside a panel | `#a8b0b6` | `#2b3035` | 6.06:1 |
| Rules, borders, accent bars | `#6c757d` | - | not text |

The dark ground is the ink tone taken further down rather than a new colour,
so the two themes are the same palette read from either end.

Neither theme is the default. The stylesheet follows
`prefers-color-scheme`, and the toggle in the header overrides it and
remembers the choice.

## Type

| Step | Size | Used for |
| --- | --- | --- |
| `--type-xs` | 0.8125rem | Captions, the menu's group labels |
| `--type-sm` | 0.875rem | Code, tables |
| `--type-base` | 1rem | Body text |
| `--type-lg` | 1.2rem | Level 3 and 4 headings |
| `--type-xl` | 1.44rem | Level 2 headings |
| `--type-2xl` | 1.728rem | The page title |
| `--type-3xl` | 2.0736rem | The site title on the home page |

A 1.2 ratio from a 16px base. Prose is set in the reading face the platform
already has, and everything else - code, mazes, tables of options - is set in
the monospace one, because the subject is a terminal.

A maze is drawn as characters, so the line height inside a code block is
1.35 rather than the 1.65 prose runs at: any looser and the walls stop
reading as walls.

## Space, rule and edge

| Token | Value | From |
| --- | --- | --- |
| `--space-1` to `--space-8` | 4, 8, 12, 16, 24, 32, 48, 64px | A 4px base, with 12px the working rhythm |
| `--rule` | 2px | The pattern stroke, scaled |
| `--accent-bar` | 3px | The vignette stroke, at the same 1.49 ratio |
| `--radius` | 0 | Every corner in the artwork is square |
| Content measure | 76ch | Long enough for a wide maze, short enough to read |

The header carries a 12px ruled ground, the pattern pitch of the logo drawn
as a repeating gradient, and a 3px bar under it in the accent tone. The menu
marks the page being read with the same 3px bar down its left edge, which is
the vignette line the logo rules its lettering off with.

## Layout and menu

The site has fourteen pages, so the menu is a side menu, grouped, and fixed
in position. Its groups collapse, and the group holding the page being read
is open when the page loads.

Below 900px the side menu leaves the flow and becomes a drawer behind a
button in the header. The button is the only thing that is added at that
width; nothing is taken away, and every page reads from a phone.

A table is the one thing on a page that cannot be made narrow. Its cells
hold names set in the monospace face - `collectible_overlay(collectibles)`
is 33 characters of it - and a name has nowhere to break, so a table of
them is wider than a 360px phone whatever the page does. Every table is
therefore a scrolling block of its own: it hugs its content up to the
measure and scrolls sideways past it, taking its header along with the
rows, and the page around it stays the width of the screen. Nothing is
hidden and nothing is truncated - the reader drags the table rather than
the page.

Focus is drawn with a 2px outline in the ink tone at a 2px offset, on every
control, and the menu is reachable by keyboard in the order it is read.
Nothing on the site conveys meaning by colour alone: links are underlined
and set at weight 600, and the current page is marked by its bar as well as
its weight.

## Graphics

No image is sourced from outside the repository. The site's marks are the
five files in [docs/assets](docs/assets), all of them drawn from the same
artwork the palette was read out of, and the ruled ground behind the header,
which is a CSS gradient. A documentation site about a program that draws
mazes out of asterisks does not need photography.

| File | Where it is drawn |
| --- | --- |
| `logo-dark.svg`, `logo-light.svg` | The header, above 900px |
| `icon-dark.svg`, `icon-light.svg` | The header, at 900px and below |
| `favicon.svg` | The browser tab |

The wordmark carries "py_maze" as artwork rather than as text, so the header
draws no lettering of its own; the link is named by its `title` and its
`aria-label` instead, and each image carries the same name as its `alt`. It
is set at 108px, and the icon at 22px, which is 40% of each file's own size
and the mark width the header was laid out around.

The pairs are one ink apiece rather than one file recoloured: `-dark` is the
`#373d42` ink for a light background and `-light` the `#e6e8ea` ink for a
dark one, the same two tones the palette above lists. An `<img>` cannot
inherit the page's colour, so which of the pair is shown is a stylesheet
rule keyed on the theme, and the size is a `<picture>` falling back to the
icon at the same 900px the menu becomes a drawer at. Both are settled before
the first paint, so no reader watches the wrong mark being replaced. The
favicon needs no pair: it is the dark ink under a light outline, which reads
on a light tab and on a dark one.
