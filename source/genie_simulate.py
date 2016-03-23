import os
import re
from genie_script_checker import ScriptChecker
import imp
import types
from utilities import waveform_to_string

if 'SCISOFT_RPC_PORT' in os.environ:
    from genie_scisoft_plot import GeniePlot, SpectraPlot
else:
    from genie_plot import GeniePlot, SpectraPlot


if os.name == 'nt':
    # Needed for correcting file paths
    import win32api


class Waitfor(object):
    def __init__(self):
        pass

    def start_waiting(self, block=None, value=None, lowlimit=None, highlimit=None, maxwait=None, wait_all=False,
                      seconds=None, minutes=None, hours=None, time=None, frames=None, uamps=None):
        pass

    def wait_for_runstate(self, state, maxwaitsecs=3600, onexit=False):
        pass


class Dae(object):
    def __init__(self):
        self.run_state = "SETUP"
        self.run_number = 123456
        self.period_current = 1
        self.num_periods = 1
        self.uamps_current = 0
        self.total_counts = 0
        self.title_current = "Simulation"
        self.rb_number = 1
        self.mevents = 1.0
        self.good_frames = 1
        self.users = ""
        self.run_duration = 1
        self.raw_frames = 1
        self.beam_current = 1
        self.total_uamps = 1
        self.num_spectra = 1
        self.num_timechannels = 1
        self.monitor_spectrum = ""
        self.monitor_counts = 1
        self.in_change = False
        self.wiring_tables = [""]
        self.spectra_tables = [""]
        self.detector_tables = [""]
        self.tcb_tables = []
        self.period_files = []
        self.spectrum = {'time':1, 'signal':1, 'sum':None, 'mode': 'distribution'}
        self.change_cache = ChangeCache()

    def begin_run(self, period=None, meas_id=None, meas_type=None, meas_subid=None,
                  sample_id=None, delayed=False, quiet=False, paused=False):
        """Starts a data collection run.

        Parameters:
            period - the period to begin data collection in [optional]
            meas_id - the measurement id [optional]
            meas_type - the type of measurement [optional]
            meas_subid - the measurement sub-id[optional]
            sample_id - the sample id [optional]
            delayed - puts the period card to into delayed start mode [optional]
            quiet - suppress the output to the screen [optional]
            paused - begin in the paused state [optional]
        """
        if self.run_state == "SETUP":
            self.run_state = "RUNNING"
        else:
            raise Exception("Can only begin run from SETUP")

    def post_begin_check(self, verbose=False):
        pass

    def post_end_check(self, verbose=False):
        pass

    def post_abort_check(self, verbose=False):
        pass

    def post_pause_check(self, verbose=False):
        pass

    def post_resume_check(self, verbose=False):
        pass

    def post_update_store_check(self, verbose=False):
        pass

    def post_update_check(self, verbose=False):
        pass

    def post_store_check(self, verbose=False):
        pass

    def abort_run(self):
        """
        Aborts the run and sets run_state to "SETUP"
        """
        if self.run_state == "RUNNING" or self.run_state == "PAUSED":
            self.run_state = "SETUP"
        else:
            raise Exception("Can only abort when RUNNING or PAUSED")

    def get_run_state(self):
        """
        Returns the current run state
        Returns: String
        """
        return self.run_state

    def get_run_number(self):
        """
        Returns the run number
        Returns: Int
        """
        return self.run_number

    def end_run(self):
        """
        ends the run and sets run_state to "SETUP"
        """
        if self.run_state == "RUNNING" or self.run_state == "PAUSED":
            self.run_state = "SETUP"
        else:
            raise Exception("Can only end when RUNNING or PAUSED")

    def pause_run(self):
        """
        pauses run and sets run_state to "PAUSED"
        """
        if self.run_state == "RUNNING":
            self.run_state = "PAUSED"
        else:
            raise Exception("Can only pause when RUNNING")

    def resume_run(self):
        """
        resumes the run and sets run_state to "RUNNING"
        """
        if self.run_state == "PAUSED":
            self.run_state = "RUNNING"
        else:
            raise Exception("Can only resume when PAUSED")

    def update_store_run(self):
        """
        Does nothing but throw error if run_state is not "RUNNING" or "PAUSED"
        """
        if self.run_state == "RUNNING" or self.run_state == "PAUSED":
            pass
        else:
            raise Exception("Can only be run when RUNNING or PAUSED")

    def update_run(self):
        """
        Does nothing but throw error if run_state is not "RUNNING" or "PAUSED"
        """
        if self.run_state == "RUNNING" or self.run_state == "PAUSED":
            pass
        else:
            raise Exception("Can only be run when RUNNING or PAUSED")

    def store_run(self):
        """
        Does nothing but throw error if run_state is not "RUNNING" or "PAUSED"
        """
        if self.run_state == "RUNNING" or self.run_state == "PAUSED":
            pass
        else:
            raise Exception("Can only be run when RUNNING or PAUSED")

    def get_period(self):
        """
        returns the current period number
        Returns: Int

        """
        return self.period_current

    def get_num_periods(self):
        """
        returns the current number of periods
        Returns: Int
        """
        return self.num_periods

    def set_period(self, period):
        """
        sets the current period to the period parameter if it is equal to or less than the number of periods
        Args:
            period: Int
        """
        if period <= self.num_periods:
            self.period_current = period
        else:
            raise Exception("Cannot set period as it is higher than the number of periods")

    def get_uamps(self, period=False):
        """Returns the current number of micro-amp hours.

        Parameters:
            period - whether to return the micro-amp hours for the current period [optional]
        """
        if period:
            return self.uamps_current
        else:
            return self.uamps_current

    def get_total_counts(self):
        """Get the total counts for the current run."""
        return self.total_counts

    def get_title(self):
        """Returns the current title

        Returns: String : the current title

        """
        return self.title_current

    def set_title(self, title):
        """Sets the current title

        Args:
            title: String: the new title

        Returns:

        """
        self.title_current = title

    def get_rb_number(self):
        """Returns the current RB number

        Returns: String : the RB number

        """
        return self.rb_number

    def get_mevents(self):
        return self.mevents

    def get_good_frames(self, period=False):
        if period:
            return self.good_frames
        else:
            return self.good_frames

    def get_users(self):
        return self.users

    def get_run_duration(self):
        return self.run_duration

    def get_raw_frames(self):
        return self.raw_frames

    def get_beam_current(self):
        return self.beam_current

    def get_total_uamps(self):
        return self.total_uamps

    def get_num_spectra(self):
        return self.num_spectra

    def get_num_timechannels(self):
        return self.num_timechannels

    def get_monitor_spectrum(self):
        return self.monitor_spectrum

    def get_monitor_from(self):
        return ""

    def get_monitor_to(self):
        return ""

    def get_monitor_counts(self):
        return 1

    def set_users(self, users):
        self.users = users

    def change_start(self):
        """Start a change operation.
        The operaton is finished when change_finish is called.
        Between these two calls a sequence of other change commands can be called.
        For example: change_tables, change_tcb etc.
        """
        # Check in setup
        if self.get_run_state() != "SETUP":
            raise Exception('Must be in SETUP before starting change!')
        if self.in_change:
            raise Exception("Already in change - previous cached values will be used")
        else:
            self.in_change = True
            self.change_cache = ChangeCache()

    def change_finish(self):
        if self.in_change:
            self.in_change = False
            self.change_cache = ChangeCache()

    def get_spectrum(self, spectrum=None, period=None, dist=None):
        return self.spectrum

    def change_monitor(self, spec, low, high):
        """Change the monitor to a specified spectrum and range.

        Parameters:
            spectrum - the spectrum number (integer)
            low - the low end of the integral (float)
            high - the high end of the integral (float)
        """
        try:
            spec = int(spec)
        except ValueError:
            raise TypeError("Spectrum number must be an integer")
        try:
            low = float(low)
        except ValueError:
            raise TypeError("Low must be a float")
        try:
            high = float(high)
        except ValueError:
            raise TypeError("High must be a float")
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        pass
        if did_change:
            self.change_finish()

    def get_wiring_tables(self):
        return self.wiring_tables

    def get_spectra_tables(self):
        return self.spectra_tables

    def get_detector_tables(self):
        return self.detector_tables

    def get_period_files(self):
        return self.period_files

    def change_cache(self):
        pass

    def configure_hard_periods(self, mode, period_file=None, sequences=None, output_delay=None, period=None, daq=False,
                               dwell=False, unused=False, frames=None, output=None, label=None):
        """Configures the DAE's hardware periods.

        Parameters:
            mode - set the mode to internal ('int') or external ('ext')

            Internal periods parameters [optional]:
                period_file - the file containing the internal period settings (ignores any other settings)
                sequences - the number of period sequences
                output_delay - the output delay in microseconds
                period - the number of the period to set the following for:
                    daq - it is a aquisition period
                    dwell - it is a dwell period
                    unused - it is a unused period
                    frames - the number of frames to count for
                    output - the binary output
                    label - the label for the period

                Note: if the period number is unspecified then the settings will be applied to all periods.

        EXAMPLE: setting external periods
        enable_hardware_periods('ext')

        EXAMPLE: setting internal periods from a file
        enable_hardware_periods('int', 'myperiods.txt')
        """
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        # Set the source to 'Use Parameters Below' by default
        self.change_cache.periods_src = 0
        if mode.strip().lower() == 'int':
            self.change_cache.periods_type = 1
            if period_file is not None:
                if not os.path.exists(period_file):
                    raise Exception('Period file could not be found')
                self.change_cache.periods_src = 1
                self.change_cache.periods_file = period_file
            else:
                self.configure_internal_periods(sequences, output_delay, period, daq, dwell, unused, frames,
                                                output, label)
        elif mode.strip().lower() == 'ext':
            self.change_cache.periods_type = 2
        else:
            raise Exception('Period mode invalid, it should be "int" or "ext"')
        if did_change:
            self.change_finish()

    def configure_internal_periods(self, sequences=None, output_delay=None, period=None, daq=False, dwell=False,
                                   unused=False, frames=None, output=None, label=None):
        """Configure the internal periods without switching to internal period mode.

        Parameters:
            file - the file containing the internal period settings (ignores any other settings) [optional]
            sequences - the number of period sequences [optional]
            output_delay - the output delay in microseconds [optional]
            period - the number of the period to set values for [optional]
            daq -  the specified period is a aquisition period [optional]
            dwell - the specified period is a dwell period [optional]
            unused - the specified period is a unused period [optional]
            frames - the number of frames to count for the specified period [optional]
            output - the binary output the specified period [optional]
            label - the label for the period the specified period [optional]

            Note: if the period number is unspecified then the settings will be applied to all periods.
        """
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        if sequences is not None:
            if isinstance(sequences, int):
                self.change_cache.periods_seq = sequences
            else:
                raise Exception("Number of period sequences must be an integer")
        if output_delay is not None:
            if isinstance(output_delay, int):
                self.change_cache.periods_delay = output_delay
            else:
                raise Exception("Output delay of periods must be an integer (microseconds)")
        self.define_hard_period(period, daq, dwell, unused, frames, output, label)
        if did_change:
            self.change_finish()

    def define_hard_period(self, period=None, daq=False, dwell=False, unused=False, frames=None,
                           output=None, label=None):
        """Define the hardware periods.

        Parameters:
            period - the number of the period to set values for [optional]
            daq -  the specified period is a aquisition period [optional]
            dwell - the specified period is a dwell period [optional]
            unused - the specified period is a unused period [optional]
            frames - the number of frames to count for the specified period [optional]
            output - the binary output the specified period [optional]
            label - the label for the period the specified period [optional]

            Note: if the period number is unspecified then the settings will be applied to all periods.
        """
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        if period is None:
            # Do for all periods (1 to 8)
            for i in range(1, 9):
                self.define_hard_period(i, daq, dwell, unused, frames, output, label)
        else:
            if isinstance(period, int) and period > 0 and period < 9:
                p_type = None  # unchanged
                if unused:
                    p_type = 0
                elif daq:
                    p_type = 1
                elif dwell:
                    p_type = 2
                p_frames = None  # unchanged
                if frames is not None and isinstance(frames, int):
                    p_frames = frames
                p_output = None  # unchanged
                if output is not None and isinstance(output, int):
                    p_output = output
                p_label = None  # unchanged
                if label is not None:
                    p_label = label
                self.change_cache.periods_settings.append((period, p_type, p_frames, p_output, p_label))
            else:
                raise Exception("Period number must be an integer from 1 to 8")
        if did_change:
            self.change_finish()

    def change_tables(self, wiring=None, detector=None, spectra=None):
        """Load the wiring, detector and/or spectra tables.

        Parameters:
            wiring - the filename of the wiring table file [optional]
            detector - the filename of the detector table file [optional]
            spectra - the filename of the spectra table file [optional]
        """
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        if wiring is not None:
            self.change_cache.wiring = wiring
        if detector is not None:
            self.change_cache.detector = detector
        if spectra is not None:
            self.change_cache.spectra = spectra
        if did_change:
            self.change_finish()

    def change_sync(self, source):
        """Change the source the DAE using for synchronisation.

        Parameters:
            source - the source to use ('isis', 'internal', 'smp', 'muon cerenkov', 'muon ms', 'isis (first ts1)')
        """
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        source = source.strip().lower()
        if source == 'isis':
            value = 0
        elif source == 'internal':
            value = 1
        elif source == 'smp':
            value = 2
        elif source == 'muon cerenkov':
            value = 3
        elif source == 'muon ms':
            value = 4
        elif source == 'isis (first ts1)':
            value = 5
        else:
            raise Exception('Invalid timing source entered, try help(change_sync)!')
        self.change_cache.dae_sync = value
        if did_change:
            self.change_finish()

    def change_tcb_file(self, tcb_file=None, default=False):
        """Change the time channel boundaries.

        Parameters:
            tcb_file - the file to load [optional]
            default - load the default file "c:\\labview modules\\dae\\tcb.dat" [optional]
        """
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        if tcb_file is not None:
            print "Reading TCB boundaries from", tcb_file
        elif default:
            tcb_file = "c:\\labview modules\\dae\\tcb.dat"
        else:
            raise Exception('No tcb file specified')
        if not os.path.exists(tcb_file):
            raise Exception('Tcb file could not be found')
        self.change_cache.tcb_file = tcb_file
        if did_change:
            self.change_finish()

    def change_tcb(self, low, high, step, trange, log=False, regime=1):
        """Change the time channel boundaries.

        Parameters:
            low - the lower limit
            high - the upper limit
            step - the step size
            trange - the time range (1 to 5)
            log - whether to use LOG binning [optional]
            regime - the time regime to set (1 to 6)[optional]
        """
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        if log:
            print "Setting TCB range", low, "to", high, "step", step, "(LOG binning)"
            self.change_cache.tcb_tables.append((regime, trange, low, high, step, 2))
        else:
            print "Setting TCB range", low, "to", high, "step", step, "(LINEAR binning)"
            self.change_cache.tcb_tables.append((regime, trange, low, high, step, 1))
        if did_change:
            self.change_finish()

    def change_vetos(self, **params):
        """Change the DAE veto settings.

        Parameters:
            clearall - remove all vetos [optional]
            smp - set SMP veto [optional]
            ts2 - set TS2 veto [optional]
            hz50 - set 50 hz veto [optional]
            ext0 - set external veto 0 [optional]
            ext1 - set external veto 1 [optional]
            ext2 - set external veto 2 [optional]
            ext3 - set external veto 3 [optional]

        If clearall is specified then all vetos are turned off, but it is possible to turn other vetoes
        back on at the same time, for example:

            change_vetos(clearall=True, smp=True)    #Turns all vetoes off then turns the SMP veto back on
        """
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        if 'clearall' in params:
            if isinstance(params['clearall'], bool):
                self.change_cache.clear_vetos()
        if 'smp' in params:
            if isinstance(params['smp'], bool):
                self.change_cache.smp_veto = int(params['smp'])
        if 'ts2' in params:
            if isinstance(params['ts2'], bool):
                self.change_cache.ts2_veto = int(params['ts2'])
        if 'hz50' in params:
            if isinstance(params['hz50'], bool):
                self.change_cache.hz50_veto = int(params['hz50'])
        if 'ext0' in params:
            if isinstance(params['ext0'], bool):
                self.change_cache.ext0_veto = int(params['ext0'])
        if 'ext1' in params:
            if isinstance(params['ext1'], bool):
                self.change_cache.ext1_veto = int(params['ext1'])
        if 'ext2' in params:
            if isinstance(params['ext2'], bool):
                self.change_cache.ext2_veto = int(params['ext2'])
        if 'ext3' in params:
            if isinstance(params['ext3'], bool):
                self.change_cache.ext3_veto = int(params['ext3'])
        if did_change:
            self.change_finish()

    def set_fermi_veto(self, enable=None, delay=1.0, width=1.0):
        """Configure the fermi chopper veto.

        Parameters:
            enable - enable the fermi veto
            delay - the veto delay
            width - the veto width
        """
        if not isinstance(enable, bool):
            raise Exception("Fermi veto: enable must be a boolean value")
        if not isinstance(delay, float) and not isinstance(delay, int):
            raise Exception("Fermi veto: delay must be a numeric value")
        if not isinstance(width, float) and not isinstance(width, int):
            raise Exception("Fermi veto: width must be a numeric value")
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        if enable:
            self.change_cache.set_fermi(1, delay, width)
            print "SET_FERMI_VETO: requested status is ON, delay:", delay, "width:", width
        else:
            self.change_cache.set_fermi(0)
            print "SET_FERMI_VETO: requested status is OFF"
        if did_change:
            self.change_finish()

    def set_num_soft_periods(self, number):
        """Sets the number of software periods for the DAE.

        Parameters:
            number - the number of periods to create
        """
        if not isinstance(number, float) and not isinstance(number, int):
            raise Exception("Number of soft periods must be a numeric value")
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        if number >= 0:
            self.change_cache.periods_soft_num = number
        if did_change:
            self.change_finish()

    def set_period_mode(self, mode):
        """Sets the period mode for the DAE

        Parameters:
            mode - the mode to switch to ('soft', 'int', 'ext')
        """
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        if mode.strip().lower() == 'soft':
            self.change_cache.periods_type = 0
        else:
            self.configure_hard_periods(mode)
        if did_change:
            self.change_finish()

    def snapshot_crpt(self, name):
        pass

    def post_snapshot_check(self, verbose=False):
        pass


