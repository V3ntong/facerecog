"""Calibrate recognition threshold using leave-one-out test.
Usage: python -m app.calibrate
"""
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    from app.database import init_db
    from app.services.recognition import load_embeddings, calibrate_threshold
    from app.config import settings

    init_db()
    load_embeddings()

    logger.info("Running leave-one-out calibration...")
    best_threshold, report = calibrate_threshold()

    print("\n" + "=" * 50)
    print("CALIBRATION REPORT")
    print("=" * 50)
    print(f"Total embeddings: {report['total_embeddings']}")
    print(f"Best threshold:   {report['best_threshold']}")
    print(f"Best accuracy:    {report['best_accuracy'] * 100:.1f}%")
    print()

    # Show key thresholds
    thresholds = report.get("thresholds", {})
    print(f"{'Threshold':>10} {'Accuracy':>10} {'Correct':>10} {'FP':>6} {'Unknowns':>10}")
    print("-" * 50)
    for t in sorted(thresholds.keys()):
        if t % 0.05 < 0.01 or t == report["best_threshold"]:
            stats = thresholds[t]
            marker = " <-- best" if t == report["best_threshold"] else ""
            print(
                f"{t:>10.2f} {stats['accuracy']*100:>9.1f}% "
                f"{stats['correct']:>10} {stats['false_positives']:>6} "
                f"{stats['unknowns']:>10}{marker}"
            )

    print("=" * 50)
    print(f"\nUpdate RECOGNITION_THRESHOLD in .env to {report['best_threshold']}")


if __name__ == "__main__":
    main()
