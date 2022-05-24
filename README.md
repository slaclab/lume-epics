# lume-epics
Lume-epics is a dedicated API for serving LUME model variables with EPICS. Configurations for LUME model variables can be found in [lume-model](https://github.com/slaclab/lume-model).

# Installation

Lume-epics may be installed via conda on the `conda-forge` channel:
<br>
``` $ conda install lume-epics -c conda-forge ```
<br>


Alternatively, you may install from the GitHub repository using:
<br>
``` $ pip install https://github.com/slaclab/lume-epics.git ```
<br>

## Server

The EPICS server requires a model class, model_kwargs, and an epics configuration for instantiation. Once instantiated, the server is started using the `Server.start()` method, which has an optional monitor keyword argument, `monitor`, that controls thread execution. When `monitor=True`, the server is run in the main thread and may be stopped using keyboard interrupt (`Ctr+C`). If using `monitor=False`, the server can be stopped manually using the `Server.stop()` method.

```python
from lume_epics.epics_server import Server
from lume_model.utils import variables_from_yaml
from lume_epics.utils import config_from_yaml
import os
from examples.model import DemoModel

import logging


if __name__ == "__main__":
    with open("examples/files/demo_config.yml", "r") as f:
        input_variables, output_variables = variables_from_yaml(f)

    with open("examples/files/epics_config.yml", "r") as f:
        epics_config = config_from_yaml(f)

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
```

## Compatable models
See docs for notes on serving online models with lume-epics.
