from bokeh.io import curdoc
from bokeh.layouts import column
from lume_epics.client.utils import render_from_yaml

prefix = "test"
protocol = "ca"

filename = "examples/files/iris_config.yml"
epics_config_filename = "examples/files/iris_epics_config.yml"


layout, callbacks = render_from_yaml(filename, epics_config_filename, read_only=False)


curdoc().add_root(layout)

for callback in callbacks:
    curdoc().add_periodic_callback(callback, 250)
