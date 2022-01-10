import pytest
import epics
from lume_model.variables import ScalarInputVariable

from lume_epics.client.widgets.controls import build_sliders
from lume_epics.client.controller import Controller


@pytest.fixture(scope="module")
def slider_variables(model):
    return [
        var for var in model.input_variables.values() if var.variable_type == "constant"
    ]


@pytest.fixture(scope="module")
def sliders(controller, slider_variables):
    # build sliders for the command process variable database
    return build_sliders(slider_variables, controller)


@pytest.mark.parametrize("value", [(4), (-8)])
def test_slider_update(value, slider_variables, sliders, epics_config):

    for var in slider_variables:
        pvname = epics_config[var.name]["pvname"]
        epics.caput(pvname, value)

    for slider in sliders:
        slider.update()
        assert value == slider.bokeh_slider.value


@pytest.mark.parametrize("value", [(4), (-8)])
def test_slider_set(value, slider_variables, sliders, epics_config):

    for slider in sliders:
        slider.bokeh_slider.value = value

    for var in slider_variables:
        pvname = epics_config[var.name]["pvname"]
        val = epics.caget(pvname)
        assert val == value
