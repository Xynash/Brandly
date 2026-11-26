import logging


def setup_logging() -> None:
    """Readable logs on the console. Request bodies and headers are never logged."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
