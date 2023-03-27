from lume_epics.epics_server import Server
from lume_model.utils import model_from_yaml
from lume_epics.utils import config_from_yaml
from pathlib import Path
import json
from botorch.models.transforms.input import AffineInputTransform
import torch
from pprint import pprint

if __name__ == "__main__":
    # load the model and the variables from LUME model
    with open("examples/files/california_config.yml", "r") as f:
        model_class, model_kwargs = model_from_yaml(f, load_model=False)

    # load the EPICS pv definitions
    with open("examples/files/california_epics_config.yml", "r") as f:
        epics_config = config_from_yaml(f)

    # load the transformers required for the model
    with open("examples/files/california_normalization.json", "r") as f:
        normalizations = json.load(f)

    input_transformer = AffineInputTransform(
        len(normalizations["x_mean"]),
        coefficient=torch.tensor(normalizations["x_scale"]),
        offset=torch.tensor(normalizations["x_mean"]),
    )
    output_transformer = AffineInputTransform(
        len(normalizations["y_mean"]),
        coefficient=torch.tensor(normalizations["y_scale"]),
        offset=torch.tensor(normalizations["y_mean"]),
    )

    # update the model kwargs with the transformers
    model_kwargs["input_transformers"] = [input_transformer]
    model_kwargs["output_transformers"] = [output_transformer]

    # start the EPICS server
    server = Server(model_class, epics_config, model_kwargs=model_kwargs)

    # monitor = False does not loop in main thread
    server.start(monitor=True)