class SimulationAPI(object):

    def __init__(self):
        self.block_dict = dict()
        self.num_periods = 1
        self.run_number = 123456
        self.waitfor = Waitfor()
        self.dae = Dae()
        self.beamline_pars = {}
        self.sample_pars = {}

    def log_info_msg(self, *args, **kwargs):
        pass

    def block_exists(self, name):
        # Create an entry for it and return True
        if name not in self.block_dict:
            self.set_block_value(name)
        return True

    def get_blocks(self):
        """
        returns a list of the block names
        Returns: List

        """
        return self.block_dict.keys()

    def get_block_value(self, name, to_string=False, attempts=3):
        if to_string:
            return str(self.block_dict[name][0])
        return self.block_dict[name][0]

    def get_run_control_settings(self, name):
        """

        Args:
            name: String - block name

        Returns: Dict - a dictionary of all the runcontrol settings

        """
        rc = dict()
        rc["ENABLE"] = self.block_dict[name][1]
        rc["LOW"] = self.block_dict[name][2]
        rc["HIGH"] = self.block_dict[name][3]
        return rc

    def get_current_block_values(self):
        return self.block_dict

    def set_block_value(self, name, value=None, runcontrol=None, lowlimit=None, highlimit=None, wait=False):
        try:
            # Final value in list is the EPICS record type
            self.block_dict[name] = [value, runcontrol, lowlimit, highlimit, ""]
        except Exception as e:
            _handle_exception(e)

    def set_multiple_blocks(self, names, values):
        """

        Args:
            names: list of block names
            values: list of block values (nested if multiple)

        Examples:
            Setting multiple blocks
            >>>set_multiple_blocks(["x","y"], [ [1, 2, 3, True], [1, 2, 3, False] ])

        """
        try:
            temp = zip(names, values)
            for name, value in temp:
                if name in self.block_dict:
                    self.block_dict[name][0] = value
                else:
                    self.block_dict[name] = [value, False, None, None, None]
        except Exception as e:
            _handle_exception(e)

    def run_pre_post_cmd(self, command, **pars):
        pass

    def get_blocks(self):
        return self.block_dict.keys()

    def get_beamline_pars(self):
        return self.beamline_pars

    def set_beamline_par(self, name, value):
        try:
            self.beamline_pars[name] = value
        except Exception as e:
            _handle_exception(e)

    def get_sample_pars(self):
        return self.sample_pars

    def set_sample_par(self, name, value):
        try:
            self.sample_pars[name] = value
        except Exception as e:
            _handle_exception(e)

    def check_alarms(self, blocks):
        try:
            return None
        except Exception as e:
            _handle_exception(e)


