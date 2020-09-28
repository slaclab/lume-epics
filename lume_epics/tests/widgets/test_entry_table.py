import pytest
from lume_model.variables import ScalarInputVariable

from lume_epics.client.widgets.controls import EntryTable
from lume_epics.client.controller import Controller


@pytest.mark.parametrize(
    "protocol,prefix,input_variables",
    [
        (
            "pva",
            "test",
            [
                ScalarInputVariable(name="input1", default=1, range=[0.0, 5.0]),
                ScalarInputVariable(name="input2", default=2, range=[0.0, 5.0]),
            ],
        ),
    ],
)
def test_entry_table_construction(
    protocol, prefix, input_variables,
):
    # create controller
    controller = Controller("pva")

    # create entry table
    entry_table = EntryTable(input_variables, controller, prefix)

    # close controller
    controller.close()


@pytest.mark.parametrize(
    "protocol,prefix,input_variables",
    [
        (
            "pva",
            "test",
            [
                ScalarInputVariable(name="input1", default=1, range=[0.0, 5.0]),
                ScalarInputVariable(name="input2", default=2, range=[0.0, 5.0]),
            ],
        ),
    ],
)
def test_entry_table_clear(
    protocol, prefix, input_variables,
):
    # create controller
    controller = Controller("pva")

    # create entry table
    entry_table = EntryTable(input_variables, controller, prefix)

    # clear
    entry_table.clear()

    # stop controller
    controller.close()
