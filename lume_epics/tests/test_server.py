import numpy as np
import time
import pytest
import epics
from lume_model.variables import (
    ScalarInputVariable,
    ScalarOutputVariable,
    ImageInputVariable,
    ImageOutputVariable,
)
from lume_epics import epics_server
from lume_model.models import SurrogateModel


class ExampleModel(SurrogateModel):
    input_variables = {
        "input1": ScalarInputVariable(name="input1", value=1, default=1, range=[0.0, 5.0]),
        "input2": ScalarInputVariable(name="input2", value=2, default=2, range=[0.0, 5.0]),
    }

    output_variables = {
        "output1": ScalarOutputVariable(name="output1"),
        "output2": ScalarOutputVariable(name="output2"),
    }

    def evaluate(self, input_variables):

        self.input_variables = {variable.name: variable for variable in input_variables}

        self.output_variables["output1"].value = self.input_variables["input1"].value * 2
        self.output_variables["output2"].value = self.input_variables["input2"].value * 2

        # return inputs * 2
        return list(self.output_variables.values())


def test_scalar_server():
    prefix = "test"
    server = epics_server.Server(ExampleScalarModel, prefix)
    server.start(monitor=False)
    time.sleep(0.5)
    server.stop()


class ExampleImageModel(SurrogateModel):
    input_variables = {
        "input1": ImageInputVariable(
            name="input1",
            default=np.array([[1, 2,], [3, 4]]),
            value_range=[1, 10],
            axis_labels=["count_1", "count_2"],
            x_min=0,
            y_min=0,
            x_max=5,
            y_max=5,
        ),
        "input2": ImageInputVariable(
            name="input2",
            default=np.array([[1, 6,], [4, 1]]),
            value_range=[1, 10],
            axis_labels=["count_1", "count_2"],
            x_min=0,
            y_min=0,
            x_max=5,
            y_max=5,
        ),
    }

    output_variables = {
        "output1": ScalarOutputVariable(name="output1"),
        "output2": ScalarOutputVariable(name="output2"),
        "output3": ImageOutputVariable(
            name="output3", axis_labels=["count_1", "count_2"],
        ),
    }

    def evaluate(self, input_variables):

        self.input_variables = {variable.name: variable for variable in input_variables}

        self.output_variables["output1"].value = self.input_variables["input1"].value * 2
        self.output_variables["output2"].value = self.input_variables["input2"].value * 2

        self.output_variables["output3"].value = (
            self.input_variables["input1"].value * 2
        )
        self.output_variables["output3"].value = (
            self.input_variables["input3"].value * 2
        )
        self.output_variables["output3"].x_min = (
            self.input_variables["input3"].x_min / 2
        )
        self.output_variables["output3"].x_max = (
            self.input_variables["input3"].x_max / 2
        )
        self.output_variables["output3"].y_min = (
            self.input_variables["input3"].y_min / 2
        )
        self.output_variables["output3"].y_max = (
            self.input_variables["input3"].y_max / 2
        )
        self.output_variables["output3"].x_min = (
            self.input_variables["input3"].x_min / 2
        )
        self.output_variables["output3"].x_max = (
            self.input_variables["input3"].x_max / 2
        )
        self.output_variables["output3"].y_min = (
            self.input_variables["input3"].y_min / 2
        )
        self.output_variables["output3"].y_max = (
            self.input_variables["input3"].y_max / 2
        )

        # return inputs * 2
        return list(self.output_variables.values())


def test_image_server():
    prefix = "test"
    server = epics_server.Server(ExampleScalarModel, prefix)

    server = epics_server.Server(ExampleModel, ExampleModel.input_variables, ExampleModel.output_variables, prefix, protocols=["pva"])
    server.start(monitor=False)

    for var in server.input_variables:
        epics.caget(f"{prefix}:{var}")

    server.stop()


@pytest.mark.parametrize("value,prefix", [(1.0, "test")])
def test_constant_variable(value,prefix):
    server = epics_server.Server(ExampleModel, ExampleModel.input_variables, ExampleModel.output_variables, prefix, protocols=["pva"])
    server.start(monitor=False)


    for variable_name, variable in server.input_variables.items():
        if variable.variable_type == "scalar":
            epics.caput(f"{prefix}:{variable_name}", value)

    for variable_name, variable in server.input_variables.items():
        if variable.variable_type == "scalar":
            val = epics.caget(f"{prefix}:{variable_name}")
            assert val == value

    server.stop()
