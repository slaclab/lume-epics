from lume_model.variables import ScalarOutputVariable

from lume_epics.client.widgets.plots import Striptool
from lume_epics.client.controller import Controller
from lume_epics import epics_server


def test_striptool_pva():
    PROTOCOL = "pva"
    PREFIX = "test"

    output1 = ScalarOutputVariable(name="output1")
    output2 = ScalarOutputVariable(name="output2")

    # create controller
    controller = Controller(PROTOCOL)

    outputs = [output1, output2]

    striptool = Striptool(outputs, controller, PREFIX)
    striptool.build_plot()

    controller.close()


def test_reset_button():
    PROTOCOL = "pva"
    PREFIX = "test"

    output1 = ScalarOutputVariable(name="output1")
    output2 = ScalarOutputVariable(name="output2")

    # create controller
    controller = Controller(PROTOCOL)

    outputs = [output1, output2]

    striptool = Striptool(outputs, controller, PREFIX)
    striptool.build_plot()

    striptool._reset_values()

    controller.close()
