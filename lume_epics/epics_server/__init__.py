import numpy as np
from typing import List, Union

from lume_epics import (
    INPUT_VARIABLE_TYPES,
    OUTPUT_VARIABLE_TYPES,
    IMAGE_VARIABLE_TYPES,
    SCALAR_VARIABLE_TYPES,
)
from lume_epics.epics_server import ca, pva


def build_pvdb(variables):
    pvdb = {}

    for variable in variables.values():
        if isinstance(variable, IMAGE_VARIABLE_TYPES):

            # infer color mode
            if variable.value.ndim == 2:
                color_mode == 0

            else:
                raise Exception("Color mode cannot be inferred from image shape.")

            image_pvs = build_image_pvs(
                variable.name,
                variable.shape,
                variable.units,
                variable.precision,
                variable.color_mode,
            )

            # assign default PVS
            pvdb = {
                f"{pvname}:NDimensions_RBV": {
                    "type": "float",
                    "prec": variable.precision,
                    "value": variable.value.ndim,
                },
                f"{pvname}:Dimensions_RBV": {
                    "type": "int",
                    "prec": variable.precision,
                    "count": variable.value.ndim,
                    "value": variable.value.shape,
                },
                f"{pvname}:ArraySizeX_RBV": {
                    "type": "int",
                    "value": variable.value.shape[0],
                },
                f"{pvname}:ArraySize_RBV": {
                    "type": "int",
                    "value": int(np.prod(variable.value.shape)),
                },
                f"{pvname}:ArrayData_RBV": {
                    "type": "float",
                    "prec": variable.precision,
                    "count": int(np.prod(variable.value.shape)),
                    "units": variable.units,
                },
                f"{pvname}:ColorMode_RBV": {"type": "int", "value": color_mode},
                f"{pvname}:dw": {"type": "float", "prec": variable.precision},
                f"{pvname}:dh": {"type": "float", "prec": variable.precision},
                f"{pvname}:ArraySizeY_RBV": {
                    "type": "int",
                    "value": variable.value.shape[1],
                },
            }

            # placeholder for color images, not yet implemented
            if ndim > 2:
                pvdb[f"{pvname}:ArraySizeZ_RBV"] = {
                    "type": "int",
                    "value": variable.value.shape[2],
                }

        else:
            pvdb[variable.name] = variable.dict(exclude_unset=True, exclude={"io_type"})

    return pvdb


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
        input_pvdb = build_pvdb(input_variables)
        output_pvdb = build_pvdb(output_variables)
        server = ca.CAServer(
            model_class, model_kwargs, input_variables, output_variables, prefix
        )

    elif protocol == "pva":
        server = pva.PVAServer(
            model_class, model_kwargs, input_variables, output_variables, prefix,
        )

    else:
        raise Exception("Must use ca or pva for protocol.")

    return server
