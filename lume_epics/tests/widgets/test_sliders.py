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
def sliders(prefix, ca_controller, slider_variables):
    # build sliders for the command process variable database
    return build_sliders(slider_variables, ca_controller, prefix)


@pytest.mark.parametrize("value", [(4), (-8)])
def test_slider_update(value, slider_variables, prefix, sliders):

    for var in slider_variables:
        epics.caput(f"{prefix}:{var.name}", value)

    for slider in sliders:
        slider.update()
        assert value == slider.bokeh_slider.value


@pytest.mark.parametrize("value", [(4), (-8)])
def test_slider_set(value, slider_variables, prefix, sliders):

    for slider in sliders:
        slider.bokeh_slider.value = value

    for var in slider_variables:
        val = epics.caget(f"{prefix}:{var.name}")
        assert val == value
