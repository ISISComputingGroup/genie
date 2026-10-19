from collections.abc import Callable
from functools import wraps
from typing import Any, Self


def _plotting_func[T, R](func: Callable[T, R]) -> Callable[T, R]:
    """
    Decorator for functions that interact with MPL.

    Specifically, turns off interactive mode while the graphs are being manipulated and turns
    it back on (and shows the graph) when finished.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> R:
        import matplotlib.pyplot as pyplt

        was_interactive = pyplt.isinteractive()
        pyplt.ioff()
        result = func(*args, **kwargs)
        pyplt.interactive(was_interactive)
        pyplt.show(block=False)
        return result

    return wrapper


class SpectraPlot:
    @_plotting_func
    def __init__(self, api: Any, spectrum: int, period: int, dist: bool) -> None:
        import matplotlib.pyplot as pyplt

        self.api = api
        self.spectra = []
        self.fig = pyplt.figure()
        self.ax = pyplt.subplot(111)
        self.ax.autoscale_view(True, True, True)
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Counts")
        self.ax.set_title(f"Spectrum {spectrum}")
        self.add_spectrum(spectrum, period, dist)

    @_plotting_func
    def add_spectrum(self, spectrum: int, period: int = 1, dist: bool = True) -> Self:
        self.spectra.append((spectrum, period, dist))
        data = self.api.dae.get_spectrum(spectrum, period, dist)
        name = f"Spect {spectrum}"
        self.ax.plot(data["time"], data["signal"], label=name)
        self.__update_legend()
        return self

    @_plotting_func
    def refresh(self) -> None:
        for i in range(len(self.ax.lines)):
            data = self.api.dae.get_spectrum(
                self.spectra[0][0], self.spectra[0][1], self.spectra[0][2]
            )
            line = self.ax.lines[i]
            line.set_data(data["time"], data["signal"])
        self.ax.autoscale_view(True, True, True)

    @_plotting_func
    def delete_plot(self, plotnum: int) -> None:
        del self.ax.lines[plotnum]
        del self.spectra[plotnum]
        self.__update_legend()

    def __update_legend(self) -> None:
        handles, labels = self.ax.get_legend_handles_labels()
        self.ax.legend(handles, labels)

    def __repr__(self) -> str:
        if len(self.spectra) > 0:
            return "Spectra plot ({})".format(", ".join([str(x[0]) for x in self.spectra]))
        else:
            return "Spectra plot (empty)"
