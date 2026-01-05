# LCLS Model + Client

This example demonstrates a summation of klystron amplitude PVs and serves the result over PVA.

The example may be run with real PV data from the accelerator, or standalone with dummy simulated values.

To run in standalone mode:
```bash
$ cd examples
$ python3 -m lcls.server --standalone
```

If you're on the SLAC network, configure the EPICS environment to point to the production gateway, and then run:
```bash
$ source $EPICS_SETUP/envSet_prodOnDev.bash
$ cd examples
$ python3 -m lcls.server
```
