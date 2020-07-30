# lume-epics
Lume-epics is a dedicated API for serving LUME model variables with EPICS. 

## Model Development
Model input and output variables are represented by [lume-model](https://github.com/slaclab/lume-model) variable representations. These variables enforce the minimal data requirements necessary for serving EPICS process variables associated with an online model. Lume-model defines two variable types: scalar and image. Scalar variables hold float values while image variables hold two dimensional arrays. The lume-epics server must be instantiated with a user defined class holding all methods necessary for model execution.

Lume-model also defines a SurrogateModel base class to enforce the defined class's compatability with the lume-epics server. The primary function of this base class is to force the implementation of an evaluate method. This method must accept a list of lume-model input variables, execute the model, and return a list of output variables. Input variables and output variables must be defined as class attributes. They may be defined directly as class attributes or assigned in __init__.

Below is an example of an model defined using class attributes.
```
from lume_epics.model import SurrogateModel
from lume_model.variables import ScalarInputVariable, ImageOutputVariable

class ExampleModel(SurrogateModel):
    input_variables = {
        "input1": ScalarInputVariable(
                    name="input1", 
                    default=1, 
                    range=[0, 256]
                ),
        "input2": ScalarInputVariable(
                    name="input2", 
                    default=2, 
                    range=[0, 256]
                ),
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
    
    def evaluate(self, input_variables):
        self.output_variables["output1"].value = np.random.uniform(
            input_variables["input1"].value, # lower dist bound
            input_variables["input2"].value, # upper dist bound
            (50,50)
        ) #shape
        

        return list(self.output_variables.values()
```

## Variable Associations

In the case that image variable axis bounds are dictated by the output of other variables, associations can be created between the bound scalar variable and the axis values of the image variables. This is accomplished by defining the `parent` attribute on the bound variables and assigning the corresponding variable name to the bound variable attributes of the image variable.

For example:
```
x_min = ScalarOutputVariable(
            name="x_min"
        )

x_max = ScalarOutputVariable(
            name="x_max"
        )

y_min = ScalarOutputVariable(
            name="y_min"
        ),
y_max = ScalarOutputVariable(
            name="y_max"
        )

image_input = ImageOutputVariable(
    name="output1", 
    axis_labels=["value_1", "value_2"], 
    axis_units=["mm", "mm"], 
    x_min_variable="x_min",
    x_max_variable="x_max", 
    y_min_variable="y_min", 
    y_max_variable="y_max"
)
```

## Server

The EPICS server requires a model class, input variables, output variables, and a prefix for intantiation. By default, the server uses both the pvAccess and Channel Access protocols when serving the EPICS process variables.An optional keyword argument allows the server to be started using a single protocol (`protocols=["pva"]` for pvAccess, `protocols=["ca"]` for Channel Access). Once instantiated, the server is started using the `Server.start()` method, which has an optional monitor keyword argument, `monitor`, that controls thread execution. When `monitor=True`, the server is run in the main thread and may be stopped using keyboard interrupt (`Ctr+C`). If using `monitor=False`, the server can be stopped manually using the `Server.stop()` method. 

```
from lume_epics.epics_server import Server

prefix = "test"
server = Server(
            DemoModel, 
            DemoModel.input_variables, 
            DemoModel.output_variables, 
            prefix
        )
# monitor = False does not loop in main thread and can be terminated 
# with server.stop()
server.start(monitor=True)
# Runs until keyboard interrupt.
```

## Client

A number of EPICS compatable widgets are included in lume-epics. Each widget accepts a controller used to monitor EPICS process variables. The controller is then used by a widget-specific monitor, which is responsible for formatting outputs of EPICS values into formats usable by the widget. There are currently slider, value table, image, and striptool widgets; however, more widgets could be configured using the base monitor and controller classes included in `lume_epics/client/`.

The controller fetches variables using a configurable protocol defined on instantiation.Variable assigment is done over both pvAccess and Channel Access protocols by default. The controller must be configured to reflect the corresponding server. If using a single protocol for serving, the controller must be set up to fetch using that protocol and the excluded protocol must be disabled manually using the appropriate `set_pva=False`, `set_ca=False` key word argument.

The same variables and prefix used for instantiating the server must be used for building the client tooling. For the purpose of separability, these variables should be saved during model development and loaded on the client side. `lume-model.utils` contains utility functions for saving variables. 

Example of client tooling:
```
from lume_model.variables import ScalarInputVariable, ScalarOutputVariable, ImageOutputVariable
from lume_epics.client.controller import Controller
from lume_epics.client.widgets.plots import ImagePlot, Striptool
from lume_epics.client.widgets.tables import ValueTable
from lume_epics.client.widgets.controls import build_sliders


input_variables = {
    "input1": ScalarInputVariable(
                name="input1", 
                value=1, 
                default=1, 
                range=[0.0, 5.0]
            ),
    "input2": ScalarInputVariable(
                name="input2", 
                value=2, 
                default=2, 
                range=[0.0, 5.0]
            ),
}

output_variables = {
    "output1": ScalarOutputVariable(name="output1"),
    "output2": ScalarOutputVariable(name="output2"),
    "output3": ImageOutputVariable(
        name="output3",
        default=np.array([[1, 2,], [3, 4]]),
        axis_labels=["count_1", "count_2"],
        x_min=0,
        y_min=0,
        x_max=5,
        y_max=5,
    ),
}

prefix = "test"

# initialize controller to use pvAccess for variable gets
controller = Controller("pva")

# build sliders for the command process variable database
sliders = build_sliders(
            input_variables["input1], 
            input_variables["input2], 
            controller, 
            prefix
        )

# build value table
value_table = ValueTable(
                [output_variables["output1], output_variables["output2], 
                controller, 
                prefix
            )

# build image plot
value_table = ImagePlot([output_variables["output3]], controller, prefix)

# build striptool
striptool = Striptool(
                [output_variables["output1], output_variables["output2], 
                controller, 
                prefix
            )


# Finally, terminate the controller
controller.close()
```

To serve the widgets using bokeh, you must include their bokeh items in the document formatting. These are stored as attributes on the widget. Tutorials for serving these directly using the bokeh server and within Jupyter notebooks are included in Tutorials.