class ChangeCache(object):
    def __init__(self):
        self.wiring = None
        self.detector = None
        self.spectra = None
        self.mon_spect = None
        self.mon_from = None
        self.mon_to = None
        self.dae_sync = None
        self.tcb_file = None
        self.tcb_tables = []
        self.smp_veto = None
        self.ts2_veto = None
        self.hz50_veto = None
        self.ext0_veto = None
        self.ext1_veto = None
        self.ext2_veto = None
        self.ext3_veto = None
        self.fermi_veto = None
        self.fermi_delay = None
        self.fermi_width = None
        self.periods_soft_num = None
        self.periods_type = None
        self.periods_src = None
        self.periods_file = None
        self.periods_seq = None
        self.periods_delay = None
        self.periods_settings = []

    def set_monitor(self, spec, low, high):
        self.mon_spect = spec
        self.mon_from = low
        self.mon_to = high

    def clear_vetos(self):
        self.smp_veto = 0
        self.ts2_veto = 0
        self.hz50_veto = 0
        self.ext0_veto = 0
        self.ext1_veto = 0
        self.ext2_veto = 0
        self.ext3_veto = 0

    def set_fermi(self, enable, delay=1.0, width=1.0):
        self.fermi_veto = 1
        self.fermi_delay = delay
        self.fermi_width = width

    def change_dae_settings(self, root):
        changed = False
        if self.wiring is not None:
            self._change_xml(root, 'String', 'Wiring Table', self.wiring)
            changed = True
        if self.detector is not None:
            self._change_xml(root, 'String', 'Detector Table', self.detector)
            changed = True
        if self.spectra is not None:
            self._change_xml(root, 'String', 'Spectra Table', self.spectra)
            changed = True
        if self.mon_spect is not None:
            self._change_xml(root, 'I32', 'Monitor Spectrum', self.mon_spect)
            changed = True
        if self.mon_from is not None:
            self._change_xml(root, 'DBL', 'from', self.mon_from)
            changed = True
        if self.mon_to is not None:
            self._change_xml(root, 'DBL', 'to', self.mon_to)
            changed = True
        if self.dae_sync is not None:
            self._change_xml(root, 'EW', 'DAETimingSource', self.dae_sync)
            changed = True
        if self.fermi_veto is not None:
            self._change_xml(root, 'EW', ' Fermi Chopper Veto', self.fermi_veto)
            self._change_xml(root, 'DBL', 'FC Delay', self.fermi_delay)
            self._change_xml(root, 'DBL', 'FC Width', self.fermi_width)
            changed = True

        changed = self._change_vetos(root, changed)
        return changed

    def _change_vetos(self, root, changed):
        if self.smp_veto is not None:
            self._change_xml(root, 'EW', 'SMP (Chopper) Veto', self.smp_veto)
            changed = True
        if self.ts2_veto is not None:
            self._change_xml(root, 'EW', ' TS2 Pulse Veto', self.ts2_veto)
            changed = True
        if self.hz50_veto is not None:
            self._change_xml(root, 'EW', ' ISIS 50Hz Veto', self.hz50_veto)
            changed = True
        if self.ext0_veto is not None:
            self._change_xml(root, 'EW', 'Veto 0', self.ext0_veto)
            changed = True
        if self.ext1_veto is not None:
            self._change_xml(root, 'EW', 'Veto 1', self.ext1_veto)
            changed = True
        if self.ext2_veto is not None:
            self._change_xml(root, 'EW', 'Veto 2', self.ext2_veto)
            changed = True
        if self.ext3_veto is not None:
            self._change_xml(root, 'EW', 'Veto 3', self.ext3_veto)
            changed = True
        return changed

    def change_tcb_settings(self, root):
        changed = False
        if self.tcb_file is not None:
            self._change_xml(root, 'String', 'Time Channel File', self.tcb_file)
            changed = True
        changed = self._change_tcb_table(root, changed)
        return changed

    def _change_tcb_table(self, root, changed):
        for row in self.tcb_tables:
            regime = str(row[0])
            trange = str(row[1])
            self._change_xml(root, 'DBL', 'TR%s From %s' % (regime, trange), row[2])
            self._change_xml(root, 'DBL', 'TR%s To %s' % (regime, trange), row[3])
            self._change_xml(root, 'DBL', 'TR%s Steps %s' % (regime, trange), row[4])
            self._change_xml(root, 'U16', 'TR%s In Mode %s' % (regime, trange), row[5])
            changed = True
        return changed

    def change_period_settings(self, root):
        changed = False
        if self.periods_type is not None:
            self._change_xml(root, 'EW', 'Period Type', self.periods_type)
            changed = True
        if self.periods_soft_num is not None:
            self._change_xml(root, 'I32', 'Number Of Software Periods', self.periods_soft_num)
            changed = True
        if self.periods_src is not None:
            self._change_xml(root, 'EW', 'Period Setup Source', self.periods_src)
            changed = True
        if self.periods_seq is not None:
            self._change_xml(root, 'DBL', 'Hardware Period Sequences', self.periods_seq)
            changed = True
        if self.periods_delay is not None:
            self._change_xml(root, 'DBL', 'Output Delay (us)', self.periods_delay)
            changed = True
        if self.periods_file is not None:
            self._change_xml(root, 'String', 'Period File', self.periods_file)
            changed = True
        if self.periods_settings is not None:
            self._change_period_table(root, self.periods_settings)
            changed = True
        return changed

    def _change_period_table(self, root, changed):
        for row in self.periods_settings:
            period = row[0]
            ptype = row[1]
            frames = row[2]
            output = row[3]
            label = row[4]
            if ptype is not None:
                self._change_xml(root, 'EW', 'Type %s' % period, ptype)
                changed = True
            if frames is not None:
                self._change_xml(root, 'I32', 'Frames %s' % period, frames)
                changed = True
            if output is not None:
                self._change_xml(root, 'U16', 'Output %s' % period, output)
                changed = True
            if label is not None:
                self._change_xml(root, 'String', 'Label %s' % period, label)
                changed = True
        return changed

    def _change_xml(self, xml, node, name, value):
        for top in xml.iter(node):
            n = top.find('Name')
            if n.text == name:
                v = top.find('Val')
                v.text = str(value)
                break

