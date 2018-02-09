from __future__ import absolute_import
from valid_to_import import HelloGenerator


def test_both_styles_of_print_statement():
    print("Hello")
    print "Bonjour"
    return True


def valid():
    return True


def check_import():
    HelloGenerator().greet()
    return True
