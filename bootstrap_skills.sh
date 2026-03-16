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
    '  Clone missing nested skill repos, including external sparse-checkout skills.' \
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

external_skill_names=(
  "pdf-reading"
)

external_skill_urls=(
  "https://github.com/aniketpanjwani/skills.git"
)

external_skill_paths=(
  "skills/general/pdf-reading"
)

cloned=0
updated=0
skipped=0
external_cloned=0
external_updated=0

link_external_skill_entrypoints() {
  local name="$1"
  local dst="$REPO/$name"
  local skill_path="$2"
  local target_dir="$dst/$skill_path"
  local entry
  local exclude_file="$dst/.git/info/exclude"

  if [[ ! -d "$target_dir" ]]; then
    printf 'Skipping %s: missing checked out path %s\n' "$name" "$skill_path"
    skipped=$((skipped + 1))
    return
  fi

  for entry in SKILL.md agents scripts; do
    if [[ -e "$dst/$entry" || -L "$dst/$entry" ]]; then
      rm -rf "$dst/$entry"
    fi
    if [[ -e "$target_dir/$entry" || -L "$target_dir/$entry" ]]; then
      ln -s "$skill_path/$entry" "$dst/$entry"
      if [[ -f "$exclude_file" ]] && ! grep -Fqx "/$entry" "$exclude_file"; then
        printf '/%s\n' "$entry" >> "$exclude_file"
      fi
    fi
  done
}

bootstrap_external_skill() {
  local name="$1"
  local repo_url="$2"
  local skill_path="$3"
  local dst="$REPO/$name"

  if [[ -d "$dst/.git" ]]; then
    current_origin="$(git -C "$dst" remote get-url origin 2>/dev/null || true)"
    if [[ "$current_origin" != "$repo_url" ]]; then
      printf 'Skipping %s: origin mismatch (%s)\n' "$name" "${current_origin:-missing}"
      skipped=$((skipped + 1))
      return
    fi

    git -C "$dst" sparse-checkout set --no-cone "$skill_path"
    if $DO_PULL; then
      git -C "$dst" pull --ff-only
      external_updated=$((external_updated + 1))
    fi
    link_external_skill_entrypoints "$name" "$skill_path"
    return
  fi

  if [[ -e "$dst" ]]; then
    rm -rf "$dst"
  fi

  git clone --filter=blob:none --sparse "$repo_url" "$dst"
  git -C "$dst" sparse-checkout set --no-cone "$skill_path"
  link_external_skill_entrypoints "$name" "$skill_path"
  external_cloned=$((external_cloned + 1))
}

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

for i in "${!external_skill_names[@]}"; do
  bootstrap_external_skill \
    "${external_skill_names[$i]}" \
    "${external_skill_urls[$i]}" \
    "${external_skill_paths[$i]}"
done

"$SYNC_SCRIPT"

printf 'Bootstrapped skills: cloned=%d updated=%d external_cloned=%d external_updated=%d skipped=%d\n' \
  "$cloned" "$updated" "$external_cloned" "$external_updated" "$skipped"
