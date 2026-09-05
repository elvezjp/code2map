"""Built-in adapters. Consumers can supply any object implementing Adapter."""

from .python import PythonAdapter
from .plsql import PLSQLAdapter


def __getattr__(name):
    # PL/SQL-only consumers can use the pure Python adapter without importing
    # Java native extensions. Keep the existing JavaAdapter export available.
    if name == "JavaAdapter":
        from .java import JavaAdapter
        return JavaAdapter
    raise AttributeError(name)


def builtin_adapters():
    from .java import JavaAdapter
    return [PythonAdapter(), PLSQLAdapter(), JavaAdapter()]
