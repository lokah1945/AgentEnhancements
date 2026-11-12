#!/usr/bin/env bash
# Consent gate for sensitive operations (voice cloning, personalized video,
# custom avatar generation). REQUIRED before invoking hyperframes voice clone,
# elevenlabs clone, or heygen custom avatar (UU PDP pasal 22-23, GDPR Art 9).
#
# Usage:
#   bash consent-gate.sh "<purpose>" "<sample_path_or_id>" "<approver_user>"
# Exit codes:
#   0 = approved, 1 = refused, 2 = invalid args
# Audit log: unified-integration/memory/audit/consent.jsonl

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIFIED_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$UNIFIED_DIR/memory/audit/consent.jsonl"

log_info()  { echo -e "\033[0;34m[consent]\033[0m $1"; }

mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"

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
echo "Purpose    : $purpose"
echo "Sample/Ref : $sample"
echo "Sample SHA : ${sample_hash:0:16}..."
echo "Approver   : $approver"
echo "Timestamp  : $ts"
echo "-----------------------------------------------"
echo "Operasi ini akan melakukan:"
echo "  - Voice cloning / personalized video generation"
echo "  - Data diproses oleh third-party (HeyGen / ElevenLabs)"
echo "  - Audit trail disimpan (UU PDP pasal 22-23, GDPR Art 9)"
echo ""
read -r -p "Setujui? (y/n): " confirm

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

echo "$entry" >> "$LOG_FILE"

exit $exit_code
