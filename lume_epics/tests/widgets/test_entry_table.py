import pytest
import epics
import time

from lume_model.variables import ScalarInputVariable
from lume_epics.client.widgets.controls import EntryTable


@pytest.fixture(scope="module", autouse=True)
def entry_inputs(model):
    return [
        var for var in model.input_variables.values() if var.variable_type == "scalar"
    ]


@pytest.fixture(scope="module", autouse=True)
def entry_table(controller, entry_inputs, server):
    # create entry table
    return EntryTable(entry_inputs, controller)


def test_entry_table_clear(entry_table, entry_inputs):
    # clear
    entry_table.clear()
    for input_var in entry_inputs:
        assert entry_table.text_inputs[input_var.name].value_input == ""


# test entry table submit
@pytest.mark.parametrize("value", [(7), (3)])
def test_entry_table_sumbit(value, entry_table, entry_inputs, epics_config, server):

    for input_var in entry_inputs:
        entry_table.text_inputs[input_var.name].value_input = str(value)

    entry_table.submit()

    time.sleep(0.1)

    for input_var in entry_inputs:
        if not input_var.is_constant:
            pvname = epics_config[input_var.name]["pvname"]
            val = epics.caget(pvname)
            assert val == value
