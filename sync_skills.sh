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
DOCLING_PYTHON="${DOCLING_PYTHON:-/Users/cristiano/.venvs/docling/bin/python}"

usage() {
  printf '%s\n' \
    'Usage: sync_skills.sh [--pull|--pull-all]' \
    '  Apply local skill patches, then sync skills to Codex and Cursor.' \
    '  DOCLING_PYTHON=/path/to/python overrides the default Docling interpreter.' \
    '  --pull      Pull the repo-local skills tree before syncing.' \
    '  --pull-all  Pull the repo-local skills tree and nested skill repos (child dirs with .git).'
}

patch_pdf_reading_local_runtime() {
  local skill_file="$REPO/pdf-reading/skills/general/pdf-reading/SKILL.md"
  local tmp

  [[ -f "$skill_file" ]] || return 0

  if ! grep -Fq "Always run the extractor with the installed Docling virtual environment" "$skill_file"; then
    tmp="$(mktemp)"
    awk -v py="$DOCLING_PYTHON" '
      {
        print
        if ($0 == "- Default to Docling for reading. Use `--fast` only when the user explicitly prefers speed over fidelity.") {
          print "- Always run the extractor with the installed Docling virtual environment at `" py "`."
        }
      }
    ' "$skill_file" > "$tmp"
    mv "$tmp" "$skill_file"
  fi

  if ! grep -Fq "## Local Runtime" "$skill_file"; then
    tmp="$(mktemp)"
    awk -v py="$DOCLING_PYTHON" '
      {
        if ($0 == "## Quick Start") {
          print "## Local Runtime"
          print ""
          print "This machine has Docling installed in:"
          print ""
          print "```bash"
          print py
          print "```"
          print ""
          print "Use that interpreter for all `scripts/pdf_extract.py` commands so Docling imports resolve reliably."
          print ""
        }
        print
      }
    ' "$skill_file" > "$tmp"
    mv "$tmp" "$skill_file"
  fi

  DOCLING_PYTHON_PATH="$DOCLING_PYTHON" perl -0pi -e '
    my $py = $ENV{DOCLING_PYTHON_PATH};
    s#/Users/cristiano/\.venvs/docling/bin/python#$py#g;
    s#python3 scripts/pdf_extract\.py#$py scripts/pdf_extract.py#g;
  ' "$skill_file"
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

patch_pdf_reading_local_runtime

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
