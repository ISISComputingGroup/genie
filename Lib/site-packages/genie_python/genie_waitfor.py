"""
Classes allowing you to wait for states
"""

from __future__ import absolute_import, print_function

from abc import ABCMeta, abstractmethod
from builtins import object, str
from datetime import datetime, timedelta
from time import sleep, strptime
from typing import TYPE_CHECKING, Callable, TypeAlias

from genie_python.utilities import check_break, get_time_delta

if TYPE_CHECKING:
    from genie_python.genie_epics_api import API

NUMERIC_TYPE = (float, int)

WAITFOR_VALUE: TypeAlias = bool | int | float | str | None

# The time in a loop to sleep for when waiting for an event, e.g. polling a pv/block value
DELAY_IN_WAIT_FOR_SLEEP_LOOP = 0.1

# The time in a start_waiting to wait until notifying the user again of an error
SECONDS_UNTIL_RENOTIFY_EXCEPTION = 5 * 60

# Use the state pattern to keep a track of transitions to when exceptions and reconnections should
# be printed
# Exceptions should be printed at disconnection, after 5 minutes of disconnection or when the
# exception changes
# When the exception disappears pv reconnected is printed once


class WaitForControllerState(object, metaclass=ABCMeta):
    """
    The abstract class for the exception state of the
     WaitForController when it is in the loop in the start_waiting method.
    """

    def __init__(
        self,
        api: "API",
        last_notification_time: datetime,
        last_exception: "Exception|None" = None,
        context: "WaitForControllerExceptionContext|None" = None,
    ) -> None:
        """
        Initializes the state.
        :param api: The api to use for logging
        :param last_notification_time: The last time the user was notified of an exception
        :param last_exception: The last exception the user was notified of
        :param context: The context the state belongs to
        """
        self._api = api
        self._last_notification_time = last_notification_time
        self._last_exception = last_exception
        self.context = context

    def process_exception(
        self, exception: Exception | None = None
    ) -> "WaitForControllerState|None":
        """
        Delegate processing of the exception to the relevant subclass method,
        based on whether the exception argument is None or not.
        :param exception: The exception to be processed (if no exception it is None)
        :return: The state the context is now in (could be the same or a transition)
        """
        if exception is not None:
            return self.handle_exception_notification(exception)
        else:
            return self.exception_cleared()

    @staticmethod
    def _transition(new_state: "WaitForControllerState") -> "WaitForControllerState":
        """
        We need to transition to a new state. Create this state, run enter on it and return it.
        :param new_state: The state to transition to
        :return: The new state
        """
        new_state.enter()
        return new_state

    @staticmethod
    def start(
        api: "API", context: "WaitForControllerExceptionContext|None" = None
    ) -> "WaitForControllerConnectedState":
        """
        Return the state the context starts at.
        :param api: The api to use for logging
        :param context: The context the state belongs to
        :return: The state the context starts at.
        """
        return WaitForControllerConnectedState(api, datetime.now(), context=context)

    @abstractmethod
    def handle_exception_notification(self, exception: Exception) -> "WaitForControllerState|None":
        """
        When there is an exception handle it.
        :param exception: The exception to handle
        :return: The state the context is now in (could be the same or a transition)
        """
        pass

    @abstractmethod
    def exception_cleared(self) -> "WaitForControllerState|None":
        """
        When there is no exception handle it.
        :return: The state the context is now in (could be the same or a transition)
        """
        pass

    @abstractmethod
    def enter(self) -> None:
        """
        When this state is first entered handle it.
        :return: None
        """
        pass


class WaitForControllerExceptionState(WaitForControllerState):
    """
    The state for when the WaitForController is in an exception state
    but should not notify the user
    """

    def handle_exception_notification(self, exception: Exception) -> "WaitForControllerState|None":
        """
        Handle the event when an exception is occurring.
        Transition to notifying user of an exception every 5 minutes or if the exception is
        different to the last, else, remain in this state.
        :param exception: The exception that has occurred.
        :return: The new exception state if 5 minutes passed since last or if there is a new type
         of exception. The current state if not.
        """
        seconds_since_last_notification = (datetime.now() - self._last_notification_time).seconds
        if seconds_since_last_notification >= SECONDS_UNTIL_RENOTIFY_EXCEPTION or not isinstance(
            exception, type(self._last_exception)
        ):
            return self._transition(
                WaitForControllerExceptionState(self._api, self._last_notification_time, exception)
            )
        else:
            return self

    def exception_cleared(self) -> "WaitForControllerState|None":
        """
        Handle the transition from an exception occurring to where the pv is connected.
        :return: The new connected state
        """
        return self._transition(
            WaitForControllerConnectedState(
                self._api, self._last_notification_time, self._last_exception
            )
        )

    def print_exception(self, exception: Exception | None) -> None:
        """
        Print an exception to stdout and log it to the api.
        :param exception: The exception to print
        :return: None
        """
        message = "{}: Exception in waitfor loop: {}: {}".format(
            str(datetime.now()), exception.__class__.__name__, exception
        )
        print(message)
        self._api.logger.log_info_msg(message)

    def enter(self) -> None:
        """
        Print message about last exception and update notification time.
        :return: None
        """
        self.print_exception(self._last_exception)
        self._last_notification_time = datetime.now()


