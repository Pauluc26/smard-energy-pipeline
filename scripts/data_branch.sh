#!/usr/bin/env bash
# Sync the pipeline data with the `data` branch.
#
#   scripts/data_branch.sh pull   # download data/raw and data/marts from the branch
#   scripts/data_branch.sh push   # replace the branch with the local data (one commit)
#
# Why a separate branch: the current month's Parquet files change every day. Committing
# them to `main` would add ~1 MB of history per day. The `data` branch always holds
# exactly one commit that is force-pushed, so the repository does not grow.
#
# Neither command touches the working tree's index or the checked-out branch.
set -euo pipefail

BRANCH=data
REMOTE=${REMOTE:-origin}
PATHS=(data/raw data/marts)

cd "$(git rev-parse --show-toplevel)"

pull() {
    if ! git ls-remote --exit-code --heads "$REMOTE" "$BRANCH" >/dev/null; then
        echo "No '$BRANCH' branch on $REMOTE yet: starting without data (update will backfill)."
        return 0
    fi
    git fetch --quiet --depth 1 "$REMOTE" "$BRANCH"
    rm -rf "${PATHS[@]}"
    # extract the files without checking the branch out
    git archive FETCH_HEAD | tar -x -C .
    echo "Pulled $(find data/raw -name '*.parquet' | wc -l | tr -d ' ') raw files from $REMOTE/$BRANCH."
}

push() {
    for path in "${PATHS[@]}"; do
        [ -d "$path" ] || { echo "Missing $path, nothing pushed." >&2; exit 1; }
    done
    # build a commit from a temporary index, so the real index stays untouched
    local index
    index=$(mktemp -u)
    GIT_INDEX_FILE="$index" git add --force "${PATHS[@]}"
    local tree commit
    tree=$(GIT_INDEX_FILE="$index" git write-tree)
    rm -f "$index"
    commit=$(git commit-tree "$tree" -m "Data as of $(date -u +%Y-%m-%dT%H:%MZ)")
    git push --quiet --force "$REMOTE" "$commit:refs/heads/$BRANCH"
    echo "Pushed $commit to $REMOTE/$BRANCH."
}

case "${1:-}" in
    pull) pull ;;
    push) push ;;
    *) echo "usage: $0 pull|push" >&2; exit 2 ;;
esac
