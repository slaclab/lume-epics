from bokeh.io import curdoc
from bokeh import palettes
from bokeh.layouts import column, row
from bokeh.models import LinearColorMapper

from lume_epics.client.controller import Controller
from lume_model.utils import load_variables

from lume_epics.client.widgets.plots import ImagePlot
from lume_epics.client.widgets.controls import build_sliders
from lume_epics.client.controller import Controller

prefix = "test"
variable_filename = "examples/variables.pickle"

# load variables
input_variables, output_variables = load_variables(variable_filename)

# use all input variables for slider
# prepare as list for rendering
input_variables = list(input_variables.values())

# select our image output variable to render
output_variables = [output_variables["output1"]]

# set up controller
controller = Controller("ca") # can also use channel access

# build sliders
sliders = build_sliders(input_variables, controller, prefix)

# create image plot
image_plot = ImagePlot(output_variables, controller, prefix)

pal = palettes.viridis(256)
color_mapper = LinearColorMapper(palette=pal, low=0, high=256)

image_plot.build_plot(color_mapper=color_mapper)

# Set up image update callback
def image_update_callback():
    image_plot.update()
    

# render
curdoc().title = "Demo App"
curdoc().add_root(
            row(
                column([slider.bokeh_slider for slider in sliders], width=350), column(image_plot.plot)
                ) 
    )


curdoc().add_periodic_callback(image_update_callback, 250)
for slider in sliders:
    curdoc().add_periodic_callback(slider.update, 250)
