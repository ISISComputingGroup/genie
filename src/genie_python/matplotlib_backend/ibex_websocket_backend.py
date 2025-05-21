"""
A matplotlib backend based on WebAgg, modified to:
- Be non-blocking
- Open plots in the IBEX client
"""

import asyncio
import atexit
import json
import logging
import sys
import threading
from functools import wraps
from time import sleep
from typing import Any, Callable, Mapping, ParamSpec, TypeVar, cast

import tornado
import tornado.websocket
from matplotlib._pylab_helpers import Gcf
from matplotlib.backend_bases import _Backend
from matplotlib.backends import backend_webagg
from matplotlib.backends import backend_webagg_core as core
from py4j.java_collections import ListConverter
from py4j.java_gateway import JavaGateway
from tornado.ioloop import IOLoop
from tornado.websocket import WebSocketClosedError

from genie_python.genie_logging import GenieLogger

logging.getLogger("asyncio").setLevel(logging.WARNING)

DEFAULT_HOST = "127.0.0.1"

PRIMARY_WEB_PORT = 8988
SECONDARY_WEB_PORT = 8989
max_number_of_figures = 3
figure_numbers = []

_web_backend_port = PRIMARY_WEB_PORT
_is_primary = True


T = TypeVar("T")
P = ParamSpec("P")


def _ignore_if_websocket_closed(func: Callable[P, T]) -> Callable[P, T | None]:
    """
    Decorator which ignores exceptions that were caused by websockets being closed.
    """

    @wraps(func)
    def wrapper(*a: P.args, **kw: P.kwargs) -> T | None:
        try:
            return func(*a, **kw)
        except WebSocketClosedError:
            pass
        except Exception as e:
            # Plotting multiple graphs quickly can cause an error where
            # pyplot tries to access a plot which
            # has been removed. This error does not break anything, so log it
            # and continue. It is better for the plot
            # to fail to update than for the whole user script to crash.
            try:
                GenieLogger().log_info_msg(
                    f"Caught (non-fatal) exception while calling matplotlib function: "
                    f"{e.__class__.__name__}: {e}"
                )
            except Exception:
                # Exception while logging, ignore...
                pass
        return None

    return wrapper


def _asyncio_send_exceptions_to_logfile_only(
    loop: asyncio.AbstractEventLoop, context: Mapping[str, Any]
) -> None:
    exception = context.get("exception")
    try:
        GenieLogger().log_info_msg(
            f"Caught (non-fatal) asyncio exception: {exception.__class__.__name__}: {exception}"
        )
    except Exception:
        # Exception while logging, ignore...
        pass


def set_up_plot_default(
    is_primary: bool = True,
    should_open_ibex_window_on_show: bool = True,
    max_figures: int | None = None,
) -> None:
    """
    Set the plot defaults for when show is called

    Args:
        is_primary: True display plot on primary web port; False display
            plot on secondary web port
        should_open_ibex_window_on_show: Does nothing; provided for
            backwards-compatibility with older backend
        max_figures: Maximum number of figures to plot simultaneously (int)
    """
    global _web_backend_port
    if is_primary:
        _web_backend_port = PRIMARY_WEB_PORT
    else:
        _web_backend_port = SECONDARY_WEB_PORT

    global _is_primary
    _is_primary = is_primary

    global max_number_of_figures
    if max_figures is not None:
        max_number_of_figures = max_figures


