import os

os.environ["EPICS_CA_MAX_ARRAY_BYTES"] = "1000000"

from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions

# EPICS variables
# channel access
CA_VARS = [
    "EPICS_CA_ADDR_LIST",
    "EPICS_CA_AUTO_ADDR_LIST",
    "EPICS_CA_CONN_TMO",
    "EPICS_CA_BEACON_PERIOD",
    "EPICS_CA_REPEATER_PORT",
    "EPICS_CA_SERVER_PORT",
    "EPICS_CA_MAX_ARRAY_BYTES",
]

# Check this
EPICS_BASE_VARS = ["EPICS_TS_MIN_WEST"]

# pvAccess variables
PVA_VARS = [
    "EPICS_PVA_ADDR_LIST",
    "EPICS_PVA_AUTO_ADDR_LIST",
    "EPICS_PVA_CONN_TMO",
    "EPICS_PVA_BEACON_PERIOD",
    "EPICS_PVA_SERVER_PORT",
]

EPICS_ENV_VARS = CA_VARS + EPICS_BASE_VARS + PVA_VARS
