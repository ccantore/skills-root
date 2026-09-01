#!/usr/bin/env bash
set -euo pipefail

SKILL_NAME="handwritten-exam-pdf-to-markdown"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

CODEX_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
CURSOR_ROOT="$HOME/.cursor/skills"

install_one() {
  local root="$1"
  local dest="$root/$SKILL_NAME"
  local tmp="$root/.$SKILL_NAME.install.$$"

  mkdir -p "$root"

  if [ -e "$dest" ]; then
    echo "Already exists, not overwriting: $dest" >&2
    echo "Remove or rename it manually, then rerun this script." >&2
    return 1
  fi

  mkdir "$tmp"
  cp -R "$SOURCE_DIR/." "$tmp/"
  mv "$tmp" "$dest"
  echo "Installed: $dest"
}

install_one "$CODEX_ROOT"
install_one "$CURSOR_ROOT"

echo
echo "Restart Codex and Cursor to pick up the new global skill."
