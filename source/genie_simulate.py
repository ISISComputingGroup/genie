import os

class Waitfor(object):
    def __init__(self):
        pass

    def start_waiting(self, block=None, value=None, lowlimit=None, highlimit=None, maxwait=None, wait_all=False,
                      seconds=None, minutes=None, hours=None, time=None, frames=None, uamps=None):
        pass

    def wait_for_runstate(self, state, maxwaitsecs=3600, onexit=False):
        # TODO: Check state entered is valid and not a misspelling
        pass


class WaitForMoveController(object):
    def __init__(self):
        pass

    def wait(self, start_timeout=None, move_timeout=None):
        pass

    def wait_specific(self, blocks, start_timeout=None, move_timeout=None):
        pass

    def wait_for_start(self, timeout, check_for_move):
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
            raise Exception("Can only be called when RUNNING or PAUSED")

    def update_run(self):
        """
        Does nothing but throw error if run_state is not "RUNNING" or "PAUSED"
        """
        if self.run_state == "RUNNING" or self.run_state == "PAUSED":
            pass
        else:
            raise Exception("Can only be called when RUNNING or PAUSED")

    def store_run(self):
        """
        Does nothing but throw error if run_state is not "RUNNING" or "PAUSED"
        """
        if self.run_state == "RUNNING" or self.run_state == "PAUSED":
            pass
        else:
            raise Exception("Can only be called when RUNNING or PAUSED")

    def recover_run(self):
        if self.run_state == "SETUP":
            pass
        else:
            raise Exception("Can only be called when SETUP")

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
            self.num_periods = number
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

    def set_verbose(self, verbose):
        pass


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


class API(object):
    def __init__(self, pv_prefix, globs):
        self.block_dict = dict()
        self.num_periods = 1
        self.run_number = 123456
        self.waitfor = Waitfor()
        self.wait_for_move = WaitForMoveController()
        self.dae = Dae()
        self.beamline_pars = {}
        self.sample_pars = {}

    def set_instrument(self, pv_prefix, globs):
        pass

    def prefix_pv_name(self, name):
        pass

    def set_pv_value(self, name, value, wait=False):
        pass

    def get_pv_value(self, name, to_string=False, attempts=3):
        pass

    def pv_exists(self, name):
        return True

    def correct_blockname(self, name, add_prefix=True):
        return name

    def get_blocks(self):
        return self.block_dict.keys()

    def block_exists(self, name):
        # Create an entry for it and return True
        if name not in self.block_dict:
            self.set_block_value(name)
        return True

    def set_block_value(self, name, value=None, runcontrol=None, lowlimit=None, highlimit=None, wait=False):
        """Sets a block's values.
        If the block already exists, update the block. Only update values that have changed.

        Args:
            name (string): the name of the block
            value (int): the value of the block
            runcontrol (boolean): whether runcontrol is enabled or disabled
            lowlimit (int): the lower limit
            highlimit (int): the higher limit
            wait (boolean): whether a readback value from the block is waited for (??)

        """
        if not name in self.block_dict:
            self.block_dict[name] = [value, runcontrol, lowlimit, highlimit, ""]
        else:
            if value is not None:
                self.block_dict[name][0] = value
            if runcontrol is not None:
                self.block_dict[name][1] = runcontrol
            if lowlimit is not None:
                self.block_dict[name][2] = lowlimit
            if highlimit is not None:
                self.block_dict[name][3] = highlimit
            if wait:
                self.block_dict[name][4] = wait

    def get_block_value(self, name, to_string=False, attempts=3):
        if to_string:
            return str(self.block_dict[name][0])
        return self.block_dict[name][0]

    def set_multiple_blocks(self, names, values):
        temp = zip(names, values)
        for name, value in temp:
            if name in self.block_dict:
                self.block_dict[name][0] = value
            else:
                self.block_dict[name] = [value, False, None, None, None]

    def run_pre_post_cmd(self, command, **pars):
        pass

    def log_entered_command(self):
        pass
        
    def log_entered_command(self):
        pass
        
    def log_command(self, arg1, arg2):
        pass

    def log_info_msg(self, *args, **kwargs):
        pass

    def log_error_msg(self, error_msg):
        pass

    def write_to_log(self, message, source):
        pass

    def get_sample_pars(self):
        return self.sample_pars

    def set_sample_par(self, name, value):
        self.sample_pars[name] = value

    def get_beamline_pars(self):
        return self.beamline_pars

    def set_beamline_par(self, name, value):
        self.beamline_pars[name] = value

    def get_runcontrol_settings(self, name):
        rc = dict()
        rc["ENABLE"] = self.block_dict[name][1]
        rc["LOW"] = self.block_dict[name][2]
        rc["HIGH"] = self.block_dict[name][3]
        return rc

    def check_alarms(self, blocks):
        minor = list()
        major = list()
        return minor, major

    def check_limit_violations(self, blocks):
        return list()

    def get_current_block_values(self):
        return self.block_dict

    def send_sms(self, phone_num, message):
        print "\"" + message + "\"" + "\nSent to " + phone_num





