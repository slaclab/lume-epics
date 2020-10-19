from examples.model import DemoModel
from lume_epics.epics_server import Server
from lume_model.utils import variables_from_yaml

with open("examples/files/demo_config.yaml", "r") as f:
    input_variables, output_variables = variables_from_yaml(f)

model = DemoModel(input_variables=input_variables, output_variables=output_variables)
prefix = "test"
server = Server(
    model,
    prefix,
)
# monitor = False does not loop in main thread
server.start(monitor=True)