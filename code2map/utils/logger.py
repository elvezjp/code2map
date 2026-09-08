import logging


def setup_logger(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(name)
