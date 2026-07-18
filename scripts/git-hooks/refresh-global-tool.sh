#!/bin/sh
# Refresh the frozen global meeting-ingest uv tool whenever main moves in this
# checkout, so consumer projects always run the latest merged code.
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || exit 0
[ "$branch" = "main" ] || exit 0
command -v uv >/dev/null 2>&1 || exit 0
repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
if uv tool install --reinstall "$repo_root" >/dev/null 2>&1; then
    echo "meeting-ingest: refreshed global uv tool from main"
else
    echo "meeting-ingest: global uv tool refresh failed; run 'uv tool install --reinstall $repo_root'" >&2
fi
exit 0
