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
def image_plot(controller, server, model, prefix, image_vars):
    image_plot = ImagePlot(image_vars, controller, prefix)

    image_plot.build_plot(palette=YlGn3)

    return image_plot


def test_image_plot_missing_build_params(image_plot):

    # missing palette or color mapper
    with pytest.raises(Exception):
        image_plot.build_plot()

    # successful test with color_mapper
    color_mapper = LinearColorMapper(palette=YlGn3, low=0, high=256)
    image_plot.build_plot(color_mapper=color_mapper)

    # successful test with palette
    image_plot.build_plot(palette=YlGn3)


@pytest.mark.skip(reason="Relies on fixes in controller")
def test_image_plot_update(image_plot, image_vars, prefix, server, controller):
    updated_vals = {}

    # random dist for variable
    for var in image_vars:
        nx = epics.caget(f"{prefix}:{var.name}:ArraySizeX_RBV")
        ny = epics.caget(f"{prefix}:{var.name}:ArraySizeY_RBV")

        new_val = np.random.uniform(0, 256, size=(nx, ny))

        # CANNOT PUT TO OUTPUT IMAGE!!!
        epics.caput(f"{prefix}:{var.name}:ArrayData_RBV", new_val.flatten())
        # take transpose as this is served as histogram
        updated_vals[var.name] = np.flipud(new_val.T)

    # random dist for variable
    for var in image_vars:
        image_plot.live_variable = var.name
        image_plot.update()

        val = image_plot.source.data["image"][0]

        assert (updated_vals[var.name] == val).all
