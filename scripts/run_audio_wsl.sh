#!/usr/bin/env bash
# Reuse the existing WSL CosyVoice installation; never install or download it.
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export COSYVOICE_REPO="${COSYVOICE_REPO:-$HOME/CosyVoice}"
export PATH="$HOME/.local/bin:$PATH"
synth_python="${COSYVOICE_PYTHON:-$COSYVOICE_REPO/.venv/bin/python}"
if [[ ! -x "$synth_python" || ! -f "$COSYVOICE_REPO/pretrained_models/CosyVoice2-0.5B/cosyvoice2.yaml" ]]; then
  echo "Existing CosyVoice2 model/environment not found. Set COSYVOICE_REPO and COSYVOICE_PYTHON." >&2
  exit 1
fi
exec "$synth_python" -u "$repo_root/scripts/synth_audio.py" --require-cuda "$@"
