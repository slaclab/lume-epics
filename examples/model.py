import numpy as np
from lume_model.variables import ScalarInputVariable, ImageOutputVariable
from lume_model.models import SurrogateModel
from lume_model.utils import save_variables

class DemoModel(SurrogateModel):
    def __init__(self, input_variables=None, output_variables=None):
        self.input_variables = input_variables
        self.output_variables = output_variables

    def evaluate(self, input_variables):
        self.output_variables["output1"].value = np.random.uniform(
            self.input_variables["input1"].value, # lower dist bound
            self.input_variables["input2"].value, # upper dist bound
            (50,50)
        )

        return list(self.output_variables.values())


if __name__ == "__main__":
    input_variables = {
        "input1": ScalarInputVariable(
            name="input1", 
            value=1, 
            default=1, 
            range=[0, 256]
        ),
        "input2": ScalarInputVariable(
            name="input2", 
            value=2, 
            default=2, 
            range=[0, 256]),
    }

    output_variables = {
        "output1": ImageOutputVariable(
            name="output1", 
            axis_labels=["value_1", "value_2"], 
            axis_units=["mm", "mm"], 
            x_min=0, 
            x_max=50, 
            y_min=0, 
            y_max=50
        )
    }

    variable_filename = "examples/variables.pickle"

    save_variables(
        input_variables, 
        output_variables, 
        variable_filename
    )