import xml.etree.ElementTree as ET
import os
import zlib
import json
from time import sleep, strftime
from genie_change_cache import ChangeCache

DAE_PVS_LOOKUP = {
    "runstate": "DAE:RUNSTATE",
    "runstate_str": "DAE:RUNSTATE_STR",
    "beginrun": "DAE:BEGINRUNEX",
    "abortrun": "DAE:ABORTRUN",
    "pauserun": "DAE:PAUSERUN",
    "resumerun": "DAE:RESUMERUN",
    "endrun": "DAE:ENDRUN",
    "recoverrun": "DAE:RECOVERRUN",
    "saverun": "DAE:SAVERUN",
    "updaterun": "DAE:UPDATERUN",
    "storerun": "DAE:STORERUN",
    "snapshot": "DAE:SNAPSHOTCRPT",
    "period_rbv": "DAE:PERIOD:RBV",
    "period": "DAE:PERIOD",
    "runnumber": "DAE:RUNNUMBER",
    "numperiods": "DAE:NUMPERIODS",
    "mevents": "DAE:MEVENTS",
    "totalcounts": "DAE:TOTALCOUNTS",
    "goodframes": "DAE:GOODFRAMES",
    "goodframesperiod": "DAE:GOODFRAMES_PD",
    "rawframes": "DAE:RAWFRAMES",
    "uamps": "DAE:GOODUAH",
    "histmemory": "DAE:HISTMEMORY",
    "spectrasum": "DAE:SPECTRASUM",
    "uampsperiod": "DAE:GOODUAH_PD",
    "title": "DAE:TITLE",
    "title_sp": "DAE:TITLE:SP",
    "rbnum": "ED:RBNUMBER",
    "rbnum_sp": "ED:RBNUMBER:SP",
    "period_sp": "DAE:PERIOD:SP",
    "users": "ED:SURNAME",
    "users_sp": "ED:USERNAME:SP",
    "starttime": "DAE:STARTTIME",
    "npratio": "DAE:NPRATIO",
    "timingsource": "DAE:DAETIMINGSOURCE",
    "periodtype": "DAE:PERIODTYPE",
    "isiscycle": "DAE:ISISCYCLE",
    "rawframesperiod": "DAE:RAWFRAMES_PD",
    "runduration": "DAE:RUNDURATION",
    "rundurationperiod": "DAE:RUNDURATION_PD",
    "numtimechannels": "DAE:NUMTIMECHANNELS",
    "memoryused": "DAE:DAEMEMORYUSED",
    "numspectra": "DAE:NUMSPECTRA",
    "monitorcounts": "DAE:MONITORCOUNTS",
    "monitorspectrum": "DAE:MONITORSPECTRUM",
    "periodseq": "DAE:PERIODSEQ",
    "beamcurrent": "DAE:BEAMCURRENT",
    "totaluamps": "DAE:TOTALUAMPS",
    "totaldaecounts": "DAE:TOTALDAECOUNTS",
    "monitorto": "DAE:MONITORTO",
    "monitorfrom": "DAE:MONITORFROM",
    "countrate": "DAE:COUNTRATE",
    "eventmodefraction": "DAE:EVENTMODEFRACTION",
    "daesettings": "DAE:DAESETTINGS",
    "daesettings_sp": "DAE:DAESETTINGS:SP",
    "tcbsettings": "DAE:TCBSETTINGS",
    "tcbsettings_sp": "DAE:TCBSETTINGS:SP",
    "periodsettings": "DAE:HARDWAREPERIODS",
    "periodsettings_sp": "DAE:HARDWAREPERIODS:SP",
    "getspectrum_x": "DAE:SPEC:%d:%d:X",
    "getspectrum_x_size": "DAE:SPEC:%d:%d:X.NORD",
    "getspectrum_y": "DAE:SPEC:%d:%d:Y",
    "getspectrum_y_size": "DAE:SPEC:%d:%d:Y.NORD",
    "errormessage": "DAE:ERRMSGS",
    "allmessages": "DAE:ALLMSGS",
    "statetrans": "DAE:STATETRANS",
    "wiringtables": "DAE:WIRINGTABLES",
    "spectratables": "DAE:SPECTRATABLES",
    "detectortables": "DAE:DETECTORTABLES",
    "periodfiles": "DAE:PERIODFILES",
}


