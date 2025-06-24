from lume_epics.epics_server import Server
from lume_model.utils import variables_from_yaml
from lume_epics.utils import config_from_yaml
import os
from examples.model import DemoModel

import logging


if __name__ == "__main__":
    input_variables, output_variables = variables_from_yaml("examples/files/demo_config.yml")
    epics_config = config_from_yaml("examples/files/epics_config.yml")

    server = Server(
        DemoModel,
        epics_config,
        model_kwargs={
            "input_variables": input_variables,
            "output_variables": output_variables,
        },
    )
    # monitor = False does not loop in main thread
    server.start(monitor=True)