__api = SimulationAPI()


def _handle_exception(e):
    print e


def _cshow_all():
    """
    Shows all blocks and their values and runcontrol settings
    """
    blks = __api.get_current_block_values()
    for bn, bv in blks.iteritems():
        if bv[0] == "*** disconnected" or bv[0] is None:
            _print_cshow(bn, connected=False)
        elif isinstance(bv[0], list) and bv[4] == "CHAR":
            # If it is a char waveform it needs to be converted
            val = waveform_to_string(bv[0])
            _print_cshow(bn, val, bv[1], bv[2], bv[3])
            output += ' (runcontrol = %s, lowlimit = %s, highlimit = %s)' % (bv[1], bv[2], bv[3])
        else:
            output = "%s = %s" % (bn, bv[0])
            output += ' (runcontrol = %s, lowlimit = %s, highlimit = %s)' % (bv[1], bv[2], bv[3])
        print output


def _print_cshow(name, value=None, rc_enabled=None, rc_low=None, rc_high=None, connected=True):
    if connected:
        print '%s = %s (runcontrol = %s, lowlimit = %s, highlimit = %s)' % (name, value, rc_enabled, rc_low, rc_high)
    else:
        print "%s = *** disconnected ***" % name


def cshow(block=None):
    """Show the current settings for one block or for all blocks.

    Args:
        block (string, optional) : the name of the block

    Examples:
        Showing all block values:
        >>> cshow()

        Showing values for one block only (name must be quoted):
        >>> cshow("block1")
    """
    try:
        if block:
            # Show only one block
            if __api.block_exists(block):
                output = block + ' = ' + str(__api.get_block_value(block, attempts=1))
                rc = __api.get_run_control_settings(block)
                if rc:
                    output += ' (runcontrol = %s, lowlimit = %s, highlimit = %s)' % (rc["ENABLE"], rc["LOW"],
                                                                                     rc["HIGH"])
                print output
            else:
                raise Exception('No block with the name "%s" exists' % block)
        else:
            # Show all blocks
            _cshow_all()
    except Exception as e:
        _handle_exception(e)


def cset(*args, **kwargs):
    """Sets the setpoint and runcontrol settings for blocks.

    Args:
        runcontrol (bool, optional) : whether to set runcontrol for this block
        wait (string, optional) : pause execution until setpoint isreached (one block only)
        lowlimit (float, optional) : the lower limit for runcontrol or waiting
        highlimit (float, optional): the upper limit for runcontrol or waiting

    Note: cannot use wait and runcontrol in the same command

    Examples:
        Setting a value for a block:

        >>> cset(block1=100)

        Or:

        >>> cset("block1", 100)

        Setting values for more than one block:

        >>> cset(block1=100, block2=200, block3=300)

        NOTE: the order in which the values are set is random,
        e.g. block1 may or may not be set before block2 and block3

        Setting runcontrol values for a block:

        >>> cset(block1=100, runcontrol=True, lowlimit=99, highlimit=101)

        Changing runcontrol settings for a block without changing the setpoint:

        >>> cset("block1", runcontrol=False)
        >>> cset(block1=None, runcontrol=False)

        Wait for setpoint to be reached (one block only):

        >>> cset(block1=100, wait=True)

        Wait for limits to be reached - this does NOT change the runcontrol limits:

        >>> cset(block1=100, wait=True, lowlimit=99, highlimit=101)
    """
    __api.log_info_msg("CSET %s" % (locals(),))
    # cset only works for blocks (currently)
    # Block names contain alpha-numeric and underscores only
    # Run-control not implemented yet!
    try:
        block = None
        blocks = []
        value = None
        values = []
        runcontrol = None
        lowlimit = None
        highlimit = None
        wait = None

        # See if single block name was entered, i.e. cset("block1", runcontrol=True)
        if len(args) > 0:
            if len(args) > 2:
                raise Exception('Too many arguments, please type: help(cset) for more information on the syntax')
            if not __api.block_exists(args[0]):
                raise Exception('No block with the name "%s" exists' % args[0])
            else:
                block = args[0]
            if len(args) == 2:
                value = args[1]

        for k in kwargs:
            if k.lower() == 'runcontrol':
                runcontrol = kwargs['runcontrol']
            elif k.lower() == 'lowlimit':
                lowlimit = kwargs['lowlimit']
            elif k.lower() == 'highlimit':
                highlimit = kwargs['highlimit']
            elif k.lower() == 'wait':
                wait = kwargs['wait']
            else:
                # Perhaps it is a block?
                if __api.block_exists(k):
                    blocks.append(k)
                    values.append(kwargs[k])
                else:
                    raise Exception('No block with the name "%s" exists' % k)

        if block is not None and len(blocks) > 0:
            raise Exception('Incorrect syntax, please type: help(cset) for more information on the syntax')

        if block is not None:
            # Something like cset("block1", runcontrol=True) or cset("block1", 10)
            if wait:
                raise Exception('Cannot wait as no setpoint specified. Please type: help(cset) for help')
            __api.set_block_value(block, value, runcontrol, lowlimit, highlimit, wait=False)
        elif len(blocks) == 1:
            # Something like cset(block1=123, runcontrol=True)
            if wait and runcontrol is not None:
                raise Exception("Cannot enable or disable runcontrol at the same time as setting a wait")
            else:
                __api.set_block_value(blocks[0], values[0], runcontrol, lowlimit, highlimit, wait)
        else:
            # Setting multiple blocks, so runcontrol and waiting are not allowed
            if runcontrol is not None or lowlimit is not None or highlimit is not None:
                raise Exception('Runcontrol settings can only be changed for one block at a time')
            if wait is not None:
                raise Exception('Cannot wait for more than one block')
            __api.set_multiple_blocks(blocks, values)
    except Exception as e:
        _handle_exception(e)


