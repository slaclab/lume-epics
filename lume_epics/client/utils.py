from lume_model.utils import variables_from_yaml
from bokeh.layouts import column, row, gridplot, layout
from bokeh.models.widgets import Select
from bokeh.models import Div
from bokeh import palettes

from lume_epics.client.controller import Controller

from lume_epics.client.widgets.tables import ValueTable 
from lume_epics.client.widgets.controls import build_sliders, EntryTable
from lume_epics.client.widgets.plots import Striptool, ImagePlot


pal = palettes.viridis(256)

# striptool data update callback
def striptool_update_callback():
    """
    Calls striptool update with the current global process variable.
    """
    global current_striptool_pv
    striptool.update(live_variable = current_striptool_pv)


class LayoutBuilder():

    def __init__(self, ncol_widgets: int):
        self._ncol_widgets = ncol_widgets
        self._input_current_row = []
        self._output_current_row = []
        self._input_header = Div(text="<h3 style='text-align:center;'>Live Model Inputs</h1>", sizing_mode="scale_both", margin=(0,0,0,0))
        self._output_header = Div(text="<h3 style='text-align:center;'>Live Model Outputs</h1>", sizing_mode="scale_both", margin=(0,0,0,0))
        self._input_layout = []
        self._output_layout = []
        self._layout = []


    def add_input(self, layout_item, title: str = None):

        if title:
            title_div = Div(text=f"<p style='text-align:center;'>{title}</p>", sizing_mode="scale_both")
            layout_item = column(title_div, layout_item, sizing_mode="scale_both")

        self._input_layout.append(layout_item)

    def add_output(self, layout_item, title: str = None):

        if title:
            title_div = Div(text=f"<p style='text-align:center;'>{title}</p>", sizing_mode="scale_both")
            layout_item = column(title_div, layout_item, sizing_mode="scale_both")

        self._output_layout.append(layout_item)


    def add_input_stack(self, layout_items, title=None):
        layout_item = column(layout_items)
        
        if title:
            title_div = Div(text=f"p style='text-align:center;'>{title}</p>", sizing_mode="scale_both")
            layout_item = column(title_div, layout_item, sizing_mode = "scale_both")

        self._input_layout.append(layout_item)

    def add_output_stack(self, layout_items, title=None):
        layout_item = column(layout_items)
        
        if title:
            title_div = Div(text=f"p style='text-align:center;'>{title}</h1>", sizing_mode="scale_both", margin=(0,0,0,0))
            layout_item = column(title_div, layout_item, sizing_mode = "scale_both")

        else:
            self._output_layout.append(layout_item)

    def build_layout(self):
        input_grid = gridplot(self._input_layout,  ncols=self._ncol_widgets, sizing_mode="scale_both")
        output_grid = gridplot(self._output_layout, ncols=self._ncol_widgets, sizing_mode="scale_both")

        built_layout = [self._input_header, input_grid, self._output_header, output_grid]
        return layout(built_layout, name="layout")



def render_from_yaml(config_file, prefix: str, protocol: str, read_only=False, striptool_limit=50, ncol_widgets=5):
    """

    Notes:
    Default palette used
    """

    # load variables
    with open(config_file, "r") as f:
        input_variables, output_variables = variables_from_yaml(f)

    # variables
    constant_scalars = []
    constant_images = []
    variable_input_scalars = []
    variable_output_scalars = []
    variable_input_images = []
    variable_output_images = []

    # organize input variables
    for variable in input_variables.values():
        if variable.variable_type == "scalar":
            if variable.is_constant:
                constant_scalars.append(variable)

            else:
                variable_input_scalars.append(variable)

        elif variable.variable_type == "image":
            if variable.is_constant:
                constant_images.append(variable)

            else:
                variable_input_images.append(variable)

    # organize output variables
    for variable in output_variables.values():
        if variable.variable_type == "scalar":
            variable_output_scalars.append(variable)

        if variable.variable_type == "image":
            variable_output_images.append(variable)

    # set up controller
    controller = Controller(protocol)

    # track callbacks
    callbacks = []

    # track all inputs
    input_value_vars = constant_scalars + variable_input_scalars


    layout_builder = LayoutBuilder(ncol_widgets)

    # add images
    current_row = []
    for variable in variable_input_images + constant_images:
        image = ImagePlot([variable], controller, prefix)
        image.build_plot(pal)
        layout_builder.add_input(image.plot, title=variable.name)
        callbacks.append(image.update)

    # build input striptools
    if read_only:
        striptools = []
        for variable in variable_input_scalars:
            striptool = Striptool([variable], controller, prefix, limit=striptool_limit)
            layout_builder.add_input(striptool.plot, title=variable.name)
            callbacks.append(striptool.update)

    # build sliders and value entry table
    else:
        sliders = build_sliders(variable_input_scalars, controller, prefix)

        slider_stack = []
        for slider in sliders:
            slider_stack.append(slider.bokeh_slider)
            callbacks.append(slider.update)

        layout_builder.add_input_stack(slider_stack)

        # build value entry
        value_entry = EntryTable(input_value_vars, controller, prefix)

        layout_builder.add_input_stack([value_entry.table, value_entry.button_row])

    table_row = []

    # add value table callback
    value_table = ValueTable(input_value_vars, controller, prefix)
    layout_builder.add_input(value_table.table)
    callbacks.append(value_table.update)


    # add output value table callback
    output_value_table = ValueTable(variable_output_scalars, controller, prefix)

    if read_only:
        value_table.table.autosize_mode="fit_columns"

    layout_builder.add_output(output_value_table.table)
    callbacks.append(output_value_table.update)

    for variable in variable_output_images:
        image = ImagePlot([variable], controller, prefix)
        image.build_plot(pal)
        layout_builder.add_output(image.plot, title=variable.name)
        callbacks.append(image.update)

    # build output striptools
    if read_only:

        for variable in variable_output_scalars:

            striptool = Striptool([variable], controller, prefix, limit=striptool_limit)
            layout_builder.add_output(striptool.plot, title=variable.name)
            callbacks.append(striptool.update)
            
    else:
        output_striptool = Striptool(variable_output_scalars, controller, prefix, limit=striptool_limit)
        striptool_select = Select(
            title="Variable to plot:",
            value=output_striptool.live_variable,
            options=list(output_striptool.pv_monitors.keys()),
        )
        layout_builder.add_output_stack([striptool_select, output_striptool.plot])

        # add the selection callback
        # striptool_select.on_change("value", striptool_select_callback)
        callbacks.append(output_striptool.update)

    layout = layout_builder.build_layout()

    return layout, callbacks
