import matplotlib.pyplot as pyplt
import matplotlib.dates as dates


class PlotController(object):
    def __init__(self):
        self.plots = dict()
        self.last_plot = None
        self.count = 1

    def set_last_plot(self, last_plot):
        self.last_plot = last_plot

    def get_last_plot(self):
        return self.last_plot

    def add_plot(self, plot):
        self.plots[self.count] = plot
        self.set_last_plot(plot)
        self.count += 1

    def get_plot(self, plot_id):
        return self.plots[plot_id]

    def get_count(self):
        return self.count


class SePlot(object):
    def __init__(self):
        pyplt.ion()
        self.fig = pyplt.figure()
        self.ax = pyplt.subplot(111)
        self.ax.xaxis_date()
        self.ax.xaxis.set_major_formatter(dates.DateFormatter('%H:%M:%S'))
        self.fig.autofmt_xdate()
        pyplt.draw()
        
    def add_plot(self, data, name=""):
        if name == "":
            name = "plot " + str(len(self.ax.lines) + 1)
        self.ax.plot(dates.date2num(data[0]), data[1], '.', label=name)
        self.fig.autofmt_xdate()
        self.__update_legend()
        self.fig.canvas.draw()
        
    def __update_legend(self):
        handles, labels = self.ax.get_legend_handles_labels()
        self.ax.legend(handles, labels)


class SpectraPlot(object):
    def __init__(self, api, spectrum, period, dist):
        self.api = api
        self.spectra = []
        pyplt.ion()
        self.fig = pyplt.figure()
        self.ax = pyplt.subplot(111)
        self.ax.autoscale_view(True, True, True)
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Counts")
        # self.ax.set_title("Spectrum %s" % spectrum)
        pyplt.draw()
        self.add_spectrum(spectrum, period, dist)
        
    def add_spectrum(self, spectrum, period=1, dist=False):
        self.spectra.append((spectrum, period, dist))
        data = self.api.dae.get_spectrum(spectrum, period, dist)
        name = "Spect %s " % spectrum
        self.ax.plot(data['time'], data['signal'], label=name)
        self.__update_legend()
        self.fig.canvas.draw()
    
    def refresh(self):
        for i in range(len(self.ax.lines)):
            data = self.api.dae.get_spectrum(self.spectra[0][0], self.spectra[0][1], self.spectra[0][2])
            line = self.ax.lines[i]
            line.set_data(data['time'], data['signal'])
        self.ax.autoscale_view(True, True, True)
        self.fig.canvas.draw()
        
    def delete_plot(self, plotnum):
        del self.ax.lines[plotnum]
        del self.spectra[plotnum]
        self.__update_legend()
        self.fig.canvas.draw()
        
    def __update_legend(self):
        handles, labels = self.ax.get_legend_handles_labels()
        self.ax.legend(handles, labels)


class GeniePlot(object):
    def __init__(self, x_label="X", y_label="Y", title=None):
        pyplt.ion()
        self.fig = pyplt.figure()
        self.ax = pyplt.subplot(111)
        self.ax.autoscale_view(True, True, True)
        self.ax.set_xlabel(x_label)
        self.ax.set_ylabel(y_label)
        if title != None:
            self.ax.set_title(str(title))
        pyplt.draw()
        
    def add_plot(self, x_data, y_data, name=""):
        if name == "":
            name = "plot " + str(len(self.ax.lines) + 1)
        self.ax.plot(x_data, y_data, label=name)
        self.__update_legend()
        self.fig.canvas.draw()
    
    def update_data(self, x_data, y_data, plotnum=0):
        line = self.ax.lines[plotnum]
        line.set_data(x_data, y_data)
        self.ax.autoscale_view(True, True, True)
        self.fig.canvas.draw()
        
    def delete_plot(self, plotnum):
        del self.ax.lines[plotnum]
        self.__update_legend()
        self.fig.canvas.draw()
        
    def __update_legend(self):
        handles, labels = self.ax.get_legend_handles_labels()
        self.ax.legend(handles, labels)


