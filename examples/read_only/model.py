import numpy as np
from lume_model.variables import (
    ScalarInputVariable,
    ImageOutputVariable,
    ScalarOutputVariable,
)
from lume_model.base import LUMEBaseModel
from lume_model.utils import save_variables


class DemoModel(LUMEBaseModel):
    def __init__(self, input_variables=None, output_variables=None):
        self.input_variables = input_variables
        self.output_variables = output_variables

    def _evaluate(self, input_dict: dict):
        return {
            "output1": input_dict["input1"].value,
            "output2": input_dict["input2"].value,
        }
