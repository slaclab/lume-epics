import logging
import pytest
import sys
import p4p
import os
import time
import subprocess
import signal
from epicscorelibs.path import get_lib
from os.path import abspath, dirname

from lume_epics.tests.launch_server import TestModel
from lume_epics.client.controller import Controller

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

package_path = abspath(dirname(dirname(__file__)))
sys.path.insert(0, package_path)

PVA_CONFIG = {
    "EPICS_PVAS_AUTO_BEACON_ADDR_LIST": "NO",
    "EPICS_PVAS_BEACON_ADDR_LIST": "127.0.0.1",
    "EPICS_PVAS_BEACON_PERIOD": "15",
    "EPICS_PVAS_BROADCAST_PORT": "60858",
    "EPICS_PVAS_INTF_ADDR_LIST": "127.0.0.1:0",
    "EPICS_PVAS_MAX_ARRAY_BYTES": "16384",
    "EPICS_PVAS_PROVIDER_NAMES": "3a7aff4f-8fd4-4f9f-b696-bd9f5f6f13ed",
    "EPICS_PVAS_SERVER_PORT": "61192",
    "EPICS_PVA_ADDR_LIST": "127.0.0.1",
    "EPICS_PVA_AUTO_ADDR_LIST": "NO",
    "EPICS_PVA_BEACON_PERIOD": "15",
    "EPICS_PVA_BROADCAST_PORT": "60858",
    "EPICS_PVA_MAX_ARRAY_BYTES": "16384",
    "EPICS_PVA_SERVER_PORT": "61192",
}
os.environ.update(PVA_CONFIG)

os.environ["PYEPICS_LIBCA"] = get_lib("ca")


@pytest.fixture(scope="session", autouse=True)
def rootdir():
    package_path = abspath(dirname(dirname(dirname(__file__))))
    return package_path


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
def server():
    """
    Initialize server and setup teardown
    """
    env = os.environ.copy()

    # add root dir to pythonpath in order to run test
    env["PYTHONPATH"] = env.get("PYTHONPATH", "") + f":{rootdir}"

    ca_proc = subprocess.Popen(
        [sys.executable, "launch_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(os.path.realpath(__file__)),
        env=env,
    )

    time.sleep(2)

    # Check it started successfully
    assert not ca_proc.poll()

    # yield ca_proc
    yield ca_proc

    # teardown
    ca_proc.send_signal(signal.SIGINT)


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
def ca_controller(prefix, protocol, model):
    controller = Controller(
        protocol, model.input_variables, model.output_variables, prefix
    )

    yield controller

    # teardown
    controller.close()
