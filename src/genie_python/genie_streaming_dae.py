from __future__ import annotations

import json
import typing
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum, IntEnum
from time import strftime
from typing import TypedDict

import numpy.typing as npt

from genie_python.genie import PVValue
from genie_python.genie_epics_api import API
from genie_python.utilities import require_runstate, compress_and_hex


DAE_PVS_LOOKUP = {
    "pauserun": "KDAECTRL:PAUSERUN",
    "resumerun": "KDAECTRL:RESUMERUN",
    "endrun": "KDAECTRL:ENDRUN",
    "hwrunning": "KDAECTRL:HWRUNNING",
    "period": "KDAECTRL:PERIOD",
    "runnumber": "KDAECTRL:RUNNUMBER",
    "numperiods": "KDAECTRL:NUMPERIODS",
    "numberiods_sp": "KDAECTRL:NUMPERIODS:SP",
    "rbnum": "ED:RBNUMBER",
    "rbnum_sp": "ED:RBNUMBER:SP",
    "period_sp": "KDAECTRL:PERIOD:SP",
    "users_dae_sp": "ED:USERNAME:DAE:SP",
    "users_surname_sp": "ED:SURNAME",
    "timingsource": "KDAECTRL:DAETIMINGSOURCE",
    "timingsource_sp": "KDAECTRL:DAETIMINGSOURCE:SP",
    "periodtype": "KDAECTRL:PERIODTYPE",
    "periodtype_sp": "KDAECTRL:PERIODTYPE:SP"
}

class RunState(StrEnum):
    PROCESSING = "PROCESSING"
    SETUP = "SETUP"
    BEGINNING = "BEGINNING"
    RUNNING = "RUNNING"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    RESUMING = "RESUMING"
    WAITING = "WAITING"
    VETOING = "VETOING"
    ENDING = "ENDING"
    ABORTING = "ABORTING"

class VetoNames(StrEnum):
    CLEAR_VETO = "clearall"
    SMP_VETO = "smp"
    TS2_VETO = "ts2"
    HZ50_VETO = "hz50"
    EXT0_VETO = "ext0"
    EXT1_VETO = "ext1"
    EXT2_VETO = "ext2"
    EXT3_VETO = "ext3"
    FIFO_VETO = "fifo"

class PeriodType(StrEnum):
    COMPUTER = "COMPUTER"
    LOOK_UP_TABLE = "LOOK_UP_TABLE"
    NOT_USED = "NOT_USED"
    EXTERNAL = "EXTERNAL"


class PeriodMode(IntEnum):
    SOFT = 0
    INT = 1
    EXT = 2


class TimingSource(StrEnum):
    ISIS = "ISIS"
    INTERNAL_TEST_CLOCK = "INTERNAL_TEST_CLOCK"
    SMP = "SMP"
    UNKNOWN = "UNKNOWN"


class SpectrumMode(StrEnum):
    DISTRIBUTION = "distribution"
    NON_DISTRIBUTION = "non-distribution"


