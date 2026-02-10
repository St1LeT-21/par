from __future__ import annotations

import asyncio
import logging
import sys

from .core.scheduler import run_forever


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    setup_logging()
    try:
        asyncio.run(run_forever())
    except KeyboardInterrupt:
        logging.info("Shutting down (KeyboardInterrupt)")
        sys.exit(0)


if __name__ == "__main__":
    main()
