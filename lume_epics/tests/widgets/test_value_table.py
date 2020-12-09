import pytest
import epics
from lume_epics.client.widgets.tables import ValueTable

@pytest.fixture(scope="module")
def table_variables(model):
    return [var for var in model.output_variables.values() if var.variable_type == "scalar"]

@pytest.fixture(scope="module")
def value_table(controller, model, prefix, table_variables):

    return ValueTable(table_variables, controller, prefix)

@pytest.mark.skip(reason="Requires controller bug fix.")
def test_value_table_update(value_table, prefix, table_variables):

    updated_vals = {}

    for var in table_variables:
        val_idx = value_table._source.data["x"].index(var.name)
        val = value_table._source.data["y"][val_idx]

        updated_vals[var.name] = float(val) * 2
        epics.caput(f"{prefix}:{var.name}", float(val) * 2)

    value_table.update()

    for var in table_variables:
        val_idx = value_table._source.data["x"].index(var.name)
        val = value_table._source.data["y"][val_idx]

        assert updated_vals[var.name] == float(val)
    