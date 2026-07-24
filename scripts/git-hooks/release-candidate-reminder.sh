#!/bin/sh
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || exit 0
[ "$branch" = "main" ] || exit 0
echo 'meeting-ingest: main moved; a release candidate may exist. Use the documented release flow (README "Release Flow"). Git hooks never build, publish, install, pin, or update.'
exit 0
