import pytest

from lume_model.variables import ScalarOutputVariable

from lume_epics.client.widgets.plots import Striptool
from lume_epics.client.controller import Controller
from lume_epics import epics_server


@pytest.fixture(scope="module")
def striptool(ca_controller, prefix, model):

    output_variables = [
        var
        for var in model.output_variables.values()
        if not var.variable_type == "image"
    ]

    return Striptool(output_variables, ca_controller, prefix)


def test_reset_button(striptool, server):
    striptool.update()
    striptool.update()

    initial_val = striptool.source.data["y"]

    striptool._reset_values()
    striptool.update()

    after_reset = striptool.source.data["y"]

    assert len(initial_val) != len(after_reset)
