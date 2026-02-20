import logging
import sys
from datetime import datetime

from scraper.config import validate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def main():
    task = sys.argv[1] if len(sys.argv) > 1 else "sync"

    validate()
    log.info(f"Starting task: {task} at {datetime.now()}")

    if task == "sync":
        from tasks.daily_sync import run
    elif task == "fix-covers":
        from tasks.fix_covers import run
    elif task == "repair-youtube":
        from tasks.repair_youtube import run
    else:
        print(f"Unknown task: {task}")
        print("Usage: python main.py [sync|fix-covers|repair-youtube]")
        sys.exit(1)

    run()
    log.info("Task complete.")


if __name__ == "__main__":
    main()
