from bokeh.io import curdoc
from bokeh.layouts import column
from lume_epics.client.utils import render_from_yaml

prefix="test"
protocol = "ca"

filename = "examples/files/iris_config.yaml"
layout, callbacks = render_from_yaml(filename, prefix, protocol, read_only=False)


curdoc().add_root(
    column(*layout)
)

for callback in callbacks:
    curdoc().add_periodic_callback(callback, 250)