class WebAggApplication(backend_webagg.WebAggApplication):
    class WebSocket(tornado.websocket.WebSocketHandler):  # pyright: ignore
        supports_binary = True

        def write_message(self, *args: Any, **kwargs: Any) -> asyncio.Future[None]:
            f = super().write_message(*args, **kwargs)

            @_ignore_if_websocket_closed
            def _cb(*args: Any, **kwargs: Any) -> None:
                return f.result()

            f.add_done_callback(_cb)
            return f

        @_ignore_if_websocket_closed
        def open(self, fignum: int, *args: Any, **kwargs: Any) -> None:
            self.fignum = int(fignum)
            self.manager = cast(_FigureManager | None, Gcf.figs.get(self.fignum, None))
            if self.manager is not None:
                self.manager.add_web_socket(self)
                if hasattr(self, "set_nodelay"):
                    self.set_nodelay(True)

        @_ignore_if_websocket_closed
        def on_close(self) -> None:
            if self.manager is not None:
                self.manager.remove_web_socket(self)

        @_ignore_if_websocket_closed
        def on_message(self, message: str | bytes) -> None:
            parsed_message: dict[str, Any] = json.loads(message)
            # The 'supports_binary' message is on a client-by-client
            # basis.  The others affect the (shared) canvas as a
            # whole.
            if parsed_message["type"] == "supports_binary":
                self.supports_binary = parsed_message["value"]
            else:
                manager = cast(_FigureManager | None, Gcf.figs.get(self.fignum, None))
                # It is possible for a figure to be closed,
                # but a stale figure UI is still sending messages
                # from the browser.
                if manager is not None:
                    manager.handle_json(parsed_message)

        @_ignore_if_websocket_closed
        def send_json(self, content: dict[str, str]) -> None:
            self.write_message(json.dumps(content))

        @_ignore_if_websocket_closed
        def send_binary(self, blob: str) -> None:
            if self.supports_binary:
                self.write_message(blob, binary=True)
            else:
                blob_code = blob.encode("base64").replace(b"\n", b"")
                data_uri = f"data:image/png;base64,{blob_code}"
                self.write_message(data_uri)

    ioloop: IOLoop | None = None
    asyncio_loop = None
    started = False
    app = None

    @classmethod
    def initialize(
        cls, url_prefix: str = "", port: int | None = None, address: str | None = None
    ) -> None:
        """
        Create the class instance

        We use a constant, hard-coded port as we will only
        ever have one plot going at the same time.
        """
        cls.app = cls(url_prefix=url_prefix)
        cls.url_prefix = url_prefix
        cls.port = port
        cls.address = address

    @classmethod
    def start(cls) -> None:
        """
        IOLoop.running() was removed as of Tornado 2.4; see for example
        https://groups.google.com/forum/#!topic/python-tornado/QLMzkpQBGOY
        Thus there is no correct way to check if the loop has already been
        launched. We may end up with two concurrently running loops in that
        unlucky case with all the expected consequences.
        """
        try:
            atexit.register(cls.stop)
            loop = asyncio.SelectorEventLoop()
            loop.set_exception_handler(_asyncio_send_exceptions_to_logfile_only)

            # For running in asyncio debug mode, only log _very_ slow callbacks
            # (we get quite a few that take just over 100ms which is the default)
            loop.slow_callback_duration = 500

            asyncio.set_event_loop(loop)
            cls.asyncio_loop = loop
            cls.ioloop = tornado.ioloop.IOLoop.current()
            if cls.port is None or cls.app is None:
                raise RuntimeError(f"port and app must be set (port={cls.port}, app={cls.app})")
            cls.app.listen(cls.port, cls.address)

            # Set the flag to True *before* blocking on ioloop.start()
            cls.started = True
            cls.ioloop.start()
        except Exception:
            import traceback

            traceback.print_exc()

    @classmethod
    def stop(cls) -> None:
        try:

            def _stop() -> None:
                if cls.ioloop is not None:
                    cls.ioloop.stop()
                    sys.stdout.flush()
                    cls.started = False

            if cls.ioloop is not None:
                cls.ioloop.add_callback(_stop)
        except Exception:
            import traceback

            traceback.print_exc()


def ibex_open_plot_window(
    figures: list[int], is_primary: bool = True, host: str | None = None
) -> None:
    """
    Open the plot window in ibex gui through py4j. With sensible defaults
    Args:
        is_primary: True for primary plot window; False for secondary
        host: host that the plot is on; if None default to local host
    """
    port = PRIMARY_WEB_PORT if is_primary else SECONDARY_WEB_PORT
    if host is None:
        host = DEFAULT_HOST
    url = f"{host}:{port}"
    try:
        gateway = JavaGateway()
        converted_figures = ListConverter().convert(figures, gateway._gateway_client)
        gateway.entry_point.openMplRenderer(converted_figures, url, is_primary)  # pyright: ignore (rpc)
    except Exception as e:
        # We need this try-except to be very broad as various
        # exceptions can, in principle,
        # be thrown while translating between python <-> java.
        # If any exceptions occur, it is better to log and
        # continue rather than crashing the entire script.
        print(f"Failed to open plot in IBEX due to: {e}")


IBEX_BACKEND_LOCK = threading.RLock()

_IBEX_FIGURE_MANAGER_LOCK = threading.RLock()


