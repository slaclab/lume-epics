from lume_model.variables import ScalarOutputVariable

from lume_epics.client.widgets.tables import ValueTable
from lume_epics.client.controller import Controller
from lume_epics import epics_server



def test_value_table_ca():
    PREFIX = "test"

    output1 = ScalarOutputVariable(name="output1")
    output2 = ScalarOutputVariable(name="output2")

    # create controller
    controller = Controller("ca")

    outputs = [output1, output2]

    value_table = ValueTable(outputs, controller, PREFIX)

    controller.close()
