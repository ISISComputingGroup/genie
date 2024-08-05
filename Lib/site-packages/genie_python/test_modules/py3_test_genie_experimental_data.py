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
from __future__ import absolute_import

import datetime
import unittest

from hamcrest import assert_that, calling, raises
from mock import call, patch
from parameterized import parameterized

from genie_python.genie_experimental_data import (
    SELECT_FOR_EXP_DETAILS,
    GetExperimentData,
    NotFoundError,
)


class TestGetExperimentData(unittest.TestCase):
    def setUp(self):
        patcher = patch("genie_python.genie_experimental_data.SQLAbstraction")
        self.addCleanup(patcher.stop)
        self.mock_sql = patcher.start()

        self.db_access = GetExperimentData("")

    @parameterized.expand(
        [
            (["%", "%", "%"], [None, None, None], False, "%"),
            ([1, "%", "%"], [1, None, None], False, "%"),
            ([1, "%", "%"], [None, None, None], True, "Found no experiments with RB number 1."),
            ([1, "a", "%"], [1, "a", None], False, "%"),
            (
                [1, "a", "%"],
                [1, None, None],
                True,
                'User with name "a" was not found. Please make sure the title and'
                ' name are correct (e.g. "Dr John Smith").',
            ),
            ([1, "a", "b"], [1, "a", "b"], False, "%"),
            ([1, "a", "b"], [1, "a", None], True, 'Role "{role}" was not found. Existing roles: '),
            (["%", "a", "%"], [None, "a", None], False, "%"),
            (
                ["%", "a", "%"],
                [None, None, None],
                True,
                'User with name "a" was not found. Please make sure the title and'
                ' name are correct (e.g. "Dr John Smith").',
            ),
            (["%", "%", "b"], [None, None, "b"], False, "%"),
            (
                ["%", "%", "b"],
                [None, None, None],
                True,
                'Role "{role}" was not found. Existing roles: ',
            ),
        ]
    )
    def test_GIVEN_parameters_WHEN_validate_parameters_THEN_correct_validation(
        self, args, res, err_exp, err_msg
    ):
        # Arrange
        self.mock_sql().query.side_effect = res

        # Act & Assert
        if err_exp is True:
            assert_that(
                calling(self.db_access.get_exp_data).with_args(args[0], args[1], args[2]),
                raises(NotFoundError),
            )

    @parameterized.expand(
        [
            (
                "%",
                "%",
                "%",
                f"{SELECT_FOR_EXP_DETAILS} WHERE e.experimentID LIKE '%' AND u.name LIKE '%' AND r.name LIKE '%' "
                f"ORDER BY experimentID DESC",
            ),
            (
                123,
                "%",
                "%",
                f"{SELECT_FOR_EXP_DETAILS} WHERE e.experimentID = %s AND u.name LIKE '%' AND r.name LIKE '%' "
                f"ORDER BY experimentID DESC",
            ),
            (
                "%",
                "name",
                "%",
                f"{SELECT_FOR_EXP_DETAILS} WHERE e.experimentID LIKE '%' AND upper(u.name) = upper(%s) "
                f"AND r.name LIKE '%' ORDER BY experimentID DESC",
            ),
            (
                "%",
                "%",
                "role",
                f"{SELECT_FOR_EXP_DETAILS} WHERE e.experimentID LIKE '%' AND u.name LIKE '%' AND "
                f"upper(r.name) = upper(%s) ORDER BY experimentID DESC",
            ),
            (
                123,
                "user",
                "%",
                f"{SELECT_FOR_EXP_DETAILS} WHERE e.experimentID = %s AND upper(u.name) = upper(%s) AND r.name LIKE '%' "
                f"ORDER BY experimentID DESC",
            ),
            (
                123,
                "%",
                "role",
                f"{SELECT_FOR_EXP_DETAILS} WHERE e.experimentID = %s AND u.name LIKE '%' AND upper(r.name) = upper(%s) "
                f"ORDER BY experimentID DESC",
            ),
            (
                "%",
                "name",
                "role",
                f"{SELECT_FOR_EXP_DETAILS} WHERE e.experimentID LIKE '%' AND upper(u.name) = upper(%s) "
                f"AND upper(r.name) = upper(%s) ORDER BY experimentID DESC",
            ),
            (
                123,
                "name",
                "role",
                f"{SELECT_FOR_EXP_DETAILS} WHERE e.experimentID = %s AND upper(u.name) = upper(%s) "
                f"AND upper(r.name) = upper(%s) ORDER BY experimentID DESC",
            ),
        ]
    )
    def test_GIVEN_args_WHEN_preparing_statement_THEN_correct_sql_statement(
        self, rb_no, user, role, sql_exp
    ):
        # Arrange
        bound_vars = [x for x in [rb_no, user, role] if x != "%"]

        # Act
        args, sql_actual = self.db_access._create_sql_statement_and_args(
            rb=rb_no, user=user, role=role
        )

        # Assert
        self.assertEqual(sql_exp, sql_actual)
        self.assertEqual(bound_vars, args)

    @parameterized.expand(
        [
            (
                [
                    ("111", "user_name_1", "role_name_1", datetime.datetime(2020, 9, 15, 8, 30), 1),
                    ("212", "user_name_2", "role_name_1", datetime.datetime(2020, 12, 8, 8, 30), 1),
                    ("765", "user_name_3", "role_name_1", datetime.datetime(2020, 10, 8, 8, 30), 1),
                    ("765", "user_name_4", "role_name_2", datetime.datetime(2020, 10, 8, 8, 30), 1),
                    ("887", "user_name_5", "role_name_1", datetime.datetime(2020, 9, 18, 8, 30), 1),
                    ("887", "user_name_6", "role_name_2", datetime.datetime(2020, 9, 18, 8, 30), 1),
                    ("912", "user_name_7", "role_name_1", datetime.datetime(2020, 9, 11, 8, 30), 1),
                    ("912", "user_name_8", "role_name_2", datetime.datetime(2020, 9, 11, 8, 30), 1),
                ],
                [
                    {
                        "rb_number": "111",
                        "user": "user_name_1",
                        "role": "role_name_1",
                        "start_date": "2020-09-15 08:30:00",
                        "duration": 1,
                    },
                    {
                        "rb_number": "212",
                        "user": "user_name_2",
                        "role": "role_name_1",
                        "start_date": "2020-12-08 08:30:00",
                        "duration": 1,
                    },
                    {
                        "rb_number": "765",
                        "user": "user_name_3",
                        "role": "role_name_1",
                        "start_date": "2020-10-08 08:30:00",
                        "duration": 1,
                    },
                    {
                        "rb_number": "765",
                        "user": "user_name_4",
                        "role": "role_name_2",
                        "start_date": "2020-10-08 08:30:00",
                        "duration": 1,
                    },
                    {
                        "rb_number": "887",
                        "user": "user_name_5",
                        "role": "role_name_1",
                        "start_date": "2020-09-18 08:30:00",
                        "duration": 1,
                    },
                    {
                        "rb_number": "887",
                        "user": "user_name_6",
                        "role": "role_name_2",
                        "start_date": "2020-09-18 08:30:00",
                        "duration": 1,
                    },
                    {
                        "rb_number": "912",
                        "user": "user_name_7",
                        "role": "role_name_1",
                        "start_date": "2020-09-11 08:30:00",
                        "duration": 1,
                    },
                    {
                        "rb_number": "912",
                        "user": "user_name_8",
                        "role": "role_name_2",
                        "start_date": "2020-09-11 08:30:00",
                        "duration": 1,
                    },
                ],
            ),
            (
                [("111", "user_name_1", "role_name_1", datetime.datetime(2020, 9, 15, 8, 30), 1)],
                [
                    {
                        "rb_number": "111",
                        "user": "user_name_1",
                        "role": "role_name_1",
                        "start_date": "2020-09-15 08:30:00",
                        "duration": 1,
                    }
                ],
            ),
            ([], []),
        ]
    )
    def test_GIVEN_records_WHEN_query_exp_data_THEN_correct_exp_data_returned(
        self, records, expected
    ):
        # Arrange
        self.mock_sql().query_returning_cursor.return_value = iter(records)

        # Act
        exp_data = self.db_access._query_database_for_data("", "")

        # Assert
        self.assertEqual(expected, exp_data)

    @parameterized.expand(
        [
            (
                [
                    {
                        "rb_number": "1",
                        "user": "user_name_-",
                        "role": "role_name_-",
                        "start_date": "2020-09-15 08:30:00",
                        "duration": "duration_1",
                    },
                    {
                        "rb_number": "22",
                        "user": "user_name_--",
                        "role": "role_name_--",
                        "start_date": "2020-09-15 08:30:00",
                        "duration": "duration_22",
                    },
                    {
                        "rb_number": "332",
                        "user": "user_name_---",
                        "role": "role_name_--",
                        "start_date": "2020-09-15 08:30:00",
                        "duration": "duration_332",
                    },
                    {
                        "rb_number": "4413",
                        "user": "user_name_-",
                        "role": "role_name_---",
                        "start_date": "2020-09-15 08:30:00",
                        "duration": "duration_4413",
                    },
                    {
                        "rb_number": "167",
                        "user": "user_name_------",
                        "role": "role_name_-------",
                        "start_date": "2020-09-15 08:30:00",
                        "duration": "duration_167",
                    },
                    {
                        "rb_number": "1",
                        "user": "user_name_-",
                        "role": "role_name_-",
                        "start_date": "2020-09-15 08:30:00",
                        "duration": "duration_1",
                    },
                ],
                [
                    "Experiment RB number: 1    | User: user_name_-      | Role: role_name_-       | Start date: "
                    "2020-09-15 08:30:00 | Duration: duration_1",
                    "Experiment RB number: 22   | User: user_name_--     | Role: role_name_--      | Start date: "
                    "2020-09-15 08:30:00 | Duration: duration_22",
                    "Experiment RB number: 332  | User: user_name_---    | Role: role_name_--      | Start date: "
                    "2020-09-15 08:30:00 | Duration: duration_332",
                    "Experiment RB number: 4413 | User: user_name_-      | Role: role_name_---     | Start date: "
                    "2020-09-15 08:30:00 | Duration: duration_4413",
                    "Experiment RB number: 167  | User: user_name_------ | Role: role_name_------- | Start date: "
                    "2020-09-15 08:30:00 | Duration: duration_167",
                    "Experiment RB number: 1    | User: user_name_-      | Role: role_name_-       | Start date: "
                    "2020-09-15 08:30:00 | Duration: duration_1",
                ],
            ),
            (
                [
                    {
                        "rb_number": "1",
                        "user": "user_name_-",
                        "role": "role_name_-",
                        "start_date": "2020-09-15 08:30:00",
                        "duration": "duration_1",
                    },
                ],
                [
                    "Experiment RB number: 1 | User: user_name_- | Role: role_name_- | Start date: 2020-09-15 08:30:00"
                    " | Duration: duration_1"
                ],
            ),
            (
                [
                    {
                        "rb_number": "167",
                        "user": "user_name_------",
                        "role": "role_name_-------",
                        "start_date": "2020-09-15 08:30:00",
                        "duration": "duration_167",
                    },
                    {
                        "rb_number": "1",
                        "user": "user_name_-",
                        "role": "role_name_-",
                        "start_date": "2020-09-15 08:30:00",
                        "duration": "duration_1",
                    },
                ],
                [
                    "Experiment RB number: 167 | User: user_name_------ | Role: role_name_------- | Start date: "
                    "2020-09-15 08:30:00 | Duration: duration_167",
                    "Experiment RB number: 1   | User: user_name_-      | Role: role_name_-       | Start date: "
                    "2020-09-15 08:30:00 | Duration: duration_1",
                ],
            ),
            (
                [
                    {
                        "rb_number": "1",
                        "user": "user_name_-",
                        "role": "role_name_-",
                        "start_date": "2020-09-15 08:30:00",
                        "duration": "duration_1",
                    },
                    {
                        "rb_number": "22",
                        "user": "user_name_--",
                        "role": "role_name_--",
                        "start_date": "2020-09-15 08:30:00",
                        "duration": "duration_22",
                    },
                ],
                [
                    "Experiment RB number: 1  | User: user_name_-  | Role: role_name_-  | Start date: 2020-09-15 "
                    "08:30:00 | Duration: duration_1",
                    "Experiment RB number: 22 | User: user_name_-- | Role: role_name_-- | Start date: 2020-09-15 "
                    "08:30:00 | Duration: duration_22",
                ],
            ),
        ]
    )
    @patch("builtins.print")
    def test_GIVEN_different_length_WHEN_pretty_printing_THEN_correct_padding(
        self, data, result, m_print
    ):
        # Arrange
        calls = [call(x) for x in result]

        # Act
        self.db_access._pretty_print(data)

        # Assert
        m_print.assert_has_calls(calls, any_order=False)
