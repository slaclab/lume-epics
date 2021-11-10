from lume_epics.epics_server import Server
from lume_model.utils import variables_from_yaml
import os
from examples.model import DemoModel

import logging


if __name__ == "__main__":
    with open("examples/files/demo_config.yml", "r") as f:
        input_variables, output_variables = variables_from_yaml(f)

    prefix = "test"
    server = Server(
        DemoModel,
        prefix,
        model_kwargs={
            "input_variables": input_variables,
            "output_variables": output_variables,
        },
        read_only=True,
        protocols=["ca"],
    )
    # monitor = False does not loop in main thread
    server.start(monitor=True)
