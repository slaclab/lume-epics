from lume_model.variables import ScalarInputVariable

from lume_epics.client.widgets.controls import build_sliders
from lume_epics.client.controller import Controller


def test_sliders_pva():
    PREFIX = "test"

    input_variables = {
        "input1": ScalarInputVariable(name="input1", value=1, default=1, range=[0.0, 5.0]),
        "input2": ScalarInputVariable(name="input2", value=2, default=2, range=[0.0, 5.0]),
    }

    inputs = list(input_variables.values())

    # create controller
    controller = Controller("pva")

    # build sliders for the command process variable database
    sliders = build_sliders(inputs, controller, PREFIX)

    controller.close()
