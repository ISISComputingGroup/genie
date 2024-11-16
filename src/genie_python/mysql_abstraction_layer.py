"""
Abstracting out the SQL connection.
"""
# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2016 Science & Technology Facilities Council.
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

from abc import abstractmethod
from collections.abc import Iterable
from typing import Generator, List, Optional, TypeAlias

import mysql.connector
from mysql.connector.abstracts import MySQLCursorAbstract
from mysql.connector.connection import MySQLConnection
from mysql.connector.pooling import PooledMySQLConnection
from mysql.connector.types import ParamsSequenceOrDictType, RowType

ParamsSequenceOrDictType = ParamsSequenceOrDictType
MySQLConnectionAbstract: TypeAlias = MySQLConnection | PooledMySQLConnection


class DatabaseError(IOError):
    """
    Exception that is thrown if there is a problem with the database
    """

    def __init__(self, message: str) -> None:
        super(DatabaseError, self).__init__(message)


class AbstractSQLCommands(object):
    """
    Abstract base class for sql commands for testing
    """

    @staticmethod
    def generate_in_binding(parameter_count: int) -> str:
        """
        Generate a list of python sql bindings for use in a sql in clause.
        One binding for each parameter. i.e. %s, %s, %s for 3 parameters.

        Args:
            parameter_count: number of items in the in clause

        Returns: in binding

        """
        return ", ".join(["%s"] * parameter_count)

    def query_returning_cursor(
        self, command: str, bound_variables: ParamsSequenceOrDictType
    ) -> Generator[RowType, None, None]:
        """
        Generator which returns rows from query.
        Args:
            command: command to run
            bound_variables: any bound variables

        Yields: a row from the query

        """
        raise NotImplementedError()

    @abstractmethod
    def _execute_command(
        self, command: str, is_query: bool, bound_variables: Optional[ParamsSequenceOrDictType]
    ) -> Optional[List[RowType]]:
        """Executes a command on the database, and returns all values

        Args:
            command: the SQL command to run
            is_query: is this a query (i.e. do we expect return values)

        Returns:
            values: list of all rows returned. None if not is_query
        """
        raise NotImplementedError()

    def query(
        self, command: str, bound_variables: Optional[ParamsSequenceOrDictType] = None
    ) -> Optional[List[RowType]]:
        """Executes a query on the database, and returns all values

        Args:
            command: the SQL command to run
            bound_variables: a tuple of parameters to bind into the query;
                Default no parameters to bind

        Returns:
            values: list of all rows returned
        """
        return self._execute_command(command, True, bound_variables)

    def update(
        self, command: str, bound_variables: Optional[ParamsSequenceOrDictType] = None
    ) -> None:
        """Executes an update on the database, and returns all values

        Args:
            command: the SQL command to run
            bound_variables: a tuple of parameters to bind into the query;
                Default no parameters to bind
        """
        self._execute_command(command, False, bound_variables)


class SQLAbstraction(AbstractSQLCommands):
    """
    A wrapper to connect to MySQL databases.
    """

    # Number of available simultaneous connections to each connection pool
    POOL_SIZE = 16

    def __init__(self, dbid: str, user: str, password: str, host: str = "127.0.0.1") -> None:
        """
        Constructor.

        Args:
            dbid: The id of the database that holds the required information
            user: The username to use to connect to the database
            password: The password to use to connect to the database
            host: The host address to use, defaults to local host
        """
        super(SQLAbstraction, self).__init__()
        self._dbid = dbid
        self._user = user
        self._password = password
        self._host = host
        self._pool_name = self._generate_pool_name()
        self._start_connection_pool()

    @staticmethod
    def generate_unique_pool_name() -> str:
        """Generate a unique name for the connection pool so each object has its own pool"""
        import uuid

        return "DBSVR_CONNECTION_POOL_" + str(uuid.uuid4())

    def _generate_pool_name(self) -> str:
        """Generate a name for the connection pool based on host, user and database name
        a connection in the pool is made with the frist set of credentials passed, so we
        have to make sure a pool name is not used with different credentials
        """
        return "DBSVR_%s_%s_%s" % (self._host, self._dbid, self._user)

    def _close_handles(self, curs: MySQLCursorAbstract, conn: MySQLConnectionAbstract) -> None:
        """Several methods need to close the cursor and connection handles.
        It's a bit complicated and it has been seperated out here.
        """
        curserr = None
        if curs is not None:
            try:
                curs.close()
            except mysql.connector.errors.InternalError as err:
                curserr = err
        if conn is not None:
            conn.close()
        if curserr is not None:
            raise curserr

    def _start_connection_pool(self) -> None:
        """Initialises a connection pool"""
        conn = mysql.connector.connect(
            user=self._user,
            password=self._password,
            host=self._host,
            database=self._dbid,
            pool_name=self._pool_name,
            pool_size=SQLAbstraction.POOL_SIZE,
        )
        assert isinstance(conn, MySQLConnectionAbstract)
        curs = conn.cursor()
        assert isinstance(curs, MySQLCursorAbstract)
        # Check db exists
        curs.execute("SHOW TABLES")
        if len(curs.fetchall()) == 0:
            # Database does not exist
            raise Exception("Requested Database %s does not exist" % self._dbid)
        self._close_handles(curs, conn)

    def _get_connection(self) -> MySQLConnectionAbstract:
        try:
            conn = mysql.connector.connect(pool_name=self._pool_name)
            assert isinstance(conn, MySQLConnectionAbstract)
            return conn
        except Exception as err:
            raise Exception("Unable to get connection from pool: %s" % str(err))

    def _execute_command(
        self, command: str, is_query: bool, bound_variables: Optional[ParamsSequenceOrDictType]
    ) -> Optional[List[RowType]]:
        """Executes a command on the database, and returns all values

        Args:
            command: the SQL command to run
            is_query: is this a query (i.e. do we expect return values)
            bound_variables: parameters to be used for the given statement
        Returns:
            values (list): list of all rows returned. None if not is_query
        """
        conn = None
        curs = None
        values = None
        try:
            conn = self._get_connection()
            curs = conn.cursor()
            if bound_variables is not None:
                curs.execute(command, bound_variables)
            else:
                curs.execute(command)
            if is_query:
                values = curs.fetchall()
                if values is not None and len(values) > 0:
                    isinstance(values[0], List)

            # Commit as part of the query or results won't be updated between subsequent
            # transactions. Can lead to values not auto-updating in the GUI.
            conn.commit()
        except Exception as err:
            raise DatabaseError(str(err))
        finally:
            assert isinstance(curs, MySQLCursorAbstract)
            assert isinstance(conn, MySQLConnectionAbstract)
            self._close_handles(curs, conn)
        return values

    def query_returning_cursor(
        self, command: str, bound_variables: ParamsSequenceOrDictType
    ) -> Generator[RowType, None, None]:
        """
        Generator which returns rows from query.

        Args:
            command: command to run
            bound_variables: any bound variables
        Yields:
            a row from the query
        """
        conn = None
        curs = None
        try:
            conn = self._get_connection()
            curs = conn.cursor()
            assert isinstance(curs, MySQLCursorAbstract)
            assert isinstance(curs, Iterable)
            curs.execute(command, bound_variables)

            for row in curs:
                yield row

            # Commit as part of the query or results won't be updated between subsequent
            #  transactions. Can lead to values not auto-updating in the GUI.
            conn.commit()
        except Exception as err:
            raise DatabaseError(str(err))
        finally:
            assert isinstance(conn, MySQLConnectionAbstract), "Wrong type"
            assert isinstance(curs, MySQLCursorAbstract)
            self._close_handles(curs, conn)
