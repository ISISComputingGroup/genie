# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2023 Science & Technology Facilities Council.
# All rights reserved.
#
# This program is distributed in the hope that it will be useful.
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License v1.0 which accompanies this distribution.
# EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM
# AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
# You should have received a copy of the Eclipse Public License v1.0
# along with this program; if not, you can obtain a copy from
# https://www.eclipse.org/org/documents/epl-v10.php or
# http://opensource.org/licenses/eclipse-1.0.php

import unittest
from typing import List
from unittest.mock import patch

from hamcrest import assert_that, equal_to
from mock import Mock
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursor
from mysql.connector.errors import InternalError
from mysql.connector.types import RowType
from parameterized import parameterized

from genie_python import mysql_abstraction_layer


class SQLCursorStub(MySQLCursor):
    _opened = False
    _closed = False

    def __init__(self, throw_error):
        SQLCursorStub._opened = True
        self._throw_error = throw_error

    def __iter__(self):
        self.a = 1
        return self

    def __next__(self) -> RowType:
        x = self.a
        if x > 10:
            raise StopIteration
        self.a += 1
        return (x,)

    def close(self) -> bool:
        """
        Optionally, raises this error to mimic the behaviour of
        handle_unread_result in mysql/connection.py.
        """
        if self._throw_error:
            raise InternalError("Unread result found")
        SQLCursorStub._closed = True
        return True

    def execute(self, operation, params=None, multi: bool = False):
        pass

    def fetchall(self) -> List[RowType]:
        return []


class SQLConnectorStub(MySQLConnection):
    _opened = False
    _closed = False

    def __init__(self, throw_error):
        SQLConnectorStub._opened = True
        self._throw_error = throw_error

    def cursor(
        self,
        buffered=None,
        raw=None,
        prepared=None,
        cursor_class=None,
        dictionary=None,
        named_tuple=None,
    ):
        """
        Creates a cursor opject.
        Which can - optionally - raise an exception on close.
        """
        cursor = SQLCursorStub(self._throw_error)
        return cursor

    def commit(self):
        pass

    def close(self):
        SQLConnectorStub._closed = True


class TestConnectionLayer(unittest.TestCase):
    @parameterized.expand(
        [
            (True,),
            (False,),
        ]
    )
    def test_GIVEN_close_error_WHEN_execute_command_THEN_connection_is_closed(self, raise_it):
        with patch("genie_python.mysql_abstraction_layer.SQLAbstraction._start_connection_pool"):
            sql = mysql_abstraction_layer.SQLAbstraction(
                dbid="exp_data", user="report", password="$report"
            )
        sql._get_connection = Mock(return_value=SQLConnectorStub(raise_it))
        exception_raised = False
        try:
            severity_names_sql = "SELECT severity_id, name FROM archive.severity"
            sql._execute_command(severity_names_sql, True, ())
        except InternalError:
            exception_raised = True
        finally:
            assert_that(exception_raised, equal_to(raise_it))
            assert_that(SQLConnectorStub._opened, equal_to(True))
            assert_that(SQLConnectorStub._closed, equal_to(True))

    @parameterized.expand(
        [
            (True,),
            (False,),
        ]
    )
    def test_GIVEN_close_error_WHEN_query_returning_cursor_THEN_connection_is_closed(
        self, raise_it
    ):
        with patch("genie_python.mysql_abstraction_layer.SQLAbstraction._start_connection_pool"):
            sql = mysql_abstraction_layer.SQLAbstraction(
                dbid="exp_data", user="report", password="$report"
            )
        sql._get_connection = Mock(return_value=SQLConnectorStub(raise_it))
        exception_raised = False
        try:
            severity_names_sql = "SELECT severity_id, name FROM archive.severity"
            [x for x in sql.query_returning_cursor(severity_names_sql, ())]
        except InternalError:
            exception_raised = True
        finally:
            assert_that(exception_raised, equal_to(raise_it))
            assert_that(SQLConnectorStub._opened, equal_to(True))
            assert_that(SQLConnectorStub._closed, equal_to(True))


if __name__ == "__main__":
    unittest.main()
