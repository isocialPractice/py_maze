#!/bin/bash

# run the package from this folder, so a checkout needs no install
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHONPATH="$here:$PYTHONPATH" python3 -m py_maze "$@"
