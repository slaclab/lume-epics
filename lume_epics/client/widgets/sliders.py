from functools import partial
from typing import Union, List

from bokeh.models import Slider

import lume_model.variables import ScalarVariable
from lume_epics.client.controller import Controller


def set_pv_from_slider(
    attr: str,
    old: float,
    new: float,
    pvname: str,
    scale: Union[float, int],
    controller: Controller,
) -> None:
    """
    Callback function for slider change.

    Parameters
    ----------
    attr:str
        Attribute to update

    old:float
        Old value

    new:float
        New value

    pvname: str
        Process variable name

    scale:float/int
        Scale of the slider

    controller: Controller
        Controller object for getting pv values

    """
    controller.put(pvname, new * scale)


def build_slider(
    prefix: str, variable: ScalarVariable, controller: Controller
) -> Slider:
    """
    Utility function for building a slider.

    Parameters
    ----------
    prefix: str
        Process variable prefix used in serving pvs

    variable: ScalarVariable
        Variable to build slider for

    controller: Controller
        Controller object for getting pv values

    Returns
    -------
    bokeh.models.widgets.sliders.Slider

    """
    title = variable.name
    if "units" in variable.__fields_set__:
        title += " (" + variable.units + ")"

    pvname = prefix + ":" + variable.name
    step = (variable.value_range[1] - variable.value_range[0]) / 100.0
    scale = 1

    # initialize value
    try:
        start_val = controller.get(pvname)

    except TimeoutError:
        print(f"No process variable found for {pvname}")
        start_val = 0

    slider = Slider(
        title=title,
        value=scale * start_val,
        start=variable.value_range[0],
        end=variable.value_range[1],
        step=step,
    )

    # set up callback
    slider.on_change(
        "value",
        partial(set_pv_from_slider, pvname=pvname, scale=scale, controller=controller),
    )

    return slider


def build_sliders(
    variables: List[ScalarVariable],
    controller: Controller,
    prefix: str,
) -> List[Slider]:
    """
    Build sliders for a list of variables.


    Parameters
    ----------
    prefix: str
        Process variable prefix used in serving pvs

    variables: list
        List of scalar variables to render

    controller: Controller
        Controller object for getting pv values

    Returns
    -------
    list
        List of sliders

    """
    sliders = []

    for variable in variables:
        slider = build_slider(prefix, variable, controller,)
        sliders.append(slider)

    return sliders
