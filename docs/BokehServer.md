# Bokeh-serve client tutorial

For this tutorial, we will create a simple model which generates an image from sampled from a uniform distribution between the two scalar input variables. This model will be served using the lume-epics server and a bokeh client will be used to display simple sliders for controlling the image, and the image output. 

## Set up conda environment

`$ conda create -n lume-epics-demo python=3.7`

`$ conda install numpy `

Install lume-model and lume-epics from the `jrgarrahan` conda channel.

`$ conda install lume-model lume-epics -c jrgarrahan`

## Create model

Create a new file named `model.py`. At the top of the file, import the `lume-model` `SurrogateModel` base class, `lume-model` `ScalarInputVariable` and `ImageOutputVariable`. 


## Create server

Create a file that will be used to serve your model.





```
import numpy as np
from lume_epics.epics_server import Server
from lume_epics.model import SurrogateModel
from lume_model.utils import save_variables
from test.MySurrogateModel import MySurrogateModel

prefix = "test"
stock_image_input = np.load("test/example_input_image.npy")
model_file = "test/CNN_060420_SurrogateModel.h5"
model_kwargs= {"model_file": model_file, "stock_image_input": stock_image_input}
import logging
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


variable_filename = "test/surrogate_model_variables.pickle"
save_variables(MySurrogateModel.input_variables, MySurrogateModel.output_variables,  variable_filename)


server = Server(MySurrogateModel, MySurrogateModel.input_variables, MySurrogateModel.output_variables, prefix, model_kwargs=model_kwargs, protocols=["ca"])
# monitor = False does not loop in main thread
server.start(monitor=True)
```





```
from bokeh.io import output_notebook, show
from bokeh import palettes
from bokeh.layouts import column, row
from bokeh.models import LinearColorMapper
from bokeh.io import curdoc
import sys, os

import logging
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


# fix for bokeh path error, maybe theres a better way to do this
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/..")

from lume_epics.client.widgets.plots import ImagePlot
from lume_epics.client.widgets.sliders import build_sliders
from lume_epics.client.controller import Controller
from lume_model.utils import load_variables



prefix = "test"
variable_filename =  "test/surrogate_model_variables.pickle"
input_variables, output_variables = load_variables(variable_filename)


 # build sliders for the command process variable database
inputs = [input_variables["phi(1)"], 
          input_variables["maxb(2)"], 
          input_variables["laser_radius"],
          input_variables["total_charge:value"],
         ]
controller = Controller("ca") # can also use channel access
sliders = build_sliders(inputs, controller, prefix)

# create image plot
output_variables = [output_variables["x:y"]]
image_plot = ImagePlot(output_variables, controller, prefix)

pal = palettes.viridis(256)
#color_mapper = LinearColorMapper(palette=pal, low=0, high=256)

image_plot.build_plot(palette=pal)

# Set up image update callback
def image_update_callback():
    image_plot.update()


# function for rendering the application in the bokeh server

curdoc().title = "Demo App"
curdoc().add_root(
            row(
                column(sliders, width=350), column(image_plot.plot)
                ) 
    )


curdoc().add_periodic_callback(image_update_callback, 250)
```