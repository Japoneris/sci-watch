#!/bin/bash
#
# Fetch HackerNews front page and run queries.
# Designed to run hourly - HN front page is volatile.
#
# Crontab example (every hour):
#   0 * * * * /home/japoneris/Code/Python/NewTeam/sci_watch/run_hn.sh >> /home/japoneris/Code/Python/NewTeam/sci_watch/logs/hn.log 2>&1
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

mkdir -p "$SCRIPT_DIR/logs"

echo ""
echo "=========================================="
echo "HackerNews fetch: $(date)"
echo "=========================================="

source "$SCRIPT_DIR/my_watch_env/bin/activate"

python3 "$SCRIPT_DIR/run_queries.py" --hn-only "$@"

EXIT_CODE=$?

echo "Finished: $(date)"
echo "Exit code: $EXIT_CODE"

deactivate

exit $EXIT_CODE