class Dae(object):
    def __init__(self, api, prefix=""):
        """The constructor"""
        self.api = api
        self.inst_prefix = prefix
        self.in_change = False
        self.change_cache = ChangeCache()
        self.verbose = False
        
    def __prefix_pv_name(self, name):
        """Adds the prefix to the PV name"""
        if self.inst_prefix is not None:
            name = self.inst_prefix + name
        return name
          
    def _get_dae_pv_name(self, name):
        """Retrieves the full pv name of a DAE variable"""
        return self.__prefix_pv_name(DAE_PVS_LOOKUP[name.lower()])

    def _get_pv_value(self, name, to_string=False):
        """Get a PV's value"""
        return self.api.get_pv_value(name, to_string)

    def _set_pv_value(self, name, value, wait=False):
        self.api.set_pv_value(name, value, wait)
        
    def _check_for_runstate_error(self, pv, header=""):
        status = self._get_pv_value(pv + ".STAT", to_string=True)
        if status != "NO_ALARM":
            errmsg = self._get_pv_value(self._get_dae_pv_name("errormessage"), to_string=True)
            raise Exception(header.strip() + " " + errmsg)
            
    def _print_verbose_messages(self):
        msgs = self._get_pv_value(self._get_dae_pv_name("allmessages"), to_string=True)
        print msgs
        
    def _dehex_decompress(self, value):
        return zlib.decompress(value.decode("hex"))
        
    def set_verbose(self, verbose):
        if isinstance(verbose, bool):
            self.verbose = verbose
            if verbose:
                print "Setting DAE messages to verbose mode"
            else:
                print "Setting DAE messages to non-verbose mode"
        else:
            raise Exception("Value must be boolean")
                       
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
        if self.in_change:
            raise Exception("Cannot start in CHANGE mode, type change_finish()")
        
        # Set sample parameters - these parameters do not currently exist
        if meas_id is not None:
            pass
        if meas_type is not None:
            pass
        if meas_subid is not None:
            pass
        if sample_id is not None:
            pass
        
        # Check PV exists
        val = self._get_pv_value(self._get_dae_pv_name("beginrun"))
        if val is None:
            raise Exception("begin_run: could not connect to DAE")

        if period is not None:
            # Set the period before starting the run
            self.set_period(period)

        if not quiet:
            print "** Beginning Run %s at %s" % (self.get_run_number(), strftime("%H:%M:%S %d/%m/%y "))
            print "*  Proposal Number: %s" % self.get_rb_number()
            print "*  Experiment Team: %s" % self.get_users()
            
        # By choosing the value sent to the begin PV it can set pause and/or delayed
        options = 0
        if paused:
            options += 1
        if delayed:
            options += 2       
        
        self._set_pv_value(self._get_dae_pv_name("beginrun"), options, wait=True)

    def post_begin_check(self, verbose=False):
        self._check_for_runstate_error(self._get_dae_pv_name("beginrun"), "BEGIN")
        if verbose or self.verbose:
            self._print_verbose_messages()

    def abort_run(self):
        """Abort the current run."""
        print "** Aborting Run %s at %s" % (self.get_run_number(), strftime("%H:%M:%S %d/%m/%y "))
        self._set_pv_value(self._get_dae_pv_name("abortrun"), 1.0, wait=True)

    def post_abort_check(self, verbose=False):
        self._check_for_runstate_error(self._get_dae_pv_name("abortrun"), "ABORT")
        if verbose or self.verbose:
            self._print_verbose_messages()
        
    def end_run(self):
        """End the current run."""
        print "** Ending Run %s at %s" % (self.get_run_number(), strftime("%H:%M:%S %d/%m/%y "))
        self._set_pv_value(self._get_dae_pv_name("endrun"), 1.0, wait=True)

    def post_end_check(self, verbose=False):
        self._check_for_runstate_error(self._get_dae_pv_name("endrun"), "END")
        if verbose or self.verbose:
            self._print_verbose_messages()
        
    def recover_run(self):
        """Recovers the run if it has been aborted.
        The command should be run before the next run is started.
        Note: the run will be recovered in the paused state.
        """
        self._set_pv_value(self._get_dae_pv_name("recoverrun"), 1.0, wait=True)

    def post_recover_check(self, verbose=False):
        self._check_for_runstate_error(self._get_dae_pv_name("recoverrun"), "RECOVER")
        if verbose or self.verbose:
            self._print_verbose_messages()
            
    def update_store_run(self):
        """Performs an update and a store operation in a combined operation.
        This is more efficient than doing the commands separately.
        """
        print "** Saving Run %s at %s" % (self.get_run_number(), strftime("%H:%M:%S %d/%m/%y "))
        self._set_pv_value(self._get_dae_pv_name("saverun"), 1.0, wait=True)

    def post_update_store_check(self, verbose=False):
        self._check_for_runstate_error(self._get_dae_pv_name("saverun"), "SAVE")
        if verbose or self.verbose:
            self._print_verbose_messages()
            
    def update_run(self):
        """Data is loaded from the DAE into the computer memory, but is not written to disk.
        """
        self._set_pv_value(self._get_dae_pv_name("updaterun"), 1.0, wait=True)

    def post_update_check(self, verbose=False):
        self._check_for_runstate_error(self._get_dae_pv_name("updaterun"), "UPDATE")
        if verbose or self.verbose:
            self._print_verbose_messages()
            
    def store_run(self):
        """Data loaded into memory by a previous update_run command is now written to disk."""
        self._set_pv_value(self._get_dae_pv_name("storerun"), 1.0, wait=True)

    def post_store_check(self, verbose=False):
        self._check_for_runstate_error(self._get_dae_pv_name("storerun"), "STORE")
        if verbose or self.verbose:
            self._print_verbose_messages()

    def snapshot_crpt(self, filename):
        """Save a snapshot of the CRPT.

        Parameters:
            filename - the name and location to save the file(s) to
        """
        self._set_pv_value(self._get_dae_pv_name("snapshot"), filename, wait=True)

    def post_snapshot_check(self, verbose=False):
        self._check_for_runstate_error(self._get_dae_pv_name("snapshot"), "SNAPSHOTCRPT")
        if verbose or self.verbose:
            self._print_verbose_messages()
        
    def pause_run(self):
        """Pause the current run."""
        print "** Pausing Run %s at %s" % (self.get_run_number(), strftime("%H:%M:%S %d/%m/%y "))
        self._set_pv_value(self._get_dae_pv_name("pauserun"), 1.0, wait=True)

    def post_pause_check(self, verbose=False):
        self._check_for_runstate_error(self._get_dae_pv_name("pauserun"), "PAUSE")
        if verbose or self.verbose:
            self._print_verbose_messages()
        
    def resume_run(self):
        """Resume the current run after it has been paused."""
        print "** Resuming Run %s at %s" % (self.get_run_number(), strftime("%H:%M:%S %d/%m/%y "))
        self._set_pv_value(self._get_dae_pv_name("resumerun"), 1.0, wait=True)

    def post_resume_check(self, verbose=False):
        self._check_for_runstate_error(self._get_dae_pv_name("resumerun"), "RESUME")
        if verbose or self.verbose:
            self._print_verbose_messages()

    def get_run_state(self):
        """Get the current state of the DAE
        Note: this value can take a few seconds to update after a change of state"""
        try:
            return self._get_pv_value(self._get_dae_pv_name("runstate"), to_string=True)
        except:
            raise Exception("get_run_state: could not get run state")

    def get_run_number(self):
        """Get the current run number."""
        return self._get_pv_value(self._get_dae_pv_name("runnumber"))
        
    def get_period_type(self):
        """Get the period type"""
        return self._get_pv_value(self._get_dae_pv_name("periodtype"))
        
    def get_period_seq(self):
        """Get the period sequence"""
        return self._get_pv_value(self._get_dae_pv_name("periodseq"))
        
    def get_period(self):
        """Returns the current period number."""
        return self._get_pv_value(self._get_dae_pv_name("period"))
        
    def get_num_periods(self):
        """Returns the number of periods."""
        return self._get_pv_value(self._get_dae_pv_name("numperiods"))

    def set_period(self, period):
        """Change to the specified period.
        
        Parameters:
            period - the number of the period to change to
        """
        self._set_pv_value(self._get_dae_pv_name("period_sp"), period, wait=True)
        
    def get_uamps(self, period=False):
        """Returns the current number of micro-amp hours.
        
        Parameters:
            period - whether to return the micro-amp hours for the current period [optional]
        """
        if period:
            return self._get_pv_value(self._get_dae_pv_name("uampsperiod"))
        else:
            return self._get_pv_value(self._get_dae_pv_name("uamps"))
        
    def get_mevents(self):
        """Returns the total number of events for all the detectors."""
        return self._get_pv_value(self._get_dae_pv_name("mevents"))
        
    def get_total_counts(self):
        """Get the total counts for the current run."""
        return self._get_pv_value(self._get_dae_pv_name("totalcounts"))
        
    def get_good_frames(self, period=False):
        """Returns the current number of good frames.
        
        Parameters:
            period - whether to return the number of good frames for the current period [optional]
        """
        if period:
            return self._get_pv_value(self._get_dae_pv_name("goodframesperiod"))
        else:
            return self._get_pv_value(self._get_dae_pv_name("goodframes"))
        
    def get_raw_frames(self, period=False):
        """Returns the current number of raw frames.
        
        Parameters:
            period - whether to return the number of raw frames for the current period [optional]
        """
        if period:
            return self._get_pv_value(self._get_dae_pv_name("rawframesperiod"))
        else:
            return self._get_pv_value(self._get_dae_pv_name("rawframes"))
        
    def sum_all_dae_memory(self):
        """Returns the sum of the counts in the DAE."""
        return self._get_pv_value(self._get_dae_pv_name("histmemory"))
        
    def get_memory_used(self):
        """Get the DAE memory used"""
        return self._get_pv_value(self._get_dae_pv_name("memoryused"))
        
    def sum_all_spectra(self):
        """Returns the sum of all the spectra in the DAE."""
        return self._get_pv_value(self._get_dae_pv_name("spectrasum"))
        
    def get_num_spectra(self):
        """Get the number of spectra"""
        return self._get_pv_value(self._get_dae_pv_name("numspectra"))
        
    def get_rb_number(self):
        """Get the RB number for the current run."""
        return self._get_pv_value(self._get_dae_pv_name("rbnum"))
        
    def get_title(self):
        """Get the title for the current run."""
        return self._get_pv_value(self._get_dae_pv_name("title"), to_string=True)
    
    def set_title(self, title):
        """Get the title for the current run."""
        self._set_pv_value(self._get_dae_pv_name("title_sp"), title)
        
    def get_users(self):
        """Get the users for the current run"""
        try:
            # Data comes as compressed and hexed json
            raw = self._dehex_decompress(self._get_pv_value(self._get_dae_pv_name("users"), to_string=True))
            names_list = json.loads(raw)
            if len(names_list) > 1:
                last = names_list.pop(-1)
                names = ", ".join(names_list)
                names += " and " + last
                return names
            else:
                # Will throw if empty - that is okay
                return names_list[0]
        except:
            return ""
        
    def set_users(self, users):
        """Set the users for the current run"""
        self._set_pv_value(self._get_dae_pv_name("users_sp"), users)
        
    def get_starttime(self):
        """Get the start time for the current run"""
        return self._get_pv_value(self._get_dae_pv_name("starttime"))
        
    def get_npratio(self):
        """Get the n/p ratio for the current run"""
        return self._get_pv_value(self._get_dae_pv_name("npratio"))
        
    def get_timing_source(self):
        """Get the DAE timing source"""
        return self._get_pv_value(self._get_dae_pv_name("timingsource"))
        
    def get_run_duration(self, period=False):
        """Get either the total run duration or the period duration
        
        Parameters:
            period - whether to return the duration for the current period [optional]
        """
        if period:
            return self._get_pv_value(self._get_dae_pv_name("rundurationperiod"))
        else:
            return self._get_pv_value(self._get_dae_pv_name("runduration"))
            
    def get_num_timechannels(self):
        """Get the number of time channels"""
        return self._get_pv_value(self._get_dae_pv_name("numtimechannels"))
        
    def get_monitor_counts(self):
        """Get the number of monitor counts"""
        return self._get_pv_value(self._get_dae_pv_name("monitorcounts"))
        
    def get_monitor_spectrum(self):
        """Get the monitor spectrum"""
        return self._get_pv_value(self._get_dae_pv_name("monitorspectrum"))
        
    def get_monitor_to(self):
        """Get the monitor 'to' limit"""
        return self._get_pv_value(self._get_dae_pv_name("monitorto"))
        
    def get_monitor_from(self):
        """Get the monitor 'from' limit"""
        return self._get_pv_value(self._get_dae_pv_name("monitorfrom"))
        
    def get_beam_current(self):
        """Get the beam current"""
        return self._get_pv_value(self._get_dae_pv_name("beamcurrent"))
        
    def get_total_uamps(self):
        """Get the total microamp hours for the current run"""
        return self._get_pv_value(self._get_dae_pv_name("totaluamps"))
        
    def get_total_dae_counts(self):
        """Get the total DAE counts for the current run"""
        return self._get_pv_value(self._get_dae_pv_name("totaldaecounts"))
        
    def get_countrate(self):
        """Get the count rate"""
        return self._get_pv_value(self._get_dae_pv_name("countrate"))
        
    def get_eventmode_fraction(self):
        """Get the event mode fraction"""
        return self._get_pv_value(self._get_dae_pv_name("countrate"))
        
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
        """End a change operation.
        The operaton is begun when change_start is called.
        Between these two calls a sequence of other change commands can be called.
        For example: change_tables, change_tcb etc.
        """
        if self.in_change:
            self.in_change = False
            self._change_dae_settings()
            self._change_tcb_settings()
            self._change_period_settings()
            self.change_cache = ChangeCache()
            
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
        self.change_cache.set_monitor(spec, low, high)
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

    def _change_dae_settings(self):
        """Changes the DAE settings"""
        root = ET.fromstring(self._get_pv_value(self._get_dae_pv_name("daesettings"), to_string=True))
        changed = self.change_cache.change_dae_settings(root)
        if changed:
            self._set_pv_value(self._get_dae_pv_name("daesettings_sp"), ET.tostring(root), wait=True)
        
    def _change_tcb_settings(self):
        """Changes the TCB settings"""
        # TCB data comes as hex and zipped!
        value = self._get_pv_value(self._get_dae_pv_name("tcbsettings"), to_string=True)
        xml = self._dehex_decompress(value)
        # Strip off any zlib checksum stuff at end of the string
        last = xml.rfind('>') + 1        
        root = ET.fromstring(xml[0:last].strip())
        changed = self.change_cache.change_tcb_settings(root)
        if changed:
            ans = zlib.compress(ET.tostring(root))             
            self._set_pv_value(self._get_dae_pv_name("tcbsettings_sp"), ans.encode('hex'), wait=True)
            
    def _change_period_settings(self):
        """Changes the period settings"""
        root = ET.fromstring(self._get_pv_value(self._get_dae_pv_name("periodsettings"), to_string=True))
        changed = self.change_cache.change_period_settings(root)
        if changed:
            self._set_pv_value(self._get_dae_pv_name("periodsettings_sp"), ET.tostring(root).strip(), wait=True)

    def get_spectrum(self, spectrum, period=1, dist=False):
        """Get a spectrum from the DAE via a PV"""
        y_data = self._get_pv_value(self._get_dae_pv_name("getspectrum_y") % (period, spectrum))
        y_size = self._get_pv_value(self._get_dae_pv_name("getspectrum_y_size") % (period, spectrum))
        y_data = y_data[:y_size]
        x_data = self._get_pv_value(self._get_dae_pv_name("getspectrum_x") % (period, spectrum))
        x_size = self._get_pv_value(self._get_dae_pv_name("getspectrum_x_size") % (period, spectrum))
        x_data = x_data[:x_size]
        return {'time': x_data, 'signal': y_data, 'sum': None, 'mode': 'distribution'}

    def in_transition(self):
        transition = self._get_pv_value(self._get_dae_pv_name("statetrans"))
        if transition == "Yes":
            return True
        else:
            return False

    def get_wiring_tables(self):
        """Get a list of wiring table choices"""
        raw = self._dehex_decompress(self._get_pv_value(self._get_dae_pv_name("wiringtables"), to_string=True))
        return json.loads(raw)
        
    def get_spectra_tables(self):
        """Get a list of spectra table choices"""
        raw = self._dehex_decompress(self._get_pv_value(self._get_dae_pv_name("spectratables"), to_string=True))
        return json.loads(raw)
        
    def get_detector_tables(self):
        """Get a list of detector table choices"""
        raw = self._dehex_decompress(self._get_pv_value(self._get_dae_pv_name("detectortables"), to_string=True))
        return json.loads(raw)

    def get_period_files(self):
        """Get a list of period file choices"""
        raw = self._dehex_decompress(self._get_pv_value(self._get_dae_pv_name("periodfiles"), to_string=True))
        return json.loads(raw)