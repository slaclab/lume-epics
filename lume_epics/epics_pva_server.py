import logging
import multiprocessing
from queue import Full, Empty
import numpy as np
import time

from p4p.nt import NTScalar, NTNDArray
from p4p.server.thread import SharedPV
from p4p.server import Server as P4PServer
from p4p.nt.ndarray import ntndarray as NTNDArrayData
from p4p.server.raw import ServOpWrap


# Each server must have their outQueue in which the comm server will set the inputs and outputs vars to be updated
# Comm server must also provide one inQueue in which it will receive inputs from Servers

logger = logging.getLogger(__name__)


class PVAServer(multiprocessing.Process):
    protocol = "pva"
    def __init__(self,
                 prefix,
                 input_variables, output_variables,
                 in_queue, out_queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._prefix = prefix
        self._input_variables = input_variables
        self._output_variables = output_variables
        self._in_queue = in_queue
        self._out_queue = out_queue
        self._providers = {}
        self.pva_server = None

    def variable_by_pvname(self, pvname):
        try:
            return self._input_variables[pvname]
        except KeyError:
            return self._output_variables[pvname]

    def update_pv(self, pvname, value):
        # Hack for now to get the pickable value
        val = value.raw.value
        pvname = pvname.replace(f"{self._prefix}:", "")
        self._in_queue.put(
            {"protocol": self.protocol, "pvname": pvname, "value": val}
        )

    def setup_pva_server(self) -> None:
        logger.info("Initializing pvAccess server")
        # initialize global inputs
        for variable in self._input_variables.values():
            # input_pvs[variable.name] = variable.value
            pvname = f"{self._prefix}:{variable.name}"

            # prepare scalar variable types
            if variable.variable_type == "scalar":
                nt = NTScalar("d")
                initial = variable.value
            # prepare image variable types
            elif variable.variable_type == "image":
                nd_array = variable.value.view(NTNDArrayData)
                nd_array.attrib = {
                    "x_min": variable.x_min,
                    "y_min": variable.y_min,
                    "x_max": variable.x_max,
                    "y_max": variable.y_max,
                }
                nt = NTNDArray()
                initial = nd_array
            else:
                raise ValueError(
                    "Unsupported variable type provided: %s", variable.variable_type
                )

            handler = PVAccessInputHandler(pvname=pvname, server=self)
            pv = SharedPV(handler=handler, nt=nt, initial=initial)
            self._providers[pvname] = pv

        # use default handler for the output process variables
        # updates to output pvs are handled from post calls within the input
        # update
        for variable in self._output_variables.values():
            pvname = f"{self._prefix}:{variable.name}"
            if variable.variable_type == "scalar":
                nt = NTScalar()
                initial = variable.value

            elif variable.variable_type == "image":
                nd_array = variable.value.view(NTNDArrayData)
                # get limits from model output
                nd_array.attrib = {
                    "x_min": np.float64(variable.x_min),
                    "y_min": np.float64(variable.y_min),
                    "x_max": np.float64(variable.x_max),
                    "y_max": np.float64(variable.y_max),
                }

                nt = NTNDArray()
                initial = nd_array
            else:
                raise ValueError(
                    "Unsupported variable type provided: %s",
                    variable.variable_type
                )
            pv = SharedPV(nt=nt, initial=initial)
            self._providers[pvname] = pv

        else:
            pass  # throw exception for incorrect data type

        self.pva_server = P4PServer(providers=[self._providers])
        logger.info("pvAccess server started")

    def update_pvs(self, input_variables, output_variables):
        """
        Function for updating inputs and outputs over pva
        """
        variables = input_variables+output_variables
        for variable in variables:
            pvname = f"{self._prefix}:{variable.name}"
            if variable.variable_type == "image":
                logger.debug("pvAccess image process variable %s updated.",
                             variable.name)
                nd_array = variable.value.view(NTNDArrayData)

                # get dw and dh from model output
                nd_array.attrib = {
                    "x_min": variable.x_min,
                    "y_min": variable.y_min,
                    "x_max": variable.x_max,
                    "y_max": variable.y_max,
                }
                value = nd_array
            # do not build attribute pvs
            else:
                logger.debug(
                    "pvAccess process variable %s updated with value %s.",
                    variable.name, variable.value)
                value = variable.value
            output_provider = self._providers[pvname]
            output_provider.post(value)

    def run(self):
        self.setup_pva_server()
        while True:
            try:
                data = self._out_queue.get_nowait()
                print('PVA Server got data: ', data)
                inputs = data.get('input_variables', [])
                outputs = data.get('output_variables', [])
                self.update_pvs(inputs, outputs)
            except Empty:
                time.sleep(0.01)
                logger.debug("out queue empty")


class PVAccessInputHandler:
    """Handler object that defines the callbacks to execute on put operations to input
    process variables.
    """

    def __init__(self, pvname, server):
        """
        Initialize the handler with prefix and image pv attributes

        Args:
            pvname (str): The PV being handled
            server (PVAServer): Reference to the server holding this PV

        """
        self.pvname = pvname
        self.server = server

    def put(self, pv: SharedPV, op: ServOpWrap) -> None:
        """Updates the global input process variable state, posts the input process
        variable value change, runs the thread local OnlineSurrogateModel instance
        using the updated global input process variable states, and posts the model
        output values to the output process variables.

        Args:
            pv (SharedPV): Input process variable on which the put operates.

            op (ServOpWrap): Server operation initiated by the put call.

        """
        # update input values and global input process variable state
        pv.post(op.value())
        self.server.update_pv(pvname=self.pvname, value=op.value())
        # mark server operation as complete
        op.done()
