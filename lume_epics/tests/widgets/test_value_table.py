import pytest
import epics
import time
from lume_epics.client.widgets.tables import ValueTable


@pytest.fixture(scope="module")
def input_variables(model):
    return [
        var for var in model.input_variables.values() if var.variable_type == "scalar"
    ]


@pytest.fixture(scope="module")
def table_variables(model):
    return [
        var for var in model.output_variables.values() if var.variable_type == "scalar"
    ]


@pytest.fixture(scope="module")
def value_table(ca_controller, model, prefix, table_variables):

    return ValueTable(table_variables, ca_controller, prefix)


@pytest.mark.parametrize("value", [(1), (5), (8)])
def test_value_table_update(
    value, value_table, prefix, table_variables, server, input_variables
):

    # update input variables to trigger output update
    for var in input_variables:
        epics.caput(f"{prefix}:{var.name}", value)

    time.sleep(1)

    value_table.update()

    for var in table_variables:
        val_idx = value_table._source.data["x"].index(var.name)
        epics_val = epics.caget(f"{prefix}:{var.name}")
        val = value_table._source.data["y"][val_idx]

        assert epics_val == float(val)
