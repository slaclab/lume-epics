WIDGET_LIST = ["striptool", "image", "table", "slider"]

from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions


from lume_model.variables import (
    ScalarInputVariable,
    ScalarOutputVariable,
    ImageInputVariable,
    ImageOutputVariable,
)

INPUT_VARIABLE_TYPES = (
    ScalarInputVariable,
    ImageInputVariable,
)
OUTPUT_VARIABLE_TYPES = (
    ScalarOutputVariable,
    ImageOutputVariable,
)

IMAGE_VARIABLE_TYPES = (
    ImageInputVariable,
    ImageOutputVariable,
)

SCALAR_VARIABLE_TYPES = (
    ScalarInputVariable,
    ScalarOutputVariable,
)
