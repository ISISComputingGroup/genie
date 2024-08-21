import unittest

from hamcrest.core import assert_that, equal_to
from hamcrest.library.text.stringcontains import contains_string

from genie_python.genie_script_generator import cast_parameters_to


def my_type(string_input):
    if string_input == "default":
        return 0.0
    else:
        return float(string_input)


def my_error_type(string_input):
    raise ValueError


def my_other_error_type(string_input):
    raise ValueError("My error string")


class TestCastParameters(unittest.TestCase):
    def test_GIVEN_func_without_args_and_kwargs_WHEN_called_THEN_expected_returned(self):
        # Arrange
        expected_return = "expected"

        @cast_parameters_to()
        def func(self):
            return expected_return

        # Act and Assert
        assert_that(func(self), equal_to(expected_return), "Should return the base function return")

    def test_GIVEN_func_with_str_that_can_cast_to_int_WHEN_called_with_kwargs_THEN_casts(self):
        # Arrange
        values = {"val1": "1", "val2": "2"}
        expected_returns = (1, 2)

        @cast_parameters_to(val1=int, val2=int)
        def func(self, val1=7, val2=7):
            return val1, val2

        # Act and Assert
        assert_that(
            func(self, **values),
            equal_to(expected_returns),
            "Should return the two values in the dict cast as ints",
        )

    def test_GIVEN_func_with_str_that_cannot_cast_to_int_WHEN_called_with_kwargs_THEN_sensible_reason(
        self,
    ):
        # Arrange
        values = {"val1": "1", "val2": "xx"}
        expected_return = "invalid literal for int() with base 10: 'xx'\n"

        @cast_parameters_to(val1=int, val2=int)
        def func(self, val1=7, val2=7):
            return val1, val2

        # Act and Assert
        assert_that(
            func(self, **values), equal_to(expected_return), "Should return the error when casting"
        )

    def test_GIVEN_func_with_str_that_can_cast_via_custom_caster_WHEN_called_with_kwargs_THEN_casts(
        self,
    ):
        # Arrange
        values = {"val1": "1", "val2": "default"}
        expected_returns = (1.0, 0.0)

        @cast_parameters_to(val1=my_type, val2=my_type)
        def func(self, val1=7, val2=7):
            return val1, val2

        # Act and Assert
        assert_that(
            func(self, **values),
            equal_to(expected_returns),
            "Should return the two values in the dict cast as 'mytype'",
        )

    def test_GIVEN_func_with_str_that_cannot_cast_via_custom_caster_WHEN_called_with_kwargs_THEN_sensible_reason(
        self,
    ):
        # Arrange
        values = {"val1": "1", "val2": "defaultxx"}
        expected_return = "could not convert string to float: 'defaultxx'\n"

        @cast_parameters_to(val1=my_type, val2=my_type)
        def func(self, val1=7, val2=7):
            return val1, val2

        # Act and Assert
        assert_that(
            func(self, **values), equal_to(expected_return), "Should return the error when casting"
        )

    def test_GIVEN_func_with_str_that_can_cast_to_int_WHEN_called_with_args_THEN_casts(self):
        # Arrange
        values = ["1", "2"]
        expected_returns = (1, 2)

        @cast_parameters_to(int, int)
        def func(self, val1, val2):
            return val1, val2

        # Act and Assert
        assert_that(
            func(self, *values),
            equal_to(expected_returns),
            "Should return the two values cast as ints",
        )

    def test_GIVEN_func_with_str_that_cannot_cast_to_int_WHEN_called_with_args_THEN_sensible_reason(
        self,
    ):
        # Arrange
        values = ["1", "xx"]
        expected_return = "invalid literal for int() with base 10: 'xx'"

        @cast_parameters_to(int, int)
        def func(self, val1, val2):
            return val1, val2

        # Act and Assert
        assert_that(
            func(self, *values),
            contains_string(expected_return),
            "Should return the error when casting",
        )

    def test_GIVEN_func_with_str_that_can_cast_via_custom_caster_WHEN_called_with_args_THEN_casts(
        self,
    ):
        # Arrange
        values = ["1", "default"]
        expected_returns = (1.0, 0.0)

        @cast_parameters_to(my_type, my_type)
        def func(self, val1, val2):
            return val1, val2

        # Act and Assert
        assert_that(
            func(self, *values),
            equal_to(expected_returns),
            "Should return the two values cast as 'mytype'",
        )

    def test_GIVEN_func_with_str_that_cannot_cast_via_custom_caster_WHEN_called_with_args_THEN_sensible_reason(
        self,
    ):
        # Arrange
        values = ["1", "defaultxx"]
        expected_return = "could not convert string to float: 'defaultxx'\n"

        @cast_parameters_to(my_type, my_type)
        def func(self, val1, val2):
            return val1, val2

        # Act and Assert
        assert_that(
            func(self, *values), equal_to(expected_return), "Should return the error when casting"
        )

    def test_GIVEN_func_with_str_that_can_cast_to_int_WHEN_called_with_args_and_kwargs_THEN_casts(
        self,
    ):
        # Arrange
        values_args = ["1"]
        values_kwargs = {"val2": "2"}
        expected_returns = (1, 2)

        @cast_parameters_to(int, val2=int)
        def func(self, val1, val2=7):
            return val1, val2

        # Act and Assert
        assert_that(
            func(self, *values_args, **values_kwargs),
            equal_to(expected_returns),
            "Should return the two values cast as ints",
        )

    def test_GIVEN_func_with_str_that_cannot_cast_to_int_WHEN_called_with_args_and_kwargs_THEN_sensible_reason(
        self,
    ):
        # Arrange
        values_args = ["1"]
        values_kwargs = {"val2": "xx"}
        expected_return = "invalid literal for int() with base 10: 'xx'\n"

        @cast_parameters_to(int, val2=int)
        def func(self, val1, val2=7):
            return val1, val2

        # Act and Assert
        assert_that(
            func(self, *values_args, **values_kwargs),
            equal_to(expected_return),
            "Should return the error when casting",
        )

    def test_GIVEN_func_with_str_that_can_cast_via_custom_caster_WHEN_called_with_args_and_kwargs_THEN_casts(
        self,
    ):
        # Arrange
        values_args = ["1"]
        values_kwargs = {"val2": "default"}
        expected_returns = (1.0, 0.0)

        @cast_parameters_to(my_type, val2=my_type)
        def func(self, val1, val2=7):
            return val1, val2

        # Act and Assert
        assert_that(
            func(self, *values_args, **values_kwargs),
            equal_to(expected_returns),
            "Should return the two values cast as 'mytype'",
        )

    def test_GIVEN_func_with_str_that_cannot_cast_via_custom_caster_WHEN_called_with_args_and_kwargs_THEN_sensible_reason(
        self,
    ):
        # Arrange
        values_args = ["1"]
        values_kwargs = {"val2": "defaultxx"}
        expected_return = "could not convert string to float: 'defaultxx'\n"

        @cast_parameters_to(my_type, val2=my_type)
        def func(self, val1, val2=7):
            return val1, val2

        # Act and Assert
        assert_that(
            func(self, *values_args, **values_kwargs),
            equal_to(expected_return),
            "Should return the error when casting",
        )

    def test_GIVEN_more_args_casts_than_args_WHEN_called_THEN_sensible_reason(self):
        # Arrange
        values_args = ["1"]
        expected_return = "There are more casters for arguments than arguments"

        @cast_parameters_to(my_type, int)
        def func(self, val1):
            return val1

        # Act and Assert
        assert_that(
            func(self, *values_args),
            contains_string(expected_return),
            "Should return the error when casting",
        )

    def test_GIVEN_keyword_casts_containing_keys_other_than_in_kwargs_WHEN_called_THEN_sensible_reason(
        self,
    ):
        # Arrange
        values_kwargs = {"val1": "defaultxx"}
        expected_return = (
            "Keyword argument casters contains keys that are not present in keyword arguments"
        )

        @cast_parameters_to(val1=my_type, val2=int)
        def func(self, val1=7):
            return val1

        # Act and Assert
        assert_that(
            func(self, **values_kwargs),
            contains_string(expected_return),
            "Should return the error when casting",
        )

    def test_GIVEN_cast_returns_value_error_with_no_message_WHEN_casting_THEN_sensible_reason(self):
        # Arrange
        values_kwargs = {"val1": "defaultxx"}
        expected_return = "Cannot convert defaultxx from string to my_error_type\n"

        @cast_parameters_to(val1=my_error_type)
        def func(self, val1=None):
            return val1

        # Act and assert
        assert_that(
            func(self, **values_kwargs),
            equal_to(expected_return),
            "Should return the error when casting",
        )

    def test_GIVEN_cast_returns_value_error_with_message_WHEN_casting_THEN_sensible_reason(self):
        # Arrange
        values_kwargs = {"val1": "defaultxx"}
        expected_return = "My error string\n"

        @cast_parameters_to(val1=my_other_error_type)
        def func(self, val1=None):
            return val1

        # Act and assert
        assert_that(
            func(self, **values_kwargs),
            equal_to(expected_return),
            "Should return the error when casting",
        )
