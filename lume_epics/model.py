import numpy as np
import time
from typing import Dict, Tuple, Mapping, Union, List
from abc import ABC, abstractmethod

from lume_model.variables import Variable
from lume_model.models import SurrogateModel


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
            variable.name: variable.value for variable in output_variables
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

        # update output variable state
        for model in self.models:
            predicted_output = model.evaluate(self.input_variables)
            for variable in predicted_output:
                self.output_variables[variable.name] = variable

        t2 = time.time()
        print("Running model...", end="")
        print("Ellapsed time: " + str(t2 - t1))

        return list(self.output_variables.values())
