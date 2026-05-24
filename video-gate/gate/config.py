"""
Calibration thresholds for CandidateQualityReportV1.

Every value here is a tuning knob, not final truth.
Change them freely as real-world samples arrive.
"""

SCHEMA_VERSION = "1.0.0"

# --- technical floor ---
MIN_DURATION_SECONDS = 1.0
MIN_FPS = 8
MAX_FPS = 120
MIN_FRAME_COUNT = 4
REQUIRED_CODECS = None  # None = accept anything ffprobe reports

# --- static / frozen detection ---
# Mean SSIM across sampled pairs; above this → "frozen"
STATIC_SSIM_THRESHOLD = 0.985
# Minimum number of evenly-spaced frames to sample for the check
STATIC_SAMPLE_COUNT = 6

# --- optical flow stability ---
# Farneback flow magnitude: mean above this triggers a warning
FLOW_WARN_MEAN_MAGNITUDE = 8.0
# …and above this triggers a rejection
FLOW_REJECT_MEAN_MAGNITUDE = 20.0
# Fraction of sampled pairs that must stay under the warn line
FLOW_STABLE_RATIO = 0.70

# --- first / last frame similarity ---
# SSIM below this warns about major visual drift
FIRST_LAST_WARN_SSIM = 0.30
# SSIM below this rejects outright
FIRST_LAST_REJECT_SSIM = 0.10