def waitfor(block=None, value=None, lowlimit=None, highlimit=None, maxwait=None,
            wait_all=False, seconds=None, minutes=None, hours=None, time=None,
            frames=None, uamps=None, **pars):
    """Interrupts execution until certain conditions are met.

    Args:
        block (string, optional) : the name of the block to wait for
        value (float, optional) : the block value to wait for
        lowlimit (float, optional): wait for the block to be >= this value
        highlimit (float, optional) : wait for the block to be <= this value
        maxwait (float, optional) : wait no longer that the specified number of seconds
        wait_all (bool, optional) : wait for all conditions to be met (e.g. a number of frames and an amount of uamps)
        seconds (float, optional) : wait for a specified number of seconds
        minutes (float, optional) : wait for a specified number of minutes
        hours (float, optional) : wait for a specified number of hours
        time (string, optional) : a quicker way of setting hours, minutes and seconds (must be of format "HH:MM:SS")
        frames (int, optional) : wait for a total number of good frames to be collected
        uamps (float, optional) : wait for a total number of uamps to be received

    Examples:
        Wait for a block to reach a specific value:
        >>> waitfor(myblock=123)
        >>> waitfor("myblock", 123)
        >>> waitfor("myblock", True)
        >>> waitfor("myblock", "OPEN")

        Wait for a block to be between limits:
        >>> waitfor("myblock", lowlimit=100, highlimit=110)

        Wait for a block to reach a specific value, but no longer than 60 seconds:
        >>> waitfor(myblock=123, maxwait=60)

        Wait for a specified time interval:
        >>> waitfor(seconds=10)
        >>> waitfor(hours=1, minutes=30, seconds=15)
        >>> waitfor(time="1:30:15")

        Wait for a data collection condition:
        >>> waitfor(frames=5000)
        >>> waitfor(uamps=200)

        Wait for either a number of frames OR a time interval to occur:
        >>> waitfor(frames=5000, hours=2)

        Wait for a number of frames AND a time interval to occur:
        >>> waitfor(frames=5000, hours=2, wait_all=True)
    """
    __api.log_info_msg("WAITFOR %s" % (locals(),))
    try:
        if block is None:
            # Search through the params to see if there is a block there
            blks = __api.get_blocks()
            for k in pars:
                if k in blks:
                    if block is not None:
                        raise Exception('Can set waitfor for only one block at a time')
                    block = k
                    value = pars[k]
        # Check that wait_for object exists
        if __api.waitfor is None:
            raise Exception("Cannot execute waitfor - try calling set_instrument first")
        # Start_waiting checks the block exists
        __api.waitfor.start_waiting(block, value, lowlimit, highlimit, maxwait, wait_all, seconds, minutes, hours, time,
                                    frames, uamps)
    except Exception as e:
        _handle_exception(e)


def begin(period=1, meas_id=None, meas_type="", meas_subid="", sample_id="", delayed=False, quiet=False, paused=False,
          verbose=False):
    """Starts a data collection run.

    Args:
        period (int, optional) : the period to begin data collection in
        meas_id (string, optional) : the measurement id
        meas_type (string, optional) : the type of measurement
        meas_subid (string, optional) : the measurement sub-id
        sample_id (string, optional) : the sample id
        delayed (bool, optional) : puts the period card to into delayed start mode
        quiet (bool, optional) : suppress the output to the screen
        paused (bool, optional) : begin in the paused state
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_info_msg("BEGIN %s" % (locals(),))
    try:
        __api.run_pre_post_cmd("begin_precmd", quiet=quiet)
        __api.dae.begin_run(period, meas_id, meas_type, meas_subid, sample_id, delayed, quiet, paused)
        waitfor_runstate("SETUP", onexit=True)
        __api.dae.post_begin_check(verbose)
        __api.run_pre_post_cmd("begin_postcmd", run_num=__api.dae.get_run_number(), quiet=quiet)
    except Exception as e:
        _handle_exception(e)


def abort(verbose=False):
    """Abort the current run.

    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_info_msg("ABORT %s" % (locals(),))
    try:
        __api.run_pre_post_cmd("abort_precmd")
        __api.dae.abort_run()
        waitfor_runstate("SETUP")
        __api.dae.post_abort_check(verbose)
        __api.run_pre_post_cmd("abort_postcmd")
    except Exception as e:
        _handle_exception(e)


def end(verbose=False):
    """End the current run.

        Args:
            verbose (bool, optional) : show the messages from the DAE
        """
    __api.log_info_msg("END %s" % (locals(),))
    try:
        __api.run_pre_post_cmd("end_precmd")
        __api.dae.end_run()
        waitfor_runstate("SETUP")
        __api.dae.post_end_check(verbose)
        __api.run_pre_post_cmd("end_postcmd")
    except Exception as e:
        _handle_exception(e)


def pause(verbose=False):
    """Pause the current run.

    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_info_msg("PAUSE %s" % (locals(),))
    try:
        __api.run_pre_post_cmd("pause_precmd")
        __api.dae.pause_run()
        waitfor_runstate("PAUSED")
        __api.dae.post_pause_check(verbose)
        __api.run_pre_post_cmd("pause_postcmd")
    except Exception as e:
        _handle_exception(e)


def resume(verbose=False):
    """Resume the current run after it has been paused.

    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_info_msg("RESUME %s" % (locals(),))
    try:
        __api.run_pre_post_cmd("resume_precmd")
        __api.dae.resume_run()
        waitfor_runstate("PAUSED", onexit=True)
        __api.dae.post_resume_check(verbose)
        __api.run_pre_post_cmd("resume_postcmd")
    except Exception as e:
        _handle_exception(e)


def updatestore(verbose=False):
    """Performs an update and a store operation in a combined operation.
    This is more efficient than doing the commands separately.

    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_info_msg("SAVING %s" % (locals(),))
    try:
        __api.dae.update_store_run()
        waitfor_runstate("SAVING", onexit=True)
        __api.dae.post_update_store_check(verbose)
    except Exception as e:
        _handle_exception(e)


def update(pause_run=True, verbose=False):
    """Data is loaded from the DAE into the computer memory, but is not written to disk.

    Args:
        pause_run (bool, optional) : whether to pause data collection first [optional]
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_info_msg("UPDATE %s" % (locals(),))
    try:
        if pause_run:
            # Pause
            pause(verbose=verbose)

        # Update
        __api.dae.update_run()
        waitfor_runstate("UPDATING", onexit=True)
        __api.dae.post_update_check(verbose)

        if pause_run:
            # Resume
            resume(verbose=verbose)
    except Exception as e:
        _handle_exception(e)


