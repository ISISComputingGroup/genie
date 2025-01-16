"""
Genie Database Access module.
"""

from typing import TypedDict

from genie_python.mysql_abstraction_layer import SQLAbstraction

SELECT_FOR_EXP_DETAILS = """
SELECT e.experimentID, u.name as userName, r.name as roleName,
t.startDate, e.duration FROM `experimentteams` t
JOIN experiment e ON e.experimentID = t.experimentID
JOIN user u ON u.userID = t.userID
JOIN role r ON r.roleID = t.roleID
"""


class GetExperimentData:
    """
    Class for storing the get_exp_data RB lookup command and related utility methods.
    """

    def __init__(self, instrument: str) -> None:
        self.instrument = instrument
        self._sql = SQLAbstraction(
            dbid="exp_data", user="report", password="$report", host=self.instrument
        )

    def get_sql(self) -> SQLAbstraction:
        """
        Get the one and only SQL abstraction layer.

        Returns:
             The SQL abstraction layer
        """
        return self._sql

    def _parameter_is_valid(self, value: bool | int | float | str, column: str, table: str) -> bool:
        """
        Checks whether the given value exists in the table.

        Args:
            value: the value to search for
            column: the column to search in
            table: the table to search in

        Returns:
            True if value was found, False otherwise

        """
        result = self.get_sql().query(
            command=f"SELECT * FROM `{table}` WHERE {column} = %s", bound_variables=(value,)
        )

        return True if result else False

    class _GetExpDataReturn(TypedDict):
        rb_number: int | str
        user: str
        role: str
        start_date: str
        duration: float

    def get_exp_data(
        self, rb: int | str = "%", user: str = "%", role: str = "%", verbose: bool = False
    ) -> list[_GetExpDataReturn]:
        """
        Returns the data of experiments that match the given criteria,
        or all if none is given, from the exp_data
        database. If verbose is enabled, only pretty-print the data.

        Args:
            rb (int, optional): The RB number of the experiment to look for, Defaults to Any.
            user (str, optional): The name of the user who is running/has
                run the experiment, Defaults to Any.
            role (str, optional): The user role, Defaults to Any.
            verbose (bool, optional): Pretty-print the data, Defaults to False.

        Returns:
            exp_data (list): The experiment(s) data as a list of dicts.

        Raises:
            NotFoundError: Thrown if a parameter's value was not found in the database.

        """
        self._validate_parameters(rb, user, role)

        args, sql = self._create_sql_statement_and_args(rb, role, user)

        exp_data = self._query_database_for_data(args, sql)

        if verbose:
            if exp_data:
                self._pretty_print(exp_data)
            else:
                raise NotFoundError(
                    f"Found no experiments that match the given criteria "
                    f"(RB: {rb if rb != '%' else 'Any'}, "
                    f"User: {user if user != '%' else 'Any'}, "
                    f"Role: {role if role != '%' else 'Any'}).\n"
                )

        return exp_data

    def _validate_parameters(self, rb: int | str, user: str, role: str) -> None:
        if rb != "%" and not self._parameter_is_valid(rb, "experimentID", "experimentteams"):
            raise NotFoundError(f"Found no experiments with RB number {rb}.")
        if user != "%" and not self._parameter_is_valid(user, "name", "user"):
            raise NotFoundError(
                f'User with name "{user}" was not found. Please make sure the title and name are '
                f'correct (e.g. "Dr John Smith").'
            )
        if role != "%" and not self._parameter_is_valid(role, "name", "role"):
            roles = ", ".join(
                [x[0] for x in self.get_sql().query_returning_cursor("SELECT name FROM `role`", ())]
            )
            raise NotFoundError(f'Role "{role}" was not found. Existing roles: {roles}')

    def _query_database_for_data(
        self, args: bool | int | float | str, sql: str
    ) -> list[_GetExpDataReturn]:
        exp_data = []
        for exp_id, user, role, start_date, duration in self.get_sql().query_returning_cursor(
            sql, args
        ):
            start_date = start_date.strftime("%Y-%m-%d %H:%M:%S")
            experiment_details = {
                "rb_number": exp_id,
                "user": user,
                "role": role,
                "start_date": start_date,
                "duration": duration,
            }
            exp_data.append(experiment_details)
        return exp_data

    @staticmethod
    def _create_sql_statement_and_args(
        rb: int | str, user: str, role: str
    ) -> tuple[bool | int | float | str, str]:
        """
        Prepare the statement and bound variables

        Args:
            rb: rb number of the experiment
            role: role being searched for
            user: user being searched for

        Returns:
            args: the bound variables
            sql: the SQL command
        """
        sql = SELECT_FOR_EXP_DETAILS + " WHERE "
        where_clauses = [
            "e.experimentID = %s" if rb != "%" else "e.experimentID LIKE '%'",
            "upper(u.name) = upper(%s)" if user != "%" else "u.name LIKE '%'",
            "upper(r.name) = upper(%s)" if role != "%" else "r.name LIKE '%'",
        ]
        args = [x for x in [rb, user, role] if x != "%"]
        sql += " AND ".join(where_clauses) + " ORDER BY experimentID DESC"
        return args, sql

    @staticmethod
    def _pretty_print(exp_data: list[_GetExpDataReturn]) -> None:
        # For pretty printing
        rb_padding = max(len(x) for x in [y["rb_number"] for y in exp_data])
        user_padding = max(len(x) for x in [y["user"] for y in exp_data])
        role_padding = max(len(x) for x in [y["role"] for y in exp_data])

        for exp in exp_data:
            print(
                f"Experiment RB number: {exp['rb_number']:{rb_padding}} | "
                f"User: {exp['user']:{user_padding}} | "
                f"Role: {exp['role']:{role_padding}} | "
                f"Start date: {exp['start_date']} | "
                f"Duration: {exp['duration']}"
            )


class NotFoundError(IOError):
    """
    Exception that is thrown if a value was not found in the database.
    """

    def __init__(self, message: str) -> None:
        super(NotFoundError, self).__init__(message)
