from functools import partial
from typing import Union, List

from bokeh.models import Slider

from lume_epics.client.controllers import Controller


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


    controller: online_model.app.widgets.controllers.Controller
        Controller object for getting pv values

    """
    controller.put(pvname, new * scale)


def build_slider(prefix, variable, controller) -> Slider:
    """
    Utility function for building a slider.

    Parameters
    ----------
    title:str
        Slider title

    pvname:str
        Process variable name

    scale:float/int
        Scale of the slider

    start:float
        Lower range of the slider

    end:float
        Upper range of the slider

    step:np.float64
        The step between consecutive values

    controller: online_model.app.widgets.controllers.Controller
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


def build_sliders(variables, controller: Controller, prefix: str) -> List[Slider]:
    """
    Build sliders from the cmd_pvdb.

    Parameters
    ----------
    cmd_pvdb: dict
        Process variable db config for slider inputs

    prefix: str
        Prefix used for server

    Return
    ------
    list
        List of slider objects


    controller: online_model.app.widgets.controllers.Controller
        Controller object for getting pv values

    """
    sliders = []

    for variable in variables:
        slider = build_slider(prefix, variable, controller,)
        sliders.append(slider)

    return sliders
