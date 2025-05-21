import numpy as np
from lume_model.variables import (
    ScalarInputVariable,
    ImageOutputVariable,
    ScalarOutputVariable,
)
from lume_model.base import LUMEBaseModel


class DemoModel(LUMEBaseModel):
    def __init__(self, input_variables=None, output_variables=None):
        self.input_variables = input_variables
        self.output_variables = output_variables

    def _evaluate(self, input_dict: dict) -> dict:
        return {
            "output1": np.random.uniform(
                input_dict["input1"],  # lower dist bound
                input_dict["input2"],  # upper dist bound
                (50, 50),
            ),
            "output2": input_dict["input1"],
            "output3": input_dict["input2"],
        }
