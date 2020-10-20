from lume_model.utils import variables_from_yaml
from bokeh.layouts import column, row
from bokeh.models.widgets import Select
from bokeh.models import Div

from lume_epics.client.controller import Controller

from lume_epics.client.widgets.tables import ValueTable 
from lume_epics.client.widgets.controls import build_sliders, EntryTable
from lume_epics.client.widgets.plots import Striptool, ImagePlot


# striptool data update callback
def striptool_update_callback():
    """
    Calls striptool update with the current global process variable.
    """
    global current_striptool_pv
    striptool.update(live_variable = current_striptool_pv)


def render_from_yaml(config_file, prefix: str, protocol: str, read_only=False, striptool_limit=50):

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


    # now build layout- organize by input/output variables


    input_title = Div(text="<h1 style='text-align:center;'>Live Model Inputs</h1>")
    output_title = Div(text="<h1 style='text-align:center;'>Live Model Outputs</h1>")

    layout = [row(input_title),]

    # add images
    images = []
    for variable in variable_output_images:
        image_title = Div(text=f"<h1 style='text-align:center;'>{variable.name}</h1>")

        image = ImagePlot([variable], controller, prefix)
        images.append(column(image_title, image.plot))
        callbacks.append(image.update)

        # create new row after 3
        if len(striptools) == 3:
            layout.append(row(*images))
            images = []

    if images:
        layout.append(row(*images))

    # build input striptools
    if read_only:
        striptools = []
        for variable in variable_input_scalars:

            striptool_title = Div(text=f"<h1 style='text-align:center;'>{variable.name}</h1>")

            striptool = Striptool([variable], controller, prefix, limit=striptool_limit)
            striptools.append(column(striptool_title, striptool.plot))
            callbacks.append(striptool.update)

            # create new row after 3
            if len(striptools) == 3:
                layout.append(row(*striptools))
                striptools = []


    # build sliders and value entry table
    else:
        control_row = []
        sliders = build_sliders(variable_input_scalars, controller, prefix)

        slider_stack = []
        for slider in sliders:

            slider_stack.append(slider.bokeh_slider)

            # add callback
            callbacks.append(slider.update)
            
        control_row.append(column(*slider_stack))

        # build value entry
        value_entry = EntryTable(input_value_vars, controller, prefix)

        control_row.append(column(value_entry.table, row(value_entry.submit_button, value_entry.clear_button)))
        layout.append(row(*control_row))

    table_row = []

    # add value table callback
    value_table = ValueTable(input_value_vars, controller, prefix)
    layout.append(row(value_table.table))
    callbacks.append(value_table.update)


    layout.append(row(output_title))

    # add output value table callback
    output_value_table = ValueTable(variable_output_scalars, controller, prefix)
    layout.append(row(output_value_table.table))
    callbacks.append(output_value_table.update)

    images = []
    for variable in variable_output_images:

        image_title = Div(text=f"<h1 style='text-align:center;'>{variable.name}</h1>")

        image = ImagePlot([variable], controller, prefix)
        images.append(column(image_title, image.plot))
        callbacks.append(image.update)

        # create new row after 3
        if len(striptools) == 3:
            layout.append(row(*images))
            images = []

    if images:
        layout.append(row(*images))

    # build output striptools
    if read_only:

        for variable in variable_output_scalars:

            striptool_title = Div(text=f"<h1 style='text-align:center;'>{variable.name}</h1>")

            striptool = Striptool([variable], controller, prefix, limit=striptool_limit)
            striptools.append(column(striptool_title, striptool.plot))
            callbacks.append(striptool.update)

            # create new row after 3
            if len(striptools) == 3:
                layout.append(row(*striptools))
                striptools = []

    else:
        output_striptool = Striptool(variable_output_scalars, controller, prefix, limit=striptool_limit)
        striptool_select = Select(
            title="Variable to plot:",
            value=output_striptool.live_variable,
            options=list(output_striptool.pv_monitors.keys()),
        )


        # add the selection callback
        # striptool_select.on_change("value", striptool_select_callback)
        layout.append(row(column(striptool_select, output_striptool.plot)))
        callbacks.append(output_striptool.update)

    return layout, callbacks
