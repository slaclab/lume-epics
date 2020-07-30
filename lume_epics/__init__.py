import os

os.environ["EPICS_CA_MAX_ARRAY_BYTES"] = "1000000"

from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions