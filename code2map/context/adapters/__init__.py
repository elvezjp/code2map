"""Built-in adapters. Consumers can supply any object implementing Adapter."""

from .plsql import PLSQLAdapter
from .python import PythonAdapter


def __getattr__(name):
    # PL/SQL-only consumers can use the pure Python adapter without importing
    # Java native extensions. Keep the existing JavaAdapter export available.
    if name == "JavaAdapter":
        from .java import JavaAdapter
        return JavaAdapter
    if name == "CSharpAdapter":
        from .csharp import CSharpAdapter
        return CSharpAdapter
    raise AttributeError(name)


def builtin_adapters():
    from .csharp import CSharpAdapter
    from .java import JavaAdapter
    return [PythonAdapter(), PLSQLAdapter(), JavaAdapter(), CSharpAdapter()]
