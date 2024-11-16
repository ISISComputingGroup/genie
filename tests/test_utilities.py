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

import json
import unittest

from mock import Mock

from genie_python.utilities import (
    EnvironmentDetails,
    PVReadException,
    compress_and_hex,
    convert_string_to_ascii,
    crc8,
    dehex_and_decompress,
    get_correct_path,
    get_json_pv_value,
    remove_field_from_pv,
    waveform_to_string,
)


class TestUtilitiesSequence(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @staticmethod
    def get_test_strings():
        return [
            "Hello, world!",
            "<xml>Some <adj>token</adj> xml</xml>",
            'Special <%$^">| characters',
            "Num83r5",
        ]

    def test_GIVEN_string_WHEN_string_is_compressed_and_hexed_THEN_return_value_is_valid_hex(self):
        # Arrange
        strings_to_test = self.get_test_strings()

        # Act
        hexed_strings = list()
        for string in strings_to_test:
            hexed_strings.append(compress_and_hex(string))

        # Assert
        for string in hexed_strings:
            try:
                int(string, 16)
            except ValueError:
                self.fail("Could not convert hexed string " + string + ". An exception was raised.")

    def test_GIVEN_string_WHEN_string_is_compressed_and_decompressed_THEN_return_value_matches_original(
        self,
    ):
        # Arrange
        strings_to_test = self.get_test_strings()

        # Act
        manipulated_strings = list()
        for string in strings_to_test:
            manipulated_strings.append(dehex_and_decompress(compress_and_hex(string)))

        # Assert
        for i in range(len(strings_to_test)):
            self.assertEqual(strings_to_test[i], manipulated_strings[i])

    def check_waveform(self, input_value, expected_value):
        self.assertTrue(expected_value in waveform_to_string(input_value))

    @staticmethod
    def create_waveform_from_list(input_list):
        if len(input_list) != 0 and isinstance(input_list[0], str):
            return "".join(input_list)
        return "".join([chr(i) for i in input_list])

    def test_GIVEN_short_list_of_strings_WHEN_waveform_converted_to_string_THEN_result_contains_a_string_of_strings(
        self,
    ):
        # Arrange
        test_waveform = ["hello", "world"]

        expected_value = self.create_waveform_from_list(test_waveform)

        # Act

        # Assert
        self.check_waveform(test_waveform, expected_value)

    def test_GIVEN_long_list_of_strings_WHEN_waveform_converted_to_string_THEN_result_contains_a_string_of_strings(
        self,
    ):
        # Arrange
        test_waveform = ["this", "is", "a", "long", "list", "of", "strings!"]

        expected_value = self.create_waveform_from_list(test_waveform)

        # Act

        # Assert
        self.check_waveform(test_waveform, expected_value)

    def test_GIVEN_short_list_of_numbers_WHEN_waveform_converted_to_string_THEN_result_contains_string_of_unicode_chars_for_numbers(
        self,
    ):
        # Arrange
        test_waveform = [1, 2, 3, 4]

        expected_value = self.create_waveform_from_list(test_waveform)

        # Act

        # Assert
        self.check_waveform(test_waveform, expected_value)

    def test_GIVEN_list_of_numbers_containing_0_WHEN_waveform_converted_to_string_THEN_result_terminates_at_character_before_0(
        self,
    ):
        # Arrange
        test_waveform = [1, 2, 3, 4, 0, 5, 6, 7, 8, 9]

        expected_value = self.create_waveform_from_list([1, 2, 3, 4])

        # Act

        # Assert
        self.check_waveform(test_waveform, expected_value)

    def test_GIVEN_long_list_of_numbers_WHEN_waveform_converted_to_string_THEN_result_contains_string_of_unicode_chars_for_numbers(
        self,
    ):
        # Arrange
        max_unichr = 128
        length = 1000
        test_waveform = [max(i % max_unichr, 1) for i in range(1, length)]

        expected_value = self.create_waveform_from_list(test_waveform)

        # Act

        # Assert
        self.check_waveform(test_waveform, expected_value)

    def test_GIVEN_negative_integer_in_waveform_WHEN_waveform_converted_to_string_THEN_result_raises_value_error(
        self,
    ):
        # Arrange
        test_waveform = [-1]

        # Act

        # Assert
        with self.assertRaises(ValueError):
            waveform_to_string(test_waveform)

    def test_GIVEN_windows_style_filepath_WHEN_corrected_THEN_result_is_unix_style(self):
        # Arrange
        filepath = "C:\\TestDir\\TestSubDir\\file.py"

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

    def test_GIVEN_pv_with_field_WHEN_remove_field_called_THEN_field_removed(self):
        self.assertEqual(remove_field_from_pv("IN:TEST:BLAH.RVAL"), "IN:TEST:BLAH")

    def test_GIVEN_pv_with_no_field_WHEN_remove_field_called_THEN_pv_returned_unchanged(self):
        self.assertEqual(remove_field_from_pv("IN:TEST:BLAH"), "IN:TEST:BLAH")


class TestCRC8Util(unittest.TestCase):
    def calc_and_test(self, expected, inst):
        result = crc8(inst)
        self.assertEqual(
            result, expected, 'CRC value was "{0}" expected "{1}"'.format(result, expected)
        )

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_GIVEN_empty_string_WHEN_crc8_THEN_result_is_blank(self):
        self.calc_and_test("", "")

    def test_GIVEN_a_WHEN_crc8_THEN_result_is_20(self):
        self.calc_and_test("20", "a")

    def test_GIVEN_b_WHEN_crc8_THEN_result_correct(self):
        self.calc_and_test("29", "b")

    def test_GIVEN_string_WHEN_crc8_THEN_result_correct(self):
        self.calc_and_test("A8", "hello world")

    def test_GIVEN_string_which_gives_hex_letters_WHEN_crc8_THEN_result_correct(self):
        self.calc_and_test("EB", "NDW1407")

    def test_GIVEN_string_which_gives_hex_less_than_10_WHEN_crc8_THEN_result_correct(self):
        self.calc_and_test("03", "l")


class TestEnvironmentDetails(unittest.TestCase):
    def test_GIVEN_readable_pv_WHEN_get_inst_list_THEN_list_returns(self):
        expected_result = [{"name": "john"}]
        compressed_list = compress_and_hex(json.dumps(expected_result))
        api = Mock()
        api.get_pv_value = Mock(return_value=compressed_list)
        env_details = EnvironmentDetails()

        result = env_details.get_instrument_list(api)

        self.assertEqual(result, expected_result)

    def test_GIVEN_invalid_list_WHEN_get_inst_list_THEN_list_returns(self):
        invalid_json = '["name": "john"}]'
        compressed_list = compress_and_hex(invalid_json)
        api = Mock()
        api.get_pv_value = Mock(return_value=compressed_list)
        env_details = EnvironmentDetails()

        result = env_details.get_instrument_list(api)

        self.assertEqual(result, EnvironmentDetails.DEFAULT_INST_LIST)


class TestGetJsonPVValue(unittest.TestCase):
    def test_GIVEN_invalid_json_WHEN_get_pv_THEN_list_raise(self):
        invalid_json = '["name": "john"}]'
        compressed_list = compress_and_hex(invalid_json)
        api = Mock()
        api.get_pv_value = Mock(return_value=compressed_list)

        self.assertRaisesRegex(
            PVReadException, "Can not unmarshal.*", get_json_pv_value, "name", api
        )

    def test_GIVEN_valid_json_WHEN_get_pv_THEN_return_python_object(self):
        expected_result = [{"name": "john"}]
        compressed_list = compress_and_hex(json.dumps(expected_result))
        api = Mock()
        api.get_pv_value = Mock(return_value=compressed_list)

        result = get_json_pv_value("name", api)

        self.assertEqual(result, expected_result)

    def test_GIVEN_invalid_compressed_string_WHEN_get_pv_THEN_raise(self):
        invalid_string = "sfjklsdf;"
        api = Mock()
        api.get_pv_value = Mock(return_value=(invalid_string))

        self.assertRaisesRegex(
            PVReadException, "Can not decompress.*", get_json_pv_value, "name", api
        )

    def test_GIVEN_pv_can_not_be_read_WHEN_get_pv_THEN_raise(self):
        api = Mock()
        api.get_pv_value = Mock(side_effect=Exception())

        self.assertRaisesRegex(PVReadException, "Can not read.*", get_json_pv_value, "name", api)

    def test_GIVEN_unicode_with_only_ascii_WHEN_converted_THEN_no_change(self):
        # Arrange
        input = "abcdefghijklmnopqrstuvwxyz1234567890"

        # Act
        output = convert_string_to_ascii(input)

        # Assert
        self.assertEqual(input, output)

    def test_GIVEN_unicode_with_non_ascii_accented_e_WHEN_converted_THEN_is_corrected(self):
        # Arrange
        input = "\xe8\xe9\xea\xeb"

        # Act
        output = convert_string_to_ascii(input)

        # Assert
        self.assertEqual("eeee", output)

    def test_GIVEN_unicode_with_non_ascii_accented_o_WHEN_converted_THEN_is_corrected(self):
        # Arrange
        input = "mot\xf6rhead"

        # Act
        output = convert_string_to_ascii(input)

        # Assert
        self.assertEqual("motorhead", output)

    def test_GIVEN_unicode_with_non_ascii_run_together_ae_WHEN_converted_THEN_is_corrected(self):
        # Arrange
        input = "encyclop\xe6dia"

        # Act
        output = convert_string_to_ascii(input)

        # Assert
        self.assertEqual("encyclopaedia", output)
