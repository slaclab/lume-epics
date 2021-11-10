from examples.model import DemoModel
from lume_epics.epics_server import Server
from lume_model.utils import variables_from_yaml

with open("examples/files/demo_config.yml", "r") as f:
    input_variables, output_variables = variables_from_yaml(f)

prefix = "test"

if __name__ == "__main__":
    server = Server(
        DemoModel,
        prefix,
        model_kwargs={
            "input_variables": input_variables,
            "output_variables": output_variables,
        },
    )
    # monitor = False does not loop in main thread
    server.start(monitor=True)
