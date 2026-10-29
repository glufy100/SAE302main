#!/usr/bin/env bash

DOSSIER="$(cd "$(dirname "$0")" && pwd)"
RACINE="$(dirname "$DOSSIER")"

PYTHON=python3
if [[ "$(uname)" == "Darwin" ]]; then
    PYTHON=/Library/Frameworks/Python.framework/Versions/3.11/bin/python3
fi

cd "$RACINE"
exec "$PYTHON" -m server.carrefour
