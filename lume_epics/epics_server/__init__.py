import numpy as np
from typing import List, Union

from lume_epics import (
    INPUT_VARIABLE_TYPES,
    OUTPUT_VARIABLE_TYPES,
    IMAGE_VARIABLE_TYPES,
    SCALAR_VARIABLE_TYPES,
)
from lume_epics.epics_server import ca, pva, combined_server


def get_server(
    prefix: str, model_class, model_kwargs: dict, protocol: str, variables,
) -> Union[ca.CAServer, pva.PVAServer]:

    input_variables = {}
    output_variables = {}

    for variable in variables:
        if isinstance(variable, INPUT_VARIABLE_TYPES):
            input_variables[variable.name] = variable

        elif isinstance(variable, OUTPUT_VARIABLE_TYPES):
            output_variables[variable.name] = variable

        else:
            raise Exception("Only input and output lume_model variables permitted.")

    if protocol == "ca":
        server = ca.CAServer(
            model_class, model_kwargs, input_variables, output_variables, prefix
        )

    elif protocol == "pva":
        server = pva.PVAServer(
            model_class, model_kwargs, input_variables, output_variables, prefix,
        )

    elif protocol == "both":
        server = combined_server.Server(
            model_class, model_kwargs, input_variables, output_variables, prefix,
        )

    else:
        raise Exception("Must use ca or pva for protocol.")

    return server
