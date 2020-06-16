import numpy as np
import time
from typing import Dict, Tuple, Mapping, Union
from abc import ABC, abstractmethod


class SurrogateModel(ABC):
    """
    Base class for the surrogate models that includes abstract predict method, which \\
    must be initialized by children.

    """

    @abstractmethod
    def predict(self):
        """
        Abstract prediction method that must be overwritten by inheriting classes.
        """
        pass


class OnlineSurrogateModel:
    """
    Class for running the executing both the scalar and image model.

    Attributes
    ----------
    scalar_model: online_model.model.surrogate_model.ScalarSurrogateModel
        Model instance used for predicting scalar outputs.

    image_model: online_model.model.surrogate_model.ImageSurrogateModel
        Model instance used for predicting image outputs.

    NOTES
    -----
    TODO:
    Understand the preprocessing here
    """

    def __init__(self, models) -> None:
        """
        Initialize OnlineSurrogateModel instance using given scalar and image model \\
        files.

        Parameters
        ----------
        models: list
            list of model objects

        """
        self.models = models

    def run(self, pv_state: Dict[str, float]) -> Mapping[str, Union[float, np.ndarray]]:
        """
        Executes both scalar and image model given process variable value inputs.

        Parameters
        ----------
        pv_state: dict
            State of input process variables.

        Returns
        -------
        dict
            Mapping of process variables to model output values.

        """
        t1 = time.time()

        output = {}

        for model in self.models:
            predicted_output = model.predict(pv_state)
            output.update(predicted_output)

        t2 = time.time()
        print("Running model...", end="")
        print("Ellapsed time: " + str(t2 - t1))

        return output
