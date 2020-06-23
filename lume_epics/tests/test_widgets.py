import numpy as np
from lume_model.variables import (
    ScalarInputVariable,
    ScalarOutputVariable,
    ImageInputVariable,
    ImageOutputVariable,
)

from lume_epics.client.widgets.tables import ValueTable
from lume_epics.client.widgets.sliders import build_sliders
from lume_epics.client.widgets.plots import ImagePlot, Striptool
from lume_epics.client.controller import Controller


def test_sliders():
    input1 = ScalarInputVariable(name="input1", value=1, range=[0.0, 5.0])
    input2 = ScalarInputVariable(name="input2", value=2, range=[0.0, 5.0])

    inputs = [input1, input2]
    PROTOCOL = "pva"
    PREFIX = "test"

    # create controller
    controller = Controller(PROTOCOL)

    # build sliders for the command process variable database
    sliders = build_sliders(inputs, controller, PREFIX)


def test_value_table():
    output1 = ScalarOutputVariable(name="output1")
    output2 = ScalarOutputVariable(name="output2")

    PROTOCOL = "pva"
    PREFIX = "test"
    # create controller
    controller = Controller(PROTOCOL)

    outputs = [output1, output2]

    value_table = ValueTable(outputs, controller, PREFIX)


def test_image_plot():
    output1 = ImageOutputVariable(
        name="output1",
        value=np.array([[1, 2,], [3, 4]]),
        axis_labels=["count_1", "count_2"],
        x_min=0,
        y_min=0,
        x_max=5,
        y_max=5,
    )

    output2 = ImageOutputVariable(
        name="output2",
        value=np.array([[1, 6,], [4, 1]]),
        axis_labels=["count_1", "count_2"],
        x_min=0,
        y_min=0,
        x_max=5,
        y_max=5,
    )

    PROTOCOL = "pva"
    PREFIX = "test"

    # create controller
    controller = Controller(PROTOCOL)

    outputs = [output1, output2]

    value_table = ImagePlot(outputs, controller, PREFIX)


def test_striptool():
    output1 = ScalarOutputVariable(name="output1")
    output2 = ScalarOutputVariable(name="output2")

    PROTOCOL = "pva"
    PREFIX = "test"
    # create controller
    controller = Controller(PROTOCOL)

    outputs = [output1, output2]

    value_table = Striptool(outputs, controller, PREFIX)
