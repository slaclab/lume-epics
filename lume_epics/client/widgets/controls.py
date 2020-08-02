"""
The controls module contains tools for constructing bokeh control widgets. 
Controls may be built for lume-model ScalarInputVariables.

"""

from functools import partial
from typing import Union, List
import logging

from bokeh.models import Slider

from lume_model.variables import ScalarInputVariable
from lume_epics.client.controller import Controller

logger = logging.getLogger(__name__)

def set_pv_from_slider(
    attr: str,
    old: float,
    new: float,
    pvname: str,
    controller: Controller,
) -> None:
    """
    Callback function for updating process variables on slider change.

    Args:
        attr (str): Attribute to update.

        old (float): Prior slider value.

        new (float): New value assigned by slider.

        pvname (str): Name of the process variable.

        controller (Controller): Controller object for interacting with process 
            variable values.

    """
    controller.put(pvname, new)


def build_slider(
    prefix: str, variable: ScalarInputVariable, controller: Controller
) -> Slider:
    """
    Utility function for building a slider.

    Args:
        prefix (str): Prefix used for serving process variables.

        variable (ScalarInputVariable): Variable associated with the slider.

        controller (Controller): Controller object for getting process variable values.

    """
    title = variable.name
    if "units" in variable.__fields_set__:
        title += " (" + variable.units + ")"

    pvname = prefix + ":" + variable.name
    step = (variable.value_range[1] - variable.value_range[0]) / 100.0


    # initialize value
    start_val = controller.get_value(pvname)

    # construct slider
    slider = Slider(
        title=title,
        value= start_val,
        start=variable.value_range[0],
        end=variable.value_range[1],
        step=step,
        format = "0[.]0000"
    )

    # set up callback
    slider.on_change(
        "value",
        partial(set_pv_from_slider, pvname=pvname, controller=controller),
    )

    return slider


def build_sliders(
    variables: List[ScalarInputVariable], controller: Controller, prefix: str,
) -> List[Slider]:
    """
    Build sliders for a list of variables.

    Args: 
        prefix (str): Prefix used to serve process variables.

        variables (List[ScalarInputVariable]): List of variables for which to build sliders.

        controller (Controller): Controller object for getting process variable values.

    """
    sliders = []

    for variable in variables:
        slider = build_slider(prefix, variable, controller,)
        sliders.append(slider)

    return sliders
