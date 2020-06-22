from typing import List

from bokeh.plotting import figure
from bokeh.models import ColumnDataSource

import lume_model
from lume_epics.client.controllers import Controller
from lume_epics.client.monitors import PVImage, PVTimeSeries


class ImagePlot:
    """
    Object for viewing and updating an image plot.

    Attributes
    ----------
    live_variable: str
        Current variable to be displayed

    source: bokeh.models.sources.ColumnDataSource
        Data source for the viewer.

    pv_monitors: PVImage
        Monitors for the process variables.

    plot: bokeh.plotting.figure.Figure
        Plot object

    img_obj: bokeh.models.renderers.GlyphRenderer
        Image renderer

    """

    def __init__(
        self,
        variables: List[lume_model.variables.ImageVariable],
        controller: Controller,
        prefix: str,
    ) -> None:
        """
        Initialize monitors, current process variable, and data source.

        Parameters
        ----------
        variables: list
            List of image variables to include in plot

        controller: online_model.app.widgets.controllers.Controller
            Controller object for getting pv values

        prefix: str
            Prefix used for server

        """
        self.pv_monitors = {}

        for variable in variables:
            self.pv_monitors[variable.name] = PVImage(prefix, variable, controller)

        self.live_variable = list(self.pv_monitors.keys())[0]
        image_data = self.pv_monitors[self.live_variable].poll()
        self.source = ColumnDataSource(image_data)

    def build_plot(self, palette: tuple) -> None:
        """
        Creates the plot object.

        Parameters
        ----------
        palette: tuple
            Color palette to use for plot.
        """
        # create plot
        self.plot = figure(
            tooltips=[("x", "$x"), ("y", "$y"), ("value", "@image")],
            height=400,
            width=400,
        )
        self.plot.x_range.range_padding = self.plot.y_range.range_padding = 0

        self.img_obj = self.plot.image(
            name="img",
            image="image",
            x="x",
            y="y",
            dw="dw",
            dh="dh",
            source=self.source,
            palette=palette,
        )

        axis_labels = self.pv_monitors[self.live_variable].axis_labels
        axis_units = self.pv_monitors[self.live_variable].axis_units

        self.plot.xaxis.axis_label = axis_labels[0]
        self.plot.yaxis.axis_label = axis_labels[1]

        if axis_units:
            self.plot.xaxis.axis_label += " (" + axis_units[0] + ")"
            self.plot.yaxis.axis_label += " (" + axis_units[1] + ")"

    def update(self, live_variable: str) -> None:
        """
        Update the plot to reflect current process variable.

        Parameters
        ----------
        live_variable: str
            Variable to display
        """
        # update internal pv trackinng
        self.live_variable = live_variable

        # update axis and labels
        axis_labels = self.pv_monitors[self.live_variable].axis_labels
        axis_units = self.pv_monitors[self.live_variable].axis_units

        self.plot.xaxis.axis_label = axis_labels[0]
        self.plot.yaxis.axis_label = axis_labels[1]

        if axis_units:
            self.plot.xaxis.axis_label += " (" + axis_units[0] + ")"
            self.plot.yaxis.axis_label += " (" + axis_units[1] + ")"

        # get image data
        image_data = self.pv_monitors[self.live_variable].poll()

        # update data source
        self.img_obj.data_source.data.update(image_data)


class Striptool:
    """
    View for striptool display.

    Attributes
    ----------
    live_variable: str
        Variable to be displayed

    source: bokeh.models.sources.ColumnDataSource
        Data source for the viewer

    pv_monitors: PVScalarMonitor
        Monitors for the scalar variables

    plot: bokeh.plotting.figure.Figure
        Plot object

    """

    def __init__(
        self,
        variables: List[lume_model.variables.ScalarVariable],
        controller: Controller,
        prefix: str,
    ) -> None:
        """
        Initialize monitors, current process variable, and data source.

        Parameters
        ----------
        variables: list
            List of variables to initialize striptool

        controller: online_model.app.widgets.controllers.Controller
            Controller object for getting pv values

        prefix: str
            Prefix used for server.

        """
        self.pv_monitors = {}

        for variable in variables:
            self.pv_monitors[variable.name] = PVTimeSeries(prefix, variable, controller)

        self.live_variable = list(self.pv_monitors.keys())
        ts, ys = self.pv_monitors[self.live_variable].poll()
        self.source = ColumnDataSource(dict(x=ts, y=ys))

    def build_plot(self) -> None:
        """
        Creates the plot object.
        """
        self.plot = figure(plot_width=400, plot_height=400)
        self.plot.line(x="x", y="y", line_width=2, source=self.source)
        self.plot.yaxis.axis_label = self.live_variable 
        )

        # add units to label
        if self.pv_monitors[self.live_variable].units:
            self.plot.yaxis.axis_label += f" ({self.pv_monitors[self.live_variable].units})"

        self.plot.xaxis.axis_label = "time (sec)"

    def update(self, live_variable: str) -> None:
        """
        Update the plot to reflect current process variable.

        Parameters
        ----------
        live_variable: str
            Variable to display
        """
        self.live_variable = live_variable
        ts, ys = self.pv_monitors[self.live_variable].poll()
        self.source.data = dict(x=ts, y=ys)
        self.plot.yaxis.axis_label = f"{self.live_variable}"

        # add units to label
        if self.pv_monitors[self.live_variable].units:
            self.plot.yaxis.axis_label += f" ({self.pv_monitors[self.live_variable].units})"
