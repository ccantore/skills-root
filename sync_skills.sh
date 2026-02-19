#!/usr/bin/env bash
set -euo pipefail

REPO="/Users/cristiano/Documents/GitHub/skills"
SRC="$REPO/notes-to-slides-diff"
CODEX_DST="/Users/cristiano/.codex/skills/notes-to-slides-diff"
CURSOR_RULE="/Users/cristiano/EcoDir Dropbox/Cristiano Cantore/Teaching/teaching 2025-2026/MTP/.cursor/rules/notes-to-slides-diff.mdc"

if [[ "${1:-}" == "--pull" ]]; then
  git -C "$REPO" pull --ff-only
fi

mkdir -p "$CODEX_DST"
rsync -a --delete "$SRC/" "$CODEX_DST/"

mkdir -p "$(dirname "$CURSOR_RULE")"
{
  cat <<'HDR'
---
description: Update Beamer slides from notes with derivation-level detail and figure-sync workflow.
globs:
  - "Topic */sections/*.tex"
  - "Sims notes_2024/**/*.tex"
alwaysApply: false
---
HDR
  awk 'NR==1 && $0=="---"{front=1;next} front && $0=="---"{front=0;next} !front{print}' "$SRC/SKILL.md"
} > "$CURSOR_RULE"

echo "Synced Codex + Cursor from $SRC"
