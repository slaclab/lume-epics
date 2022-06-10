import logging
import pytest
import sys
import os
import subprocess
import signal
from epicscorelibs.path import get_lib
from os.path import abspath, dirname
import time

from lume_epics.client.controller import Controller
from lume_epics.tests.launch_server import TestModel
from lume_epics.utils import config_from_yaml


logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

package_path = abspath(dirname(dirname(__file__)))
sys.path.insert(0, package_path)

PVA_CONFIG = {
    "EPICS_PVA_ADDR_LIST": "127.0.0.1",
    "EPICS_PVA_AUTO_ADDR_LIST": "NO",
    "EPICS_PVA_BROADCAST_PORT": "60858",
}
os.environ.update(PVA_CONFIG)

os.environ["PYEPICS_LIBCA"] = get_lib("ca")


@pytest.fixture(scope="session", autouse=True)
def rootdir():
    return os.path.dirname(os.path.abspath(__file__))


def clear_loggers():
    """
    Remove handlers from all loggers
    """
    import logging

    loggers = [logging.getLogger()] + list(logging.Logger.manager.loggerDict.values())
    for logger in loggers:
        handlers = getattr(logger, "handlers", [])
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


@pytest.fixture(scope="session", autouse=True)
def epics_config(rootdir):
    with open(f"{rootdir}/files/epics_config.yml", "r") as f:
        epics_config = config_from_yaml(f)

    yield epics_config


@pytest.fixture(scope="session", autouse=True)
def epics_config_struct(rootdir):
    with open(f"{rootdir}/files/epics_config_struct.yml", "r") as f:
        epics_config = config_from_yaml(f)

    yield epics_config


@pytest.fixture(scope="session", autouse=True)
def server():
    #
    # Initialize server and setup teardown
    #
    env = os.environ.copy()

    # add root dir to pythonpath in order to run test
    env["PYTHONPATH"] = env.get("PYTHONPATH", "") + f":{rootdir}"

    logger.info(sys.executable)

    ca_proc = subprocess.Popen(
        [sys.executable, "launch_server.py", "files/epics_config.yml"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        cwd=os.path.dirname(os.path.realpath(__file__)),
        env=env,
    )

    # Check it started successfully
    #    assert not ca_proc.poll()

    # yield ca_proc
    yield ca_proc

    # teardown
    ca_proc.send_signal(signal.SIGINT)
    time.sleep(1)


@pytest.fixture(scope="session", autouse=True)
def model():
    yield TestModel


@pytest.fixture(scope="session", autouse=True)
def prefix():
    yield "test"


@pytest.fixture(scope="session", autouse=True)
def protocol():
    yield "ca"


@pytest.fixture(scope="session", autouse=True)
def controller(epics_config):
    controller = Controller(epics_config)

    yield controller

    # teardown
    controller.close()
