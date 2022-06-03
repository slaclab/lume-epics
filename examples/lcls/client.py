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
from pathlib import Path

variable_path = Path(__file__).parent / "variables.yml"

with variable_path.open() as f:
    input_variables, output_variables = variables_from_yaml(f)

# load epics configuration
epics_path = Path(__file__).parent / "epics_config.yml"

with epics_path.open() as f:
    epics_config = config_from_yaml(f)

# create controller from epics config
controller = Controller(epics_config)

# prepare as list for rendering
input_variables = list(input_variables.values())
output_variables = list(output_variables.values())

input_value_table = ValueTable(input_variables, controller)
output_value_table = ValueTable(output_variables, controller)

title_div = Div(
    text=f"<b>LCLS ampl sum: Last  update {controller.last_update}</b>",
    style={
        "font-size": "150%",
        "color": "#3881e8",
        "text-align": "center",
        "width": "100%",
    },
)


def update_div_text():
    global controller
    title_div.text = f"<b>LCLS ampl sum: Last  update {controller.last_update}</b>"


# render
curdoc().title = "LCLS ampl"
curdoc().add_root(
    column(
        row(column(title_div)),
        row(input_value_table.table, output_value_table.table),
    )
)

# must add refresh callbacks
curdoc().add_periodic_callback(input_value_table.update, 250)
curdoc().add_periodic_callback(output_value_table.update, 250)
