"""Shared logging setup so every stage logs consistently to console + file."""
import logging
import sys
from pathlib import Path


def get_logger(name: str, month: str, log_dir: str = "logs") -> logging.Logger:
    """Return a logger that writes to logs/pipeline_<month>.log and stdout.

    Reused across stages (ingest/validate/transform/metrics) so a single
    run produces one coherent log file per month, per the assignment's
    "include logging/checks" requirement.
    """
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_path = Path(log_dir) / f"pipeline_{month}.log"

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if get_logger is called multiple times
    if not logger.handlers:
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)-10s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(fmt)
        logger.addHandler(stream_handler)

    return logger


class StageError(Exception):
    """Raised when a pipeline stage fails in a way that should halt the run.

    Caught only at the top level (run_pipeline.py) so that a failure in one
    stage never silently continues into the next with partial data.
    """
