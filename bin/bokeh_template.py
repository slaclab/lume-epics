from bokeh.io import curdoc
from bokeh.layouts import column
from bokeh.server.server import Server
from lume_epics.client.utils import render_from_yaml
import argparse
import sys

import argparse



parser = argparse.ArgumentParser(description="Process bokeh args")
parser.add_argument("filename", type=str, help="Filename to load.")
parser.add_argument("prefix", type=str, help="Prefix to serve.")
parser.add_argument("protocol", type=str, help="Protocol used to build client.")
parser.add_argument('read_only', type=bool, default=False, help="Render as read-only")

args = parser.parse_args()

filename=args.filename
prefix = args.prefix
protocol = args.protocol
read_only = args.read_only
layout, callbacks = render_from_yaml(filename, prefix, protocol, read_only=read_only)

curdoc().add_root(
    column(*layout)
)

for callback in callbacks:
    curdoc().add_periodic_callback(callback, 250)