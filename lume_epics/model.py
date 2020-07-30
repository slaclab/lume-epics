"""
This module is used for executing callbacks on the user's SurrogateModel class for use
with the EPICS server defined in lume_epics.epics_server. The SurrogateModel must be
defined using the guidelines outlined in the lume_model.models module to be surfaced 
using the OnlineSurrogateModel class.

"""

import numpy as np
import time
import logging
from typing import Dict, Tuple, Mapping, Union, List
from abc import ABC, abstractmethod

from lume_model.variables import InputVariable, OutputVariable
from lume_model.models import SurrogateModel

logger = logging.getLogger(__name__)

class OnlineSurrogateModel:
    """
    Class for executing surrogate model.

    Attributes:
        model (SurrogateModel): Model for execution.
            
        input_variables (List[InputVariable]): List of lume-model variables to use as inputs.

        ouput_variables (List[OutputVariable]): List of lume-model variables to use as outputs.

    """

    def __init__(
        self,
        model: SurrogateModel,
    ) -> None:
        """
        Initialize OnlineSurrogateModel with the surrogate model. 

        Args:
            model (SurrogateModel): Instantiated surrogate model.

        """
        self.model = model

        self.input_variables = list(self.model.input_variables.values())
        self.output_variables = self.model.output_variables

    def run(
        self, input_variables: List[InputVariable]
    ) -> List[OutputVariable]:
        """
        Executes both scalar and image model given process variable value inputs.

        Args:
            input_variables (List[InputVariable]): List of lume-model variables to use as inputs.            

        """
        # update input variables and get state representation
        self.input_variables = input_variables

        # update output variable state
        predicted_output = self.model.evaluate(self.input_variables)

        logger.info("Running model")
        t1 = time.time()
        for variable in predicted_output:
            self.output_variables[variable.name] = variable
        t2 = time.time()
    
        logger.info("Ellapsed time: %s", str(t2 - t1))

        return list(self.output_variables.values())
