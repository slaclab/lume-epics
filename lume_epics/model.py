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
from lume_model.models import BaseModel

logger = logging.getLogger(__name__)


class OnlineModel:
    """
    Class for executing surrogate model.

    Attributes:
        model (SurrogateModel): Model for execution.

        input_variables (Dict[str, InputVariable]): List of lume-model variables to use as inputs.

        ouput_variables (Dict[str, OutputVariable]): List of lume-model variables to use as outputs.

    """

    def __init__(self, model: BaseModel,) -> None:
        """
        Initialize OnlineModel with the base model class.

        Args:
            model (BaseModel): Instantiated model.

        """
        self.model = model

        self.input_variables = self.model.input_variables
        self.output_variables = self.model.output_variables

    def run(
        self, input_variables: Dict[str, InputVariable]
    ) -> Dict[str, OutputVariable]:
        """
        Executes both scalar and image model given process variable value inputs.

        Args:
            input_variables (Dict[str, InputVariable]): Dict of lume-model variables to use as inputs.

        """
        # update input variables and get state representation
        self.input_variables = input_variables

        # update output variable state
        logger.info("Running model")
        t1 = time.time()
        self.output_variables = self.model.evaluate(self.input_variables)
        t2 = time.time()

        logger.info("Ellapsed time: %s", str(t2 - t1))

        return self.output_variables
