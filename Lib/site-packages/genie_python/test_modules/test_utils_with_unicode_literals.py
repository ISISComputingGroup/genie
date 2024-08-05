# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2019 Science & Technology Facilities Council.
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
from __future__ import unicode_literals

import unittest

from genie_python.utilities import get_correct_path


class TestUtilsUnicode(unittest.TestCase):
    """
    Test get_correct_path with unicode literals imported, when they are not in test_utilities.
    """

    def test_GIVEN_windows_style_filepath_WHEN_corrected_THEN_result_is_unix_style(self):
        # Arrange
        filepath = "C:\\TestDir\TestSubDir\file.py"

        # Act
        ans = get_correct_path(filepath)

        # Assert
        self.assertEqual("C:/TestDir/TestSubDir/file.py", ans)

    def test_GIVEN_windows_style_filepath_with_unescaped_chars_WHEN_corrected_THEN_result_is_unix_style(
        self,
    ):
        # Arrange
        # \a and \t are unescaped
        filepath = "C:\\TestDir\aSubDir\test.py"

        # Act
        ans = get_correct_path(filepath)

        # Assert
        self.assertEqual("C:/TestDir/aSubDir/test.py", ans)

    def test_GIVEN_mixed_style_filepath_WHEN_corrected_THEN_result_is_unix_style(self):
        # Arrange
        filepath = "C:/TestDir\TestSubDir/file.py"

        # Act
        ans = get_correct_path(filepath)

        # Assert
        self.assertEqual("C:/TestDir/TestSubDir/file.py", ans)

    def test_GIVEN_overly_backslashed_filepath_WHEN_corrected_THEN_result_is_unix_style(self):
        # Arrange
        filepath = "C:\\\\TestDir//////TestSubDir\\\\\file.py"

        # Act
        ans = get_correct_path(filepath)

        # Assert
        self.assertEqual("C:/TestDir/TestSubDir/file.py", ans)
