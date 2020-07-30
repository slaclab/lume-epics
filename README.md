# lume-epics
Lume-epics is a dedicated API for serving LUME model variables with EPICS. Configurations for LUME model variables can be found in [lume-model](https://github.com/slaclab/lume-model).

## Requirements
* Python >= 3.7
* EPICS >= 4

## Server
The EPICS server requires a model class, input variables, output variables, and a prefix for intantiation. By default, the server uses both the pvAccess and Channel Access protocols when serving the EPICS process variables. An optional keyword argument allows the server to be started using a single protocol (`protocols=["pva"]` for pvAccess, `protocols=["ca"]` for Channel Access). Once instantiated, the server is started using the `Server.start()` method, which has an optional monitor keyword argument, `monitor`, that controls thread execution. When `monitor=True`, the server is run in the main thread and may be stopped using keyboard interrupt (`Ctr+C`). If using `monitor=False`, the server can be stopped manually using the `Server.stop()` method. 

```
from lume_epics.epics_server import Server

prefix = "test"
server = Server(
            DemoModel, 
            DemoModel.input_variables, 
            DemoModel.output_variables, 
            prefix
        )
# monitor = False does not loop in main thread and can be terminated 
# with server.stop()
server.start(monitor=True)
# Runs until keyboard interrupt.
```

## Compatable models
See docs for notes on serving online models with lume-epics.
