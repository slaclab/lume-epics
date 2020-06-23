import numpy as np
import time
from typing import Dict, Tuple, Mapping, Union, List
from abc import ABC, abstractmethod

from lume_model.variables import Variable


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
    Class for running the executing surrogate models.

    Attributes
    ----------

    models: list
        list of model objects
            
    input_variables: list
        List of lume-model variables to use as inputs

    ouput_variables: list
        List of lume-model variables to use as outputs

    """

    def __init__(
        self,
        models: List[SurrogateModel],
        input_variables: List[Variable],
        output_variables: List[Variable],
    ) -> None:
        """
        Initialize OnlineSurrogateModel provided models. \\

        Parameters
        ----------
        models: list
            list of model objects
            
        input_variables: list
            List of lume-model variables to use as inputs

        ouput_variables: list
            List of lume-model variables to use as outputs

        """
        self.models = models

        self.input_variables = input_variables

        # dict of name -> var
        self.output_variables = {
            variable.name: variable for variable in output_variables
        }

    def run(
        self, input_variables: List[Variable]
    ) -> Mapping[str, Union[float, np.ndarray]]:
        """
        Executes both scalar and image model given process variable value inputs.

        Parameters
        ----------
        input_variables: list
            List of lume-model variables to use as inputs

        Returns
        -------
        ouput_variables: list
            List of updated lume-model output variables

            

        """
        t1 = time.time()

        # update input variables and get state representation
        self.input_variables = input_variables
        input_state = {variable.name: variable.value for variable in input_variables}

        # update output variable state
        for model in self.models:
            predicted_output = model.predict(input_state)
            for output, value in predicted_output.items():
                self.output_variables[output].value = value

        t2 = time.time()
        print("Running model...", end="")
        print("Ellapsed time: " + str(t2 - t1))

        return list(self.output_variables.values())