class StreamState(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


class FileWriterState(StrEnum):
    IDLE = "idle"
    WRITING = "writing"
    FINISHING = "finishing"
    ERROR = "error"


class Spectrum(TypedDict):
    time: npt.NDArray
    signal: npt.NDArray
    sum: float | None
    mode: SpectrumMode


@dataclass(frozen=True, slots=True)
class ComponentHealth:
    name: str
    state: StreamState
    last_message_time: datetime | None
    consumer_lag: int | None
    message: str | None


@dataclass(frozen=True, slots=True)
class BinningSpec:
    low: float
    high: float
    step: float
    logarithmic: bool = False


class StreamingDae:
    def __init__(
        self,
        api: "API",
        pv_prefix: str = "",
    ) -> None:
        """
        The constructor.

        Args:
            api(genie_python.genie_epics_api.API): the API used for communication
            pv_prefix: the PV prefix
        """
        self.api = api
        self.inst_prefix = pv_prefix
        self.verbose = False

    # ------------------------------------------------------------------
    # run control
    # ------------------------------------------------------------------

    def begin_run(
        self,
        period: int | None = None,
        meas_id: str | None = None,
        meas_type: str | None = None,
        meas_subid: str | None = None,
        sample_id: str | None = None,
        delayed: bool = False,
        quiet: bool = False,
        paused: bool = False,
        prepost: bool = True,
        start_time: datetime | None = None,
    ) -> None:
        ...

    def end_run(
        self,
        verbose: bool = False,
        quiet: bool = False,
        immediate: bool = False,
        prepost: bool = True,
    ) -> None:
        """
        End the current run.

        Args:
            verbose: whether to print verbosely
            quiet: suppress the output to the screen [optional]
            immediate: end immediately, without waiting for a period sequence to finish [optional]
            prepost: run pre and post commands [optional]
        """
        if self.get_run_state() == "ENDING" and not immediate:
            print("Please specify the 'immediate=True' flag to end a run while in the ENDING state")
            return

        run_number = self.get_run_number()
        if not quiet:
            print(("** Ending Run {} at {}".format(run_number, strftime("%H:%M:%S %d/%m/%y "))))

        self.api.logger.log_info_msg(f"END: run number: {run_number}")
        try:
            self.api.logger.log_info_msg(
                f"END: Proposal number: {self.get_rb_number()} Team: {self.get_users()}"
            )
        except Exception as e:
            self.api.logger.log_error_msg(f"END: Unable to read RB/Users from service: {e}")

        if immediate:
            ... # TODO

        self._set_pv_value(self._get_dae_pv_name("endrun", base=not prepost), 1, wait=True)
        if verbose or self.verbose:
            self._print_verbose_messages()

    def abort_run(self, prepost: bool = True) -> None:
        ...

    def pause_run(self, immediate: bool = False, prepost: bool = True) -> None:
        """
        Pause the current run.

        Args:
            immediate: pause immediately, without waiting for a period sequence to complete
            prepost: run pre and post commands
        """
        if self.get_run_state() == "PAUSING" and not immediate:
            print(
                "Please specify the 'immediate=True' flag to pause a run while in the PAUSING state"
            )
            return

        print(
            (
                "** Pausing Run {} at {}".format(
                    self.get_run_number(), strftime("%H:%M:%S %d/%m/%y ")
                )
            )
        )

        if immediate:
            ... # TODO

        self._set_pv_value(self._get_dae_pv_name("pauserun", base=not prepost), 1, wait=True)

    def resume_run(self, prepost: bool = True) -> None:
        """
        Resume the current run after it has been paused.
            prepost - run pre and post commands [optional]
        """
        print(
            (
                "** Resuming Run {} at {}".format(
                    self.get_run_number(), strftime("%H:%M:%S %d/%m/%y ")
                )
            )
        )
        self._set_pv_value(self._get_dae_pv_name("resumerun", base=not prepost), 1, wait=True)

    # ------------------------------------------------------------------
    # genie_python transition hooks
    # called unconditionally by genie.py; no-ops unless errors are
    # reported out-of-band rather than raised by the transition itself
    # ------------------------------------------------------------------

    def post_begin_check(self, verbose: bool = False) -> None:
        ...

    def post_end_check(self, verbose: bool = False) -> None:
        ...

    def post_abort_check(self, verbose: bool = False) -> None:
        ...

    def post_pause_check(self, verbose: bool = False) -> None:
        ...

    def post_resume_check(self, verbose: bool = False) -> None:
        ...

    def set_verbose(self, verbose: bool) -> None:
        ...

    # ------------------------------------------------------------------
    # state
    # ------------------------------------------------------------------

    def get_run_state(self) -> RunState:
        ...

    # ------------------------------------------------------------------
    # dae simulation mode control
    # ------------------------------------------------------------------

    @require_runstate([RunState.SETUP, RunState.PROCESSING])
    def set_simulation_mode(self, mode: bool) -> None:
        """
        Sets the DAE simulation mode by ...
        Args:
            mode (bool): True to simulate the DAE, False otherwise
        """
        ...

    def get_simulation_mode(self) -> bool:
        """
        Gets the DAE simulation mode.
        Returns:
            True if the DAE is in simulation mode, False otherwise.
        """
        ...

    # ------------------------------------------------------------------
    # run metadata
    # ------------------------------------------------------------------

    def get_run_number(self) -> str:
        """
        Gets the current run number.

        Returns:
            string: the current run number
        """
        return typing.cast(str, self._get_pv_value(self._get_dae_pv_name("runnumber")))

    def get_title(self) -> str:
        ...

    def set_title(self, title: str) -> None:
        ...

    def get_display_title(self) -> bool:
        ...

    def set_display_title(self, display_title: bool) -> None:
        ...

    def get_users(self) -> str:
        """
        Gets the users for the current run.

        Returns:
            string: the names

        Raises:
            ValueError: if the user list is empty
        """
        # Data comes as comma separated list
        raw = str(self._get_pv_value(self._get_dae_pv_name("users_dae_sp"), to_string=True))
        names_list = [x.strip() for x in raw.split(",")]
        if len(names_list) > 1:
            last = names_list.pop(-1)
            names = ", ".join(names_list)
            names += " and " + last
            return names
        elif len(names_list) == 1:
            return names_list[0]
        else:
            raise ValueError("User list is empty.")

    def set_users(self, users: str) -> None:
        """
        Set the users for the current run.

        Args:
            users: the users as a comma-separated string
        """
        split_users = users.split(",") if users else []
        table_data = json.dumps([{"name": user.strip()} for user in split_users])
        # Send just the username and database server will clear the table if only user is set
        self._set_pv_value(
            self._get_dae_pv_name("users_table_sp"), compress_and_hex(table_data), True
        )
        self.api.logger.log_info_msg(f"Users set to: {users}")

    def get_rb_number(self) -> str:
        """
        Gets the RB number for the current run.

        Returns:
            string: the current RB number
        """
        return typing.cast(str, self._get_pv_value(self._get_dae_pv_name("rbnum")))

    def set_rb_number(self, rbno: str) -> None:
        """
        Set the RB number for the current run.

        Args:
            rbno (str): the new RB number
        """
        self._set_pv_value(self._get_dae_pv_name("rbnum_sp"), rbno)
        self.api.logger.log_info_msg(f"Proposal number changed to: {rbno}")

    def get_time_since_begin(self, as_timedelta: bool = False) -> float | timedelta:
        ...

    def get_run_duration(self, period: bool = False) -> int:
        ...

    # ------------------------------------------------------------------
    # counters
    # ------------------------------------------------------------------

    def get_good_frames(self, period: bool = False) -> int:
        ...

    def get_raw_frames(self, period: bool = False) -> int:
        ...

    def get_uamps(self, period: bool = False, total: bool = False) -> float:
        ...

    def get_events(self, period: bool = False) -> int:
        ...

    def get_total_counts(self) -> int:
        ...

    def get_beam_current(self) -> float:
        ...

    # ------------------------------------------------------------------
    # periods
    # ------------------------------------------------------------------

    def get_period(self) -> int:
        """
        Gets the current period number.

        Returns:
            int: the current period
        """
        return typing.cast(int, self._get_pv_value(self._get_dae_pv_name("period")))

    def set_period(self, period: int) -> None:
        """
        Change to the specified period.

        Args:
            period: the number of the period to change to

        Raises:
            IOError: if the DAE can not set the period to the given number.
            ValueError: if currently in a run.
        """
        run_state = self.get_run_state()
        if run_state == "SETUP" or run_state == "PAUSED":
            self._set_pv_value(self._get_dae_pv_name("period_sp"), period, wait=True)

            if self.api.get_pv_alarm(self._get_dae_pv_name("period_sp")) == "INVALID":
                raise IOError(
                    f"You are trying to set an invalid period number {period}! "
                    f"The number must be between 1 and {self.get_num_periods()}."
                )
        else:
            raise ValueError("Cannot change period whilst running")

    def get_num_periods(self) -> int:
        """
        Gets the number of periods.

        Returns:
            int: the number of periods
        """
        return typing.cast(int, self._get_pv_value(self._get_dae_pv_name("numperiods")))


    def get_period_type(self) -> str:
        """
        Gets the period type.

        Returns:
            string: the period type
        """
        return PeriodType(self._get_pv_value(self._get_dae_pv_name("periodtype")))


    def set_num_soft_periods(self, number: int) -> None:
        """
        Sets the number of software periods for the DAE.

        Args:
            number: the number of periods to create

        Raises:
            ValueError: if wrongly typed value supplied
            ValueError: if PERIODTYPE is not COMPUTER
        """
        if (not isinstance(number, float) and not isinstance(number, int)) or number < 1:
            raise ValueError("Number of soft periods must be a numeric value greater than 0.")

        if self.get_period_type() != PeriodType.COMPUTER:
            raise ValueError("Setting number of soft periods is only meaningful when PERIODTYPE=COMPUTER")

        self._set_pv_value(self._get_dae_pv_name("numberiods_sp"), number, wait=True)


    def set_period_mode(self, mode: int) -> None:
        """
        Sets the period mode for the DAE.

        Args:
            mode: the mode to switch to ('soft', 'int', 'ext')
        """

        if mode == PeriodMode.SOFT:
            self._set_pv_value(self._get_dae_pv_name("periodtype_sp"), 0, wait=True)
        else:
            self.configure_hard_periods(str(mode))

    def configure_hard_periods(
        self,
        mode: str,
        period_file: str | None = None,
        sequences: int | None = None,
        output_delay: int | None = None,
        period: int | None = None,
        daq: bool = False,
        dwell: bool = False,
        unused: bool = False,
        frames: int | None = None,
        output: int | None = None,
        label: str | None = None,
    ):
        ...

    # ------------------------------------------------------------------
    # vetoes
    # ------------------------------------------------------------------

    def change_vetos(self, **params: bool) -> None:
        """
        Change the DAE veto settings.

        Args:
            clearall: remove all vetoes [optional]
            smp: set SMP veto [optional]
            ts2: set TS2 veto [optional]
            hz50: set 50 hz veto [optional]
            ext0: set external veto 0 [optional]
            ext1: set external veto 1 [optional]
            ext2: set external veto 2 [optional]
            ext3: set external veto 3 [optional]

        If clearall is specified then all vetoes are turned off,
        but it is possible to turn other vetoes back on at the same time.

        Example:
            Turns all vetoes off then turns the SMP veto back on
            >>> self.change_vetos(clearall=True, smp=True)
        """

        # Change keys to be case-insensitive
        params = dict((k.lower(), v) for k, v in params.items())

        # Check for invalid veto names and invalid (non-boolean) values
        not_bool = []
        for k, v in params.items():
            if k not in VetoNames:
                raise Exception("Invalid veto name: {}".format(k))
            if not isinstance(v, bool):
                not_bool.append(k)
        if len(not_bool) > 0:
            raise Exception(
                "Vetoes must be set to True or False, "
                "the following vetoes were incorrect: {}".format(" ".join(not_bool))
            )

        # TODO figure out how to send veto array
        ...

    def get_veto_names(self) -> Sequence[str]:
        ... # VETO:NAMES

    def get_hard_vetoes(self) -> Mapping[str, bool]:
        ... # VETO:HARD

    # ------------------------------------------------------------------
    # timing and detector configuration
    # ------------------------------------------------------------------

    def get_timing_source(self, timing_source: str):
        """
        Gets the DAE timing source.

        Returns:
            string: the current timing source being used
        """
        return TimingSource(self._get_pv_value(self._get_dae_pv_name("timingsource")))

    def set_timing_source(self, source: TimingSource) -> None:
        """
        Sets the DAE timing source.

        Args:
            source: The current timing source to be used
        """
        self._set_pv_value(self._get_dae_pv_name("timingsource_sp"), source, wait=True)

    def get_num_spectra(self) -> int:
        ...

    def get_monitor_spectrum(self) -> int:
        ...

    def get_monitor_counts(self) -> int:
        ...

    def change_monitor(self, spec: int, low: float, high: float) -> None:
        """
        Change the monitor to a specified spectrum and range.

        Args:
            spec: the spectrum number (integer)
            low: the low end of the integral (float)
            high: the high end of the integral (float)

        Raises:
            TypeError: if a value supplied is not correctly typed
        """
        ...

    # ------------------------------------------------------------------
    # data
    # ------------------------------------------------------------------

    def get_spectrum(
        self,
        spectrum: int,
        period: int = 1,
        dist: bool = True,
    ) -> Spectrum:
        ...

    def integrate_spectrum(
        self,
        spectrum: int,
        period: int = 1,
        t_min: float | None = None,
        t_max: float | None = None,
    ) -> float | None:
        ...

    # ------------------------------------------------------------------
    # kafka topology and stream health
    # ------------------------------------------------------------------

    def get_broker_address(self) -> str:
        ...

    def get_topics(self) -> Mapping[str, str]:
        ...

    def get_component_health(self) -> Mapping[str, ComponentHealth]:
        ...

    # ------------------------------------------------------------------
    # hardware access
    # ------------------------------------------------------------------

    def is_hardware_running(self) -> bool:
        return typing.cast(bool, self._get_pv_value(self._get_dae_pv_name("hwrunning")))

    # ------------------------------------------------------------------
    # legacy ISISICP surface
    # present so genie_python call sites fail with a clear message
    # rather than AttributeError; intended to raise NotImplementedError
    # ------------------------------------------------------------------

    def update_run(self) -> None:
        raise NotImplementedError()

    def store_run(self) -> None:
        raise NotImplementedError()

    def update_store_run(self) -> None:
        raise NotImplementedError()

    def post_update_check(self, verbose: bool = False) -> None:
        raise NotImplementedError()

    def post_store_check(self, verbose: bool = False) -> None:
        raise NotImplementedError()

    def post_update_store_check(self, verbose: bool = False) -> None:
        raise NotImplementedError()

    def snapshot_crpt(self, filename: str) -> None:
        raise NotImplementedError()

    def post_snapshot_check(self, verbose: bool = False) -> None:
        raise NotImplementedError()

    def recover_run(self) -> None:
        raise NotImplementedError()

    def post_recover_check(self, verbose: bool = False) -> None:
        raise NotImplementedError()

    def get_autosave_freq(self) -> int | None:
        raise NotImplementedError()

    def set_autosave_freq(self, freq: int) -> None:
        raise NotImplementedError()

    # ------------------------------------------------------------------
    # internal methods
    # ------------------------------------------------------------------

    def _set_pv_value(self, name: str, value: "PVValue", wait: bool = False) -> None:
        """
        Sets a PV value via the API.

        Args:
            name: the PV name
            value: the value to set
            wait: whether to wait for it to be set before returning
        """
        self.api.set_pv_value(name, value, wait)

    def _get_pv_value(
            self, name: str, to_string: bool = False, use_numpy: bool | None = None
    ) -> "PVValue":
        """
        Gets a PV's value.

        Args:
            name: the PV name
            to_string: whether to convert the value to a string
            use_numpy (None|boolean): True use numpy to return arrays, False return a list;
                                      None for use the default

        Returns:
            object: the PV's value
        """
        return self.api.get_pv_value(name, to_string, use_numpy=use_numpy)

    def _get_dae_pv_name(self, name: str, base: bool = False) -> str:
        """
        Retrieves the full pv name of a DAE variable.

        Args:
            name: the short name for the DAE variable
            base: return the underlying action PV name

        Returns:
            string: the full PV name
        """
        if base:
            return self._prefix_pv_name(DAE_PVS_LOOKUP[name.lower()]) + "_"
        else:
            return self._prefix_pv_name(DAE_PVS_LOOKUP[name.lower()])

    def _print_verbose_messages(self) -> None:
        """
        Prints all the messages.
        """
        ...

    def _prefix_pv_name(self, name: str) -> str:
        """
        Adds the prefix to the PV name.

        Args:
            name: the name to be prefixed

        Returns:
            string: the full PV name
        """
        if self.inst_prefix is not None:
            name = self.inst_prefix + name
        return name
