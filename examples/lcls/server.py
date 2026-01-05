import numpy as np
import yaml
import argparse
from lume_model.base import LUMEBaseModel
from lume_model.utils import variables_from_yaml
from lume_epics.utils import config_from_yaml
from lume_epics.epics_server import Server
from common.p4p_server import SimpleSimServer

from pathlib import Path

class AmplSummationModel(LUMEBaseModel):
    def __init__(self):
        variable_path = Path(__file__).parent / "variables.yml"

        with variable_path.open() as f:
            input_variables, output_variables = variables_from_yaml(variable_path)

        super().__init__(input_variables=input_variables, output_variables=output_variables)

    def _evaluate(self, input_dict: dict) -> dict:
        return {
            "summation": float(sum(input_dict.values()))
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--standalone', action='store_true', help='Spins up an internal EPICS PVA server to simulate the PVs used by this test')
    args = parser.parse_args()
    
    # Spin up P4P server if requested
    if args.standalone:
        with open(Path(__file__).parent / "sim_config.yml") as fp:
            config = yaml.safe_load(fp)
        sim_server = SimpleSimServer(config)
        sim_server.update_env()

    # load epics configuration
    epics_path = Path(__file__).parent / "epics_config.yml"
    epics_config = config_from_yaml(Path(__file__).parent / "epics_config.yml")

    server = Server(
        AmplSummationModel,
        epics_config,
    )
    # monitor = False does not loop in main thread
    server.start(monitor=True)

    if sim_server:
        sim_server.stop()