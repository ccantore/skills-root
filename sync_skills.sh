#!/usr/bin/env bash
set -euo pipefail

REPO="/Users/cristiano/Documents/GitHub/skills"
CODEX_DIR="/Users/cristiano/.codex/skills"
CURSOR_DIR="/Users/cristiano/.cursor/skills"

usage() {
  cat <<'USAGE'
Usage: sync_skills.sh [--pull|--pull-all]
  --pull      Pull the root skills repo before syncing.
  --pull-all  Pull the root skills repo and pull nested skill repos (child dirs with .git).
USAGE
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
  while IFS= read -r d; do
    if [[ -d "$d/.git" ]] && git -C "$d" remote get-url origin >/dev/null 2>&1; then
      git -C "$d" pull --ff-only
    fi
  done < <(find "$REPO" -mindepth 1 -maxdepth 1 -type d ! -name .git | sort)
fi

mkdir -p "$CODEX_DIR" "$CURSOR_DIR"

synced=0
while IFS= read -r src; do
  [[ -f "$src/SKILL.md" ]] || continue

  name="$(basename "$src")"
  codex_dst="$CODEX_DIR/$name"
  cursor_dst="$CURSOR_DIR/$name"

  sync_one_target "$src" "$codex_dst"
  sync_one_target "$src" "$cursor_dst"

  synced=$((synced + 1))
done < <(find "$REPO" -mindepth 1 -maxdepth 1 -type d ! -name .git | sort)

echo "Synced $synced skills to Codex ($CODEX_DIR) and Cursor ($CURSOR_DIR)."
