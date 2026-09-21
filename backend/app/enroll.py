"""Enroll faces from dataset into the database.
Usage: python -m app.enroll
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
    from app.services.enrollment import enroll_all
    from app.config import settings

    logger.info("Initializing database...")
    init_db()

    logger.info("Starting enrollment from: %s", settings.DATASET_DIR)
    summary = enroll_all(settings.DATASET_DIR)

    if not summary:
        logger.error("No enrollment data. Check your DATASET_DIR and image files.")
        return

    print("\n" + "=" * 50)
    print("ENROLLMENT SUMMARY")
    print("=" * 50)
    print(f"{'Person':<15} {'Images':>8} {'Used':>8} {'Skipped':>8}")
    print("-" * 50)
    total_used = 0
    total_skipped = 0
    for name, stats in summary.items():
        if name.startswith("__"):
            continue
        used = stats.get("used", 0)
        skipped = stats.get("skipped", 0)
        already = stats.get("already_enrolled", 0)
        total = stats.get("images", 0)
        total_used += used
        total_skipped += skipped
        if already > 0:
            print(f"{name:<15} {total:>8} {'(already':>8} {already:>8})")
        else:
            print(f"{name:<15} {total:>8} {used:>8} {skipped:>8}")

    print("-" * 50)
    print(f"{'TOTAL':<15} {'':>8} {total_used:>8} {total_skipped:>8}")
    print("=" * 50)

    if total_used > 0:
        logger.info("Now run calibration: python -m app.calibrate")
    elif total_skipped > 0:
        logger.warning("All images were skipped. Check logs above for reasons.")


if __name__ == "__main__":
    main()
