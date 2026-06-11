#!/usr/bin/env bash
# Launch the Tomato Detector app using the project venv.
set -e
cd "$(dirname "$0")"
exec ./.venv/bin/python -m app.main "$@"
