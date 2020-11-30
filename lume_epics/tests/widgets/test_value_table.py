from lume_model.variables import ScalarOutputVariable

from lume_epics.client.widgets.tables import ValueTable
from lume_epics.client.controller import Controller
from lume_epics import epics_server



def test_value_table_ca():
    prefix = "test"

    output1 = ScalarOutputVariable(name="output1")
    output2 = ScalarOutputVariable(name="output2")

    # create controller
    controller = Controller("ca", [], [f"{prefix}:{output1.name}", f"{prefix}:{output2.name}"])

    outputs = [output1, output2]

    value_table = ValueTable(outputs, controller, prefix)

    controller.close()
