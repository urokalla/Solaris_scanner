#!/usr/bin/env bash
# Push this repo (full history on current branch) to a new empty GitHub/GitLab repo.
#
# 1. Create an EMPTY repo on GitHub/GitLab (no README, no .gitignore).
# 2. Run:
#    export NEW_REMOTE_URL='https://github.com/YOU/new-repo.git'
#    ./scripts/push_to_new_remote.sh
#
# Optional: name the remote (default: copy)
#    REMOTE_NAME=backup ./scripts/push_to_new_remote.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -z "${NEW_REMOTE_URL:-}" ]]; then
  echo "Set NEW_REMOTE_URL to the new repo HTTPS or SSH URL, e.g."
  echo "  export NEW_REMOTE_URL='https://github.com/you/new-repo.git'"
  echo "  $0"
  exit 1
fi

NAME="${REMOTE_NAME:-copy}"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"

if git remote get-url "$NAME" &>/dev/null; then
  echo "Remote '$NAME' already exists; updating URL."
  git remote set-url "$NAME" "$NEW_REMOTE_URL"
else
  git remote add "$NAME" "$NEW_REMOTE_URL"
fi

echo "Pushing branch '$BRANCH' to '$NAME' ..."
# New repos often use 'main'; map local branch to main on first push.
if git ls-remote --heads "$NAME" main 2>/dev/null | grep -q main; then
  git push -u "$NAME" "$BRANCH:main"
elif git ls-remote --heads "$NAME" master 2>/dev/null | grep -q master; then
  git push -u "$NAME" "$BRANCH:master"
else
  git push -u "$NAME" "$BRANCH:main"
fi

echo "Done. Remotes:"
git remote -v
