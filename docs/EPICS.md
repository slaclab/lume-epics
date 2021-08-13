# EPICS configuration

The environment variables passed to the server subprocesses may be specified directly in the server construction. Otherwise, the variables will be inherited from the shell environment variables, defaulting to EPICS defaults in their absence. The following example may be run from the repository root:


```python
from examples.model import DemoModel
from lume_epics.epics_server import Server
from lume_model.utils import variables_from_yaml

with open("examples/files/demo_config.yml", "r") as f:
    input_variables, output_variables = variables_from_yaml(f)

prefix = "test"
server = Server(
    DemoModel,
    prefix,
    model_kwargs={"input_variables": input_variables, "output_variables": output_variables},
    epics_config={"EPICS_CA_SERVER_PORT": 63000, "EPICS_PVA_SERVER_PORT": 63001}
)
# monitor = False does not loop in main thread
server.start(monitor=True)
```

A description of the channel access variables may be found [here](https://epics.anl.gov/base/R3-14/12-docs/CAref.html#EPICS). pvAccess variables take a similar form (substituting PVA for CA).
