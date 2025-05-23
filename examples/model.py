import numpy as np
from lume_model.variables import ScalarVariable
from lume_model.base import LUMEBaseModel


class DemoModel(LUMEBaseModel):
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
