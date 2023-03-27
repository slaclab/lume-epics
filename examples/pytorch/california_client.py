from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import Div, Button

from lume_epics.client.controller import Controller
from lume_model.utils import variables_from_yaml
from lume_epics.utils import config_from_yaml

from lume_epics.client.widgets.tables import ValueTable
from lume_epics.client.widgets.controls import build_sliders
from lume_epics.client.controller import Controller

# load the model and the variables from LUME model
with open("examples/files/california_config.yml", "r") as f:
    input_variables, output_variables = variables_from_yaml(f)

# load the EPICS pv definitions
with open("examples/files/california_epics_config.yml", "r") as f:
    epics_config = config_from_yaml(f)

# create controller from epics config
controller = Controller(epics_config)

# prepare as list for rendering
# define the variables that have range to make as sliders
sliding_variables = [
    input_var
    for input_var in input_variables.values()
    if input_var.value_range[0] != input_var.value_range[1]
]
input_variables = list(input_variables.values())
output_variables = list(output_variables.values())

# define the plots we want to see - sliders for all input values
# and tables summarising the current state of the inputs and
# output values
sliders = build_sliders(sliding_variables, controller)
input_value_table = ValueTable(input_variables, controller)
output_value_table = ValueTable(output_variables, controller)


title_div = Div(
    text=f"<b>California Housing Prediction: Last  update {controller.last_update}</b>",
    style={
        "font-size": "150%",
        "color": "#3881e8",
        "text-align": "center",
        "width": "100%",
    },
)


def update_div_text():
    global controller
    title_div.text = (
        f"<b>California Housing Prediction: Last  update {controller.last_update}</b>"
    )


def reset_slider_values():
    for slider in sliders:
        slider.reset()


slider_reset_button = Button(label="Reset")
slider_reset_button.on_click(reset_slider_values)

# render
curdoc().title = "California Housing Prediction"
curdoc().add_root(
    column(
        row(column(title_div, width=600)),
        row(
            column(
                [slider_reset_button] + [slider.bokeh_slider for slider in sliders],
                width=350,
            ),
            column(input_value_table.table, output_value_table.table, width=350),
        ),
    ),
)

# add refresh callbacks to ensure that the values are updated
# curdoc().add_periodic_callback(image_plot.update, 1000)
for slider in sliders:
    curdoc().add_periodic_callback(slider.update, 1000)
curdoc().add_periodic_callback(update_div_text, 1000)
curdoc().add_periodic_callback(input_value_table.update, 1000)
curdoc().add_periodic_callback(output_value_table.update, 1000)
