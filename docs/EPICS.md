# EPICS configuration


The server expects a dictionary defining the EPICS configuration for each model input and output variable. This may be loaded using the utility function `config_from_yaml(file)` packaged in `lume_epics.utils`. The YAML file should be structured as below:


```yaml
input_variables:
  input1:
    pvname: test:input1
    protocol: ca
    serve: false

  input2:
    pvname: test:input2
    protocol: pva

output_variables:
  output1:
    pvname: test:output1
    protocol: pva

  output2:
    pvname: test:output2
    protocol: pva

  output3:
    pvname: test:output3
    protocol: pva
```

The optional field `serve` for each variable accepts a boolean defaulting to true. If false, this assumes that the PV is hosted externally monitors will be used to execute the model on changes to variable values.

The client controller `lume_epics.client.controller.Controller` is also initialized using the EPICS configuration dictionary and a common file may be used for a project, though the serve field is unimportant to the controller.

Over pvAccess, you also have the option to host a summary process variable:

```yaml
input_variables:
  input1:
    pvname: test:input1
    protocol: ca
    serve: false

  input2:
    pvname: test:input2
    protocol: pva

output_variables:
  output1:
    pvname: test:output1
    protocol: pva

  output2:
    pvname: test:output2
    protocol: pva

  output3:
    pvname: test:output3
    protocol: pva

summary:
  pvname: test:summary_variable
  owner: Jacqueline Garrahan
  date_published: 1/27/22
  description: A basic epics configuration
  id: model1
```


You can also serve output variables as a pvAccess structure:

```yaml
input_variables:
  input1:
    pvname: test:input1
    protocol: ca
    serve: false

  input2:
    pvname: test:input2
    protocol: pva

output_variables:
  pvname: test:output
  protocol: pva
  fields:
    - output1
    - output2
    - output3

summary:
  pvname: test:summary_variable
  owner: Jacqueline Garrahan
  date_published: 1/27/22
  description: A basic epics configuration
  id: model1
```


## EPICS environment configuration

The environment variables passed to the server subprocesses may be specified directly in the server construction. Otherwise, the variables will be inherited from the shell environment variables, defaulting to EPICS defaults in their absence. The following example may be run from the repository root:


```python
from examples.model import DemoModel
from lume_epics.epics_server import Server
from lume_epics.utils import config_from_yaml
from lume_model.utils import variables_from_yaml

# must use main conditional due to multiprocess spawning
if __name__ == "__main__":
    with open("examples/files/demo_config.yml", "r") as f:
        input_variables, output_variables = variables_from_yaml(f)

    with open("examples/files/epics_config.yml", "r") as f:
        epics_config = config_from_yaml(f)

    prefix = "test"
    server = Server(
        DemoModel,
        epics_config,
        model_kwargs={"input_variables": input_variables, "output_variables": output_variables},
        epics_config={"EPICS_CA_SERVER_PORT": 63000, "EPICS_PVA_SERVER_PORT": 63001}
    )
    # monitor = False does not loop in main thread
    server.start(monitor=True)
```

A description of the channel access variables may be found [here](https://epics.anl.gov/base/R3-14/12-docs/CAref.html#EPICS). pvAccess variables take a similar form (substituting PVA for CA).