class WaitForControllerConnectedState(WaitForControllerState):
    """
    The state for when the WaitForController has just reconnected after an exception state.
    """

    def handle_exception_notification(
        self, exception: "Exception|None"
    ) -> "WaitForControllerState|None":
        """
        Transition to the exception occurring state.
        :param exception: The exception that has occurred.
        :return: The new state of the context, which is an exception state.
        """
        return self._transition(
            WaitForControllerExceptionState(self._api, self._last_notification_time, exception)
        )

    def exception_cleared(self) -> WaitForControllerState | None:
        """
        Remain in this state as we are still connected.
        :return: The current state
        """
        return self

    def print_exception_cleared(self) -> None:
        """
        Print to the console that the pv is connected.
        :return: None
        """
        message = "{}: Exception cleared".format(str(datetime.now()))
        print(message)
        self._api.logger.log_info_msg(message)

    def enter(self) -> None:
        """
        When first entering this state print the the pv is connected.
        :return: None
        """
        self.print_exception_cleared()


class WaitForControllerExceptionContext(object):
    """
    The exception context of the WaitForController when it is
    in the loop in the start_waiting method
    """

    def __init__(self, api: "API") -> None:
        """
        Set the starting state of the context.
        :param api: The api for logging
        """
        self._state = WaitForControllerState.start(api, context=self)

    def process_exception(self, exception: Exception | None) -> None:
        """
        Delegate the processing of the exception to the state
        and create the new state based on what is returned.
        :param exception: The exception to process
        :return: None
        """
        if self._state is not None:
            self._state = self._state.process_exception(exception)


