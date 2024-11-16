import time
import unittest

import mock

from genie_python.matplotlib_backend import ibex_websocket_backend


class ErroringWebAggApplication(object):
    started = False

    @classmethod
    def initialize(cls, *a, **k):
        pass

    @classmethod
    def start(cls, *a, **k):
        raise IOError("Mock matplotlib worker thread error")


class TestMatplotlibBackend(unittest.TestCase):
    def test_WHEN_plotting_thread_fails_to_start_THEN_script_does_not_hang(self):
        ibex_websocket_backend.WebAggApplication = ErroringWebAggApplication
        ibex_websocket_backend.ibex_open_plot_window = lambda *a, **k: None
        ibex_websocket_backend.Gcf = mock.MagicMock()

        start = time.time()
        ibex_websocket_backend._BackendIbexWebAgg.show()

        self.assertLess(time.time() - start, 30, "show() hung for more than 30 seconds")
