from lume_model.variables import ScalarInputVariable

from lume_epics.client.widgets.controls import build_sliders
from lume_epics.client.controller import Controller


def sliders(prefix, controller, model):
    prefix = "test"

    slider_inputs = [var for var in model.input_variables.values() if var.variable_type == "scalar"]


    inputs = list(model.input_variables.values())

    # create controller
    controller = Controller("pva", [f"{prefix}:{pv}" for pv in model.input_variables], [])

    # build sliders for the command process variable database
    sliders = build_sliders(inputs, controller, prefix)

    controller.close()