from __future__ import absolute_import

from builtins import object

import matplotlib.dates as dates
import scisoftpy as dnp

# Plot using a scisoftpy's AnalysisRPC plot server, e.g. to display in a Java application


class SePlot(object):
    def __init__(self):
        self.title = "Se plot"
        # TODO: Set date/time formatting for x-axis

    def add_plot(self, data, name=""):
        x = dates.date2num(data[0])
        dnp.plot.addline(_configure_x(x, "Date"), _configure_y(data[1], "y", name), self.title)
        # TODO: Set line names


class SpectraPlot(object):
    def __init__(self, api, spectrum, period, dist):
        self.api = api
        self.spectra = []
        self.x_label = "Time"
        self.y_label = "Counts"
        self.title = "Spectrum %s" % spectrum

        self.add_spectrum(spectrum, period, dist)

    def add_spectrum(self, spectrum, period, dist):
        plot = dnp.plot.plot if not self.spectra else dnp.plot.addline
        self.spectra.append((spectrum, period, dist))
        data = self.api.dae.get_spectrum(spectrum, period, dist)
        name = "Spect %s " % spectrum

        plot(
            _configure_x(data["time"], self.x_label),
            _configure_y(data["signal"], self.y_label, name),
            self.title,
        )

    def refresh(self):
        # TODO
        pass

    def delete_plot(self, plotNum):
        # TODO
        pass


class GeniePlot(object):
    def __init__(self, x_label="X", y_label="Y", title=None):
        self.x_label = x_label
        self.y_label = y_label
        self.title = title
        self.plot_count = 0

    def add_plot(self, x_data, y_data, name=""):
        plot = dnp.plot.plot if not self.plot_count else dnp.plot.addline
        self.plot_count += 1
        plot(
            _configure_x(x_data, self.x_label), _configure_y(y_data, self.y_label, name), self.title
        )

    def update_data(self, x_data, y_data, plotnum=0):
        # TODO
        pass

    def delete_plot(self, plotnum):
        # TODO
        # self.plot_count -= 1
        pass


def _configure_x(x, axis_label="x"):
    # format for plotting on the x-axis
    return {axis_label: dnp.array(x)}


def _configure_y(y, axis_label="y", line_label=""):
    # format for plotting on the y-axis
    return [{axis_label: (dnp.array(y), line_label)}]
