import numpy as np
import time
import pytest
import subprocess
import os
import sys
import epics
import signal
from epicscorelibs.path import get_lib
from p4p.client.thread import Context
from p4p import cleanup
from lume_model.variables import (
    ScalarInputVariable,
    ScalarOutputVariable,
    ImageInputVariable,
    ImageOutputVariable,
)
from lume_epics import epics_server
from lume_model.models import SurrogateModel
from lume_epics.tests.conftest import PVA_CONFIG

class ExampleModel(SurrogateModel):
    input_variables = {
        "input1": ScalarInputVariable(name="input1", value=1, default=1, range=[0.0, 5.0]),
        "input2": ScalarInputVariable(name="input2", value=2, default=2, range=[0.0, 5.0], is_constant=True),
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
    }

    output_variables = {
        "output1": ScalarOutputVariable(name="output1"),
        "output2": ScalarOutputVariable(name="output2"),
        "output3": ImageOutputVariable(
            name="output3", axis_labels=["count_1", "count_2"],
        ),
    }

    def evaluate(self, input_variables):

        self.input_variables = {variable.name: variable for variable in input_variables}

        self.output_variables["output1"].value = self.input_variables["input1"].value * 2
        self.output_variables["output2"].value = self.input_variables["input2"].value * 2

        self.output_variables["output3"].value = (
            self.input_variables["input3"].value * 2
        )
        self.output_variables["output3"].x_min = (
            self.input_variables["input3"].x_min / 2
        )
        self.output_variables["output3"].x_max = (
            self.input_variables["input3"].x_max / 2
        )
        self.output_variables["output3"].y_min = (
            self.input_variables["input3"].y_min / 2
        )
        self.output_variables["output3"].y_max = (
            self.input_variables["input3"].y_max / 2
        )
        self.output_variables["output3"].x_min = (
            self.input_variables["input3"].x_min / 2
        )
        self.output_variables["output3"].x_max = (
            self.input_variables["input3"].x_max / 2
        )
        self.output_variables["output3"].y_min = (
            self.input_variables["input3"].y_min / 2
        )
        self.output_variables["output3"].y_max = (
            self.input_variables["input3"].y_max / 2
        )

        # return inputs * 2
        return list(self.output_variables.values())



@pytest.fixture(scope="module")
def ca_server(rootdir):
    env = os.environ.copy()

    # add root dir to pythonpath in order to run test
    env["PYTHONPATH"] = env.get("PYTHONPATH", "") + f":{rootdir}"

    ca_proc = subprocess.Popen(
            [
                sys.executable, "launch_server.py"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd= os.path.dirname(os.path.realpath(__file__)),
            env=env
    )

    time.sleep(1)

    # Check it started successfully
    assert not ca_proc.poll()

    #yield ca_proc
    yield ca_proc

    # teardown
    ca_proc.send_signal(signal.SIGINT)

    for ln in ca_proc.stdout:
        print(ln)

    for ln in ca_proc.stderr:
        print(ln)

    print("Printed...")




@pytest.mark.parametrize("value,prefix", [(1.0, "test")])
def test_constant_variable_ca(value, prefix, ca_server):

    os.environ["PYEPICS_LIBCA"] = get_lib('ca')

    # check constant variable assignment
    for _, variable in ExampleModel.input_variables.items():
        pvname = f"{prefix}:{variable.name}"
        if variable.variable_type == "scalar":
            epics.caput(pvname, value, timeout=1)

    for _, variable in ExampleModel.input_variables.items():
        if variable.variable_type == "scalar":
            pvname = f"{prefix}:{variable.name}"
            val = epics.caget(pvname, timeout=1)

            if variable.is_constant:
                assert val != value

            else:
                assert val == value

@pytest.mark.parametrize("value,prefix", [(1.0, "test")])
def test_pva_manual(value, prefix, ca_server):
    ctxt = Context("pva", conf=PVA_CONFIG, maxsize=2)

    #check constant variable assignment
    for _, variable in ExampleModel.input_variables.items():
        pvname = f"{prefix}:{variable.name}"
            
        if variable.variable_type == "scalar":

            count = 3
            successful_put = False
            while count > 0 and not successful_put:
                try:
                    ctxt.put(pvname, value)
                    successful_put = True

                except:
                    ctxt.close()
                    del ctxt
                    time.sleep(3)
                    ctxt = Context("pva", conf=PVA_CONFIG)
                    count -= 1

            if count == 0:
                raise Exception("Failed puts.")

    for _, variable in ExampleModel.input_variables.items():
        if variable.variable_type == "scalar":
            pvname = f"{prefix}:{variable.name}"

            count = 3
            successful_get = False
            val = None
            while count > 0 and not successful_get:
                try:
                    val = ctxt.get(pvname)
                    successful_get = True

                except:
                    ctxt.close()
                    del ctxt
                    time.sleep(5)
                    ctxt = Context("pva", conf=PVA_CONFIG)
                    time.sleep(1)
                    count -= 1
            
            if count == 0:
                raise Exception("Failed gets.")

            if variable.is_constant:
                assert val != value

            else:
                assert val == value

    ctxt.close()