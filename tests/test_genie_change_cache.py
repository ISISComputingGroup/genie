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

import unittest

from genie_python.genie_change_cache import ChangeCache


class TestGenieChangeCache(unittest.TestCase):
    def setUp(self):
        self.change_cache = ChangeCache()

    def set_fermi_veto(self, initial_value, enable):
        # Arrange
        self.change_cache.fermi_veto = initial_value

        # Act
        self.change_cache.set_fermi(enable=enable)

        # Assert
        expected_value = 1 if enable else 0
        self.assertEqual(self.change_cache.fermi_veto, expected_value)

    def test_given_no_fermi_veto_WHEN_set_fermi_to_enabled_THEN_fermi_veto_flag_on(self):
        self.set_fermi_veto(0, True)

    def test_given_no_fermi_veto_WHEN_set_fermi_to_disabled_THEN_fermi_veto_flag_off(self):
        self.set_fermi_veto(0, False)

    def test_given_fermi_veto_on_WHEN_set_fermi_to_disabled_THEN_fermi_veto_flag_off(self):
        self.set_fermi_veto(1, False)

    def test_given_fermi_veto_on_WHEN_set_fermi_to_enabled_THEN_fermi_veto_flag_on(self):
        self.set_fermi_veto(1, True)
