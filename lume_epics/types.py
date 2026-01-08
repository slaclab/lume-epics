
from p4p.server.thread import SharedPV
from p4p import Type, Value
from p4p.nt import NTScalar, NTBase
from typing import Any, Dict
from lume_model.variables import Variable, ScalarVariable
import typing

class VariableTypeHandler:
    """
    Base class for all variable types
    Implements type-specific operations in a portable manner.

    Specializations of this class for additional types should be added to the _TYPE_HANDLERS dict, keyed
    by the LUME variable type they're specialized for (i.e. ScalarVariable).

    Type handlers for a specific variable instance may be obtained using the type_handler() function in this module.
    type_handlers() returns the full list.
    """

    def default_value(self, variable: Variable) -> Any:
        """
        Returns the default value of the variable

        Parameters
        ----------
        variable : Variable
            The variable instance to get the default value for

        Returns
        -------
        Any :
            The default value
        """
        raise NotImplementedError()
    
    def pva_typedef(self) -> Type:
        """
        Returns the p4p typedef for the variable.
        """
        raise NotImplementedError()

    def ca_typedef(self) -> dict:
        """
        Returns the CA typedef, passed to pcaspy to create the structure.
        """
        raise NotImplementedError()

    def to_value(self, pyvalue: Any) -> Value:
        """
        Convert the variable's value to a p4p Value

        Parameters
        ----------
        pyvalue : Any
            Convert the Python value to a P4P Value
        
        Returns
        -------
        Value :
            The P4P value
        """
        raise NotImplementedError()

    def from_value(self, value: Value) -> Any:
        """
        Convert the p4p Value to a value that can be used in Python

        Parameters
        ----------
        value : Value
            P4P value to be converted to a Python value

        Returns
        -------
        Any :
            The value converted to Python
        """
        raise NotImplementedError()

    def initial_value(self, config: dict, variable: Variable) -> Value:
        """
        Create an initial value for p4p to use
        This should generally include important metadata (description, units, etc.) that are not
        otherwise going to change.

        Parameters
        ----------
        config : dict
            Configuration for this variable.
        variable : Variable
            The variable to obtain the default from, and convert it to p4p.Value

        Returns
        -------
        Value :
            P4P value to be passed to SharedPV()
        """
    
class ScalarTypeHandler(VariableTypeHandler):
    """Type handler for ScalarVariable"""
    def __init__(self):
        self._nt = NTScalar('d', control=True, display=True)

    def default_value(self, variable: Variable) -> Any:
        d = variable.default_value
        return d if d is not None else 0.0

    def pva_typedef(self):
        return NTScalar.buildType('d', control=True, display=True)

    def ca_typedef(self):
        raise NotImplementedError()

    def to_value(self, pyvalue: Any) -> Value:
        return self._nt.wrap(pyvalue)

    def from_value(self, value: Value) -> Any:
        return self._nt.unwrap(value)
    
    def initial_value(self, config: dict, variable: Variable) -> Value:
        v = self.to_value(self.default_value(variable))

        # Set initial display parameters
        v['display']['description'] = config.get('description', '')
        return v


_TYPE_HANDLERS = {
    ScalarVariable: ScalarTypeHandler()
}

def type_handlers() -> Dict[typing.Type, VariableTypeHandler]:
    """
    Returns a map of LUME variable type -> handler.
    """
    return _TYPE_HANDLERS

def type_handler(var: Variable) -> VariableTypeHandler | None:
    """
    Returns the type handler for the variable

    Parameters
    ----------
    var : Variable
        The variable to get the type handler for.
    
    Returns
    -------
    VariableTypeHandler | None :
        The type handler, or None if one is not registered for this variable type.
    """
    try:
        return _TYPE_HANDLERS[type(var)]
    except:
        return None
