"""
Wrapping of channel access in genie_python
"""

from __future__ import absolute_import, print_function

import os
import threading
from builtins import object
from collections.abc import Callable
from threading import Event
from typing import TYPE_CHECKING, Optional, Tuple, TypeVar

from CaChannel import CaChannel, CaChannelException, ca

try:
    from CaChannel._ca import (
        AlarmCondition,
        AlarmSeverity,
        dbf_type_to_DBR_STS,
        dbf_type_to_DBR_TIME,
        dbf_type_to_text,
    )
except ImportError:
    # Note: caffi dynamically added to dependencies by CaChannel if not using built backend.
    from caffi.ca import (  # type: ignore[reportMissingImports]
        AlarmCondition,
        AlarmSeverity,
        dbf_type_to_DBR_STS,
        dbf_type_to_DBR_TIME,
        dbf_type_to_text,
    )

if TYPE_CHECKING:
    from genie_python.genie import PVValue

from .channel_access_exceptions import (
    InvalidEnumStringException,
    ReadAccessException,
    UnableToConnectToPVException,
    WriteAccessException,
)
from .utilities import waveform_to_string

TIMEOUT = 15  # Default timeout for PV set/get
EXIST_TIMEOUT = 3  # Separate smaller timeout for pv_exists() and searchw() operations
CACHE = threading.local()
CACHE_LOCK = threading.local()
T = TypeVar("T")


