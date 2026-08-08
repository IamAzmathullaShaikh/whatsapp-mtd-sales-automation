#!/usr/bin/env bash
# update.sh — refresh the upstream skills repos this skill set was learned from,
# record their current state in upstream-manifest.md, and report what changed.
# Shallow clones live in .agents/skills/.upstream/ (gitignored).
set -euo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$(cd "$SELF_DIR/.." && pwd)"
UPSTREAM_DIR="$SKILLS_DIR/.upstream"
MANIFEST="$SKILLS_DIR/upstream-manifest.md"

REPOS=(
  "anthropics/skills"
  "obra/superpowers"
  "mattpocock/skills"
  "google/skills"
  "vercel-labs/skills"
  "emilkowalski/skills"
  "MiniMax-AI/skills"
  "slavingia/skills"
  "MengTo/Skills"
  "multica-ai/andrej-karpathy-skills"
  "VoltAgent/awesome-openclaw-skills"
)

mkdir -p "$UPSTREAM_DIR"

# Read previous SHAs from the existing manifest.
declare -A PREV
if [[ -f "$MANIFEST" ]]; then
  while IFS='|' read -r _ repo sha rest; do
    repo="${repo// /}";  sha="${sha// /}"
    sha="${sha//\`/}"    # strip markdown backticks if present
    [[ -n "$repo" && "$repo" != "Repo" ]] && PREV["$repo"]="$sha"
  done < "$MANIFEST"
fi

NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "=== Upstream drift report ($NOW) ==="
CHANGED=0
{
  echo "# Upstream Skills Manifest"
  echo
  echo "Refresh date: $NOW"
  echo
  echo "| Repo | Commit | Skills | Status |"
  echo "|---|---|---|---|"
} > "$MANIFEST"

for repo in "${REPOS[@]}"; do
  dir="$UPSTREAM_DIR/${repo//\//_}"
  if [[ ! -d "$dir/.git" ]]; then
    git clone --depth 1 -q "https://github.com/$repo.git" "$dir" >/dev/null 2>&1 \
      || { echo "  !! failed to clone $repo"; continue; }
  else
    git -C "$dir" fetch -q --depth 1 origin >/dev/null 2>&1 || true
    git -C "$dir" reset -q --hard FETCH_HEAD >/dev/null 2>&1 \
      || git -C "$dir" reset -q --hard origin/main >/dev/null 2>&1 \
      || true
  fi
  sha="$(git -C "$dir" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  n="$(find "$dir" -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')"

  if [[ -n "${PREV[$repo]:-}" && "${PREV[$repo]}" != "$sha" ]]; then
    echo "  UP  $repo: ${PREV[$repo]} -> $sha ($n skills)"
    status="CHANGED (${PREV[$repo]} → $sha)"
    CHANGED=$((CHANGED + 1))
  elif [[ -z "${PREV[$repo]:-}" ]]; then
    echo "  +   $repo @ $sha ($n skills)"
    status="new"
  else
    echo "  =   $repo @ $sha ($n skills)"
    status="unchanged"
  fi
  echo "| $repo | $sha | $n | $status |" >> "$MANIFEST"
done

echo
if [[ $CHANGED -eq 0 ]]; then
  echo "No upstream repos moved since the last refresh."
else
  echo "$CHANGED upstream repo(s) moved — review the changes and update the"
  echo "skills that drew from them (see writing-skills), bumping versions."
fi
echo "Manifest written: $MANIFEST"
