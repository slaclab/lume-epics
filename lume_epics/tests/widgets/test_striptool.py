import pytest

from lume_model.variables import ScalarOutputVariable

from lume_epics.client.widgets.plots import Striptool
from lume_epics.client.controller import Controller
from lume_epics import epics_server

@pytest.mark.parametrize("protocol,prefix,output_variables", [("pva", "test", [ScalarOutputVariable(name="output1"),  ScalarOutputVariable(name="output2")]), ("ca", "test", [ScalarOutputVariable(name="output1"),  ScalarOutputVariable(name="output2")])]
)
def test_striptool_build(protocol, prefix, output_variables):
    # create controller
    controller = Controller(protocol)

    striptool = Striptool(output_variables, controller, prefix)

    striptool.build_plot()
    controller.close()

@pytest.mark.parametrize("protocol,prefix,output_variables", [("pva", "test", [ScalarOutputVariable(name="output1"),  ScalarOutputVariable(name="output2")]), ("ca", "test", [ScalarOutputVariable(name="output1"),  ScalarOutputVariable(name="output2")])]
)
def test_reset_button(protocol, prefix, output_variables):

    # create controller
    controller = Controller(protocol)

    striptool = Striptool(output_variables, controller, prefix)

    striptool.build_plot()

    striptool._reset_values()

    controller.close()
