import numpy as np
import time
from lume_model.variables import (
    ScalarInputVariable,
    ScalarOutputVariable,
    ImageInputVariable,
    ImageOutputVariable,
)
from lume_epics import epics_server
from lume_epics.model import SurrogateModel


def test_scalar_server():
    class ExampleModel(SurrogateModel):
        input_variables = {
            "input1": ScalarInputVariable(name="input1", value=1, range=[0.0, 5.0]),
            "input2": ScalarInputVariable(name="input2", value=2, range=[0.0, 5.0]),
        }

        output_variables = {
            "output1": ScalarOutputVariable(name="output1"),
            "output2": ScalarOutputVariable(name="output2"),
        }

        def predict(self, input_variables):

            self.input_variables = {
                variable.name: variable for variable in input_variables
            }

            self.output_variables["output1"].value = (
                self.input_variables["input1"].value * 2
            )
            self.output_variables["output2"].value = (
                self.input_variables["input2"].value * 2
            )

            # return inputs * 2
            return list(self.output_variables.values())

    prefix = "test"
    model_class = ExampleModel
    model_kwargs = {}
    server = epics_server.Server(model_class, model_kwargs, prefix)

    # start and stop pva server
    server.start_pva_server()
    time.sleep(0.5)
    server.pva_server.stop()

    # start and stop channel access server
    server.start_ca_server()
    time.sleep(0.5)
    server.exit_event.set()


def test_image_server():
    input1 = ImageInputVariable(
        name="input1",
        value=np.array([[1, 2,], [3, 4]]),
        value_range=[1, 10],
        axis_labels=["count_1", "count_2"],
        x_min=0,
        y_min=0,
        x_max=5,
        y_max=5,
    )

    input2 = ImageInputVariable(
        name="input2",
        value=np.array([[1, 6,], [4, 1]]),
        value_range=[1, 10],
        axis_labels=["count_1", "count_2"],
        x_min=0,
        y_min=0,
        x_max=5,
        y_max=5,
    )

    output1 = ImageOutputVariable(
        name="output1",
        #    value=np.array([[1, 2,], [3, 4]]),
        axis_labels=["count_1", "count_2"],
    )

    output2 = ImageOutputVariable(
        name="output2",
        #    value=np.array([[1, 2,], [3, 4]]),
        axis_labels=["count_1", "count_2"],
    )

    class ExampleModel(SurrogateModel):
        input_variables = {
            "input1": ImageInputVariable(
                name="input1",
                value=np.array([[1, 2,], [3, 4]]),
                value_range=[1, 10],
                axis_labels=["count_1", "count_2"],
                x_min=0,
                y_min=0,
                x_max=5,
                y_max=5,
            ),
            "input2": ImageInputVariable(
                name="input2",
                value=np.array([[1, 6,], [4, 1]]),
                value_range=[1, 10],
                axis_labels=["count_1", "count_2"],
                x_min=0,
                y_min=0,
                x_max=5,
                y_max=5,
            ),
        }

        output_variables = {
            "output1": ImageOutputVariable(
                name="output1", axis_labels=["count_1", "count_2"],
            ),
            "output2": ImageOutputVariable(
                name="output2", axis_labels=["count_1", "count_2"],
            ),
        }

        def predict(self, input_variables):

            self.input_variables = {
                variable.name: variable for variable in input_variables
            }

            self.output_variables["output1"].value = (
                self.input_variables["input1"].value * 2
            )
            self.output_variables["output2"].value = (
                self.input_variables["input2"].value * 2
            )
            self.output_variables["output1"].x_min = (
                self.input_variables["input1"].x_min / 2
            )
            self.output_variables["output1"].x_max = (
                self.input_variables["input1"].x_max / 2
            )
            self.output_variables["output1"].y_min = (
                self.input_variables["input1"].y_min / 2
            )
            self.output_variables["output1"].y_max = (
                self.input_variables["input1"].y_max / 2
            )
            self.output_variables["output2"].x_min = (
                self.input_variables["input2"].x_min / 2
            )
            self.output_variables["output2"].x_max = (
                self.input_variables["input2"].x_max / 2
            )
            self.output_variables["output2"].y_min = (
                self.input_variables["input2"].y_min / 2
            )
            self.output_variables["output2"].y_max = (
                self.input_variables["input2"].y_max / 2
            )

            return list(self.output_variables.values())

    prefix = "test"
    model_class = ExampleModel
    model_kwargs = {}
    server = epics_server.Server(model_class, model_kwargs, prefix)

    # start and stop pva server
    server.start_pva_server()
    time.sleep(0.5)
    server.pva_server.stop()

    # start and stop channel access server
    server.start_ca_server()
    time.sleep(0.5)
    server.exit_event.set()