class _FigureManager(core.FigureManagerWebAgg):
    _toolbar2_class = core.NavigationToolbar2WebAgg

    @_ignore_if_websocket_closed
    def _send_event(self, *args: Any, **kwargs: Any) -> None:
        with _IBEX_FIGURE_MANAGER_LOCK:
            super()._send_event(*args, **kwargs)

    def remove_web_socket(self, *args: Any, **kwargs: Any) -> None:
        with _IBEX_FIGURE_MANAGER_LOCK:
            super().remove_web_socket(*args, **kwargs)

    def add_web_socket(self, *args: Any, **kwargs: Any) -> None:
        with _IBEX_FIGURE_MANAGER_LOCK:
            super().add_web_socket(*args, **kwargs)

    @_ignore_if_websocket_closed
    def refresh_all(self) -> None:
        with _IBEX_FIGURE_MANAGER_LOCK:
            super().refresh_all()

    @classmethod
    def pyplot_show(cls, *args: Any, **kwargs: Any) -> None:
        """
        Show a plot.

        Args:
            args and kwargs: ignored (needed for compatibility with genie_python)
        """
        if not WebAggApplication.started:
            with IBEX_BACKEND_LOCK:
                WebAggApplication.initialize(port=_web_backend_port)
                worker_thread = threading.Thread(
                    target=WebAggApplication.start, daemon=True, name="ibex_websocket_backend"
                )
                worker_thread.start()

                for _ in range(1000):
                    # Wait for it to start
                    if WebAggApplication.started:
                        break
                    sleep(0.01)
                else:
                    # If for some reason thread failed to start, log an error then continue anyway
                    # (we do not want to hang the entire script)
                    print("Failed to start plotting thread - plots will not be available")

        ibex_open_plot_window(list(Gcf.figs.keys()), is_primary=_is_primary)

        with IBEX_BACKEND_LOCK:
            try:
                Gcf.draw_all()
            except Exception:
                # Very occasionally draw_all() can fail, if that's the case it's better to not draw
                # (IBEX will force an update 2s later anyway) rather than crash.
                pass


class _FigureCanvas(backend_webagg.FigureCanvasWebAgg):
    manager_class = _FigureManager

    def set_image_mode(self, mode: str) -> None:
        """
        Always send full images to ibex.
        """
        self._current_image_mode = "full"

    def get_diff_image(self) -> bytes | None:
        """
        Always send full images to ibex.
        """
        self._force_full = True
        return super().get_diff_image()

    def draw_idle(self) -> None:
        """
        From
        https://matplotlib.org/stable/api/backend_bases_api.html#matplotlib.backend_bases.FigureCanvasBase.draw_idle

        'Backends may choose to override the method and implement
        their own strategy to prevent multiple renderings.'

        The IBEX GUI has it's own (RCP) mechanism for preventing concurrent drawing,
        therefore it is sufficient to define this as a no-op. The IBEX GUI also automatically
        requests a plot redraw every 2 seconds.

        Note: don't call superclass here. The superclass sends a "draw" websocket event,
        which can lead to a queue of UI events building up and excessive memory use.
        """


@_Backend.export
class _BackendIbexWebAgg(_Backend):
    FigureCanvas = _FigureCanvas
    FigureManager = _FigureManager

    @classmethod
    def trigger_manager_draw(cls, manager: FigureManager) -> None:
        with IBEX_BACKEND_LOCK:
            manager.canvas.draw_idle()

    @classmethod
    def draw_if_interactive(cls) -> None:
        with IBEX_BACKEND_LOCK:
            super(_BackendIbexWebAgg, cls).draw_if_interactive()  # pyright: ignore

    @classmethod
    def new_figure_manager(cls, num: int, *args: Any, **kwargs: Any) -> _FigureManager:
        with IBEX_BACKEND_LOCK:
            for x in list(figure_numbers):
                if x not in Gcf.figs.keys():
                    figure_numbers.remove(x)
            figure_numbers.append(num)
            if len(figure_numbers) > max_number_of_figures:
                Gcf.destroy(figure_numbers[0])
                print(
                    f"There are too many figures so deleted "
                    f"the oldest figure, which was {figure_numbers[0]}."
                )
                figure_numbers.pop(0)
            return super(_BackendIbexWebAgg, cls).new_figure_manager(num, *args, **kwargs)  # pyright: ignore
