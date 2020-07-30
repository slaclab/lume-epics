from examples.model import DemoModel
from lume_epics.epics_server import Server
from lume_model.utils import load_variables

variable_filename = "examples/variables.pickle"
input_variables, output_variables = load_variables(variable_filename)

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