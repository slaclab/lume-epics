from typing import List

from bokeh.plotting import figure
from bokeh.models import ColumnDataSource

from online_model.app.controllers import Controller
from online_model.app.monitors import PVImage, PVTimeSeries


class ImagePlot:
    """
    Object for viewing and updating an image plot.

    Attributes
    ----------
    current_pv: str
        Current process variable to be displayed

    source: bokeh.models.sources.ColumnDataSource
        Data source for the viewer.

    pv_monitors: PVImageMonitor
        Monitors for the process variables.

    p: bokeh.plotting.figure.Figure
        Plot object

    img_obj: bokeh.models.renderers.GlyphRenderer
        Image renderer

    """

    def __init__(self, sim_pvdb: dict, controller: Controller, prefix: str) -> None:
        """
        Initialize monitors, current process variable, and data source.

        Parameters
        ----------
        sim_pvdb: dict
            Dictionary of process variable values

        controller: online_model.app.widgets.controllers.Controller
            Controller object for getting pv values

        prefix: str
            Prefix used for server

        """
        self.pv_monitors = {}

        for opv in sim_pvdb:
            if len(sim_pvdb[opv]["units"].split(":")) == 2:
                self.pv_monitors[opv] = PVImage(
                    f"{prefix}:{opv}", sim_pvdb[opv]["units"], controller
                )

        self.current_pv = list(self.pv_monitors.keys())[0]
        image_data = self.pv_monitors[self.current_pv].poll()
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
        self.p = figure(
            tooltips=[("x", "$x"), ("y", "$y"), ("value", "@image")],
            height=400,
            width=400,
        )
        self.p.x_range.range_padding = self.p.y_range.range_padding = 0

        self.img_obj = self.p.image(
            name="img",
            image="image",
            x="x",
            y="y",
            dw="dw",
            dh="dh",
            source=self.source,
            palette=palette,
        )

        variables = self.pv_monitors[self.current_pv].variables()
        units = self.pv_monitors[self.current_pv].units

        self.p.xaxis.axis_label = variables[-2] + " (" + units[0] + ")"
        self.p.yaxis.axis_label = variables[-1] + " (" + units[1] + ")"

    def update(self, current_pv: str) -> None:
        """
        Update the plot to reflect current process variable.

        Parameters
        ----------
        current_pv: str
            Current process variable
        """
        # update internal pv trackinng
        self.current_pv = current_pv

        # Update x and y axes
        variables = self.pv_monitors[current_pv].variables()
        units = self.pv_monitors[current_pv].units

        self.p.xaxis.axis_label = variables[-2] + " (" + units[0] + ")"
        self.p.yaxis.axis_label = variables[-1] + " (" + units[1] + ")"

        # get image data
        image_data = self.pv_monitors[current_pv].poll()

        # update data source
        self.img_obj.data_source.data.update(image_data)


class Striptool:
    """
    View for striptool display.

    Attributes
    ----------
    current_pv: str
        Current process variable to be displayed

    source: bokeh.models.sources.ColumnDataSource
        Data source for the viewer.

    pv_monitors: PVScalarMonitor
        Monitors for the scalar variables.

    p: bokeh.plotting.figure.Figure
        Plot object

    """

    def __init__(self, variables, controller: Controller, prefix: str) -> None:
        """
        Initialize monitors, current process variable, and data source.

        Parameters
        ----------
        sim_pvdb: dict
            Dictionary of process variable values

        controller: online_model.app.widgets.controllers.Controller
            Controller object for getting pv values

        prefix: str
            Prefix used for server.

        """
        self.pv_monitors = {}

        for variable in variables:
            self.pv_monitors[variable.name] = PVTimeSeries(
                f"{prefix}:{variable.name}", variable.units, controller
            )

        self.current_pv = list(self.pv_monitors.keys())[0]
        ts, ys = self.pv_monitors[self.current_pv].poll()
        self.source = ColumnDataSource(dict(x=ts, y=ys))

    def build_plot(self) -> None:
        """
        Creates the plot object.
        """
        self.p = figure(plot_width=400, plot_height=400)
        self.p.line(x="x", y="y", line_width=2, source=self.source)
        self.p.yaxis.axis_label = (
            self.current_pv + " (" + self.pv_monitors[self.current_pv].units[0] + ")"
        )
        self.p.xaxis.axis_label = "time (sec)"

    def update(self, current_pv: str) -> None:
        """
        Update the plot to reflect current process variable.

        Parameters
        ----------
        current_pv: str
            Current process variable
        """
        self.current_pv = current_pv
        ts, ys = self.pv_monitors[current_pv].poll()
        units = self.pv_monitors[current_pv].units[0]
        self.source.data = dict(x=ts, y=ys)
        self.p.yaxis.axis_label = f"{current_pv} ({units})"
