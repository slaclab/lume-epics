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
from lume_model.models import BaseModel
from lume_epics.tests.conftest import PVA_CONFIG


@pytest.mark.parametrize("value", [(1.0)])
def test_scalar_variables_ca(value, server, model, epics_config):

    model_obj = model()

    os.environ["PYEPICS_LIBCA"] = get_lib("ca")

    # check constant variable assignment
    for variable in model_obj.input_variables.values():
        pvname = epics_config[variable.name]["pvname"]

        if variable.variable_type == "scalar":
            epics.caput(pvname, value, timeout=1)

    for variable in model_obj.input_variables.values():
        if variable.variable_type == "scalar":
            pvname = epics_config[variable.name]["pvname"]
            val = epics.caget(pvname, timeout=1)

            if variable.is_constant:
                assert val != value

            else:
                assert val == value

            # update vars
            model_obj.input_variables[variable.name].value = val

        else:
            model_obj.input_variables[variable.name].value = variable.default

    output_variables = model_obj.evaluate(model_obj.input_variables)

    for variable in output_variables.values():

        if variable.variable_type == "scalar":
            pvname = epics_config[variable.name]["pvname"]
            val = epics.caget(pvname, timeout=1)
            assert variable.value == val


@pytest.mark.skip(
    reason="pvAccess server requires spawn method disrupted by subprocess popen..."
)
@pytest.mark.parametrize("value", [(1.0)])
def test_constant_variable_pva(value, server, model, epics_config):
    ctxt = Context("pva", conf=PVA_CONFIG)

    # check constant variable assignment
    for _, variable in model.input_variables.items():
        pvname = epics_config[variable.name]["pvname"]

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

    for _, variable in model.input_variables.items():
        if variable.variable_type == "scalar":
            pvname = epics_config[variable.name]["pvname"]

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
