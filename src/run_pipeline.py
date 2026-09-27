"""
Class 8 — Dependable pipeline.

Orchestrates: ingest -> validate -> transform -> metrics.

Design choices (the "dependability" story for the demo):
  - Each stage is its own module/function with its own inputs/outputs on
    disk, so any stage can be re-run independently for debugging.
  - Idempotent reruns: ingest skips re-downloading if the raw file already
    exists (unless --force-download); every other stage simply overwrites
    its own deterministic output file, so re-running the whole pipeline
    twice produces the same result, not duplicated/appended data.
  - Failure handling: a StageError in any stage stops the run immediately
    (non-zero exit) and does NOT proceed to later stages with partial or
    missing upstream data. Whatever the previous stage already wrote stays
    on disk untouched — a failed run never corrupts prior good output.
  - A single run-level log records which stages ran, in what order, with
    what timing, independent of each stage's own detailed log lines.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))  # allow `import ingest` etc.

import ingest
import validate
import transform
import metrics
from utils.logging_utils import get_logger, StageError


STAGES = [
    ("ingest", lambda month, force: ingest.run(month, force=force)),
    ("validate", lambda month, force: validate.run(month)),
    ("transform", lambda month, force: transform.run(month)),
    ("metrics", lambda month, force: metrics.run(month)),
]


def main():
    parser = argparse.ArgumentParser(description="Run the NYC taxi metrics pipeline")
    parser.add_argument("--month", required=True, help="YYYY-MM, e.g. 2024-01")
    parser.add_argument(
        "--force-download", action="store_true",
        help="Re-download raw files even if already present",
    )
    parser.add_argument(
        "--only", choices=[s[0] for s in STAGES], default=None,
        help="Run a single stage instead of the full pipeline (for debugging)",
    )
    args = parser.parse_args()

    logger = get_logger("pipeline", args.month)
    logger.info(f"########## PIPELINE RUN: month={args.month} ##########")

    stages_to_run = [s for s in STAGES if args.only in (None, s[0])]

    for name, fn in stages_to_run:
        start = time.time()
        logger.info(f"--- Stage '{name}' starting ---")
        try:
            fn(args.month, args.force_download)
        except StageError as e:
            logger.error(f"Stage '{name}' FAILED: {e}")
            logger.error(
                "Pipeline halted. Upstream outputs from prior successful "
                "stages are left untouched on disk."
            )
            sys.exit(1)
        except Exception as e:  # noqa: BLE001 — catch-all is intentional here
            logger.error(f"Stage '{name}' raised an unexpected error: {e!r}")
            logger.error("Pipeline halted (unexpected error, not a StageError).")
            sys.exit(2)
        elapsed = time.time() - start
        logger.info(f"--- Stage '{name}' finished in {elapsed:.1f}s ---")

    logger.info("########## PIPELINE RUN complete ##########")


if __name__ == "__main__":
    main()
