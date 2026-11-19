#!/usr/bin/env bash
# Consent gate for sensitive operations (voice cloning, personalized video,
# custom avatar generation). AE policy requires explicit approval before
# voice cloning/custom avatars; external callers must check the exit status.
#
# Usage:
#   bash consent-gate.sh "<purpose>" "<sample_path_or_id>" "<approver_user>"
# Exit codes:
#   0 = approved, 1 = refused, 2 = invalid args
# Audit log: unified-integration/memory/audit/consent.jsonl

set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIFIED_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$UNIFIED_DIR/memory/audit/consent.jsonl"

log_info()  { echo -e "\033[0;34m[consent]\033[0m $1"; }

if [ -L "$UNIFIED_DIR/memory" ] || [ -L "$(dirname "$LOG_FILE")" ] || [ -L "$LOG_FILE" ]; then
    echo "Refusing symlinked consent storage" >&2
    exit 1
fi
mkdir -p "$(dirname "$LOG_FILE")"
chmod 700 "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"
chmod 600 "$LOG_FILE"

purpose="${1:-}"
sample="${2:-}"
approver="${3:-user}"

if [ -z "$purpose" ] || [ -z "$sample" ]; then
    echo "Usage: $0 <purpose> <sample_path_or_id> [approver_user]"
    exit 2
fi

# Sample hash untuk audit trail (evidence bila ada dispute)
sample_hash="null"
if [ -f "$sample" ]; then
    sample_hash=$(sha256sum "$sample" | awk '{print $1}')
fi

ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "==============================================="
echo "CONSENT GATE - Operasi Sensitif"
echo "==============================================="
printf 'Purpose    : %s\nSample/Ref : %s\nApprover   : %s\n' "$purpose" "$sample" "$approver" |
    python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); from api_config import redact; print(redact(sys.stdin.read()), end="")' "$SCRIPT_DIR"
echo "Sample SHA : ${sample_hash:0:16}..."
echo "Timestamp  : $ts"
echo "-----------------------------------------------"
echo "Operasi ini akan melakukan:"
echo "  - Voice cloning / personalized video generation"
echo "  - Data diproses oleh third-party (HeyGen / ElevenLabs)"
echo "  - Audit trail disimpan; persetujuan dan retensi mengikuti kebijakan operator"
echo ""
# EOF (non-interactive / CI) is treated as a refusal, not a crash,
# so the decision still lands in the audit log.
if ! read -r -p "Setujui? (y/n): " confirm; then
    confirm=""
    echo ""
    log_info "Input tidak tersedia (non-interactive) - dianggap refused."
fi

if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    decision="approved"
    exit_code=0
    log_info "Approved. Log disimpan ke $LOG_FILE"
else
    decision="refused"
    exit_code=1
    log_info "Refused. Log disimpan ke $LOG_FILE"
fi

entry=$(jq -c -n \
  --arg ts "$ts" \
  --arg purpose "$purpose" \
  --arg sample "$sample" \
  --arg hash "$sample_hash" \
  --arg approver "$approver" \
  --arg decision "$decision" \
  '{timestamp: $ts, purpose: $purpose, sample_ref: $sample, sample_sha256: $hash, approver: $approver, decision: $decision}')

entry=$(python3 -c '
import json, sys
sys.path.insert(0, sys.argv[1])
from api_config import redact
entry = json.load(sys.stdin)
print(json.dumps({key: redact(value) if isinstance(value, str) else value for key, value in entry.items()}, ensure_ascii=False))
' "$SCRIPT_DIR" <<< "$entry")

echo "$entry" >> "$LOG_FILE"

exit $exit_code
