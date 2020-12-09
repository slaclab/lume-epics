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
from lume_epics.tests.launch_server import TestModel


@pytest.mark.parametrize("value,prefix", [(1.0, "test")])
def test_constant_variable_ca(value, prefix, server):

    print(get_lib('ca'))

    os.environ["PYEPICS_LIBCA"] = get_lib('ca')

    # check constant variable assignment
    for _, variable in TestModel.input_variables.items():
        pvname = f"{prefix}:{variable.name}"
        if variable.variable_type == "scalar":
            epics.caput(pvname, value, timeout=1)

    for _, variable in TestModel.input_variables.items():
        if variable.variable_type == "scalar":
            pvname = f"{prefix}:{variable.name}"
            val = epics.caget(pvname, timeout=1)

            if variable.is_constant:
                assert val != value

            else:
                assert val == value

@pytest.mark.parametrize("value,prefix", [(1.0, "test")])
def test_pva_manual(value, prefix, server):
    ctxt = Context("pva", conf=PVA_CONFIG, maxsize=2)

    #check constant variable assignment
    for _, variable in TestModel.input_variables.items():
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

    for _, variable in TestModel.input_variables.items():
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