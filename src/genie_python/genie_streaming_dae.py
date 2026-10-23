from __future__ import annotations

import json
import typing
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import IntEnum, StrEnum
from time import strftime
from typing import TYPE_CHECKING, NoReturn, TypedDict

import numpy.typing as npt

from genie_python.utilities import compress_and_hex, require_runstate

if TYPE_CHECKING:
    from genie_python.genie import PVValue, _GetspectrumReturn
    from genie_python.genie_epics_api import API


# Names of the components that must exist before the corresponding
# methods below can be implemented.
_DIAGNOSTICS = "kafka_dae_diagnostics"
_FILEWRITER = "the NeXus filewriter job controller"
_UDP_TO_KAFKA = "event_udp_to_kafka"


DAE_PVS_LOOKUP = {
    # --- kafka_dae_control -------------------------------------------------
    "beginrun": "KDAECTRL:BEGINRUNEX",
    "endrun": "KDAECTRL:ENDRUN",
    "pauserun": "KDAECTRL:PAUSERUN",
    "resumerun": "KDAECTRL:RESUMERUN",
    "hwrunning": "KDAECTRL:HWRUNNING",
    "runnumber": "KDAECTRL:RUNNUMBER",
    "irunnumber": "KDAECTRL:IRUNNUMBER",
    "period": "KDAECTRL:PERIOD",
    "period_sp": "KDAECTRL:PERIOD:SP",
    "numperiods": "KDAECTRL:NUMPERIODS",
    "numperiods_max": "KDAECTRL:NUMPERIODS:MAX",
    "numperiods_sp": "KDAECTRL:NUMPERIODS:SP",
    "periodtype": "KDAECTRL:PERIODTYPE",
    "periodtype_sp": "KDAECTRL:PERIODTYPE:SP",
    "timingsource": "KDAECTRL:DAETIMINGSOURCE",
    "timingsource_sp": "KDAECTRL:DAETIMINGSOURCE:SP",
    "veto_names": "KDAECTRL:VETO:NAMES",
    "veto_sp": "KDAECTRL:VETO:SP",
    "veto_hard": "KDAECTRL:VETO:HARD",
    # --- experiment details -------------------------------------------------
    "rbnum": "ED:RBNUMBER",
    "rbnum_sp": "ED:RBNUMBER:SP",
    "users_surname": "ED:SURNAME",
    "users_table_sp": "ED:USERNAME:SP",
    "users_dae_sp": "ED:USERNAME:DAE:SP",
}


# Name of the veto used internally to implement pause, as it appears in
# VETO:NAMES. VETO:NAMES is populated from the IOC config file, so this
# must match that config. If it does not appear, PAUSED cannot be
# distinguished from RUNNING, and resume_run() will be unusable.
PAUSE_VETO_NAME = "pause"

LEGACY_STARTTIME_FORMAT = "%a %d-%b-%Y %H:%M:%S"


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


class PeriodType(StrEnum):
    """Mirrors the PERIODTYPE PV. Numeric values are 0-3 in declaration order."""

    COMPUTER = "COMPUTER"
    LOOK_UP_TABLE = "LOOK_UP_TABLE"
    NOT_USED = "NOT_USED"
    EXTERNAL = "EXTERNAL"


class TimingSource(StrEnum):
    ISIS = "ISIS"
    INTERNAL_TEST_CLOCK = "INTERNAL_TEST_CLOCK"
    SMP = "SMP"
    UNKNOWN = "UNKNOWN"


class VetoLevel(IntEnum):
    """Values written to the VETO:SP array."""

    DISABLED = 0
    SOFT = 1
    HARD = 2


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
class Veto:
    name: str
    index: int
    level: VetoLevel
    applied_in_hardware: bool


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


def _unavailable(component: str, what: str) -> NoReturn:
    raise NotImplementedError(f"{what} is not available yet; it requires {component}.")


def _removed(what: str, reason: str) -> NoReturn:
    raise NotImplementedError(f"{what} does not exist on the streaming DAE: {reason}")