def store(verbose=False):
    """Data loaded into memory by a previous update command is now written to disk.

    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_info_msg("STORING %s" % (locals(),))
    try:
        __api.dae.store_run()
        waitfor_runstate("STORING", onexit=True)
        __api.dae.post_store_check(verbose)
    except Exception as e:
        _handle_exception(e)


def get_runstate():
    """Get the current status of the instrument as a string.

    Note: this value can take a few seconds to update after a change of state.

    Returns:
        string : the current run state
    """
    try:
        return __api.dae.get_run_state()
    except Exception as e:
        _handle_exception(e)


def get_period():
    """Gets the current period number.

    Returns:
        int : the current period
    """
    try:
        return __api.dae.get_period()
    except Exception as e:
        _handle_exception(e)


def get_number_periods():
    """Get the number of software periods.

    Returns:
        int : the number of periods
    """
    try:
        return __api.dae.get_num_periods()
    except Exception as e:
        _handle_exception(e)


def set_period(period):
    """Sets the current period number.

    Deprecated - use change_period

    Args:
        period (int) : the period to switch to
    """
    print "set_period is deprecated - use change_period"
    change_period(period)


def change_period(period):
    """Changes the current period number.

    Args:
        period (int) : the period to switch to
    """
    try:
        __api.dae.set_period(period)
    except Exception as e:
        _handle_exception(e)


def get_blocks():
    """Get the names of the blocks.

    Returns:
        list : the blocknames
    """
    try:
        return __api.get_blocks()
    except Exception as e:
        _handle_exception(e)


def cget(block):
    """Gets the useful values associated with a block.

    Args:
        block (string) : the name of the block

    Returns
        dict : details about about the block
    """
    try:
        if block not in __api.block_dict.keys():
            raise Exception('No block with the name "%s" exists' % block)

        ans = dict()
        ans['name'] = block
        ans['value'] = __api.block_dict[block][0]

        rc = __api.block_dict[block][1:]

        if rc is not None:
            ans['runcontrol'] = rc[1]
            ans['lowlimit'] = rc[2]
            ans['highlimit'] = rc[3]

        return ans
    except Exception as e:
        _handle_exception(e)


def waitfor_runstate(state, maxwaitsecs=3600, onexit=False):
    """Wait for a particular instrument run state.

    Args:
        state (string) : the state to wait for (e.g. "paused")
        maxwaitsecs (int, optional) : the maximum time to wait for the state before carrying on
        onexit (bool, optional) : wait for runstate to change from the specified state

    Examples:
        Wait for a run to enter the paused state:
        >>> waitfor_runstate("pause")

        Wait for a run to exit the paused state:
        >>> waitfor_runstate("pause", onexit=True)
    """
    __api.log_info_msg("WAITFOR_RUNSTATE %s" % (locals(),))
    try:
        # Check that wait_for object exists
        if __api.waitfor is None:
            raise Exception("Cannot execute waitfor - try calling set_instrument first")
        __api.waitfor.wait_for_runstate(state, maxwaitsecs, onexit)
    except Exception as e:
        _handle_exception(e)


def waitfor_move(*blocks, **kwargs):
    """ Wait for all motion or specific motion to complete.

    If block names are supplied then it will only wait for those to stop moving. Otherwise, it will wait for all motion
    to stop.

    Args:
        blocks (string, multiple, optional) : the names of specific blocks to wait for
        start_timeout (int, optional) : the number of seconds to wait for the movement to begin (default = 2 seconds)
        move_timeout (int, optional) : the maximum number of seconds to wait for motion to stop

    Examples:
        Wait for all motors to stop moving:
        >>> waitfor_move()

        Wait for all motors to stop moving with a timeout of 30 seconds:
        >>> waitfor_move(move_timeout=30)

        Wait for only slit1 and slit2 motors to stop moving:
        >>> waitfor_move("slit1", "slit2")
    """
    try:
        None
    except Exception as e:
        _handle_exception(e)


def get_runnumber():
    """Get the current run-number.

    Returns:
        string : the run-number
    """
    try:
        return __api.run_number
    except Exception as e:
        _handle_exception(e)


def snapshot_crpt(filename="c:\\Data\snapshot_crpt.tmp", verbose=False):
    """Create a snapshot of the current data.

    Args:
        filename (string, optional) : where to write the data file(s)
        verbose (bool, optional) : show the messages from the DAE

    Examples:
        Snapshot to a file called my_snapshot:

        >>> snapshot_crpt("c:\\Data\my_snapshot")
    """
    try:
        name = _correct_filepath(filename)
        __api.dae.snapshot_crpt(name)
        waitfor_runstate("STORING", onexit=True)
        __api.dae.post_snapshot_check(verbose)
    except Exception as e:
        _handle_exception(e)


def get_uamps(period=False):
    """Get the current number of micro-amp hours.

    Args:
        period (bool, optional) : whether to return the value for the current period only

    Returns:
        float : the number of uamps
    """
    try:
        return __api.dae.get_uamps(period)
    except Exception as e:
        _handle_exception(e)


def get_frames(period=False):
    """Gets the current number of good frames.

    Args:
        period (bool, optional) : whether to return the value for the current period only

    Returns:
        int : the number of frames
    """
    try:
        return __api.dae.get_good_frames(period)
    except Exception as e:
        _handle_exception(e)


def get_mevents():
    """Gets the total counts for all the detectors.

    Returns:
        float : the number of mevents
    """
    try:
        return __api.dae.get_mevents()
    except Exception as e:
        _handle_exception(e)


def get_totalcounts():
    """Get the total counts for the current run.

    Returns:
        int : the total counts
    """
    try:
        return __api.dae.get_total_counts()
    except Exception as e:
        _handle_exception(e)


def get_title():
    """Returns the current title.

    Returns:
        string : the title
    """
    try:
        return __api.dae.get_title()
    except Exception as e:
        _handle_exception(e)


def set_title(title):
    """Sets the current title.

    Deprecated - use change_title

    Args:
        title : the new title
    """
    print("set_title is deprecated - use change_title")
    change_title(title)


def change_title(title):
    """Sets the current title.

    Args:
        title : the new title
    """
    try:
        __api.dae.set_title(title)
    except Exception as e:
        _handle_exception(e)


def get_rb():
    """Returns the current RB number.

    Returns:
        string : the RB number
    """
    try:
        return __api.dae.get_rb_number()
    except Exception as e:
        _handle_exception(e)


def get_dashboard():
    """Get the current experiment values.

    Returns:
        dict : the experiment values
    """
    try:
        data = dict()
        data["status"] = __api.dae.get_run_state()
        data["run_number"] = __api.dae.get_run_number()
        data["rb_number"] = __api.dae.get_rb_number()
        data["user"] = __api.dae.get_users()
        data["title"] = __api.dae.get_title()
        data["run_time"] = __api.dae.get_run_duration()
        data["good_frames_total"] = __api.dae.get_good_frames()
        data["good_frames_period"] = __api.dae.get_good_frames(True)
        data["raw_frames_total"] = __api.dae.get_raw_frames()
        data["raw_frames_period"] = __api.dae.get_good_frames(True)
        data["beam_current"] = __api.dae.get_beam_current()
        data["total_current"] = __api.dae.get_total_uamps()
        data["spectra"] = __api.dae.get_num_spectra()
        data["spectra"] = __api.dae.get_num_spectra()
        data["periods"] = __api.dae.get_num_periods()
        data["time_channels"] = __api.dae.get_num_timechannels()
        data["monitor_spectrum"] = __api.dae.get_monitor_spectrum()
        data["monitor_from"] = __api.dae.get_monitor_from()
        data["monitor_to"] = __api.dae.get_monitor_to()
        data["monitor_counts"] = __api.dae.get_monitor_counts()
        return data
    except Exception as e:
        _handle_exception(e)


def _correct_filepath(filepath):
    """Corrects the slashes"""
    return filepath.__repr__().replace("\\", "/").replace("'", "").replace("//", "/")


def _correct_filepath_existing(filepath):
    """If the file exists it get the correct path with the correct casing"""
    filepath = _correct_filepath(filepath)
    if os.name == 'nt':
        try:
            # Correct path case for windows as Python needs correct casing
            return win32api.GetLongPathName(win32api.GetShortPathName(filepath))
        except Exception as err:
            raise Exception("Invalid file path entered: %s" % err)
    else:
        # Nothing to do for unix
        return filepath


def _convert_to_rawstring(data):
    escape_dict = {'\a': r'\a',
                   '\b': r'\b',
                   '\c': r'\c',
                   '\f': r'\f',
                   '\n': r'\n',
                   '\r': r'\r',
                   '\t': r'\t',
                   '\v': r'\v',
                   '\'': r'\'',
                   '\"': r'\"'}
    raw_string = ''
    for char in data:
        try:
            raw_string += escape_dict[char]
        except KeyError:
            raw_string += char
    return raw_string


def import_user_script_module(name, globs):
    """Loads user scripts from a module.
    This method should not be called directly instead use the load_script method.

    Args:
        name (string) : the name of the file to load
        globs (dict) : the global settings dictionary of the caller
    """
    try:
        name = _convert_to_rawstring(name)

        try:
            if "/" in name:
                # Probably a fullpath name
                name = _correct_filepath_existing(name)
            else:
                # May be a file in the SCRIPT_DIR
                name = _correct_filepath_existing(SCRIPT_DIR + name)
            directory, filename = os.path.split(os.path.abspath(name))
            directory += '\\'
        except:
            raise Exception("Script file was not found")

        mod = __load_module(filename[0:-3], directory)
        # If we get this far then the script is syntactically correct as far as Python is concerned
        # Now check the script details manually
        sc = ScriptChecker(__file__)
        errs = sc.check_script(name)
        if len(errs) > 0:
            combined = "script not loaded as errors found in script: "
            for e in errs:
                combined += "\n\t" + e
            raise Exception(combined)

        # Safe to load
        # Read the file to get the name of the functions
        funcs = []
        f = open(directory + filename, "r")
        for l in f.readlines():
            m = re.match("^def\s+(.+)\(", l)
            if m is not None:
                funcs.append(m.group(1))
        f.close()
        scripts = []
        for att in dir(mod):
            if isinstance(mod.__dict__.get(att), types.FunctionType):
                # Check function comes from script file not an import
                if att in funcs:
                    scripts.append(att)
        if len(scripts) > 0:
            # This is where the script file is actually loaded
            execfile(directory + filename, globs)
            msg = "Loaded the following script(s): "
            for script in scripts:
                msg += script + ", "
            print msg[0:-2]
            print "From: %s%s" % (directory, filename)
        else:
            raise Exception("No script found")
    except Exception as e:
        _handle_exception(e)


def __load_module(name, directory):
    """This will reload the module if it has already been loaded."""
    fpath = None
    try:
        fpath, pathname, description = imp.find_module(name, [directory])
        return imp.load_module(name, fpath, pathname, description)
    except Exception as e:
        raise Exception(e)
    finally:
        # Since we may exit via an exception, close fpath explicitly.
        if fpath is not None:
            fpath.close()


def get_script_dir():
    """Get the current script directory.

    Returns:
        string : the directory
    """
    return SCRIPT_DIR


def set_script_dir(directory):
    """Set the directory for loading scripts from.

    Deprecated - use change_script_dir.

    Args:
        string : the directory to load scripts from
    """
    print "set_script_dir is deprecated - use change_script_dir"
    change_script_dir(directory)


def change_script_dir(directory):
    """Set the directory for loading scripts from.

    Args:
        string : the directory to load scripts from
    """
    try:
        directory = _convert_to_rawstring(directory)
        directory = _correct_filepath_existing(directory)
        if os.path.exists(directory):
            global SCRIPT_DIR
            if directory[-1] == "/":
                SCRIPT_DIR = directory
            else:
                SCRIPT_DIR = directory + "/"
        else:
            raise Exception("Directory does not exist")
    except Exception as e:
        _handle_exception(e)


def change_start():
    """Start a change operation.
    The operation is finished when change_finish is called.

    Between these two calls a sequence of other change commands can be called.
    For example: change_tables, change_tcb etc.
    """
    try:

        __api.dae.change_start()
    except Exception as e:
        _handle_exception(e)


def change_finish():
    """End a change operation.
    The operation is begun when change_start is called.

    Between these two calls a sequence of other change commands can be called.
    For example: change_tables, change_tcb etc.
    """
    try:
        __api.dae.change_finish()
    except Exception as e:
        _handle_exception(e)


def change_monitor(spec, low, high):
    """Change the monitor to a specified spectrum and range.

    Args:
        spectrum (int) : the spectrum number
        low (float) : the low end of the integral
        high (float) : the high end of the integral
    """
    try:
        __api.dae.change_monitor(spec, low, high)
    except Exception as e:
        _handle_exception(e)


def change_tables(wiring=None, detector=None, spectra=None):
    """Load the wiring, detector and/or spectra tables.

    Args:
        wiring (string, optional) : the filename of the wiring table file
        detector (string, optional) : the filename of the detector table file
        spectra (string, optional) : the filename of the spectra table file
    """
    try:
        __api.dae.change_tables(wiring, detector, spectra)
    except Exception as e:
        _handle_exception(e)


def change_sync(source):
    """Change the source the DAE using for synchronisation.

    Args:
        source (string) : the source to use ('isis', 'internal', 'smp', 'muon cerenkov', 'muon ms', 'isis (first ts1)')
    """
    try:
        __api.dae.change_sync(source)
    except Exception as e:
        _handle_exception(e)


def change_tcb_file(tcbfile=None, default=False):
    """Change the time channel boundaries.

    Args:
        tcbfile (string, optional) : the file to load
        default (bool, optional): load the default file
    """
    try:
        __api.dae.change_tcb_file(tcbfile, default)
    except Exception as e:
        _handle_exception(e)


def change_tcb(low, high, step, trange, log=False, regime=1):
    """Change the time channel boundaries.

    Args
        low (float) : the lower limit
        high (float) : the upper limit
        step (float) : the step size
        trange (int) : the time range (1 to 5)
        log (bool, optional) : whether to use LOG binning
        regime (int, optional) : the time regime to set (1 to 6)
    """
    try:
        __api.dae.change_tcb(low, high, step, trange, log, regime)
    except Exception as e:
        _handle_exception(e)


def change_vetos(**params):
    """Change the DAE veto settings.

    Args:
        clearall (bool, optional) : remove all vetos
        smp (bool, optional) : set SMP veto
        ts2 (bool, optional) : set TS2 veto
        hz50 (bool, optional) : set 50 hz veto
        ext0  (bool, optional): set external veto 0
        ext1  (bool, optional): set external veto 1
        ext2 (bool, optional) : set external veto 2
        ext3 (bool, optional) : set external veto 3

    Note: If clearall is specified then all vetos are turned off,
    but it is possible to turn other vetoes back on at the same time:

    Examples:
        Turns all vetoes off then turns the SMP veto back on:
        >>> change_vetos(clearall=True, smp=True)
    """
    try:
        __api.dae.change_vetos(**params)
    except Exception as e:
        _handle_exception(e)


def change_fermi_veto(enable=None, delay=1.0, width=1.0):
    """Configure the fermi chopper veto.

    Args:
        enable (bool, optional) : enable the fermi veto
        delay (float, optional) : the veto delay
        width (float, optional) : the veto width
    """
    try:
        __api.dae.set_fermi_veto(enable, delay, width)
    except Exception as e:
        _handle_exception(e)


def enable_soft_periods(nperiods=None):
    """Switch the DAE to software periods mode.

    Args:
        nperiods (int, optional) : the number of software periods
    """
    try:
        __api.dae.set_period_mode('soft')
        __api.dae.set_num_soft_periods(nperiods)
    except Exception as e:
        _handle_exception(e)


def set_number_soft_periods(number, enable=None):
    """Sets the number of software periods for the DAE.

    Deprecated - use change_number_soft_periods

    Args:
        number (int) : the number of periods to create
        enable (bool, optional) : switch to soft period mode
    """
    print "set_number_soft_periods is deprecated - use change_number_soft_periods"
    change_number_soft_periods(number, enable)


def change_number_soft_periods(number, enable=None):
    """Sets the number of software periods for the DAE.

    Args:
        number (int) : the number of periods to create
        enable (bool, optional) : switch to soft period mode
    """
    try:
        if enable:
            __api.dae.set_period_mode('soft')
        __api.dae.set_num_soft_periods(number)
    except Exception as e:
        _handle_exception(e)


def enable_hard_periods(mode, period_file=None, sequences=None, output_delay=None, period=None, daq=False, dwell=False,
                        unused=False, frames=None, output=None, label=None):
    """Sets the DAE to use hardware periods.

    Args:
        mode (string) : set the mode to internal ('int') or external ('ext')
        period_file (string, optional) : the file containing the internal period settings (ignores any other settings)
        sequences (int, optional) : the number of times to repeat the period loop (0 = infinite loop)
        output_delay (int, optional) : the output delay in microseconds
        period (int, optional) : the number of the period to set the following parameters for
        daq (bool, optional) :  the specified period is a acquisition period
        dwell (bool, optional) : the specified period is a dwell period
        unused (bool, optional) : the specified period is a unused period
        frames (int, optional) : the number of frames to count for the specified period
        output (int, optional) : the binary output the specified period
        label (string, optional) : the label for the period the specified period

    Note: if the period number is unspecified then the settings will be applied to all periods

    Examples:
        Setting external periods:
        >>> enable_hard_periods('ext')

        Setting internal periods from a file:
        >>> enable_hard_periods('int', 'c:\\myperiods.txt')
        """
    try:
        __api.dae.configure_hard_periods(mode, period_file, sequences, output_delay, period, daq, dwell, unused, frames,
                                         output, label)
    except Exception as e:
        _handle_exception(e)


def configure_internal_periods(sequences=None, output_delay=None, period=None, daq=False, dwell=False, unused=False,
                               frames=None, output=None, label=None):
    """Configure the internal periods without switching to internal period mode.

    Args:
        sequences (int, optional) : the number of times to repeat the period loop (0 = infinite loop)
        output_delay (int, optional) : the output delay in microseconds
        period (int, optional) : the number of the period to set the following parameters for
        daq (bool, optional) :  the specified period is a acquisition period
        dwell (bool, optional) : the specified period is a dwell period
        unused (bool, optional) : the specified period is a unused period
        frames (int, optional) : the number of frames to count for the specified period
        output (int, optional) : the binary output the specified period
        label (string, optional) : the label for the period the specified period

    Note: if the period number is unspecified then the settings will be applied to all periods
    """
    try:
        __api.dae.configure_internal_periods(sequences, output_delay, period, daq, dwell, unused, frames, output, label)
    except Exception as e:
        _handle_exception(e)


def define_hard_period(period=None, daq=False, dwell=False, unused=False, frames=None, output=None, label=None):
    """Define the internal hardware periods.

    Args:
        period (int, optional) : the number of the period to set the following parameters for
        daq (bool, optional) :  the specified period is a acquisition period
        dwell (bool, optional) : the specified period is a dwell period
        unused (bool, optional) : the specified period is a unused period
        frames (int, optional) : the number of frames to count for the specified period
        output (int, optional) : the binary output the specified period
        label (string, optional) : the label for the period the specified period

    Note: if the period number is unspecified then the settings will be applied to all periods
    """
    try:
        configure_internal_periods(None, None, period, daq, dwell, unused, frames, output, label)
    except Exception as e:
        _handle_exception(e)


def change_users(users):
    """Define the internal hardware periods.

    Args:
        users (string): the names of the users
    """
    try:
        __api.dae.set_users(users)
    except Exception as e:
        _handle_exception(e)


def change(**params):
    """Change experiment parameters.

    Note: it is possible to change more than one item at a time.

    Args:
        title (string, optional) : change the current title
        period (int, optional) : change to a different period (must be in a non-running state)
        nperiods (int, optional) : change the number of software periods (must be in a non-running state)
        user (string, optional) : change the user(s) (not implemented)
        sample_name string, optional) : change the sample name (not implemented)
        rbno (int, optional) : change the RB number (not implemented)
        aoi (float, optional) : change the angle of incidence (reflectometers only) (not implemented)
        phi (float, optional) : change the sample angle PHI (reflectometers only) (not implemented)

    Examples:
        Change the title:
        >>> change(title="The new title")

        Change the RB number and the users:
        >>> change(rbno=123456, user="A. User and Ann Other")
    """
    try:
        for k in params:
            key = k.lower().strip()
            if key == 'title':
                change_title(params[k])
            elif key == 'period':
                change_period(params[k])
            elif key == 'nperiods':
                change_number_soft_periods(params[k])
            elif key == 'user' or key == 'users':
                __api.dae.set_users(params[k])
            # elif key == 'sample_name':
                # api.set_sample_name(params[k])
            # elif key == 'thickness':
                # api.set_sample_par('thickness', params[k])
            # elif key == 'rb' or key == 'rbno':
                # api.set_rb_number(params[k])
            # elif key == 'aoi':
                # api.change_vars(aoi=params[k])
            # elif key == 'phi':
                # api.change_vars(phi=params[k])
    except Exception as e:
        _handle_exception(e)


def get_spectrum(spectrum, period=1, dist=False):
    """Get the specified spectrum from the DAE.

    Args:
        spectrum (int) : the spectrum number
        period (int, optional) : the period
        dist (bool, optional) : whether to get the spectrum as a distribution

    Returns:
        dict : dictionary of values
    """
    try:
        return __api.dae.get_spectrum(spectrum, period, dist)
    except Exception as e:
        _handle_exception(e)


def plot_spectrum(spectrum, period=1, dist=False):
    """Get the specified spectrum from the DAE and plot it.

    Args:
        spectrum (int) : the spectrum number
        period (int, optional) : the period
        dist (bool, optional) : whether to get the spectrum as a distribution

    Returns:
        GeniePlot : the plot object
    """
    try:
        graph = SpectraPlot(__api, spectrum, period, dist)
        return graph
    except Exception as e:
        _handle_exception(e)


def get_sample_pars():
    """Get the current sample parameter values.

    Returns:
        dict : the sample parameters
    """
    try:
        names = __api.get_sample_pars()
        return names
    except Exception as e:
        _handle_exception(e)


def set_sample_par(name, value):
    """Set a new value for a sample parameter

    Deprecated - use change_sample_par

    Args:
        name (string, optional) : the name of the parameter to change
        value (optional) : the new value
    """
    print "set_sample_par is deprecated - use change_sample_par"
    change_sample_par(name, value)


def change_sample_par(name, value):
    """Set a new value for a sample parameter

    Args:
        name (string, optional) : the name of the parameter to change
        value (optional) : the new value
    """
    try:
        __api.set_sample_par(name, value)
    except Exception as e:
        _handle_exception(e)


def get_beamline_pars():
    """Get the current beamline parameter values.

    Returns:
        dict : the beamline parameters
    """
    try:
        names = __api.get_beamline_pars()
        return names
    except Exception as e:
        _handle_exception(e)


def set_beamline_par(name, value):
    """Set a new value for a beamline parameter

    Deprecated - use change_beamline_par

    Args:
        name (string, optional) : the name of the parameter to change
        value (optional) : the new value
    """
    print "set_beamline_par is deprecated - use change_beamline_par"
    change_beamline_par(name, value)


def change_beamline_par(name, value):
    """Set a new value for a beamline parameter

    Args:
        name (string, optional) : the name of the parameter to change
        value (optional) : the new value
    """
    try:
        __api.set_beamline_par(name, value)
    except Exception as e:
        _handle_exception(e)


def send_sms(phone_num, message):
    """Send a text message to a mobile phone

    Args:
        phone_num (string) : the mobile number to send to
        message (string) : the message to send
    """
    try:
        from smslib.sms import send_sms
        send_sms(phone_num, message)
    except Exception as e:
        _handle_exception(e)


def get_wiring_tables():
    """Gets a list of possible wiring table choices.

    Returns:
        list : the files
    """
    try:
        return __api.dae.get_wiring_tables()
    except Exception as e:
        _handle_exception(e)


def get_spectra_tables():
    """Gets a list of possible spectra table choices.

    Returns:
        list : the files
    """
    try:
        return __api.dae.get_spectra_tables()
    except Exception as e:
        _handle_exception(e)


def get_detector_tables():
    """Gets a list of possible detector table choices.

    Returns:
        list : the files
    """
    try:
        return __api.dae.get_detector_tables()
    except Exception as e:
        _handle_exception(e)


def get_period_files():
    """Gets a list of possible period file choices.

    Returns:
        list : the files
    """
    try:
        return __api.dae.get_period_files()
    except Exception as e:
        _handle_exception(e)


def check_alarms(*blocks):
    """Checks whether the specified blocks are in alarm.

    Args:
        blocks (string, multiple) : the block(s) to check

    Returns:
        list, list : the blocks in minor alarm and major alarm respectively

    Example:
        Check alarm state for block1 and block2:
        >>> check_alarms("block1", "block2")
    """
    return __api.check_alarms(blocks)