class CaChannelWrapper(object):
    """
    Wrap CA Channel access to give utilities methods for access in one place
    """

    error_log_func: Optional[Callable[[str], None]] = None

    # noinspection PyPep8Naming
    @staticmethod
    def logError(message: str):  # noqa N802
        """
        Log an error
        Args:
            message: message to log
        """
        if CaChannelWrapper.error_log_func is not None:
            try:
                CaChannelWrapper.error_log_func(message)
            except Exception:
                pass
        else:
            print("CAERROR: {}".format(message))

    # noinspection PyPep8Naming
    @staticmethod
    def printfHandler(message: str, user_args: Tuple[T, ...]) -> None:  # noqa N802
        """
        Callback used for CA printing messages.

        Args:
            message (string): Contains the results of the action.
            user_args (tuple): Contains any extra arguments supplied to the call.

        Returns:
            None.
        """
        CaChannelWrapper.logError("CAMessage: {}".format(message))

    # noinspection PyPep8Naming
    @staticmethod
    def CAExceptionHandler(epics_args: dict[str, str], user_args: Tuple[None]) -> None:  # noqa N802
        """
        Callback used for CA exception messages.

        Args:
            epics_args (dict): Contains the results of the action - see C struct
                "exception_handler_args"
                Available ones are: chid, type, count, state, op, ctx, file, lineNo

            user_args (dict): Contains any extra arguments supplied to the call.

        Returns:
            None.
        """
        CaChannelWrapper.logError(
            "CAException: ctx={} type={} state={} op={} file={} lineNo={}".format(
                epics_args["ctx"],
                epics_args["type"],
                epics_args["state"],
                epics_args["op"],
                epics_args["file"],
                epics_args["lineNo"],
            )
        )

    # noinspection PyPep8Naming
    @staticmethod
    def installHandlers(chan: CaChannel) -> None:  # noqa N802
        """
        Installs callbacks for printf and exceptions.

        Args:
            chan: CaChannel instance

        Returns:
            None.
        """
        # We do a poll() so ca_context_create() gets called with arguments to enable preemptive
        # callbacks CaChannel itself delays creation of the context, so if we just installed the
        # handlers now we would get a default non-preemptive CA context created.
        chan.poll()
        try:
            chan.replace_printf_handler(CaChannelWrapper.printfHandler)
        except AttributeError:
            # If we can't replace the printf handler, ignore that error - it is not crucial.
            # It probably means we are using default CaChannel, as opposed to ISIS' special build.
            # Cope with both cases.
            pass
        chan.add_exception_event(CaChannelWrapper.CAExceptionHandler)

    # noinspection PyPep8Naming
    @staticmethod
    def putCB(epics_args: Tuple[str, int, int, int], user_args: Tuple[Event, ...]) -> None:  # noqa N802
        """
        Callback used for setting PV values.

        Args:
            epics_args (tuple): Contains the results of the action.
            user_args (tuple): Contains any extra arguments supplied to the call.

        Returns:
            None.
        """
        user_args[0].set()

    @staticmethod
    def set_pv_value(
        name: str,
        value: "PVValue",
        wait: bool = False,
        timeout: float = TIMEOUT,
        safe_not_quick: bool = True,
    ) -> None:
        """
        Set the PV to a value.

        When getting a PV value this call should be used, unless there is a special requirement.

        Args:
            name (string): The PV name.
            value: The value to set.
            wait (bool, optional): Wait for the value to be set before returning.
            timeout (optional): How long to wait for the PV to connect etc.
            safe_not_quick (bool): True run all checks while setting the pv, False don't run checks
                just write the value, e.g. disp check

        Returns:
            None.

        Raises:
            UnableToConnectToPVException: If cannot connect to PV.
            WriteAccessException: If write access is denied.
            InvalidEnumStringException: If the PV is an enum and the string value supplied is not a
            valid enum value.
        """
        chan = CaChannelWrapper.get_chan(name)
        chan.setTimeout(timeout)

        # Validate user input and format accordingly for mbbi/bi records
        value = CaChannelWrapper.check_for_enum_value(value, chan, name)

        if not chan.write_access():
            raise WriteAccessException(name)
        if safe_not_quick:
            CaChannelWrapper._check_for_disp(name)
        if wait:
            ftype = chan.field_type()
            ecount = chan.element_count()
            event = Event()
            chan.array_put_callback(value, ftype, ecount, CaChannelWrapper.putCB, event)
            CaChannelWrapper._wait_for_pend_event(chan, event, timeout=None)
        else:
            # putw() flushes send buffer, but doesn't wait for a CA completion callback
            # Write value to PV, or produce error
            chan.putw(value)

    @staticmethod
    def _check_for_disp(name: str) -> None:
        """
        Check if DISP is set on a PV. If passed a field instead of a PV, do nothing.
        Only check DISP if it exists.
        """
        if (
            ".DISP" not in name
        ):  # Do not check for DISP if it's already in the name of the PV to check
            if "." in name:  # If given a field on a PV, check the PV itself if DISP is set
                name = name.split(".")[0]
            _disp_name = "{}.DISP".format(name)
            if (
                CaChannelWrapper.pv_exists(_disp_name, 0)
                and CaChannelWrapper.get_pv_value(_disp_name) != "0"
            ):
                raise WriteAccessException("{} (DISP is set)".format(name))

    @staticmethod
    def get_chan(name: str, timeout: float = EXIST_TIMEOUT) -> CaChannel:
        """
        Gets a channel based on a channel name, from the cache if it exists.

        Args:
            name: the name of the channel to get
            timeout: timeout to set on channel

        Returns:
            CaChannel object representing the channel

        Raises:
            UnableToConnectToPVException if it was unable to connect to the channel
        """

        try:
            lock = CACHE_LOCK.lock
        except AttributeError:
            lock = CACHE_LOCK.lock = threading.RLock()

        with lock:
            try:
                pv_map = CACHE.map
            except AttributeError:
                pv_map = CACHE.map = {}

            if name in list(pv_map.keys()) and pv_map[name].state() == ca.cs_conn:
                chan = pv_map[name]
            else:
                chan = CaChannel(name)
                # do not install handlers if server
                if os.getenv("EPICS_CAS_INTF_ADDR_LIST") is None:
                    # noinspection PyTypeChecker
                    CaChannelWrapper.installHandlers(chan)
                chan.setTimeout(timeout)
                # Try to connect - throws if cannot
                CaChannelWrapper.connect_to_pv(chan)
                pv_map[name] = chan
        return chan

    @staticmethod
    def clear_monitor(name: str, timeout: float = EXIST_TIMEOUT) -> None:
        channel = CaChannelWrapper.get_chan(name, timeout)
        channel.clear_channel()

    @staticmethod
    def get_pv_value(
        name: str, to_string: bool = False, timeout: float = TIMEOUT, use_numpy: bool | None = None
    ) -> "PVValue":
        """
        Get the current value of the PV.

        Args:
            name (name): The PV.
            to_string (bool, optional): Whether to convert the value to a string.
            timeout (optional): How long to wait for the PV to connect etc.
            use_numpy (None|boolean): True use numpy to return arrays, False return a list;
            None for use the default

        Returns:
            The PV value.

        Raises:
            UnableToConnectToPVException: If cannot connect to PV.
            ReadAccessException: If read access is denied.
        """
        chan = CaChannelWrapper.get_chan(name)
        chan.setTimeout(timeout)
        if not chan.read_access():
            raise ReadAccessException(name)
        ftype = chan.field_type()
        if ca.dbr_type_is_ENUM(ftype) or ca.dbr_type_is_CHAR(ftype) or ca.dbr_type_is_STRING(ftype):
            to_string = True
        if to_string:
            if ca.dbr_type_is_ENUM(ftype) or ca.dbr_type_is_STRING(ftype):
                value = chan.getw(ca.DBR_STRING)
            else:
                # If we get a numeric using ca.DBR_CHAR the value still comes back as a numeric
                # In other words, it does not get cast to char
                value = chan.getw(ca.DBR_CHAR)
            # Could see if the element count is > 1 instead
            if isinstance(value, list):
                return waveform_to_string(value)
            else:
                return str(value)
        else:
            if use_numpy is None:
                output = chan.getw()
            else:
                output = chan.getw(use_numpy=use_numpy)
            assert not isinstance(output, dict)
            return output

    @staticmethod
    def get_pv_timestamp(name: str, timeout: float = TIMEOUT) -> Tuple[int, int]:
        """
        Get the timestamp of when the PV was last processed.

        Args:
            name (name): The PV.
            timeout (optional): How long to wait for the PV to connect etc.

        Returns:
            tuple of: (seconds, nanoseconds)

        Raises:
            UnableToConnectToPVException: If cannot connect to PV.
            ReadAccessException: If read access is denied.
        """
        chan = CaChannelWrapper.get_chan(name)
        chan.setTimeout(timeout)
        if not chan.read_access():
            raise ReadAccessException(name)
        ftype = chan.field_type()
        info = chan.getw(dbf_type_to_DBR_TIME(ftype))
        assert isinstance(info, dict)
        return info["pv_seconds"], info["pv_nseconds"]

    @staticmethod
    def pv_exists(name: str, timeout: float = EXIST_TIMEOUT) -> bool:
        """
        See if the PV exists.

        Args:
            name (string): The PV name.
            timeout(optional): How long to wait for the PV to "appear".

        Returns:
            True if exists, otherwise False.
        """
        try:
            chan = CaChannelWrapper.get_chan(name, timeout)
            CaChannelWrapper.connect_to_pv(chan)
            return True
        except UnableToConnectToPVException:
            return False

    @staticmethod
    def connect_to_pv(ca_channel: CaChannel) -> None:
        """
        Connects to the PV.

        Args:
            ca_channel (CaChannel): The channel to connect to.

        Returns:
            None.

        Raises:
            UnableToConnectToPVException: If cannot connect to PV.
        """
        if os.getenv("GITHUB_ACTIONS"):
            # genie_python does some PV accesses on import. To avoid them timing out and making CI
            # builds really slow, shortcut every PV to "non-existent" here.
            raise UnableToConnectToPVException("", "In CI")

        event = Event()
        try:
            ca_channel.search_and_connect(None, CaChannelWrapper.putCB, event)
        except CaChannelException as e:
            raise UnableToConnectToPVException(ca_channel.name(), e)

        ca_channel.flush_io()

        # we do not need to call pend_event / poll as we are using preemptive callbacks
        time_elapsed = 0.0
        interval = 0.1
        while True:
            time_elapsed += interval
            if event.wait(interval) or time_elapsed >= ca_channel.getTimeout():
                break

        if not event.is_set():
            raise UnableToConnectToPVException(ca_channel.name(), "Connection timeout (event)")

        if ca_channel.state() != ca.cs_conn:
            raise UnableToConnectToPVException(ca_channel.name(), "Connection timeout (state)")

    @staticmethod
    def check_for_enum_value(value: "PVValue", chan: CaChannel, name: str) -> "PVValue":
        """
        Check for string input for MBBI/BI records and replace with the equivalent index value.

        Args:
            value: The PV value.
            chan (CaChannel): The channel access channel.
            name (string): The name of the channel.

        Returns:
            Index value of enum, if the record is mbbi/bi. Otherwise, returns unmodified value.

        Raises:
            InvalidEnumStringException: If the string supplied is not a valid enum value.
        """
        # If PV is MBBI/BI type, search list of enum values and iterate to find a match
        if ca.dbr_type_is_ENUM(chan.field_type()) and isinstance(value, str):
            chan.array_get(ca.DBR_CTRL_ENUM)
            chan.pend_io()
            channel_properties = chan.getValue()
            for index, enum_value in enumerate(channel_properties["pv_statestrings"]):
                if enum_value.lower() == value.lower():
                    # Replace user input with enum index value
                    return index
            # If the string entered isn't valid then throw
            raise InvalidEnumStringException(name, channel_properties["pv_statestrings"])

        return value

    @staticmethod
    def add_monitor(
        name: str,
        call_back_function: "Callable[[PVValue, str, str], None]",
        link_alarm_on_disconnect: bool = True,
        to_string: bool = False,
        use_numpy: bool | None = None,
    ) -> Callable[[], None]:
        """
        Add a callback to a pv which responds on a monitor (i.e. value change).
        This currently only tested for numbers.
        Args:
            name: name of the pv
            call_back_function: the callback function, arguments are value, alarm severity
                (CaChannel._ca.AlarmSeverity), alarm status (CaChannel._ca.AlarmCondition)
            link_alarm_on_disconnect: if set to True, a link alarm is sent with the last value
                when the pv disconnects
            use_numpy (bool, optional): True use numpy to return arrays,
                 False return a list; None for use the default
        Returns:
            unsubscribe event function
        """
        from CaChannel import USE_NUMPY

        if use_numpy is None:
            use_numpy = USE_NUMPY
        chan = CaChannelWrapper.get_chan(name)
        if not chan.read_access():
            raise ReadAccessException(name)
        field_type = chan.field_type()
        # if this is an enum field return the monitor as a string (not an int)
        if ca.dbr_type_is_ENUM(field_type):
            field_type = ca.DBR_STRING
        # Modify the field type from monitor the value to includes the alarm severity and status
        field_type_with_status = dbf_type_to_DBR_STS(field_type)

        def _process_call_back(epics_args: dict[str, str], _: dict[str, str]) -> None:
            value = epics_args.get("pv_value", None)

            if to_string:
                # Could see if the element count is > 1 instead
                if isinstance(value, list):
                    value = waveform_to_string(value)
                else:
                    value = str(value)

            chan.last_value = value
            call_back_function(
                value,
                epics_args.get("pv_severity", AlarmSeverity.No),
                epics_args.get("pv_status", AlarmCondition.No),
            )

        def _connection_callback(epics_args: Tuple[T, ...], _: dict[str, str]) -> None:
            if epics_args[1] == ca.CA_OP_CONN_DOWN:
                call_back_function(chan.last_value, AlarmSeverity.Invalid, AlarmCondition.Link)

        chan.add_masked_array_event(
            field_type_with_status,
            count=None,
            mask=None,
            callback=_process_call_back,
            use_numpy=use_numpy,
        )
        if link_alarm_on_disconnect:
            chan.change_connection_event(_connection_callback)

        return chan.clear_event

    @staticmethod
    def poll() -> None:
        """
        Flush the send buffer and execute any outstanding background activity for all connected pvs.
        NB Connected pv is one which is in the cache
        """
        # pick first channel and perform flush on it.
        try:
            for key, value in CACHE.map.items():
                value.poll()
                break
        except AttributeError:
            # There are no channels so we do not need to poll them
            pass

    @staticmethod
    def _wait_for_pend_event(
        chan: CaChannel, event: Event, timeout: Optional[float] = None, interval: float = 0.1
    ) -> None:
        """
        Wait for a pending event to occur in short intervals to allow for keyboard interrupt;
        has possible timeout for maximum time to wait. This should be used for put operation
        callbacks.

        Args:
            chan: channel to use
            event: the event posted by the callback to wait for
            timeout: maximum time to wait for the event, None means wait forever.
            interval: time to poll channel access
        """

        time_elapsed = 0

        while True:
            # Should use overall timeout somehow? need to make sure it is long enough for
            # all requests to complete did try flush_io() followed by event.wait(1.0) inside the
            # loop for set pv, but a send got missed (this is what util/caput in CaChannel does with
            # its wait is set to True)So looks like pend_event() / pend_io() / poll() is needed
            # CaChannel example uses pend_event, pyepics seems to do both pend_io and pend_event
            # According to docs, if using preemptive callbacks then only an initial flush_io()
            # should be needed

            status = chan.poll()  # equivalent to pend_event() with a small timeout
            if status != ca.ECA_TIMEOUT:
                raise CaChannelException(status)

            time_elapsed += interval
            if event.wait(interval) or (timeout is not None and time_elapsed >= timeout):
                break

        if not event.is_set():
            raise UnableToConnectToPVException(chan.name(), "Pend event timeout")

    @staticmethod
    def dbf_type_to_string(typ: int) -> str:
        """
        Return DB field type as text

        Args:
            typ: DB field type as integer

        Returns: DB field type as string
            Valid values:
            DBF_STRING, DBF_CHAR, DBF_UCHAR, DBF_SHORT, DBF_USHORT, DBF_LONG,
            DBF_ULONG, DBF_INT64, DBF_UINT64, DBF_FLOAT, DBF_DOUBLE, DBF_ENUM,
            DBF_MENU, DBF_DEVICE, DBF_INLINK, DBF_OUTLINK, DBF_FWDLINK, DBF_NOACCESS
        """
        return dbf_type_to_text(typ)
