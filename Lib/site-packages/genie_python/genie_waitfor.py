"""
Classes allowing you to wait for states
"""
from __future__ import absolute_import
from __future__ import print_function
from time import strptime
from datetime import timedelta, datetime
import six
from genie_python.utilities import sleep


class WaitForController(object):
    """
    Controller for waiting for states
    """
    def __init__(self, api):
        self.api = api
        self.time_delta = None
        self.start_time = None
        self.block = None
        self.low = None
        self.high = None

    def start_waiting(self, block=None, value=None, lowlimit=None, highlimit=None, maxwait=None, wait_all=False,
                      seconds=None, minutes=None, hours=None, time=None, frames=None, raw_frames=None, uamps=None,
                      early_exit=lambda: False):
        """
        Wait until a condition is reached. If wait_all is False then wait for one of the conditions if True wait until
        all are reached
        Args:
            block: wait for a block to become a value
            value: the value the block should become
            lowlimit: the low limit the value should bea above this value
            highlimit: the high limit the value should bea above this value
            maxwait: maximum time to wait for the state to be reached
            wait_all: True wait for all conditions to be reached; False wait for one condition to be reached
            seconds: number of seconds to wait
            minutes: number of minutes to wait
            hours: number of hours to wait
            time: total time to wait (overrides seconds minutes and hours)
            frames: number of frames to wait
            raw_frames: number of raw frames to wait
            uamps: number of micro amps to wait
            early_exit: function to check if wait should exit early. Function should return true to exit wait.

        Returns: nothing

        """
        # Error checks
        timeout_msg = ''
        if maxwait is not None:
            if not isinstance(maxwait, float) and not isinstance(maxwait, six.integer_types):
                raise Exception("The value entered for maxwait was invalid, it should be numeric.")
            else:
                maxwait = timedelta(seconds=maxwait)
                timeout_msg = '[timeout={}]'.format(maxwait.total_seconds())
        if seconds is not None and not (isinstance(seconds, six.integer_types) or isinstance(seconds, float)):
            raise Exception("Invalid value entered for seconds")
        if minutes is not None and not isinstance(minutes, six.integer_types):
            raise Exception("Invalid value entered for minutes")
        if hours is not None and not isinstance(hours, six.integer_types):
            raise Exception("Invalid value entered for hours")
        if time is not None:
            try:
                ans = strptime(time, "%H:%M:%S")
                seconds = ans.tm_sec
                minutes = ans.tm_min
                hours = ans.tm_hour
            except Exception:
                raise Exception("Time string entered was invalid. It should be of the form HH:MM:SS")
        if frames is not None:
            if not isinstance(frames, six.integer_types):
                raise Exception("Invalid value entered for frames")
            else:
                print('Waiting for {} frames {}'.format(frames, timeout_msg))
        if raw_frames is not None:
            if not isinstance(raw_frames, (int, long)):
                raise Exception("Invalid value entered for raw_frames")
            else:
                print('Waiting for {} raw frames {}'.format(raw_frames, timeout_msg))
        if uamps is not None:
            if not (isinstance(uamps, six.integer_types) or isinstance(uamps, float)):
                raise Exception("Invalid value entered for uamps")
            else:
                print('Waiting for {} uamps {}'.format(uamps, timeout_msg))

        if block is not None:
            if not self.api.block_exists(block):
                raise NameError('No block with the name "{}" exists'.format(block))
            block = self.api.correct_blockname(block)
            if value is not None and (not isinstance(value, float) and not isinstance(value, six.integer_types)
                                      and not isinstance(value, six.string_types)):
                raise Exception("The value entered for the block was invalid, it should be numeric or a string.")
            if lowlimit is not None and (not isinstance(lowlimit, float) and not isinstance(lowlimit, six.integer_types)):
                raise Exception("The value entered for lowlimit was invalid, it should be numeric.")
            if highlimit is not None and (not isinstance(highlimit, float) and not isinstance(highlimit, six.integer_types)):
                raise Exception("The value entered for highlimit was invalid, it should be numeric.")

        self._init_wait_time(seconds, minutes, hours, timeout_msg)
        self._init_wait_block(block, value, lowlimit, highlimit, timeout_msg)
        start_time = datetime.utcnow()

        while True:
            if maxwait is not None:
                if datetime.utcnow() - start_time >= maxwait:
                    print("Waitfor timed out after {} seconds".format(maxwait))
                    self.api.log_info_msg("WAITFOR TIMED OUT")
                    return

            if early_exit():
                print("Early exit handler evaluated to true in waitfor - stopping wait")
                self.api.log_info_msg("EARLY EXIT HANDLER REACHED IN WAITFOR - STOPPING WAIT")
                return

            res = list()
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

            if len(res) == 0:
                self.api.log_error_msg("NO VALID WAITFOR CONDITIONS PROVIDED")
                return
            elif (wait_all and True not in res) or (not wait_all and False in res):
                self.api.log_info_msg("WAITFOR EXITED NORMALLY")
                return

            sleep(0.5)

    def wait_for_runstate(self, state, maxwaitsecs=3600, onexit=False):
        """
        Wait for a given run state
        Args:
            state: the run state to wait for
            maxwaitsecs: maximum time to wait
            onexit: if True wait only as long as in transitional state; False wait whatever the current state

        Returns: nothing

        """
        time_delta = self._get_time_delta(maxwaitsecs, 0, 0)
        state = state.upper().strip()
        start_time = datetime.utcnow()
        while True:
            sleep(0.3)
            curr = self.api.dae.get_run_state()
            if onexit:
                if curr != state and not self.api.dae.in_transition():
                    self.api.log_info_msg("WAITFOR_RUNSTATE ONEXIT STATE EXITED")
                    break
            else:
                if curr == state:
                    self.api.log_info_msg("WAITFOR_RUNSTATE STATE REACHED")
                    break
            # Check for timeout
            if datetime.utcnow() - start_time >= time_delta:
                self.api.log_info_msg("WAITFOR_RUNSTATE TIMED OUT")
                break

    def _init_wait_time(self, seconds, minutes, hours, timeout_msg=""):
        self.time_delta = self._get_time_delta(seconds, minutes, hours)
        if self.time_delta is not None:
            self.start_time = datetime.utcnow()
            print('Waiting for {} seconds {}'.format(self.time_delta.total_seconds(), timeout_msg))
        else:
            self.start_time = None

    def _waiting_for_time(self):
        if datetime.utcnow() - self.start_time >= self.time_delta:
            return False
        else:
            return True

    def _get_time_delta(self, seconds, minutes, hours):
        """
        Returns a timedelta representation of the input seconds, minutes and hours. If all parameters are None, then
        None returned, else None parameters are interpreted as 0
        """
        if all(t is None for t in (seconds, minutes, hours)):
            return None
        else:
            num_seconds, num_minutes, num_hours = (0 if t is None else t for t in (seconds, minutes, hours))
            return timedelta(hours=num_hours, minutes=num_minutes, seconds=num_seconds)

    def _init_wait_block(self, block, value, lowlimit, highlimit, timeout_msg=""):
        self.block = block
        if self.block is None:
            return
        self.low, self.high = self._get_block_limits(value, lowlimit, highlimit)
        if self.low is None and self.high is None:
            raise Exception("No limit(s) set for {0}".format(block))
        if self.low == self.high:
            print('Waiting for {0}={1}{2}'.format(str(block), str(self.low), timeout_msg))
        else:
            print('Waiting for {0} (lowlimit={1}, highlimit={2}){3}'.format(str(block), str(self.low), str(self.high),
                                                                            timeout_msg))

    def _get_block_limits(self, value, lowlimit, highlimit):
        low = None
        high = None
        if value is not None:
            low = high = value
        if lowlimit is not None:
            low = lowlimit
        if highlimit is not None:
            high = highlimit
        # Check low and high are round the correct way
        if low is not None and high is not None and low > high:
            low, high = high, low
            print("WARNING: The highlimit and lowlimit have been swapped to lowlimit({}) and highlimit({})"
                  .format(low, high))
        return low, high

    def _block_has_waited_for_value(self):
        """
        Return True if the block is above any low lmit and below any high limit. In the case
        of a string type it is if it is at the low limit.

        :return: true of the block has the value that is being waited for; False otherwise
        """
        currval = self.api.get_block_value(self.block)
        flag = True
        try:
            if self.low is not None:
                flag = currval >= float(self.low)
            if self.high is not None:
                flag = currval <= float(self.high) and flag
        except ValueError:
            #  pv is a string values so just test
            flag = currval == self.low
        return not flag
