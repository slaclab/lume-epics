# lume-epics
Lume-epics is a dedicated API for serving LUME model variables with EPICS. 

## Model Development

The lume-epics server must be instantiated with a user defined class holding all methods necessary for model execution and the  input and output variables associated with the model. For the purpose of example, we consider a model that accepts two float inputs and returns a value sampled between the two inputs.

Our model expressed as a function:
```python
import numpy as np

def model(input_1, input_2):
    return np.random.uniform(input_1, input_2)
```

### Defining input and output variables

Model input and output variables are represented by [lume-model](https://github.com/slaclab/lume-model) variable representations. These variables enforce the minimal data requirements necessary for serving EPICS process variables associated with an online model. Lume-model defines two variable types: scalar and image. Each type has both an associated input and output class. Scalar variables hold float values while image variables hold two dimensional arrays. 

In order to appropriately interface with the EPICS server, scalar input variables must be assigned a range and default. When started, the server uses these defaults to execute the model and serve output variables based on the default execution. The range limits correspond the the low and high limits for EPICS graphics displays. During model execution, the current value of the variable is stored using the `value` attribute.

For our model, we must define two scalar input variables and one scalar output variable:
```python
from lume_model.variables import ScalarInputVariable, ScalarOutputVariable

input_1 = ScalarInputVariable(
    name="input_1", 
    default=1.0, 
    range=[0, 256]
)

input_2 = ScalarInputVariable(
    name="input_2", 
    default=2.0, 
    range=[0, 256]
)

output = ScalarOutputVariable(name="output")
```

### Defining the model

[Lume-model](https://github.com/slaclab/lume-model) includes a SurrogateModel base class to enforce the defined class's compatability with the lume-epics server. The primary function of this base class is to force the implementation of an evaluate method. This method must accept a list of `lume-model` input variables, execute the model, and return a list of `lume-model` output variables. Input variables and output variables must be defined as class attributes. They may be defined directly as class attributes or assigned in __init__.

For our model, we will construct a class that accepts and stores our input and output variables on initialization. Then, we implement an `evaluate` method that accepts an updated list of input variables, executes the model, and updates the output variable value appropriately. Place the following code in a file named `server.py`.
```python
from lume_epics.model import SurrogateModel
import numpy as np

class ExampleModel(SurrogateModel):
    def __init__(self, input_variables = [], output_variables = []):
        self.input_variables = input_variables
        self.output_variables = output_variables
    
    def evaluate(self, input_variables):
        self.input_variables = {input_variable.name: input_variable for input_variable in input_variables}
        self.output_variables["output"].value = np.random.uniform(
            self.input_variables["input_1"].value, self.input_variables["input_2"].value
        )
        return list(self.output_variables.values()
```

### Setting up the server

We can now use the EPICS server to serve our model. The EPICS server requires a model class, input variables, output variables, and a prefix for intantiation. By default, the server uses both the pvAccess and Channel Access protocols when serving the EPICS process variables. An optional keyword argument allows the server to be started using a single protocol (`protocols=["pva"]` for pvAccess, `protocols=["ca"]` for Channel Access). Once instantiated, the server is started using the `Server.start()` method, which has an optional monitor keyword argument, `monitor`, that controls thread execution. When `monitor=True`, the server is run in the main thread and may be stopped using keyboard interrupt (`Ctr+C`). If using `monitor=False`, the server can be stopped manually using the `Server.stop()` method. 

The input variables and output variables must be passed in the `model_kwargs` keyword argument because the model class accepts them in its `__init__` method. Arbitrary data may also be passed to the model with this approach.

The same variables and prefix used for instantiating the server must be used for building the client tooling. For the purpose of separability, these variables should be saved during model development and loaded on the client side. `lume-model.utils` contains utility functions for saving variables.

In our example, we can accomplish this by saving `input_variables` and `output_variables` before starting our server. Adding to `server.py`:

```python
from lume_epics.epics_server import Server
from lume_model.utils import save_variables

# create dictionary representations of input/output variables
input_variables = {
    "input_1": input_1,
    "input_2": input_2,
}

output_variables = {
    "output": output
}


# save variables
save_variables(input_variables, output_variables, "example_variables.pickle")

prefix = "test"
server = Server(
            ExampleModel, 
            input_variables, 
            output_variables, 
            prefix,
            model_kwargs = {"input_variables": input_variables, "output_variables": output_variables}
        )

# monitor = False does not loop in main thread and can be terminated 
# with server.stop()
server.start(monitor=True)
# Runs until keyboard interrupt.
```

### Setting up the client

A number of EPICS compatable widgets are included in `lume-epics`. Each widget accepts a controller used to monitor EPICS process variables. The controller is then used by a widget-specific monitor, which is responsible for formatting outputs of EPICS values into formats usable by the widget. There are currently slider, value table, image, and striptool widgets; however, more widgets could be configured using the base monitor and controller classes included in `lume_epics/client/`.

The controller fetches variables using a configurable protocol defined on instantiation. Variable assigment is done over both pvAccess and Channel Access protocols by default. The controller must be configured to reflect the corresponding server. If using a single protocol for serving, the controller must be set up to fetch using that protocol and the excluded protocol must be disabled manually using the appropriate `set_pva=False`, `set_ca=False` key word argument. The prefix used for serving must match the prefix used with the client.

For our client, we will load our saved variables and create a set of sliders for our inputs and a value table displaying the output variable. This code should be in a separate script from the server setup named `client.py`.  

```python
from lume_model.utils import load_variables
from lume_epics.client.controller import Controller
from lume_epics.client.widgets.tables import ValueTable
from lume_epics.client.widgets.controls import build_sliders


input_variables, output_variables = load_variables("example_variables.pickle")
prefix = "test"

# initialize controller to use pvAccess for variable gets
controller = Controller("pva")

# build sliders for the command process variable database
sliders = build_sliders(
            [input_variables["input_1"], input_variables["input_2"]],
            controller, 
            prefix
        )

# build value table
value_table = ValueTable(
                [output_variables["output"]], 
                controller, 
                prefix
)
```

To serve the widgets using bokeh, you must include the bokeh items in the document formatting. These are stored as attributes on the widget. Tutorials for serving these directly using the bokeh server and within Jupyter notebooks are included in Tutorials. For the purpose of this example, a bokeh application can be built by including the following:

```python
from bokeh.io import curdoc
from bokeh.layouts import column, row

# collect bokeh sliders from sliders
bokeh_sliders = [slider.bokeh_slider for slider in sliders]

# render
curdoc().title = "Demo App"
curdoc().add_root(
            row(
                column(bokeh_sliders, width=350), column(value_table.table)
                ) 
    )

curdoc().add_periodic_callback(value_table.update, 250)
# add callback for updating slider variable to reflect live variable value
for slider in sliders:
    curdoc().add_periodic_callback(slider.update, 250)
```

### Running the application

The application may now be executed using the following commands in separate windows:

``` $ python server.py ```

``` $ bokeh serve client.py --show```

## Image variables

Models with images can be constructed similarly to the above model.

The following example uses the two input variables defined in the above model to create an image from the distribution. In this case, the axis limits of the image output are fixed. This model can also be run using the Bokeh server demo.

In `server.py`:
```python
import numpy as np
from lume_model.variables import ScalarInputVariable, ImageOutputVariable
from lume_model.models import SurrogateModel
from lume_model.utils import save_variables

class ExampleModel(SurrogateModel):
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

from lume_epics.epics_server import Server
from lume_model.utils import save_variables

# save variables
save_variables(input_variables, output_variables, "example_variables.pickle")

prefix = "test"
server = Server(
            ExampleModel, 
            input_variables, 
            output_variables, 
            prefix,
            model_kwargs = {"input_variables": input_variables, "output_variables": output_variables}
        )

# monitor = False does not loop in main thread and can be terminated 
# with server.stop()
server.start(monitor=True)
# Runs until keyboard interrupt.
```


### Variable Associations

In the case that image variable axis bounds are dictated by the output of other variables, associations can be created between the bound scalar variable and the axis values of the image variables. This is accomplished by defining the `parent` attribute on the bound variables and assigning the corresponding variable name to the bound variable attributes of the image variable.

For example, the following variables indicate that `x_min`, `x_max`, `y_min`, and `y_max` define the axis limits of the image output `image_output`:
```python
x_min = ScalarOutputVariable(
            name="x_min",
            parent="image_output"
        )

x_max = ScalarOutputVariable(
            name="x_max",
            parent="image_output"
        )

y_min = ScalarOutputVariable(
            name="y_min",
            parent="image_output"
        ),
y_max = ScalarOutputVariable(
            name="y_max"
            parent="image_output"
        )

image_output = ImageOutputVariable(
    name="image_output", 
    axis_labels=["value_1", "value_2"], 
    axis_units=["mm", "mm"], 
    x_min_variable="x_min",
    x_max_variable="x_max", 
    y_min_variable="y_min", 
    y_max_variable="y_max"
)
```
