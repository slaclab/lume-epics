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

class EpicsSlider:
    """EPICS based Slider used for building bokeh sliders and synchronizing process variable values.

    """

    def __init__(self, prefix: str, variable: ScalarInputVariable, controller: Controller):
        self.prefix = prefix
        self.controller = controller
        self.variable = variable
        self.build_slider()

    def build_slider(self):
        """
        Utility function for building a slider.

        Args:
            prefix (str): Prefix used for serving process variables.

            variable (ScalarInputVariable): Variable associated with the slider.

            controller (Controller): Controller object for getting process variable values.

        """
        title = self.variable.name
        if "units" in self.variable.__fields_set__:
            title += " (" + self.variable.units + ")"

        self.pvname = self.prefix + ":" + self.variable.name
        step = (self.variable.value_range[1] - self.variable.value_range[0]) / 100.0

        # construct slider
        self.bokeh_slider = Slider(
            title=title,
            value= self.variable.value_range[0],
            start=self.variable.value_range[0],
            end=self.variable.value_range[1],
            step=step,
            format = "0[.]0000"
        )

        # set up callback
        self.bokeh_slider.on_change(
            "value",
            partial(set_pv_from_slider, pvname=self.pvname, controller=self.controller),
        )

    def update(self):
        """
        Updates bokeh slider with the process variable value.

        """
        self.bokeh_slider.value = self.controller.get_value(self.pvname)


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
        slider = EpicsSlider(prefix, variable, controller,)
        sliders.append(slider)

    return sliders

def set_pv_from_slider(
    attr: str,
    old: float,
    new: float,
    pvname: str,
    controller: Controller,) -> None:
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