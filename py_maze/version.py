#!/usr/bin/env python3
"""The single source of the package version.

`pyproject.toml` reads `py_maze.__version__`, the `--version` flag prints
it and the test suite checks the changelog has an entry for it, so a
version change only ever touches the string below. It lives in a module
of its own so both the package and the command line can read it without
one importing the other.

The string is a PEP 440 pre-release of the release being worked towards,
not a release number: nothing is published to any registry and nothing
depends on this package, so `1.0.0` is where it is going rather than
where it has been. The semantic-versioning scheme this one replaced
reached `1.0.0` on 2025-12-25, so that entry is headed
`## [1.0.0 under semver]` in `CHANGELOG.md` and the plain `## [1.0.0]`
is left for the release this counter is climbing to.

A pre-release segment holds exactly one number, which means the size
of a change cannot be written into the version at all - the counter
advances by one for any version-relevant run, whatever the size, and
the size is recorded in that run's `CHANGELOG.md` entry. The core
`1.0.0` does not move until the project actually releases.
"""

__version__ = '1.0.0a5'
