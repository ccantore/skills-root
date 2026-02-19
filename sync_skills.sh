#!/usr/bin/env bash
set -euo pipefail

REPO="/Users/cristiano/Documents/GitHub/skills"
SRC="$REPO/notes-to-slides-diff"
CODEX_DST="/Users/cristiano/.codex/skills/notes-to-slides-diff"
CURSOR_SKILLS_DIR="/Users/cristiano/.cursor/skills"
CURSOR_LINK="$CURSOR_SKILLS_DIR/notes-to-slides-diff"

if [[ "${1:-}" == "--pull" ]]; then
  git -C "$REPO" pull --ff-only
fi

mkdir -p "$CODEX_DST"
rsync -a --delete "$SRC/" "$CODEX_DST/"

mkdir -p "$CURSOR_SKILLS_DIR"
if [[ -L "$CURSOR_LINK" ]]; then
  current_target="$(readlink "$CURSOR_LINK")"
  if [[ "$current_target" != "$SRC" ]]; then
    rm "$CURSOR_LINK"
    ln -s "$SRC" "$CURSOR_LINK"
  fi
elif [[ -d "$CURSOR_LINK" ]]; then
  rsync -a --delete "$SRC/" "$CURSOR_LINK/"
else
  ln -s "$SRC" "$CURSOR_LINK"
fi

echo "Synced Codex skill + Cursor skill from $SRC"
