import astroid
from astroid import MANAGER


def register(linter: None) -> None:
    """Required for registering the plugin"""
    pass


def transform(cls: astroid.ClassDef) -> None:
    """ " Add ScanningInstrument methods to the declaring module

    If the given class is derived from ScanningInstrument,
    get all its public methods and, for each one, add a dummy method
    with the same name to the module where the class is declared (note: adding a reference
    to the actual method rather than a dummy will cause the linter to crash).
    """
    if cls.basenames and "ScanningInstrument" in cls.basenames:
        public_methods = filter(lambda method: not method.name.startswith("__"), cls.methods())
        for public_method in public_methods:
            cls.parent.locals[public_method.name] = astroid.FunctionDef(
                name=public_method.name,
                lineno=0,
                col_offset=0,
                parent=cls.parent,
                end_lineno=0,
                end_col_offset=0,
            )


MANAGER.register_transform(astroid.ClassDef, transform)
