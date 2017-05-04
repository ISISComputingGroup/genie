from datetime import datetime


class HelloGenerator(object):
    def greet(self):
        print str(datetime.now()) + ": Hello, world!"