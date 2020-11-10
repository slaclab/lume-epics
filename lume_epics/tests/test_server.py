import numpy as np
import time
import pytest
import subprocess
import os
from p4p.client.thread import Context
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
        "input2": ScalarInputVariable(name="input2", value=2, default=2, range=[0.0, 5.0], is_constant=True),
        "input3": ImageInputVariable(
            name="input3",
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



@pytest.fixture(scope='session')
def server():
    prefix = "test"

    server = epics_server.Server(ExampleModel, prefix)
    server.start(monitor=False)
    yield server
    # teardown
    server.stop()


@pytest.mark.parametrize("value,prefix", [(1.0, "test")])
def test_constant_variable_pva(value, prefix, server):
    ctxt = Context('pva')

    for variable_name, variable in server.input_variables.items():
        if variable.variable_type == "scalar":
            ctxt.put(f"{prefix}:{variable.name}", value, timeout=2.0, throw=True)



    for variable_name, variable in server.input_variables.items():
        if variable.variable_type == "scalar":
            val = None
            count = 5

            while not val and count > 0:
                try:
                    val = ctxt.get(f"{prefix}:{variable.name}", timeout=2.0, throw = True)
                except:
                    count -= 1

            if variable.is_constant:
                assert val != value

            else:
                assert val == value

    ctxt.close()


@pytest.mark.parametrize("value,prefix", [(1.0, "test")])
def test_constant_variable_ca(value, prefix, server):

    for variable_name, variable in server.input_variables.items():
        if variable.variable_type == "scalar":
            p = subprocess.Popen(["caput", f"{prefix}:{variable.name}", f"{value}"], stdout=subprocess.PIPE)

    for variable_name, variable in server.input_variables.items():
        if variable.variable_type == "scalar":
            p = subprocess.Popen(["caget", f"{prefix}:{variable.name}"], stdout=subprocess.PIPE)

            stdout = p.communicate()[0]
            val = float(stdout.split()[-1])

            if variable.is_constant:
                assert val != value

            else:
                assert val == value
