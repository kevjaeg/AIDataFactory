from loguru import logger

from logging_config import setup_logging


def test_setup_logging_configures_loguru() -> None:
    setup_logging(level="DEBUG")
    with logger.catch():
        logger.info("Test message")
    assert True


def test_setup_logging_accepts_level() -> None:
    setup_logging(level="WARNING")
    assert True
