from bokeh.io import curdoc
from bokeh.layouts import column
from bokeh.server.server import Server
from lume_epics.client.utils import render_from_yaml
import argparse
import sys

import argparse



parser = argparse.ArgumentParser(description="Process bokeh args")
parser.add_argument("filename", type=str, help="Filename to load.")
parser.add_argument("protocol", type=str, help="Protocol used to build client.")
parser.add_argument("prefix", type=str, help="Prefix to serve.")
parser.add_argument('--read-only', default=False, action="store_true", help="Render as read-only")
parser.add_argument('--ncol-widgets', dest='ncol_widgets', default=5, type=int, help="Number of widgets to render per column")
parser.add_argument('--striptool-limit', dest='striptool_limit', default=50, type=int, help="Number of striptool steps to keep")

args = parser.parse_args()

filename=args.filename
prefix = args.prefix
protocol = args.protocol
read_only = args.read_only
striptool_limit = args.striptool_limit
ncol_widgets = args.ncol_widgets

layout, callbacks = render_from_yaml(filename, prefix, protocol, read_only=read_only, striptool_limit=striptool_limit, ncol_widgets=ncol_widgets)


curdoc().add_root(
    layout
)

for callback in callbacks:
    curdoc().add_periodic_callback(callback, 250)