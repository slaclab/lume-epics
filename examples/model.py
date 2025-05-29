import numpy as np
from lume_model.variables import ScalarVariable
from lume_model.base import LUMEBaseModel


class DemoModel(LUMEBaseModel):
    def _evaluate(self, input_dict: dict) -> dict:
        return {
            "output1": input_dict["input1"],
            "output2": input_dict["input2"],
        }
