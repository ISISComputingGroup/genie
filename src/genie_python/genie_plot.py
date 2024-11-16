from __future__ import absolute_import, print_function

from builtins import object, str
from functools import wraps


def _plotting_func(func):
    """
    Decorator for functions that interact with MPL.

    Specifically, turns off interactive mode while the graphs are being manipulated and turns
    it back on (and shows the graph) when finished.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        import matplotlib.pyplot as pyplt

        was_interactive = pyplt.isinteractive()
        pyplt.ioff()
        result = func(*args, **kwargs)
        pyplt.interactive(was_interactive)
        pyplt.show(block=False)
        return result

    return wrapper


class SpectraPlot(object):
    @_plotting_func
    def __init__(self, api, spectrum, period, dist):
        import matplotlib.pyplot as pyplt

        self.api = api
        self.spectra = []
        self.fig = pyplt.figure()
        self.ax = pyplt.subplot(111)
        self.ax.autoscale_view(True, True, True)
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Counts")
        self.ax.set_title("Spectrum {}".format(spectrum))
        self.add_spectrum(spectrum, period, dist)

    @_plotting_func
    def add_spectrum(self, spectrum, period=1, dist=True):
        self.spectra.append((spectrum, period, dist))
        data = self.api.dae.get_spectrum(spectrum, period, dist)
        name = "Spect {}".format(spectrum)
        self.ax.plot(data["time"], data["signal"], label=name)
        self.__update_legend()
        return self

    @_plotting_func
    def refresh(self):
        for i in range(len(self.ax.lines)):
            data = self.api.dae.get_spectrum(
                self.spectra[0][0], self.spectra[0][1], self.spectra[0][2]
            )
            line = self.ax.lines[i]
            line.set_data(data["time"], data["signal"])
        self.ax.autoscale_view(True, True, True)

    @_plotting_func
    def delete_plot(self, plotnum):
        del self.ax.lines[plotnum]
        del self.spectra[plotnum]
        self.__update_legend()

    def __update_legend(self):
        handles, labels = self.ax.get_legend_handles_labels()
        self.ax.legend(handles, labels)

    def __repr__(self):
        if len(self.spectra) > 0:
            return "Spectra plot ({})".format(", ".join([str(x[0]) for x in self.spectra]))
        else:
            return "Spectra plot (empty)"
