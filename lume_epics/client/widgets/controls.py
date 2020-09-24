"""
The controls module contains tools for constructing bokeh control widgets. 
Controls may be built for lume-model ScalarInputVariables.

"""

from functools import partial
from typing import Union, List
import logging

from bokeh.models import Slider, ColumnDataSource, DataTable, TableColumn, StringFormatter, TextInput, StringEditor, Button, TextEditor, HTMLTemplateFormatter, Paragraph
from bokeh.events import Tap, MouseLeave, ButtonClick
from bokeh.models.callbacks import CustomJS
from bokeh import document
from bokeh.layouts import column, row

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


class EntryTable:
    """
    Table of process variable names and values.

    Attriibutes:
        pv_monitors (Dict[str, PVScalar]): Monitors associated with process variables.

        output_values (dict): Dict mapping process variable name to current value.

        labels (dict): Dict mapping process variable name to labels.

        source (ColumnDataSource): Data source for populating bokeh table.



    """
    def __init__(
        self, variables: List[ScalarInputVariable], controller: Controller, prefix: str, row_height: int=50
    ) -> None:
        """
        Initialize table.

        Args:
            variables (List[ScalarVariable]): List of variables to display.

            controller (Controller): Controller object for accessing process variables.

            prefix (str): Prefix used in setting up the server.

            row_height (int): Height to render row

        """
        self.prefix = prefix
        self.controller = controller

        # be sure to surface units in the table
        self.unit_map = {}
        self.text_inputs = {}

        title_column = []
        input_column = []

        for variable in variables:

            # check if units assigned
            if "units" in variable.__fields_set__ and variable.units:
                label = variable.name + f" ({variable.units})"

            else:
                label = variable.name

            entry_title = Paragraph(text=variable.name, align='center')
            self.text_inputs[variable.name] = TextInput(name=label)

            # create columns
            title_column.append(row(entry_title, height=row_height))
            input_column.append(row(self.text_inputs[variable.name], height=row_height))


        # set up table
        self.table = row(column(*title_column), column(*input_column))

        # Set up buttons
        self.clear_button = Button(label="Clear")
        self.clear_button.on_click(self.clear)
        self.submit_button = Button(label="Submit")
        self.submit_button.on_click(self.submit)
    

    def submit(self) -> None:
        """
        Function to submit values entered into table
        """
        for variable, text_input in self.text_inputs.items():
            if text_input.value_input  != "":
                pvname = f"{self.prefix}:{variable}"
                self.controller.put(pvname, text_input.value_input)


    def clear(self) -> None:
        """
        Function to clear all entered values
        """
        for variable, text_input in self.text_inputs.items():
            text_input.value_input = ""