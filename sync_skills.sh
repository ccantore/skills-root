#!/usr/bin/env bash
set -euo pipefail

export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:${PATH:-}"
shopt -s nullglob

SCRIPT_PATH="${BASH_SOURCE[0]}"
SCRIPT_DIR="${SCRIPT_PATH%/*}"
if [[ "$SCRIPT_DIR" == "$SCRIPT_PATH" ]]; then
  SCRIPT_DIR="."
fi

REPO="$(cd -- "$SCRIPT_DIR" && pwd -P)"
CODEX_DIR="${HOME}/.codex/skills"
CURSOR_DIR="${HOME}/.cursor/skills"

usage() {
  printf '%s\n' \
    'Usage: sync_skills.sh [--pull|--pull-all]' \
    '  --pull      Pull the repo-local skills tree before syncing.' \
    '  --pull-all  Pull the repo-local skills tree and nested skill repos (child dirs with .git).'
}

sync_one_target() {
  local src="$1"
  local dst="$2"

  if [[ -L "$dst" ]]; then
    local current_target
    current_target="$(readlink "$dst")"
    if [[ "$current_target" != "$src" ]]; then
      rm "$dst"
      ln -s "$src" "$dst"
    fi
  elif [[ -e "$dst" ]]; then
    rsync -a --delete "$src/" "$dst/"
  else
    ln -s "$src" "$dst"
  fi
}

DO_PULL_ROOT=false
DO_PULL_NESTED=false

skill_dirs=()
for d in "$REPO"/*; do
  [[ -d "$d" ]] || continue
  [[ "${d##*/}" == ".git" ]] && continue
  skill_dirs+=("$d")
done

case "${1:-}" in
  "") ;;
  --pull)
    DO_PULL_ROOT=true
    ;;
  --pull-all)
    DO_PULL_ROOT=true
    DO_PULL_NESTED=true
    ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    usage
    exit 1
    ;;
esac

if $DO_PULL_ROOT; then
  git -C "$REPO" pull --ff-only
fi

if $DO_PULL_NESTED; then
  for d in "${skill_dirs[@]}"; do
    if [[ -d "$d/.git" ]] && git -C "$d" remote get-url origin >/dev/null 2>&1; then
      git -C "$d" pull --ff-only
    fi
  done
fi

mkdir -p "$CODEX_DIR" "$CURSOR_DIR"

synced=0
for src in "${skill_dirs[@]}"; do
  [[ -f "$src/SKILL.md" ]] || continue

  name="$(basename "$src")"
  codex_dst="$CODEX_DIR/$name"
  cursor_dst="$CURSOR_DIR/$name"

  sync_one_target "$src" "$codex_dst"
  sync_one_target "$src" "$cursor_dst"

  synced=$((synced + 1))
done

echo "Synced $synced skills to Codex ($CODEX_DIR) and Cursor ($CURSOR_DIR)."
