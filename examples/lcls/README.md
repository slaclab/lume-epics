# LCLS Model + Client

Provided you're connected to the SLAC network via VPN, this demo will monitor LCLS pvs, execute summation of those PV values on value change, serve an output pv, and display the results in a Bokeh-based web app.


Open two terminal windows. Activate a Python environment with an updated `lume-epics` installation. Set the channel access address list in each:
```
$ export EPICS_CA_ADDR_LIST={LCLS_PROD_HOST}:{CA_SERVER_PORT}
```

## Server
In the first window, run:
```
python examples/lcls/server.py
```

## Client
In the second window, run:
```
bokeh serve examples/lcls/client.py --show
```
