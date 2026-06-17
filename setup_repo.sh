#!/usr/bin/env bash
# WHAT: creates the public GitHub repository for ATELIER and pushes the
#       deployed scaffold as the first commit.
# WHY:  reuses the existing mgalanme account and gh authentication already
#       configured on this machine, consistent with previous case studies.
# HOW:  run from inside /home/pruebas/formacion/atelier, after deploy.sh.
set -euo pipefail

REPO_OWNER="mgalanme"
REPO_NAME="atelier"

if ! gh auth status >/dev/null 2>&1; then
  echo "gh is not authenticated. Run 'gh auth login' first, then re-run this script."
  exit 1
fi

if [ ! -d .git ]; then
  git init
  git branch -M main
fi

gh repo create "${REPO_OWNER}/${REPO_NAME}" \
  --public \
  --description "ATELIER: conversational AI platform for the fashion industry (bootcamp case study)" \
  --source=. \
  --remote=origin

git add .
git commit -m "Initial commit: ATELIER demo scaffold" || echo "Nothing to commit"
git pull --rebase origin main || true
git push -u origin main

echo "Repository ready at https://github.com/${REPO_OWNER}/${REPO_NAME}"
