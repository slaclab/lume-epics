# Bokeh-serve client tutorial

For this tutorial, we will create a simple model which generates an image from sampled from a uniform distribution between the two scalar input variables. This model will be served using the lume-epics server and a bokeh client will be used to display simple sliders for controlling the image, and the image output. 

### Note: 
The code for this example can be found in [lume-epics/examples](https://github.com/slaclab/lume-epics/examples)


## Set up conda environment

`$ conda create -n lume-epics-demo python=3.7`

`$ conda activate lume-epics-demo`

`$ conda install numpy `

Install lume-model and lume-epics from the `jrgarrahan` conda channel:

`$ conda install lume-model lume-epics -c jrgarrahan`

## Create model

Create a new file named `model.py`. At the top of the file, import the `lume-model` `SurrogateModel` base class, `lume-model` `ScalarInputVariable` and `ImageOutputVariable`, `numpy`, and the `lume-model` `save_variables` utility.

```python
import numpy as np
from lume_model.variables import ScalarInputVariable, ImageOutputVariable
from lume_model.models import SurrogateModel
from lume_model.utils import save_variables
```

Next, define the demo model. Here, we define the input and output variables as keyword arguments. In order for the evaluate method to execute correctly, these 
passed variables must be dictionaries of variables with corresponding types and names. These could also be defined as class attributes.

```python
class DemoModel(SurrogateModel):
    def __init__(self, input_variables=None, output_variables=None):
        self.input_variables = input_variables
        self.output_variables = output_variables

    def evaluate(self, input_variables):
        self.output_variables["output1"].value = np.random.uniform(
            self.input_variables["input1"].value, # lower dist bound
            self.input_variables["input2"].value, # upper dist bound
            (50,50)
        )

        return list(self.output_variables.values())
```

Now, we use the main method to define and save the input and output variables. This is done in the main method because the server will import and execute the `DemoModel` class. 

```python
if __name__ == "__main__":
    input_variables = {
        "input1": ScalarInputVariable(
            name="input1", 
            value=1, 
            default=1, 
            range=[0, 256]
        ),
        "input2": ScalarInputVariable(
            name="input2", 
            value=2, 
            default=2, 
            range=[0, 256]),
    }

    output_variables = {
        "output1": ImageOutputVariable(
            name="output1", 
            axis_labels=["value_1", "value_2"], 
            axis_units=["mm", "mm"], 
            x_min=0, 
            x_max=50, 
            y_min=0, 
            y_max=50
        )
    }

    variable_filename = "variables.pickle"

    save_variables(
        input_variables, 
        output_variables, 
        variable_filename
    )
```

## Create server

Create a new file named `server.py`. Import the `DemoModel`, load the variables, and configure the server. 

```python
from examples.model import DemoModel
from lume_epics.epics_server import Server
from lume_model.utils import load_variables

variable_filename = "variables.pickle"
input_variables, output_variables = load_variables(variable_filename)

# pass the input + output variable to initialize the classs
model_kwargs = {
    "input_variables": input_variables,
    "output_variables": output_variables
}

prefix = "test"
server = Server(
    DemoModel, 
    input_variables, 
    output_variables, 
    prefix,
    model_kwargs=model_kwargs
)
# monitor = False does not loop in main thread
server.start(monitor=True)
```

## Set up the client

Create a new file named `client.py`. Add the following imports:

```python
from bokeh.io import curdoc
from bokeh import palettes
from bokeh.layouts import column, row
from bokeh.models import LinearColorMapper

from lume_epics.client.controller import Controller
from lume_model.utils import load_variables

from lume_epics.client.widgets.plots import ImagePlot
from lume_epics.client.widgets.controls import build_sliders
from lume_epics.client.controller import Controller
```

Set up the `Controller` for interfacing with EPICS process variables:

```python
controller = Controller("ca")
```

Load variables from your variable file:
```python
input_variables, output_variables = load_variables("variables.pickle")
```

Prepare sliders:
```python
prefix = "test"

# use all input variables for slider
# prepare as list for rendering
input_variables = list(input_variables.values())

# build sliders
sliders = build_sliders(input_variables, controller, prefix)
```

Setup the image output variable:
```python
output_variables = list(output_variables.values())

# create image plot
image_plot = ImagePlot(output_variables, controller, prefix)

# build plot using a bokeh color map
pal = palettes.viridis(256)
color_mapper = LinearColorMapper(palette=pal, low=0, high=256)

image_plot.build_plot(color_mapper=color_mapper)
```

The image plot will require a callback to continually update the plot to display the lates process variables. Here we define the callback function:
```python
# Set up image update callback
def image_update_callback():
    image_plot.update()

```
Render the application using bokeh `curdoc()` function. The image_plot object's `plot` attribute must be used in formatting:

```python
curdoc().title = "Demo App"
curdoc().add_root(
            row(
                column(sliders, width=350), column(image_plot.plot)
                ) 
    )

curdoc().add_periodic_callback(image_update_callback, 250)
```

# Run demo
Now, open two terminal windows and navigate to the directory with your demo files. Activate the `lume-epics-demo` environment. In the first, execute the command:

` $ python example/server.py`

In the second, serve the bokeh client using the command:

` $ bokeh serve --show example/client.py`

A browser window will display the user interface. Both the client and server may be terminated with keyboard interrupt (`Ctrl+C`).

