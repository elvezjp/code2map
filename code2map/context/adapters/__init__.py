"""Built-in adapters. Consumers can supply any object implementing Adapter."""

from .python import PythonAdapter
from .plsql import PLSQLAdapter
from .java import JavaAdapter


def builtin_adapters():
    return [PythonAdapter(), PLSQLAdapter(), JavaAdapter()]
