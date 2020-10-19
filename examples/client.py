from bokeh.io import curdoc
from bokeh import palettes
from bokeh.layouts import column, row
from bokeh.models import LinearColorMapper

from lume_epics.client.controller import Controller
from lume_model.utils import variables_from_yaml

from lume_epics.client.widgets.plots import ImagePlot, Striptool
from lume_epics.client.widgets.controls import build_sliders, EntryTable
from lume_epics.client.controller import Controller

prefix = "test"

# load variables
with open("examples/files/demo_config.yaml", "r") as f:
    input_variables, output_variables = variables_from_yaml(f)

# use all input variables for slider
# prepare as list for rendering
input_variables = list(input_variables.values())

# select our image output variable to render
image_output = [output_variables["output1"]]

# set up controller
controller = Controller("ca")  # can also use channel access

# build sliders
sliders = build_sliders(input_variables, controller, prefix)

# create image plot
image_plot = ImagePlot(image_output, controller, prefix)

pal = palettes.viridis(256)
color_mapper = LinearColorMapper(palette=pal, low=0, high=256)
image_plot.build_plot(color_mapper=color_mapper)

striptool = Striptool(
    [output_variables["output2"], output_variables["output3"]], controller, prefix
)
entry_table = EntryTable(input_variables, controller, prefix)

# Set up image update callback
def image_update_callback():
    image_plot.update()


# render
curdoc().title = "Demo App"
curdoc().add_root(
    column(
        row(
            column([slider.bokeh_slider for slider in sliders], width=350),
            column(image_plot.plot),
        ),
        row(
            entry_table.table,
            column(entry_table.clear_button, entry_table.submit_button),
        ),
        row(striptool.plot, striptool.selection, striptool.reset_button),
    )
)


curdoc().add_periodic_callback(image_plot.update, 250)
for slider in sliders:
    curdoc().add_periodic_callback(slider.update, 250)
curdoc().add_periodic_callback(striptool.update, 250)
