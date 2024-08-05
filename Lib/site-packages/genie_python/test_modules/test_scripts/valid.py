from __future__ import absolute_import

from valid_to_import import HelloGenerator


def valid():
    return True


def check_import():
    HelloGenerator().greet()
    return True
