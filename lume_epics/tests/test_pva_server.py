from lume_epics.epics_pva_server import PVAServer
from lume_model.variables import (
    ScalarInputVariable,
    ImageInputVariable,
    ArrayInputVariable,
    ScalarOutputVariable,
    ImageOutputVariable,
    ArrayOutputVariable,
    TableVariable,
)
import multiprocessing
import numpy as np


def test_pva_server(epics_config):

    table_data = {
        "col1": ArrayInputVariable(
            name="test", default=np.array([1, 2]), value_range=[0, 10]
        ),
        "col2": {
            "row1": ScalarInputVariable(
                name="col2_row1", default=0, value_range=[-1, -1]
            ),
            "row2": ScalarInputVariable(
                name="col2_row2", default=0, value_range=[-1, 1]
            ),
        },
    }

    input_variables = {
        "input1": ScalarInputVariable(name="input1", default=1.0, range=[0.0, 5.0]),
        "input2": ScalarInputVariable(
            name="input2", default=2.0, range=[0.0, 5.0], is_constant=True
        ),
        "input3": ImageInputVariable(
            name="input3",
            default=np.array([[1, 6,], [4, 1]]),
            value_range=[1, 10],
            axis_labels=["count_1", "count_2"],
            x_min=0,
            y_min=0,
            x_max=5,
            y_max=5,
        ),
        "input4": ArrayInputVariable(
            name="input4", default=np.array([1, 2]), range=[0, 5]
        ),
    }

    output_variables = {
        "output1": ScalarOutputVariable(name="output1"),
        "output2": TableVariable(table_rows=["row1", "row2"], table_data=table_data),
        "output3": ImageOutputVariable(
            name="output3", axis_labels=["count_1", "count_2"],
        ),
        "output4": ArrayOutputVariable(name="output4"),
    }

    in_queue = multiprocessing.Queue()
    out_queue = multiprocessing.Queue()
    running_indicator = multiprocessing.Value("b", False)

    server = PVAServer(
        input_variables,
        output_variables,
        epics_config,
        in_queue,
        out_queue,
        running_indicator,
    )

    server.start()
    server.shutdown()


def test_pva_server_struct(epics_config_struct):

    table_data = {
        "col1": ArrayInputVariable(
            name="test", default=np.array([1, 2]), value_range=[0, 10]
        ),
        "col2": {
            "row1": ScalarInputVariable(
                name="col2_row1", default=0, value_range=[-1, -1]
            ),
            "row2": ScalarInputVariable(
                name="col2_row2", default=0, value_range=[-1, 1]
            ),
        },
    }

    input_variables = {
        "input1": ScalarInputVariable(name="input1", default=1.0, range=[0.0, 5.0]),
        "input2": ScalarInputVariable(
            name="input2", default=2.0, range=[0.0, 5.0], is_constant=True
        ),
        "input3": ImageInputVariable(
            name="input3",
            default=np.array([[1, 6,], [4, 1]]),
            value_range=[1, 10],
            axis_labels=["count_1", "count_2"],
            x_min=0,
            y_min=0,
            x_max=5,
            y_max=5,
        ),
        "input4": ArrayInputVariable(
            name="input4", default=np.array([1, 2]), range=[0, 5]
        ),
    }

    output_variables = {
        "output1": ScalarOutputVariable(name="output1"),
        "output2": TableVariable(table_rows=["row1", "row2"], table_data=table_data),
        "output3": ImageOutputVariable(
            name="output3", axis_labels=["count_1", "count_2"],
        ),
        "output4": ArrayOutputVariable(name="output4"),
    }

    in_queue = multiprocessing.Queue()
    out_queue = multiprocessing.Queue()
    running_indicator = multiprocessing.Value("b", False)

    server = PVAServer(
        input_variables,
        output_variables,
        epics_config_struct,
        in_queue,
        out_queue,
        running_indicator,
    )

    server.start()
    server.shutdown()
