import logging
import pytest

def clear_loggers():
    """
    Remove handlers from all loggers
    """
    import logging
    loggers = [logging.getLogger()] + list(logging.Logger.manager.loggerDict.values())
    for logger in loggers:
        handlers = getattr(logger, 'handlers', [])
        for handler in handlers:
            logger.removeHandler(handler)


@pytest.fixture(scope="session", autouse=True)
def tear_down():
    """
    Appropriately close down testing session.

    Note
    ----
    Running with out teardown leads to problems with p4p atexit handling
    """
    clear_loggers()