#!/usr/bin/env bash
# Apply the branch-protection ruleset defined in .github/branch-protection-ruleset.json
# to the main branch of Zesseth/BeatForge.
#
# Note: GitHub Free tier does not support branch protection or rulesets on PRIVATE
# repositories. This script will fail with HTTP 403 until the repository is either
# made public OR the account is upgraded to Pro/Team/Enterprise.
#
# Once the repository is public (or the plan is upgraded), run:
#   ./scripts/apply-branch-protection.sh
#
# Requires: gh CLI (logged in with `repo` scope).

set -euo pipefail

REPO="${REPO:-Zesseth/BeatForge}"
RULESET_FILE="$(dirname "$0")/../.github/branch-protection-ruleset.json"

if [ ! -f "$RULESET_FILE" ]; then
  echo "Ruleset file not found: $RULESET_FILE" >&2
  exit 1
fi

# Check if a ruleset with the same name already exists; update if so, otherwise create.
existing_id=$(gh api "repos/$REPO/rulesets" --jq '.[] | select(.name == "Protect main") | .id' 2>/dev/null || true)

if [ -n "$existing_id" ]; then
  echo "Updating existing ruleset $existing_id on $REPO ..."
  gh api -X PUT "repos/$REPO/rulesets/$existing_id" --input "$RULESET_FILE" --jq '"updated id=\(.id) name=\(.name) enforcement=\(.enforcement)"'
else
  echo "Creating new ruleset on $REPO ..."
  gh api -X POST "repos/$REPO/rulesets" --input "$RULESET_FILE" --jq '"created id=\(.id) name=\(.name) enforcement=\(.enforcement)"'
fi

echo "Done. Verify in repo Settings → Rules → Rulesets."
