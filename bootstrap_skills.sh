#!/usr/bin/env bash
set -euo pipefail

export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:${PATH:-}"

SCRIPT_PATH="${BASH_SOURCE[0]}"
SCRIPT_DIR="${SCRIPT_PATH%/*}"
if [[ "$SCRIPT_DIR" == "$SCRIPT_PATH" ]]; then
  SCRIPT_DIR="."
fi

REPO="$(cd -- "$SCRIPT_DIR" && pwd -P)"
SYNC_SCRIPT="$REPO/sync_skills.sh"

usage() {
  printf '%s\n' \
    'Usage: bootstrap_skills.sh [--pull]' \
    '  Clone missing nested skill repos into this directory.' \
    '  --pull  Also fast-forward existing nested repos before syncing.'
}

DO_PULL=false

case "${1:-}" in
  "")
    ;;
  --pull)
    DO_PULL=true
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

skill_names=(
  "jambro-beamer-setup"
  "lit-review"
  "notes-to-beamer-sections"
  "notes-to-slides-diff"
  "pdf-to-md"
  "proofread"
  "review-paper"
  "skill"
  "tex-exercises-from-notes"
)

skill_urls=(
  "https://github.com/ccantore/jambro-beamer-setup.git"
  "https://github.com/ccantore/lit-review.git"
  "https://github.com/ccantore/notes-to-beamer-sections.git"
  "https://github.com/ccantore/notes-to-slides-diff.git"
  "https://github.com/ccantore/pdf-to-md.git"
  "https://github.com/ccantore/proofread.git"
  "https://github.com/ccantore/review-paper.git"
  "https://github.com/ccantore/skill.git"
  "https://github.com/ccantore/tex-exercises-from-notes.git"
)

cloned=0
updated=0
skipped=0

for i in "${!skill_names[@]}"; do
  name="${skill_names[$i]}"
  url="${skill_urls[$i]}"
  dst="$REPO/$name"

  if [[ -d "$dst/.git" ]]; then
    current_origin="$(git -C "$dst" remote get-url origin 2>/dev/null || true)"
    if [[ "$current_origin" != "$url" ]]; then
      printf 'Skipping %s: origin mismatch (%s)\n' "$name" "${current_origin:-missing}"
      skipped=$((skipped + 1))
      continue
    fi

    if $DO_PULL; then
      git -C "$dst" pull --ff-only
      updated=$((updated + 1))
    fi
    continue
  fi

  if [[ -e "$dst" ]]; then
    printf 'Skipping %s: path exists but is not a git repo\n' "$name"
    skipped=$((skipped + 1))
    continue
  fi

  git clone "$url" "$dst"
  cloned=$((cloned + 1))
done

"$SYNC_SCRIPT"

printf 'Bootstrapped skills: cloned=%d updated=%d skipped=%d\n' "$cloned" "$updated" "$skipped"
