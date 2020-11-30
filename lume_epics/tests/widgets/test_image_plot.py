import numpy as np

from lume_model.variables import ImageOutputVariable
from lume_epics.client.widgets.plots import ImagePlot
from lume_epics.client.controller import Controller
from lume_epics import epics_server



def test_image_plot_ca():
    prefix = "test"

    output3 = ImageOutputVariable(
            name="output3",
            default=np.array([[1, 2,], [3, 4]]),
            axis_labels=["count_1", "count_2"],
            x_min=0,
            y_min=0,
            x_max=5,
            y_max=5,
        )

    outputs = [output3]

    controller = Controller("pva", [], [output3.name])

    image_plot = ImagePlot(outputs, controller, prefix)
    image_plot.build_plot()
    controller.close()


