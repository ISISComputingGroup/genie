from typing import TYPE_CHECKING, Any

import astroid
from astroid import MANAGER

if TYPE_CHECKING:
    from pylint.lint import PyLinter


def register(linter: "PyLinter") -> None:
    """Register the plugin."""


def transform(node: astroid.ClassDef, *args: Any, **kwargs: Any) -> None:
    """Add ScanningInstrument methods to the declaring module.

    If the given class is derived from ScanningInstrument,
    get all its public methods and, for each one, add a dummy method
    with the same name to the module where the class is declared (note: adding a reference
    to the actual method rather than a dummy will cause the linter to crash).
    """
    if node.basenames and "ScanningInstrument" in node.basenames:
        public_methods = filter(lambda method: not method.name.startswith("__"), node.methods())
        for public_method in public_methods:
            if isinstance(node.parent, astroid.Module):
                new_func = astroid.FunctionDef(
                    name=public_method.name,
                    lineno=0,
                    col_offset=0,
                    parent=node.parent,
                    end_lineno=0,
                    end_col_offset=0,
                )
                arguments = astroid.Arguments(
                    vararg=None,
                    kwarg=None,
                    parent=new_func,
                )
                arguments.postinit(
                    args=None,
                    defaults=None,
                    kwonlyargs=[],
                    kw_defaults=None,
                    annotations=[],
                    posonlyargs=[],
                    kwonlyargs_annotations=[],
                    posonlyargs_annotations=[],
                )
                new_func.postinit(args=arguments, body=[])
                node.parent.locals[public_method.name] = [new_func]


MANAGER.register_transform(astroid.ClassDef, transform)
