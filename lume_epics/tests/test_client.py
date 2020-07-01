import numpy as np
from lume_model.variables import (
    ScalarInputVariable,
    ScalarOutputVariable,
    ImageInputVariable,
    ImageOutputVariable,
)
from lume_epics.client.controller import Controller
from lume_epics import epics_server
from lume_model.models import SurrogateModel


class ExampleModel(SurrogateModel):
    input_variables = {
        "input1": ScalarInputVariable(name="input1", value=1, range=[0.0, 5.0]),
        "input2": ScalarInputVariable(name="input2", value=2, range=[0.0, 5.0]),
    }

    output_variables = {
        "output1": ScalarOutputVariable(name="output1", value=2.0),
        "output2": ScalarOutputVariable(name="output2", value=5.0),
        "output3": ImageOutputVariable(
            name="output3",
            value=np.array([[1, 2,], [3, 4]]),
            axis_labels=["count_1", "count_2"],
            x_min=0,
            y_min=0,
            x_max=5,
            y_max=5,
        ),
    }

    def evaluate(self, input_variables):
        self.output_variables["output1"].value = (
            self.input_variables["input1"].value * 2
        )
        self.output_variables["output2"].value = (
            self.input_variables["input2"].value * 2
        )
        self.output_variables["output3"].value = (
            self.input_variables["input2"].value
            * self.output_variables["output3"].value
        )
        return list(self.output_variables.values())


def test_ca():
    PREFIX = "test"

    server = epics_server.Server(ExampleModel, PREFIX)
    server.start(monitor=False)
    # create controller

    controller = Controller("ca")
    print("Getting inputs")
    controller.get("test:input1")
    controller.get("test:input2")

    print("Getting outputs")
    controller.get("test:output1")
    controller.get("test:output2")
    controller.get_image("test:output3")

    controller.close()
    server.stop()


def test_pva():
    PREFIX = "test"

    server = epics_server.Server(ExampleModel, PREFIX)
    server.start(monitor=False)

    # create controller
    controller = Controller("pva")
    print("Getting inputs")
    controller.get("test:input1")
    controller.get("test:input2")
    print("Getting outputs")
    controller.get("test:output1")
    controller.get("test:output2")
    controller.get_image("test:output3")

    controller.close()
    server.stop()

