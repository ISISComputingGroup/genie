from __future__ import absolute_import
from __future__ import print_function
from datetime import datetime


class HelloGenerator(object):
    def greet(self):
        print(str(datetime.now()) + ": Hello, world!")