class WaitForController(object):
    """
    Controller for waiting for states
    """

    def __init__(self, api: "API") -> None:
        self.api = api
        self.time_delta = None
        self.start_time = None
        self.block = None
        self.low = None
        self.high = None

    def start_waiting(
        self,
        block: str | None = None,
        value: WAITFOR_VALUE | None = None,
        lowlimit: float | int | None = None,
        highlimit: float | int | None = None,
        maxwait: float | None = None,
        wait_all: bool = False,
        seconds: float | None = None,
        minutes: float | None = None,
        hours: float | None = None,
        time: str | None = None,
        frames: int | None = None,
        raw_frames: int | None = None,
        uamps: float | None = None,
        mevents: float | None = None,
        early_exit: Callable[[], bool] = lambda: False,
        quiet: bool = False,
    ) -> None:
        """
        Wait until a condition is reached. If wait_all is False then wait for one of the
        conditions if True wait until all are reached
        Args:
            block: wait for a block to become a value
            value: the value the block should become
            lowlimit: the low limit, the value should be above this value
            highlimit: the high limit, the value should be below this value
            maxwait: maximum time in seconds to wait for the state to be reached
            wait_all: True wait for all conditions to be reached; False wait for one condition
                        to be reached
            seconds: number of seconds to wait
            minutes: number of minutes to wait
            hours: number of hours to wait
            time: total time to wait (overrides seconds minutes and hours)
            frames: number of frames to wait
            raw_frames: number of raw frames to wait
            uamps: number of micro amps to wait
            mevents: number of millions of events to wait
            early_exit: function to check if wait should exit early. Function should return true
                        to exit wait.
            quiet: Suppress confirmation and countdown output to the console
                    (warning/error messages still sent)

        Returns: nothing

        """
        # Error checks
        timeout_msg = ""
        self._print_if_not_quiet(
            "Start time: {}".format(datetime.now().time().strftime("%H:%M:%S")), quiet
        )
        self.api.logger.log_info_msg("WAITFOR STARTED")
        if maxwait is not None:
            if not isinstance(maxwait, NUMERIC_TYPE):
                raise Exception("The value entered for maxwait was invalid, it should be numeric.")
            else:
                timeout_msg = "[timeout={}]".format(timedelta(seconds=maxwait).total_seconds())
        if seconds is not None and not isinstance(seconds, NUMERIC_TYPE):
            raise Exception("Invalid value entered for seconds")
        if minutes is not None and not isinstance(minutes, NUMERIC_TYPE):
            raise Exception("Invalid value entered for minutes")
        if hours is not None and not isinstance(hours, NUMERIC_TYPE):
            raise Exception("Invalid value entered for hours")
        if time is not None:
            try:
                ans = strptime(time, "%H:%M:%S")
                seconds = ans.tm_sec
                minutes = ans.tm_min
                hours = ans.tm_hour
            except Exception:
                raise Exception(
                    "Time string entered was invalid. It should be of the form HH:MM:SS"
                )
        if frames is not None:
            if not isinstance(frames, int):
                raise Exception("Invalid value entered for frames")
            else:
                self._print_if_not_quiet(
                    "Waiting for {} frames {}".format(frames, timeout_msg), quiet
                )
        if raw_frames is not None:
            if not isinstance(raw_frames, int):
                raise Exception("Invalid value entered for raw_frames")
            else:
                self._print_if_not_quiet(
                    "Waiting for {} raw frames {}".format(raw_frames, timeout_msg), quiet
                )
        if uamps is not None:
            if not (isinstance(uamps, NUMERIC_TYPE)):
                raise Exception("Invalid value entered for uamps")
            else:
                self._print_if_not_quiet(
                    "Waiting for {} uamps {}".format(uamps, timeout_msg), quiet
                )
        if mevents is not None:
            if not (isinstance(mevents, NUMERIC_TYPE)):
                raise Exception("Invalid value entered for mevents")
            else:
                self._print_if_not_quiet(
                    "Waiting for {} million events {}".format(mevents, timeout_msg), quiet
                )

        if block is not None:
            if not self.api.block_exists(block):
                raise NameError('No block with the name "{}" exists'.format(block))
            block = self.api.correct_blockname(block, add_prefix=False)
            if value is not None and (not isinstance(value, NUMERIC_TYPE + (str,))):
                raise Exception(
                    "The value entered for the block was invalid, it should be numeric or a string."
                )
            if lowlimit is not None and (not isinstance(lowlimit, NUMERIC_TYPE)):
                raise Exception("The value entered for lowlimit was invalid, it should be numeric.")
            if highlimit is not None and (not isinstance(highlimit, NUMERIC_TYPE)):
                raise Exception(
                    "The value entered for highlimit was invalid, it should be numeric."
                )

        self._init_wait_time(seconds, minutes, hours, quiet, timeout_msg)
        self._init_wait_block(block, value, lowlimit, highlimit, quiet, timeout_msg)
        start_time = datetime.now()

        # Start with a state where the pv is considered connected and
        # there is no need to notify of it
        context = WaitForControllerExceptionContext(self.api)

        while True:
            if maxwait is not None:
                if datetime.now() - start_time >= timedelta(seconds=maxwait):
                    print("Waitfor timed out after {} seconds".format(maxwait))
                    print("End time: {}".format(datetime.now().time().strftime("%H:%M:%S")))
                    self.api.logger.log_info_msg("WAITFOR TIMED OUT")
                    return

            if early_exit():
                print("Early exit handler evaluated to true in waitfor - stopping wait")
                print("End time: {}".format(datetime.now().time().strftime("%H:%M:%S")))
                self.api.logger.log_info_msg(
                    "EARLY EXIT HANDLER REACHED IN WAITFOR - STOPPING WAIT"
                )
                return

            try:
                res = []
                if self.block is not None:
                    res.append(self._block_has_waited_for_value())
                if self.start_time is not None and self.time_delta is not None:
                    res.append(self._waiting_for_time())
                if frames is not None:
                    res.append(self.api.dae.get_good_frames() < frames)
                if raw_frames is not None:
                    res.append(self.api.dae.get_raw_frames() < raw_frames)
                if uamps is not None:
                    res.append(self.api.dae.get_uamps() < uamps)
                if mevents is not None:
                    res.append(self.api.dae.get_mevents() < mevents)
                # Notify the context that no exception has occurred
                context.process_exception(None)

                if len(res) == 0:
                    self.api.logger.log_error_msg("NO VALID WAITFOR CONDITIONS PROVIDED")
                    print("End time: {}".format(datetime.now().time().strftime("%H:%M:%S")))
                    return
                elif (wait_all and True not in res) or (not wait_all and False in res):
                    self.api.logger.log_info_msg("WAITFOR EXITED NORMALLY")
                    self._print_if_not_quiet(
                        "End time: {}".format(datetime.now().time().strftime("%H:%M:%S")), quiet
                    )
                    return
            except Exception as e:
                # Notify the context that an exception has occurred
                context.process_exception(e)

            sleep(DELAY_IN_WAIT_FOR_SLEEP_LOOP)
            check_break(2)

    def _print_if_not_quiet(self, text: str, quiet: bool) -> None:
        if not quiet:
            print(text)

    def wait_for_runstate(
        self,
        state: str,
        maxwaitsecs: int = 3600,
        onexit: bool = False,
        quiet: bool = False,
    ) -> None:
        """
        Wait for a given run state
        Args:
            state: the run state to wait for
            maxwaitsecs: maximum time to wait
            onexit: if True wait only as long as in transitional state;
                    False wait whatever the current state
            quiet: This has been added in alignment with
                    genie_simulate_impl.wait_for_runstate()

        Returns: nothing

        """
        time_delta = timedelta(seconds=maxwaitsecs)
        state = state.upper().strip()
        start_time = datetime.now()
        while True:
            # The sleep is to allow run control to set state before wait_for_runstate
            #   (it polls on 0.1s loop). This is
            #   in case user does cset(x, lim=...), waitfor("RUNNING") - without a wait this
            #   might not catch the run
            #   state change from run control to waiting.
            sleep(0.3)
            check_break(2)
            curr = self.api.dae.get_run_state()
            if onexit:
                if curr != state and not self.api.dae.in_transition():
                    self.api.logger.log_info_msg("WAITFOR_RUNSTATE ONEXIT STATE EXITED")
                    break
            else:
                if curr == state:
                    self.api.logger.log_info_msg("WAITFOR_RUNSTATE STATE REACHED")
                    break
            # Check for timeout
            if datetime.now() - start_time >= time_delta:
                self.api.logger.log_info_msg("WAITFOR_RUNSTATE TIMED OUT")
                break

    def _init_wait_time(
        self,
        seconds: float | int | None,
        minutes: float | int | None,
        hours: float | int | None,
        quiet: bool = False,
        timeout_msg: str = "",
    ) -> None:
        self.time_delta = get_time_delta(seconds, minutes, hours)
        if self.time_delta is not None:
            self.start_time = datetime.now()
            self._print_if_not_quiet(
                "Waiting for {} seconds {}".format(self.time_delta.total_seconds(), timeout_msg),
                quiet,
            )
        else:
            self.start_time = None

    def _waiting_for_time(self) -> bool:
        if (self.start_time is None) or (self.time_delta is None):
            raise Exception("start_time and time_delta must not be None")
        else:
            if datetime.now() - self.start_time >= self.time_delta:
                return False
            else:
                return True

    def _init_wait_block(
        self,
        block: str | None,
        value: WAITFOR_VALUE,
        lowlimit: float | int | None,
        highlimit: float | int | None,
        quiet: bool = False,
        timeout_msg: str = "",
    ) -> None:
        self.block = block
        if self.block is None:
            return
        self.low, self.high = self._get_block_limits(value, lowlimit, highlimit)
        if self.low is None and self.high is None:
            raise Exception("No limit(s) set for {0}".format(block))
        if self.low == self.high:
            self._print_if_not_quiet(
                "Waiting for {0}={1}{2}".format(str(block), str(self.low), timeout_msg), quiet
            )
        else:
            self._print_if_not_quiet(
                "Waiting for {0} (lowlimit={1}, highlimit={2}){3}".format(
                    str(block), str(self.low), str(self.high), timeout_msg
                ),
                quiet,
            )

    def _get_block_limits(
        self, value: WAITFOR_VALUE, lowlimit: float | int | None, highlimit: float | int | None
    ) -> tuple[WAITFOR_VALUE | None, WAITFOR_VALUE | None]:
        low = None
        high = None
        if value is not None:
            low = high = value
        if isinstance(lowlimit, NUMERIC_TYPE):
            low = lowlimit
        if isinstance(highlimit, NUMERIC_TYPE):
            high = highlimit
        # Check low and high are round the correct way
        if isinstance(low, NUMERIC_TYPE) and isinstance(high, NUMERIC_TYPE) and low > high:
            low, high = high, low
            print(
                "WARNING: The highlimit and lowlimit have been \
                swapped to lowlimit({}) and highlimit({})".format(low, high)
            )
        return low, high

    def _block_has_waited_for_value(self) -> bool:
        """
        Return True if the block is above any low limit and below any high limit. In the case
        of a string type it is if it is at the low limit.

        :return: true of the block has the value that is being waited for; False otherwise
        """
        flag = True
        currval = self.api.get_block_value(self.block)
        if not isinstance(currval, NUMERIC_TYPE):
            #  pv is a string values so just test
            flag = currval == self.low
        else:
            try:
                if self.low is not None:
                    flag = currval >= float(self.low)
                if self.high is not None:
                    flag = currval <= float(self.high) and flag
            except ValueError:
                #  pv is a string values so just test
                flag = currval == self.low
        return not flag
