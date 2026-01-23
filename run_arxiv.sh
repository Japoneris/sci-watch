#!/bin/bash
#
# Fetch arXiv papers and run queries.
# Designed to run once daily - arXiv papers don't change after publication.
#
# Crontab example (daily at 8am):
#   0 8 * * * /home/japoneris/Code/Python/NewTeam/sci_watch/run_arxiv.sh >> /home/japoneris/Code/Python/NewTeam/sci_watch/logs/arxiv.log 2>&1
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

mkdir -p "$SCRIPT_DIR/logs"

echo ""
echo "=========================================="
echo "arXiv fetch: $(date)"
echo "=========================================="

source "$SCRIPT_DIR/my_watch_env/bin/activate"

python3 "$SCRIPT_DIR/run_queries.py" --arxiv-only "$@"

EXIT_CODE=$?

echo "Finished: $(date)"
echo "Exit code: $EXIT_CODE"

deactivate

exit $EXIT_CODE
