from abc import ABCMeta, abstractmethod
from builtins import object
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable, Type


class GlobalParamValidationError(Exception):
    """
    An error to throw when a global parameter is invalid
    """

    pass


class CopyPreviousRow(object):
    """
    Class to use when an action should copy its previous row's value when a new action is added.
    Examples:
        Run with temperature kwarg that should copy whatever the previous value a user entered,
        but defaulting to 1.0 if there are no previous actions.
        >>> @cast_parameters_to(temperature=float, field=float, mevents=int)
        >>> def run(self, temperature=CopyPreviousRow(1.0), field=1.0, mevents=10)
    """

    def __init__(self, default_value: bool | int | float | str) -> None:
        self.value = default_value


class ScriptDefinition(object, metaclass=ABCMeta):
    global_params: dict[str, Any] | None

    @abstractmethod
    def run(self, **kwargs) -> str | None:  # noqa:ANN003 - abstract, can be overridden to any type in subclass
        """
        Defines the steps of an action which can be used in the script generator.

        Args:
            **kwargs: The action parameters and their values in a keyword
                argument format. These must have a default value provided
                as shown in examples e.g. value1: str="1" where "1" is the
                default value.

        Returns:
            None if run runs without exception, otherwise a String containing the error message

        Examples:
            Run with kwargs that are not cast:
            >>> def run(self, value1="1", value2="2"):
            Typical run with kwargs that are cast to float:
            >>> @cast_parameters_to(temperature=float, field=float, uamps=mytype)
            >>> def run(self, temperature=0.0, field=0.0, uamps=0.0):
        """
        pass

    @abstractmethod
    def parameters_valid(self, **kwargs) -> str | None:  # noqa:ANN003 - abstract, can be overridden to any type in subclass
        """
        Contains tests to check whether a given set of inputs is valid

        Args:
            **kwargs: The action parameters and their values in a keyword
                argument format. These must have a default value provided
                as shown in examples e.g. value1: str="1" where "1" is the
                default value.

        Returns:
            None if all parameters are valid, otherwise a String containing an error message.

        Examples:
            Parameter check with kwargs that are not cast:
            >>> def parameters_valid(self, value1="1", value2="2"):
            Typical parameter check with kwargs that are cast to float:
            >>> @cast_parameters_to(temperature=float, field=float, uamps=mytype)
            >>> def parameters_valid(self, temperature=0.0, field=0.0, uamps=0.0):
        """
        pass

    def estimate_time(self, **kwargs) -> float | None:  # noqa:ANN003 - abstract, can be overridden to any type in subclass
        """
        Calculates an estimate in seconds of how long the specified parameters
        will take to execute. The Script Generator only calls this function
        if all parameters are valid (i.e. parameters_valid returns None)

        Args:
            **kwargs: The action parameters and their values in a keyword argument format.
                These must have a default value provided as shown in the examples e.g.
                value1: str="1" where "1" is the default value.

        Returns:
            The estimated time in seconds or None to signify "no estimate"
        """
        return None

    def get_help(self) -> str:
        """
        Shows a help string with useful information about the script.

        Returns:
            The help string shown in the client.
        """
        return ""

    def estimate_custom(self, **kwargs) -> OrderedDict:  # noqa:ANN003 - abstract, can be overridden to any type in subclass
        """
        Create custom estimates that display how many events are in the script.
        This function must return an OrderedDict with string keys and string values.
        The keys are the event names and will be displayed as columns in the client.
        The Script Generator only calls this function if all parameters are valid
        (i.e. parameters_valid returns None)

        Args:
            **kwargs: The action parameters and their values in a keyword argument format.
                These must have a default value provided as shown in the examples e.g.
                value1: str="1" where "1" is the default value.

        Returns:
            An ordered dictionary

        Examples:
            Custom estimation with kwargs that are not cast:
            >>> def estimate_custom(self, value1="1", value2="2"):
            >>>     ...
            >>> # Values can be numeric or a descriptive string.
            >>>     return OrderedDict([("custom1", "42"), ("custom2", "Unstable")])
        """
        return OrderedDict()

    def get_file(self) -> str:
        return __file__


def cast_parameters_to(
    *args_casts: Type | Callable, **keyword_casts: Type | Callable
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    A decorator to cast args and kwargs using the passed casters.

    Args:
        *args_casts: An ordered list of casters to use to cast args.
        **keyword_casts: A dictionary of casters to use to cast kwargs.

    Returns:
        return value of wrapped function or a string containing an error message if an error occurs.

    Examples:
        Cast run parameters (run only takes kwargs currently):
        >>> @cast_parameters_to(kwarg1=int, kwarg2=custom_caster, kwarg3=float, kwarg4=str)
        >>> def run(kwarg1="10", kwarg2="keyword", kwarg3="1.0", kwarg4="mystr")
        Cast parameters_valid parameters (parameters_valid only takes kwargs currently):
        >>> @cast_parameters_to(kwarg1=int, kwarg2=custom_caster, kwarg3=float, kwarg4=str)
        >>> def do_run(kwarg1="10", kwarg2="keyword", kwarg3="1.0", kwarg4="mystr")
        Cast a subset of parameters:
        >>> @cast_parameters_to(kwarg1=int, kwarg3=float)
        >>> def do_run(kwarg1="10", kwarg2="keyword", kwarg3="1.0", kwarg4="mystr")
        Error string returned when more args_casts than args:
        >>> @cast_parameters_to(int, custom_caster, float, str)
        >>> def func(arg1, arg2)
        >>> Returned: There are more casters for arguments than arguments
        Error string returnd when keyword_casts contains keys not present in kwargs:
        >>> @cast_parameters_to(kwarg1=int, kwarg2=custom_caster, kwargs3=float, kwarg4=str)
        >>> def func(kwarg1="10", kwarg2="20")
        >>> Returned: There are more casters for arguments than arguments
        Error string returned when cannot cast:
        >>> @cast_parameters_to(int)
        >>> def run("mystr")
        >>> Returned: "Cannot convert mystr from string to int"
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(self: ScriptDefinition, *args: Any, **kwargs: Any) -> Any:
            # Check for incorrect keyword_casts and args_casts
            if not set(keyword_casts.keys()).issubset(set(kwargs.keys())):
                return (
                    "Keyword argument casters contains keys"
                    " that are not present in keyword arguments"
                )
            if len(args_casts) > len(args):
                return "There are more casters for arguments than arguments"
            # Cast kwargs
            casting_failures = ""
            cast_kwargs = {}
            for k, v in kwargs.items():
                try:
                    cast_kwargs[k] = keyword_casts[k](v)
                except ValueError as e:
                    if str(e) != "":
                        casting_failures += str(e) + "\n"
                    else:
                        casting_failures += "Cannot convert {} from string to {}\n".format(
                            str(v), str(keyword_casts[k].__name__)
                        )
            # Cast args
            cast_args = []
            for i in range(len(args_casts)):
                try:
                    cast_args.append(args_casts[i](args[i]))
                except ValueError as e:
                    if str(e) != "":
                        casting_failures += str(e) + "\n"
                    else:
                        casting_failures += "Cannot convert {} from string to {}\n".format(
                            args[i], str(args_casts[i].__name__)
                        )
            if casting_failures != "":
                return casting_failures
            return func(self, *cast_args, **cast_kwargs)

        return wrapper

    return decorator
