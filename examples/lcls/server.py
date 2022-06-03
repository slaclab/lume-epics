import numpy as np
from lume_model.models import BaseModel
from lume_model.utils import variables_from_yaml
from lume_epics.utils import config_from_yaml
from lume_epics.epics_server import Server
from pathlib import Path


class AmplSummationModel(BaseModel):
    def __init__(self):

        variable_path = Path(__file__).parent / "variables.yml"

        with variable_path.open() as f:
            input_variables, output_variables = variables_from_yaml(f)

        self.input_variables = input_variables
        self.output_variables = output_variables

    def evaluate(self, input_variables):

        summation = sum([var.value for var in input_variables.values()])
        self.output_variables["summation"].value = summation

        return self.output_variables


if __name__ == "__main__":
    # load epics configuration
    epics_path = Path(__file__).parent / "epics_config.yml"

    with epics_path.open() as f:
        epics_config = config_from_yaml(f)

    server = Server(
        AmplSummationModel,
        epics_config,
    )
    # monitor = False does not loop in main thread
    server.start(monitor=True)
