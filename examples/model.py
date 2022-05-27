import numpy as np
from lume_model.variables import (
    ScalarInputVariable,
    ImageOutputVariable,
    ScalarOutputVariable,
)
from lume_model.models import BaseModel


class DemoModel(BaseModel):
    def __init__(self, input_variables=None, output_variables=None):
        self.input_variables = input_variables
        self.output_variables = output_variables

    def evaluate(self, input_variables: dict) -> dict:
        self.output_variables["output1"].value = np.random.uniform(
            input_variables["input1"].value,  # lower dist bound
            input_variables["input2"].value,  # upper dist bound
            (50, 50),
        )
        self.output_variables["output2"].value = input_variables["input1"].value
        self.output_variables["output3"].value = input_variables["input2"].value

        return self.output_variables