class StreamingDae:
    """
    Communications with the streaming DAE PVs.
    """

    def __init__(self, api: API, prefix: str = "") -> None:
        """
        The constructor.

        Args:
            api(genie_python.genie_epics_api.API): the API used for communication
            prefix: the PV prefix
        """
        self.api = api
        self.inst_prefix = prefix
        self.verbose = False

        self._begin_time: datetime | None = None  # TODO link this to START_TIME PV

    # ------------------------------------------------------------------
    # run control
    # ------------------------------------------------------------------

    @require_runstate([RunState.SETUP])
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
    ) -> None:
        """
        Starts a data collection run.

        Args:
            period: the period to begin data collection in [optional]
            meas_id: the measurement id [optional]
            meas_type: the type of measurement [optional]
            meas_subid: the measurement sub-id [optional]
            sample_id: the sample id [optional]
            delayed: puts the period card into delayed start mode [optional]
            quiet: suppress the output to the screen [optional]
            paused: begin in the paused state [optional]
            prepost: run pre- and post-commands [optional]

        Raises:
            NotImplementedError: if delayed or paused is requested
        """
        self._check_prepost_supported(prepost)

        if delayed:
            # The legacy DAE encoded this as bit 1 of the value written to
            # BEGINRUNEX. The new PV only accepts 1.
            raise NotImplementedError("delayed start is not supported by the streaming DAE yet")
        if paused:
            # Could be emulated as begin-then-pause, but that leaves a short
            # window of unpaused acquisition.
            raise NotImplementedError("beginning in the paused state is not supported yet")

        sample_pars = {
            "MEAS:ID": meas_id,
            "MEAS:TYPE": meas_type,
            "MEAS:SUBID": meas_subid,
            "ID": sample_id,
        }
        for pv, value in sample_pars.items():
            if value is not None:
                self.api.set_sample_par(pv, str(value))

        if period is not None:
            self.set_period(period)

        run_number = self.get_run_number()
        if not quiet:
            if self.get_timing_source() == TimingSource.INTERNAL_TEST_CLOCK:
                self._test_clock_warning()
            print("** Beginning Run {} at {}".format(run_number, strftime("%H:%M:%S %d/%m/%y ")))
            # Do not fail begin() if we are unable to print RB/user details.
            try:
                print(
                    "The following details will currently be used to determine "
                    "ownership of the data file"
                )
                print(f"*  Proposal Number: {self.get_rb_number()}")
                print(f"*  Experiment Team: {self.get_users()}")
                print("If this is incorrect, you can change it any time before the run is ENDed\n")
            except Exception as e:
                print(f"WARNING: Unable to read RB/Users from service: {e}")

        self.api.logger.log_info_msg(f"BEGIN: run number: {run_number}")
        try:
            self.api.logger.log_info_msg(
                f"BEGIN: Proposal number: {self.get_rb_number()} Team: {self.get_users()}"
            )
        except Exception as e:
            self.api.logger.log_error_msg(f"BEGIN: Unable to read RB/Users from service: {e}")

        # The IOC errors the put if either the hardware start or the pl72
        # run start message fails, so no separate error monitor is needed.
        self._begin_time = datetime.now()
        self._set_pv_value(self._get_dae_pv_name("beginrun"), 1, wait=True)

    @require_runstate([RunState.RUNNING, RunState.PAUSED])
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
            prepost: run pre- and post-commands [optional]
        """
        self._check_prepost_supported(prepost)
        if immediate:
            # TODO link this to STOP_TIME PV
            raise NotImplementedError("immediate end is not supported by the streaming DAE yet")

        run_number = self.get_run_number()
        if not quiet:
            print("** Ending Run {} at {}".format(run_number, strftime("%H:%M:%S %d/%m/%y ")))

        self.api.logger.log_info_msg(f"END: run number: {run_number}")
        try:
            self.api.logger.log_info_msg(
                f"END: Proposal number: {self.get_rb_number()} Team: {self.get_users()}"
            )
        except Exception as e:
            self.api.logger.log_error_msg(f"END: Unable to read RB/Users from service: {e}")

        self._set_pv_value(self._get_dae_pv_name("endrun"), 1, wait=True)
        self._begin_time = None

        if verbose or self.verbose:
            self._print_verbose_messages()

    def abort_run(self, prepost: bool = True) -> None:
        """
        Abort the current run.

        Args:
            prepost: run pre- and post-commands [optional]
        """
        _unavailable(_FILEWRITER, "abort_run")

    @require_runstate([RunState.RUNNING])
    def pause_run(self, immediate: bool = False, prepost: bool = True) -> None:
        """
        Pause the current run.

        Args:
            immediate: pause immediately, without waiting for a period sequence to complete
            prepost: run pre- and post-commands
        """
        self._check_prepost_supported(prepost)
        if immediate:
            raise NotImplementedError("immediate pause is not supported by the streaming DAE yet")

        print(
            "** Pausing Run {} at {}".format(self.get_run_number(), strftime("%H:%M:%S %d/%m/%y "))
        )
        self._set_pv_value(self._get_dae_pv_name("pauserun"), 1, wait=True)

    @require_runstate([RunState.PAUSED])
    def resume_run(self, prepost: bool = True) -> None:
        """
        Resume the current run after it has been paused.

        Args:
            prepost: run pre- and post-commands [optional]
        """
        self._check_prepost_supported(prepost)
        print(
            "** Resuming Run {} at {}".format(self.get_run_number(), strftime("%H:%M:%S %d/%m/%y "))
        )
        self._set_pv_value(self._get_dae_pv_name("resumerun"), 1, wait=True)

    # ------------------------------------------------------------------
    # genie_python transition hooks
    #
    # The IOC errors the put itself when a transition fails, so there is
    # nothing to check out-of-band. These remain as no-ops because genie.py
    # calls them unconditionally after every transition.
    # ------------------------------------------------------------------

    def post_begin_check(self, verbose: bool = False) -> None:
        pass

    def post_end_check(self, verbose: bool = False) -> None:
        pass

    def post_abort_check(self, verbose: bool = False) -> None:
        pass

    def post_pause_check(self, verbose: bool = False) -> None:
        pass

    def post_resume_check(self, verbose: bool = False) -> None:
        pass

    def set_verbose(self, verbose: bool) -> None:
        """
        Sets the verbosity of the DAE messages printed.

        Args:
            verbose: bool setting

        Raises:
            TypeError: if the supplied value is not a bool
        """
        if not isinstance(verbose, bool):
            raise TypeError("Value must be boolean")
        self.verbose = verbose
        print("Setting DAE messages to {} mode".format("verbose" if verbose else "non-verbose"))

    # ------------------------------------------------------------------
    # state
    # ------------------------------------------------------------------

    def get_run_state(self) -> str:
        """
        Gets the current state of the DAE.

        TODO Only SETUP, RUNNING and PAUSED can be distinguished at present.
        TODO The transitional states (BEGINNING, ENDING, ...) and VETOING/WAITING
        TODO require kafka_dae_diagnostics.

        Returns:
            RunState: the current run state
        """
        if not self.is_hardware_running():
            return RunState.SETUP
        if self._is_paused():
            return RunState.PAUSED
        return RunState.RUNNING

    def in_transition(self) -> bool:
        """
        Checks whether the DAE is in transition.

        Every setting on the streaming DAE is an individual atomic put, so
        there is no multistep transition to observe.

        Returns:
            bool: always False
        """
        return False

    def is_changing(self) -> bool:
        """
        Gets whether the DAE is in state changing mode.

        Returns:
            bool: always False, see in_transition()
        """
        return False

    def is_hardware_running(self) -> bool:
        """
        Gets whether the streaming hardware is acquiring.

        Returns:
            bool: True if the run status register reports running
        """
        return bool(self._get_pv_value(self._get_dae_pv_name("hwrunning")))

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
        _unavailable(_DIAGNOSTICS, "get_title")

    def set_title(self, title: str) -> None:
        _unavailable(_DIAGNOSTICS, "set_title")

    def get_display_title(self) -> bool:
        _unavailable(_DIAGNOSTICS, "get_display_title")

    def set_display_title(self, display_title: bool) -> None:
        _unavailable(_DIAGNOSTICS, "set_display_title")

    def get_users(self) -> str:
        """
        Gets the users for the current run.

        Returns:
            string: the names, or an empty string if none are set
        """
        raw = str(self._get_pv_value(self._get_dae_pv_name("users_dae_sp"), to_string=True) or "")
        names_list = [x.strip() for x in raw.split(",") if x.strip()]
        if not names_list:
            return ""
        if len(names_list) == 1:
            return names_list[0]
        return "{} and {}".format(", ".join(names_list[:-1]), names_list[-1])

    def set_users(self, users: str) -> None:
        """
        Set the users for the current run.

        Args:
            users: the users as a comma-separated string
        """
        split_users = users.split(",") if users else []
        table_data = json.dumps([{"name": user.strip()} for user in split_users])
        # Send just the username; the database server clears the table if only
        # the user is set.
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
            rbno: the new RB number
        """
        self._set_pv_value(self._get_dae_pv_name("rbnum_sp"), rbno)
        self.api.logger.log_info_msg(f"Proposal number changed to: {rbno}")

    def get_starttime(self) -> str:
        """
        Gets the start time for the current run.

        There is no start-time PV, so this reports the time at which
        begin_run() was called in this session. It is unavailable if the run
        was begun elsewhere.

        Returns:
            string: the start time

        Raises:
            RuntimeError: if the run was not begun from this session
        """
        if self._begin_time is None:
            raise RuntimeError(
                "Run start time is unknown; the run was not begun from this session. "
                f"A start-time readback requires {_DIAGNOSTICS}."
            )
        return self._begin_time.strftime(LEGACY_STARTTIME_FORMAT)

    @require_runstate([RunState.RUNNING, RunState.PAUSED])
    def get_time_since_begin(self, get_timedelta: bool) -> float | timedelta:
        """
        Gets the time since the start of the current run.

        Args:
            get_timedelta: if True return a timedelta, otherwise return seconds

        Returns:
            float | timedelta: the time since the run started
        """
        time_since_start = datetime.now() - datetime.strptime(
            self.get_starttime(), LEGACY_STARTTIME_FORMAT
        )
        return time_since_start if get_timedelta else time_since_start.total_seconds()

    def get_run_duration(self, period: bool = False) -> int:
        _unavailable(_DIAGNOSTICS, "get_run_duration")

    # ------------------------------------------------------------------
    # counters
    # ------------------------------------------------------------------

    def get_good_frames(self, period: bool = False) -> int:
        _unavailable(_DIAGNOSTICS, "get_good_frames")

    def get_raw_frames(self, period: bool = False) -> int:
        _unavailable(_DIAGNOSTICS, "get_raw_frames")

    def get_uamps(self, period: bool = False) -> float:
        _unavailable(_DIAGNOSTICS, "get_uamps")

    def get_total_uamps(self) -> float:
        _unavailable(_DIAGNOSTICS, "get_total_uamps")

    def get_events(self) -> int:
        _unavailable(_DIAGNOSTICS, "get_events")

    def get_mevents(self) -> float:
        # Needed by g.waitfor(mevents=...).
        _unavailable(_DIAGNOSTICS, "get_mevents")

    def get_total_counts(self) -> int:
        _unavailable(_DIAGNOSTICS, "get_total_counts")

    def get_total_dae_counts(self) -> int:
        _unavailable(_DIAGNOSTICS, "get_total_dae_counts")

    def get_countrate(self) -> float:
        _unavailable(_DIAGNOSTICS, "get_countrate")

    def get_beam_current(self) -> float:
        _unavailable(_DIAGNOSTICS, "get_beam_current")

    def get_npratio(self) -> float:
        _unavailable(_DIAGNOSTICS, "get_npratio")

    def sum_all_spectra(self) -> int:
        _unavailable(_DIAGNOSTICS, "sum_all_spectra")

    def get_eventmode_fraction(self) -> float:
        _removed(
            "get_eventmode_fraction",
            "the streaming DAE is event mode only, so this would always be 1.0.",
        )

    # ------------------------------------------------------------------
    # periods
    # ------------------------------------------------------------------

    def get_period(self) -> int:
        """
        Gets the current period number.

        Returns:
            int: the current period, 1-indexed
        """
        return typing.cast(int, self._get_pv_value(self._get_dae_pv_name("period")))

    def set_period(self, period: int) -> None:
        """
        Change to the specified period.

        Args:
            period: the number of the period to change to

        Raises:
            OSError: if the DAE cannot set the period to the given number
            ValueError: if currently in a run
        """
        if self.get_run_state() not in (RunState.SETUP, RunState.PAUSED):
            raise ValueError("Cannot change period whilst running")

        self._set_pv_value(self._get_dae_pv_name("period_sp"), period, wait=True)
        if self.api.get_pv_alarm(self._get_dae_pv_name("period_sp")) == "INVALID":
            raise OSError(
                f"You are trying to set an invalid period number {period}! "
                f"The number must be between 1 and {self.get_num_periods()}."
            )

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
            PeriodType: the period type
        """
        return PeriodType(self._get_pv_value(self._get_dae_pv_name("periodtype"), to_string=True))

    def set_period_mode(self, mode: str) -> None:
        """
        Sets the period mode for the DAE.

        Args:
            mode: the mode to switch to

        Raises:
            ValueError: if the mode is not a valid PeriodType
        """
        mode = PeriodType(mode)
        self._set_pv_value(self._get_dae_pv_name("periodtype_sp"), str(mode), wait=True)

    def set_num_soft_periods(self, number: int) -> None:
        """
        Sets the number of software periods for the DAE.

        Args:
            number: the number of periods to create

        Raises:
            ValueError: if a wrongly typed value is supplied, or if the
                        period type is not COMPUTER
        """
        if not isinstance(number, (int, float)) or isinstance(number, bool) or number < 1:
            raise ValueError("Number of soft periods must be a numeric value greater than 0.")
        if self.get_period_type() != PeriodType.COMPUTER:
            raise ValueError(
                "Setting the number of soft periods is only meaningful when PERIODTYPE=COMPUTER"
            )
        self._set_pv_value(self._get_dae_pv_name("numperiods_sp"), int(number), wait=True)

    def get_period_seq(self) -> int:
        _unavailable(_DIAGNOSTICS, "get_period_seq")

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
    ) -> None:
        # LOOK_UP_TABLE mode exists on the hardware, but there is no PV to
        # populate the table.
        _unavailable("a hardware period table PV", "configure_hard_periods")

    def configure_internal_periods(
        self,
        sequences: int | None = None,
        output_delay: int | None = None,
        period: int | None = None,
        daq: bool = False,
        dwell: bool = False,
        unused: bool = False,
        frames: int | None = None,
        output: int | None = None,
        label: str | None = None,
    ) -> None:
        _unavailable("a hardware period table PV", "configure_internal_periods")

    def define_hard_period(
        self,
        period: int | None = None,
        daq: bool = False,
        dwell: bool = False,
        unused: bool = False,
        frames: int | None = None,
        output: int | None = None,
        label: str | None = None,
    ) -> None:
        _unavailable("a hardware period table PV", "define_hard_period")

    # ------------------------------------------------------------------
    # vetoes
    # ------------------------------------------------------------------

    def get_veto_names(self) -> Sequence[str]:
        """
        Gets the veto names, in bit-mask order.

        These are fixed at IOC startup from its configuration file.

        Returns:
            Sequence[str]: the veto names
        """
        raw = self._get_pv_value(self._get_dae_pv_name("veto_names"), to_string=True)
        if raw is None:
            return []
        if isinstance(raw, str):
            return [name.strip() for name in raw.split(",") if name.strip()]
        elif isinstance(raw, list):
            return [str(name).strip() for name in raw]

        raise ValueError("Veto names was not supplied in a format that is supported.")

    def get_hard_vetoes(self) -> Mapping[str, bool]:
        """
        Gets the vetoes currently applied on the streaming control board.

        Returns:
            Mapping[str, bool]: whether each veto is set in hardware
        """
        return {name: veto.applied_in_hardware for name, veto in self._get_vetoes().items()}

    def set_vetoes(self, vetoes: Mapping[str, VetoLevel | int]) -> None:
        """
        Sets the veto configuration.

        Only the named vetoes are modified; the rest keep their current level.

        Args:
            vetoes: the veto levels to apply, keyed by name

        Raises:
            ValueError: if a veto name is not present in VETO:NAMES
        """
        names = self.get_veto_names()
        levels = list(self._get_veto_levels())
        levels.extend([VetoLevel.DISABLED] * (len(names) - len(levels)))

        for name, level in vetoes.items():
            if name not in names:
                raise ValueError(f"Invalid veto name: {name}. Valid names are: {', '.join(names)}")
            levels[names.index(name)] = int(VetoLevel(level))

        self._set_pv_value(self._get_dae_pv_name("veto_sp"), levels, wait=True)
        self.api.logger.log_info_msg(f"Vetoes set to: {dict(zip(names, levels))}")

    def clear_vetoes(self) -> None:
        """
        Disables all vetoes.
        """
        self.set_vetoes({name: VetoLevel.DISABLED for name in self.get_veto_names()})

    def change_vetos(self, **params: bool) -> None:
        """
        Change the DAE veto settings.

        Valid keyword names are whatever VETO:NAMES reports for this
        instrument, plus 'clearall'. Boolean values map to HARD or DISABLED;
        use set_vetoes() for soft vetoes.

        Args:
            clearall: remove all vetoes [optional]
            **params: veto name to boolean

        Raises:
            ValueError: if a veto name is unknown or a value is not a bool

        Example:
            Turns all vetoes off then turns the SMP veto back on
            >>> self.change_vetos(clearall=True, smp=True)
        """
        params = {k.lower(): v for k, v in params.items()}

        valid_names = [name.lower() for name in self.get_veto_names()]
        unknown = [k for k in params if k != "clearall" and k not in valid_names]
        if unknown:
            raise ValueError(
                "Invalid veto name(s): {}. Valid names are: {}".format(
                    ", ".join(unknown), ", ".join(valid_names)
                )
            )

        not_bool = [k for k, v in params.items() if not isinstance(v, bool)]
        if not_bool:
            raise ValueError(
                "Vetoes must be set to True or False, "
                "the following vetoes were incorrect: {}".format(" ".join(not_bool))
            )

        # clearall is applied first so other keywords can re-enable vetoes.
        if params.pop("clearall", False):
            self.clear_vetoes()

        if params:
            name_lookup = {name.lower(): name for name in self.get_veto_names()}
            self.set_vetoes(
                {
                    name_lookup[k]: VetoLevel.HARD if v else VetoLevel.DISABLED
                    for k, v in params.items()
                }
            )

    def set_fermi_veto(
        self, enable: bool | None = None, delay: float = 1.0, width: float = 1.0
    ) -> None:
        # The fermi chopper veto was a dedicated ISISICP setting with its own
        # delay/width. If it survives, it should appear in VETO:NAMES and be
        # set through set_vetoes(), but delay/width have no home yet.
        _unavailable("a fermi chopper veto timing PV", "set_fermi_veto")

    # ------------------------------------------------------------------
    # timing and detector configuration
    # ------------------------------------------------------------------

    def get_timing_source(self) -> str:
        """
        Gets the DAE timing source.

        Returns:
            TimingSource: the current timing source being used
        """
        return TimingSource(
            self._get_pv_value(self._get_dae_pv_name("timingsource"), to_string=True)
        )

    def set_timing_source(self, source: TimingSource | str) -> None:
        """
        Sets the DAE timing source.

        Args:
            source: the timing source to use

        Raises:
            ValueError: if the source is not a valid TimingSource
        """
        source = TimingSource(source)
        if source == TimingSource.UNKNOWN:
            raise ValueError("UNKNOWN is a readback-only timing source and cannot be set")
        self._set_pv_value(self._get_dae_pv_name("timingsource_sp"), str(source), wait=True)

    def change_sync(self, source: str) -> None:
        """
        Change the source the DAE uses for synchronisation.

        Retained for compatibility with g.change_sync(); prefer
        set_timing_source().

        Args:
            source: 'isis', 'internal' or 'smp'

        Raises:
            ValueError: if an invalid source is entered
        """
        legacy_lookup = {
            "isis": TimingSource.ISIS,
            "internal": TimingSource.INTERNAL_TEST_CLOCK,
            "smp": TimingSource.SMP,
        }
        key = source.strip().lower()
        if key not in legacy_lookup:
            raise ValueError(
                "Invalid timing source entered. The streaming DAE supports: {}".format(
                    ", ".join(legacy_lookup)
                )
            )
        self.set_timing_source(legacy_lookup[key])

    def get_num_spectra(self) -> int:
        _unavailable(_DIAGNOSTICS, "get_num_spectra")

    def get_monitor_spectrum(self) -> int:
        _unavailable(_DIAGNOSTICS, "get_monitor_spectrum")

    def get_monitor_counts(self) -> int:
        _unavailable(_DIAGNOSTICS, "get_monitor_counts")

    def get_monitor_from(self) -> float:
        _unavailable(_DIAGNOSTICS, "get_monitor_from")

    def get_monitor_to(self) -> float:
        _unavailable(_DIAGNOSTICS, "get_monitor_to")

    def change_monitor(self, spec: int, low: float, high: float) -> None:
        _unavailable(_DIAGNOSTICS, "change_monitor")

    # ------------------------------------------------------------------
    # detector mapping
    #
    # Replaces the legacy wiring/detector/spectra tables, which are now the
    # responsibility of event_udp_to_kafka.
    # ------------------------------------------------------------------

    def get_detector_mapping(self) -> str:
        _unavailable(_UDP_TO_KAFKA, "get_detector_mapping")

    def set_detector_mapping(self, path: str) -> None:
        _unavailable(_UDP_TO_KAFKA, "set_detector_mapping")

    def change_tables(
        self, wiring: str | None = None, detector: str | None = None, spectra: str | None = None
    ) -> None:
        _removed(
            "change_tables",
            f"channel-to-pixel mapping now lives in {_UDP_TO_KAFKA}; "
            "use set_detector_mapping() once available.",
        )

    def get_wiring_tables(self) -> list[str]:
        _removed("get_wiring_tables", f"see {_UDP_TO_KAFKA} and get_detector_mapping().")

    def get_spectra_tables(self) -> list[str]:
        _removed("get_spectra_tables", f"see {_UDP_TO_KAFKA} and get_detector_mapping().")

    def get_detector_tables(self) -> list[str]:
        _removed("get_detector_tables", f"see {_UDP_TO_KAFKA} and get_detector_mapping().")

    def get_table_path(self, table_type: str) -> str:
        _removed("get_table_path", f"see {_UDP_TO_KAFKA} and get_detector_mapping().")

    def get_period_files(self) -> list[str]:
        _removed("get_period_files", "hardware period tables are not configurable by file.")

    # ------------------------------------------------------------------
    # binning
    #
    # Replaces the legacy time channel boundaries. Binning is now a
    # diagnostics concern rather than a hardware histogramming one.
    # ------------------------------------------------------------------

    def get_diagnostic_binning(self, regime: int = 1) -> BinningSpec:
        _unavailable(_DIAGNOSTICS, "get_diagnostic_binning")

    def set_diagnostic_binning(self, spec: BinningSpec, regime: int = 1) -> None:
        _unavailable(_DIAGNOSTICS, "set_diagnostic_binning")

    def reset_diagnostics(self) -> None:
        _unavailable(_DIAGNOSTICS, "reset_diagnostics")

    def change_tcb(
        self,
        low: float | None,
        high: float | None,
        step: float | None,
        trange: int,
        log: bool = False,
        regime: int = 1,
    ) -> None:
        _unavailable(_DIAGNOSTICS, "change_tcb (see set_diagnostic_binning)")

    def change_tcb_file(self, tcb_file: str | None = None, default: bool = False) -> None:
        _unavailable(_DIAGNOSTICS, "change_tcb_file (see set_diagnostic_binning)")

    def get_tcb_settings(self, trange: int, regime: int = 1) -> dict[str, int]:
        _unavailable(_DIAGNOSTICS, "get_tcb_settings (see get_diagnostic_binning)")

    def get_num_timechannels(self) -> int:
        _unavailable(_DIAGNOSTICS, "get_num_timechannels")

    # ------------------------------------------------------------------
    # change transaction model
    # ------------------------------------------------------------------

    def change_start(self) -> None:
        """
        Start a change operation.

        Raises:
            ValueError: if the run state is not SETUP
        """
        if self.get_run_state() != RunState.SETUP:
            raise ValueError("Instrument must be in SETUP when changing settings!")

    def change_finish(self) -> None:
        """
        End a change operation.

        Raises:
            ValueError: if the run state is not SETUP
        """
        if self.get_run_state() != RunState.SETUP:
            raise ValueError("Instrument must be in SETUP when changing settings!")

    # ------------------------------------------------------------------
    # data
    # ------------------------------------------------------------------

    def get_spectrum(
        self, spectrum: int, period: int = 1, dist: bool = True, use_numpy: bool | None = None
    ) -> _GetspectrumReturn:
        _unavailable(_DIAGNOSTICS, "get_spectrum")

    def integrate_spectrum(
        self, spectrum: int, period: int = 1, t_min: float | None = None, t_max: float | None = None
    ) -> float:
        _unavailable(_DIAGNOSTICS, "integrate_spectrum")

    def get_spec_integrals(self) -> npt.NDArray:
        _unavailable(_DIAGNOSTICS, "get_spec_integrals")

    def get_spec_data(self) -> npt.NDArray:
        _unavailable(_DIAGNOSTICS, "get_spec_data")

    # ------------------------------------------------------------------
    # kafka topology and stream health
    # ------------------------------------------------------------------

    def get_broker_address(self) -> str:
        _unavailable("a broker address PV or local configuration", "get_broker_address")

    def get_topics(self) -> Mapping[str, str]:
        _unavailable("a topic configuration PV or local configuration", "get_topics")

    def get_component_health(self) -> Mapping[str, ComponentHealth]:
        _unavailable("per-component status PVs", "get_component_health")

    # ------------------------------------------------------------------
    # filewriter
    # ------------------------------------------------------------------

    def get_filewriter_state(self) -> FileWriterState:
        _unavailable(_FILEWRITER, "get_filewriter_state")

    def get_output_file_path(self) -> str | None:
        _unavailable(_FILEWRITER, "get_output_file_path")

    def wait_for_file_written(self, timeout: float | None = None) -> str:
        _unavailable(_FILEWRITER, "wait_for_file_written")

    # ------------------------------------------------------------------
    # simulation mode
    # ------------------------------------------------------------------

    def get_simulation_mode(self) -> bool:
        # The legacy implementation rewrote icp_config.xml and restarted
        # ISISICP. Simulation should now be chosen when the DAE object is
        # constructed rather than toggled at runtime.
        _unavailable(
            "streaming dae simulation mode",
            "get_simulation_mode",
        )

    def set_simulation_mode(self, mode: bool) -> None:
        _unavailable(
            "streaming dae simulation mode",
            "set_simulation_mode",
        )

    # ------------------------------------------------------------------
    # legacy ISISICP surface
    #
    # Declared so that genie_python call sites fail with a clear message
    # rather than AttributeError.
    # ------------------------------------------------------------------

    _NO_CRPT = "there is no CRPT; data is written continuously from Kafka."

    def update_run(self) -> None:
        _removed("update_run", self._NO_CRPT)

    def store_run(self) -> None:
        _removed("store_run", self._NO_CRPT)

    def update_store_run(self) -> None:
        _removed("update_store_run", self._NO_CRPT)

    def post_update_check(self, verbose: bool = False) -> None:
        _removed("post_update_check", self._NO_CRPT)

    def post_store_check(self, verbose: bool = False) -> None:
        _removed("post_store_check", self._NO_CRPT)

    def post_update_store_check(self, verbose: bool = False) -> None:
        _removed("post_update_store_check", self._NO_CRPT)

    def snapshot_crpt(self, filename: str) -> None:
        _removed("snapshot_crpt", self._NO_CRPT)

    def post_snapshot_check(self, verbose: bool = False) -> None:
        _removed("post_snapshot_check", self._NO_CRPT)

    def recover_run(self) -> None:
        # Events survive in Kafka, so recovery is a filewriter replay rather
        # than a DAE state transition.
        _unavailable(_FILEWRITER, "recover_run")

    def post_recover_check(self, verbose: bool = False) -> None:
        _unavailable(_FILEWRITER, "post_recover_check")

    def get_autosave_freq(self) -> int | None:
        _removed("get_autosave_freq", self._NO_CRPT)

    def set_autosave_freq(self, freq: int) -> None:
        _removed("set_autosave_freq", self._NO_CRPT)

    def sum_all_dae_memory(self) -> int:
        _removed("sum_all_dae_memory", "there is no DAE histogram memory.")

    def get_memory_used(self) -> int:
        _removed("get_memory_used", "there is no DAE histogram memory.")

    @contextmanager
    def temporarily_kill_icp(self) -> typing.Generator[None, None, None]:
        _removed("temporarily_kill_icp", "there is no ISISICP process.")

    # ------------------------------------------------------------------
    # internal methods
    # ------------------------------------------------------------------

    def _check_prepost_supported(self, prepost: bool) -> None:
        """
        Guards against silently running pre- / post-commands when they were
        explicitly disabled.

        Raises:
            NotImplementedError: if prepost is False
        """
        if not prepost:
            raise NotImplementedError(
                "prepost=False is not supported by the streaming DAE: the IOC does not "
                "expose an action PV that skips pre/post commands."
            )

    def _get_veto_levels(self) -> Sequence[int]:
        """
        Reads the raw VETO:SP array.
        """
        levels = self._get_pv_value(self._get_dae_pv_name("veto_sp"))
        if levels is None:
            return []
        if isinstance(levels, (int, float)):
            return [int(levels)]
        return [int(level) for level in typing.cast(Sequence[int], levels)]

    def _is_paused(self) -> bool:
        """
        Determines whether the run is paused.

        Pause is implemented as a software veto.
        """
        names = [name.lower() for name in self.get_veto_names()]
        if PAUSE_VETO_NAME not in names:
            return False
        levels = self._get_veto_levels()
        index = names.index(PAUSE_VETO_NAME)
        return index < len(levels) and levels[index] != VetoLevel.DISABLED

    def _test_clock_warning(self) -> None:
        """
        Warn the user they are using the test clock.
        """
        print("\n========= RUNNING AGAINST DAE TEST CLOCK =========\n")
        print("Timing source can be changed using:               \n")
        print("         >>>change_sync(source)                   \n")
        print("==================================================\n")

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

    def _get_dae_pv_name(self, name: str) -> str:
        """
        Retrieves the full PV name of a DAE variable.

        Args:
            name: the short name for the DAE variable

        Returns:
            string: the full PV name
        """
        return self._prefix_pv_name(DAE_PVS_LOOKUP[name.lower()])

    def _get_pv_value(
        self, name: str, to_string: bool = False, use_numpy: bool | None = None
    ) -> PVValue:
        """
        Gets a PV's value.

        Args:
            name: the PV name
            to_string: whether to convert the value to a string
            use_numpy: True to return arrays as numpy, False for a list,
                       None for the default

        Returns:
            object: the PV's value
        """
        return self.api.get_pv_value(name, to_string, use_numpy=use_numpy)

    def _set_pv_value(self, name: str, value: PVValue, wait: bool = False) -> None:
        """
        Sets a PV value via the API.

        Args:
            name: the PV name
            value: the value to set
            wait: whether to wait for it to be set before returning
        """
        self.api.set_pv_value(name, value, wait)

    def _get_vetoes(self) -> Mapping[str, Veto]:
        """
        Gets the current veto configuration.

        Returns:
            Mapping[str, Veto]: vetoes keyed by name
        """
        names = self.get_veto_names()
        levels = self._get_veto_levels()
        hard = self._get_pv_value(self._get_dae_pv_name("veto_hard")) or []
        hard = typing.cast(Sequence[int], hard)

        return {
            name: Veto(
                name=name,
                index=index,
                level=VetoLevel(levels[index]) if index < len(levels) else VetoLevel.DISABLED,
                applied_in_hardware=bool(hard[index]) if index < len(hard) else False,
            )
            for index, name in enumerate(names)
        }

    def _print_verbose_messages(self) -> None:
        _unavailable("Verbose messages", "_print_verbose_messages")
