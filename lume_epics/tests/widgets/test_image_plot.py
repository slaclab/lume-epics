import numpy as np
import pytest
import epics
import time

from bokeh.palettes import YlGn3
from bokeh.models import LinearColorMapper

from lume_model.variables import ImageOutputVariable
from lume_epics.client.widgets.plots import ImagePlot


@pytest.fixture(scope="session")
def image_vars(model):
    return [
        var for var in model.input_variables.values() if var.variable_type == "image"
    ]


@pytest.fixture(scope="session")
def image_plot(controller, server, model, image_vars):
    image_plot = ImagePlot(image_vars, controller, palette=YlGn3)

    return image_plot


def test_image_plot_update(image_plot, image_vars, server, epics_config):
    updated_vals = {}

    # random dist for variable
    for var in image_vars:
        pvname = epics_config[var.name]["pvname"]
        nx = epics.caget(f"{pvname}:ArraySizeX_RBV")
        ny = epics.caget(f"{pvname}:ArraySizeY_RBV")

        new_val = np.random.uniform(0, 256, size=(nx, ny))

        # CANNOT PUT TO OUTPUT IMAGE!!!
        epics.caput(f"{pvname}:ArrayData_RBV", new_val.flatten())

        # take transpose as this is served as histogram
        updated_vals[var.name] = np.flipud(new_val.T)

    # random dist for variable
    for var in image_vars:
        image_plot.update(live_variable=var.name)

        val = image_plot.source.data["image"][0]

        assert (updated_vals[var.name] == val).all
