import matplotlib.pyplot as pyplt
import matplotlib.dates as dates


class PlotController(object):
    def __init__(self):
        self.plot_by_index = dict()
        self.last_plots = list()
        self.max_index = 1

    def set_last_plot(self, last_plot):
        if last_plot in self.last_plots:
            self.last_plots.append(self.last_plots.pop(self.last_plots.index(last_plot)))
        else:
            self.last_plots.append(last_plot)
        print "Figure " + repr(self.get_plot_index(last_plot)) + ": new default plot window"

    def get_last_plot(self):
        pos_last = len(self.last_plots)-1
        return self.last_plots[pos_last]

    def add_plot(self, plot):
        self.max_index = self.find_max_index()
        self.plot_by_index[self.max_index] = plot
        self.set_last_plot(plot)

    def delete_plot(self, plot):
        index = self.get_plot_index(plot)
        if index in self.plot_by_index:
            del self.plot_by_index[index]
        if plot in self.last_plots:
            self.last_plots.remove(plot)

    def get_plot(self, index):
        return self.plot_by_index[index]

    def get_plot_index(self, plot):
        inv_plots = {v: k for k, v in self.plot_by_index.iteritems()}
        index = inv_plots.get(plot)
        return index

    def find_max_index(self):
        if len(self.plot_by_index) != 0:
            maxind = max(self.plot_by_index.keys()) + 1
        else:
            maxind = 1
        return maxind

    def remove_closed(self):
        inv_plots = {v: k for k, v in self.plot_by_index.iteritems()}
        for plot in inv_plots:
            fignum = plot.fig.number
            if not pyplt.fignum_exists(fignum):
                self.delete_plot(plot)


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
        self.ax.set_title("Spectrum %s" % spectrum)
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


