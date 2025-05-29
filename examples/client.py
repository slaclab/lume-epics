from bokeh.io import curdoc
from bokeh import palettes
from bokeh.layouts import column, row
from bokeh.models import LinearColorMapper, Div

from lume_epics.client.controller import Controller
from lume_model.utils import variables_from_yaml
from lume_epics.utils import config_from_yaml

from lume_epics.client.widgets.plots import ImagePlot, Striptool
from lume_epics.client.widgets.tables import ValueTable
from lume_epics.client.widgets.controls import build_sliders, EntryTable
from lume_epics.client.controller import Controller


# load variables
input_variables, output_variables = variables_from_yaml("examples/files/demo_config.yml")

# load epics config
epics_config = config_from_yaml("examples/files/epics_config.yml")

controller = Controller(epics_config)

input_variable_names = list(input_variables.keys())
output_variable_names = list(output_variables.keys())


# use all input variables for slider
# prepare as list for rendering
input_variables = list(input_variables.values())

# build sliders
sliders = build_sliders(input_variables, controller)

striptool = Striptool(
    [output_variables["output1"], output_variables["output2"]], controller
)

entry_table = EntryTable(input_variables, controller)
value_table = ValueTable(input_variables, controller)

# set sizes
striptool.plot.height = 400
striptool.plot.width = 450

title_div = Div(
    text=f"<b>Demo app: Last  update {controller.last_update}</b>",
    style={
        "font-size": "150%",
        "color": "#3881e8",
        "text-align": "center",
        "width": "100%",
    },
)


def update_div_text():
    global controller
    title_div.text = f"<b>Demo app: Last  update {controller.last_update}</b>"


# render
curdoc().title = "Demo App"
curdoc().add_root(
    column(
        row(column(title_div)),
        row(
            column([slider.bokeh_slider for slider in sliders], width=350),
            column(striptool.selection, striptool.reset_button, striptool.plot),
        ),
        row(
            column(
                entry_table.table, entry_table.clear_button, entry_table.submit_button
            ),
            value_table.table,
        ),
    )
)

for slider in sliders:
    curdoc().add_periodic_callback(slider.update, 250)
curdoc().add_periodic_callback(striptool.update, 250)
curdoc().add_periodic_callback(update_div_text, 250)
curdoc().add_periodic_callback(value_table.update, 250)
