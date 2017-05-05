from time import sleep, strptime
from datetime import timedelta, datetime


class WaitForController(object):
    def __init__(self, api):
        self.api = api
        self.time_delta = None
        self.start_time = None
        self.block = None
        self.low = None
        self.high = None
    
    def start_waiting(self, block=None, value=None, lowlimit=None, highlimit=None, maxwait=None, wait_all=False, 
                      seconds=None, minutes=None, hours=None, time=None, frames=None, uamps=None):
        # Error checks
        timeout_msg = ''
        if maxwait is not None:
            if not isinstance(maxwait, float) and not isinstance(maxwait, int):
                raise Exception("The value entered for maxwait was invalid, it should be numeric.")
            else:
                maxwait = timedelta(seconds=maxwait)
                timeout_msg = ' [timeout=' + str(maxwait.total_seconds()) + ']'         
        if seconds is not None and not (isinstance(seconds, int) or isinstance(seconds, float)):
            raise Exception("Invalid value entered for seconds")
        if minutes is not None and not isinstance(minutes, int):
            raise Exception("Invalid value entered for minutes")
        if hours is not None and not isinstance(hours, int):
            raise Exception("Invalid value entered for hours")
        if time is not None:
            try:
                ans = strptime(time, "%H:%M:%S")
                seconds = ans.tm_sec
                minutes = ans.tm_min
                hours = ans.tm_hour
            except:
                raise Exception("Time string entered was invalid. It should be of the form HH:MM:SS")
        if frames is not None:
            if not isinstance(frames, int):
                raise Exception("Invalid value entered for frames")
            else:
                print 'Waiting for', str(frames), 'frames' + timeout_msg
        if uamps is not None:
            if not (isinstance(uamps, int) or isinstance(uamps, float)):
                raise Exception("Invalid value entered for uamps")
            else:
                print 'Waiting for', str(uamps), 'uamps' + timeout_msg
            
        if block is not None:
            if not self.api.block_exists(block):
                raise NameError('No block with the name "%s" exists' % block)
            block = self.api.correct_blockname(block)            
            if value is not None and (not isinstance(value, float) and not isinstance(value, int)):
                raise Exception("The value entered for the block was invalid, it should be numeric.")
            if lowlimit is not None and (not isinstance(lowlimit, float) and not isinstance(lowlimit, int)):
                raise Exception("The value entered for lowlimit was invalid, it should be numeric.")
            if highlimit is not None and (not isinstance(highlimit, float) and not isinstance(highlimit, int)):
                raise Exception("The value entered for highlimit was invalid, it should be numeric.")        
            
        self.init_wait_time(seconds, minutes, hours, timeout_msg)
        self.init_wait_block(block, value, lowlimit, highlimit, timeout_msg)
        start_time = datetime.utcnow()
        
        while True:
            if maxwait is not None:
                if datetime.utcnow() - start_time >= maxwait:
                    print "Waitfor timed out after %s" % maxwait
                    self.api.log_info_msg("WAITFOR TIMED OUT")
                    return      
            res = list()
            res.append(self.waiting_for_block())
            res.append(self.waiting_for_time())
            if frames is not None:
                res.append(self.api.dae.get_good_frames() < frames)
            if uamps is not None:
                res.append(self.api.dae.get_uamps() < uamps)
            if wait_all:
                if True not in res:
                    self.api.log_info_msg("WAITFOR EXITED NORMALLY")
                    return
            else:
                # Only need to wait for one of the settings to become false
                if False in res:
                    self.api.log_info_msg("WAITFOR EXITED NORMALLY")
                    return                  
            sleep(0.5)
            
    def wait_for_runstate(self, state, maxwaitsecs=3600, onexit=False):
        time_delta = self._get_time_delta(maxwaitsecs, 0, 0)
        state = state.upper().strip()
#        if onexit:
#            print "Waiting for state to exit:", state, "(Timeout after %d seconds)" % maxwaitsecs
#        else:
#            print "Waiting for state:", state, "(Timeout after %d seconds)" % maxwaitsecs
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
    
    def init_wait_time(self, seconds, minutes, hours, timeout_msg=""):
        self.time_delta = self._get_time_delta(seconds, minutes, hours)
        if self.time_delta is not None:
            self.start_time = datetime.utcnow()
            print 'Waiting for', str(self.time_delta.total_seconds()), 'seconds' + timeout_msg
        else:
            self.start_time = None
        
    def waiting_for_time(self):
        if self.start_time is None or self.time_delta is None:
            # Not initiated so not waiting
            return None
        else:
            if datetime.utcnow() - self.start_time >= self.time_delta:
                return False
            else:
                return True

    def _get_time_delta(self, seconds, minutes, hours):
        """
        Returns a timedelta representation of the input seconds, minutes and hours. If all parameters are None, then
        None returned, else None parameters are interpreted as 0
        """
        if any(t is not None for t in (seconds, minutes, hours)):
            num_seconds, num_minutes, num_hours = (0 if t is None else t for t in (seconds, minutes, hours))
            return timedelta(hours=num_hours, minutes=num_minutes, seconds=num_seconds)
        else:
            return None
        
    def init_wait_block(self, block, value, lowlimit, highlimit, timeout_msg=""):
        self.block = block
        if self.block is None:
            return
        self.low, self.high = self._get_block_limits(value, lowlimit, highlimit)
        if self.low is None and self.high is None:
            raise Exception("No limit(s) set for " + block)
        if self.low == self.high:
            print 'Waiting for ' + str(block) + '=' + str(self.low) + timeout_msg
        else:
            print 'Waiting for ' + str(block) + ' (lowlimit='+ str(self.low) + ', highlimit=' + str(self.high) + ')' + timeout_msg
            
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
            temp = high
            high = low
            low = temp
        return (low, high)
        
    def waiting_for_block(self):
        if self.block is None:
            return None                
        currval = self.api.get_block_value(self.block)
        flag = True
        if self.low is not None:
            flag = currval >= float(self.low)
        if self.high is not None:
            flag = currval <= float(self.high) and flag
        return not flag