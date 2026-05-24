"""
Orchestrator calibration constants.

Everything here is a tuning knob for the autonomous feedback loop.
Adjust freely as real generation runs reveal optimal values.
"""

from pathlib import Path

# ── ComfyUI backend ─────────────────────────────────────────────────
COMFYUI_BASE_URL = "http://127.0.0.1:8188"
COMFYUI_POLL_INTERVAL_SEC = 5.0
COMFYUI_TIMEOUT_SEC = 600  # 10 min hard ceiling per generation

# ── generation defaults ─────────────────────────────────────────────
DEFAULT_WIDTH = 832
DEFAULT_HEIGHT = 480
DEFAULT_NUM_FRAMES = 81        # ~3.2s at 25fps (Wan2.1 native rate)
DEFAULT_FPS = 25
DEFAULT_STEPS = 30
DEFAULT_CFG_SCALE = 6.0
DEFAULT_CONTROL_STRENGTH = 1.0
DEFAULT_BATCH_SIZE = 3         # parallel seeds per attempt

# ── retry policy ────────────────────────────────────────────────────
MAX_RETRY_ROUNDS = 4           # total rounds before giving up on a shot
MAX_TOTAL_CANDIDATES = 15      # hard cap across all rounds

# ── self-correction adjustments ─────────────────────────────────────
# optical_flow_spike / optical_flow_unstable → lower CFG
CFG_REDUCTION_ON_FLOW_FAIL = 1.5      # subtract this from current CFG
CFG_FLOOR = 2.0                        # never go below this

# static_or_frozen → raise control strength or flag prompt
CONTROL_STRENGTH_BUMP_ON_STATIC = 0.15
CONTROL_STRENGTH_CEILING = 1.5

# first_last_drift → moderate CFG reduction
CFG_REDUCTION_ON_DRIFT = 0.5

# ── paths ───────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GATE_MODULE_DIR = PROJECT_ROOT            # where `python -m gate` runs
CANDIDATE_DIR = PROJECT_ROOT / "output" / "candidates"
PROMOTED_DIR = PROJECT_ROOT / "output" / "promoted"
MANIFEST_DIR = PROJECT_ROOT / "output" / "manifests"

CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)
PROMOTED_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
