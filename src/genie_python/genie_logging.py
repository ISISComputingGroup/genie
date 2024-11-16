"""Logging module for genie"""

import getpass
import logging
import logging.config

import graypy


def send(self, s):
    """
    Needed otherwise graypy spits out logs if the DNS alias cannot be resolved.
    See https://github.com/ISISComputingGroup/IBEX/issues/7059
    """
    try:
        if len(s) < self.gelf_chunker.chunk_size:
            super(graypy.GELFUDPHandler, self).send(s)
        else:
            for chunk in self.gelf_chunker.chunk_message(s):
                super(graypy.GELFUDPHandler, self).send(chunk)
    except Exception:
        # logging to graypy failed, silently fail rather than throwing
        pass


graypy.GELFUDPHandler.send = send

import os
import socket
from contextlib import contextmanager
from time import localtime, strftime

from genie_python.version import VERSION


class InstrumentFilter(logging.Filter):
    """For Graylog fields (https://graypy.readthedocs.io/en/latest/readme.html#adding-custom-logging-fields)"""

    def __init__(self):
        self.instrument = ""
        self.sim_mode = False
        self.genie_version = VERSION
        self.reset()

    def set_inst_name(self, inst_name):
        self.instrument = inst_name

    def set_sim_mode(self, sim_mode):
        self.sim_mode = sim_mode

    def filter(self, record):
        record.instrument = self.instrument
        record.command_called = self.command_called
        record.function_args = self.function_args
        record.function_kwargs = self.function_kwargs
        record.time_taken = self.time_taken
        record.exception_text = self.exception_text
        record.from_channel_access = str(self.from_channel_access)  # need to cast bool to str
        record.from_ibex = str(os.getenv("FROM_IBEX"))
        record.genie_version = self.genie_version
        record.is_sim_mode = str(self.sim_mode)
        self.reset()
        return True

    def reset(self):
        """
        Reset filter fields back to blank values.
        """
        self.command_called = ""
        self.function_args = ""
        self.function_kwargs = ""
        self.time_taken = 0
        self.exception_text = ""
        self.from_channel_access = False


filter = InstrumentFilter()

vhd_build_machines = ["NDHSPARE11"]


class LoggingConfigurer:
    @staticmethod
    def get_file_name():
        curr_time = localtime()
        current_date_time = strftime("%Y-%m-%d-%a", curr_time)
        return f"genie-{current_date_time}.log"

    @staticmethod
    def get_log_file_dir():
        if socket.gethostname() in vhd_build_machines:
            return os.path.join("C:", os.sep, "genie_python_logs")
        else:
            if os.name == "nt":
                return os.path.join("C:", os.sep, "Instrument", "Var", "logs", "genie_python")
            else:
                return os.path.join("/tmp/{}/genie_python".format(getpass.getuser()))

    @staticmethod
    def get_log_file_path():
        logs_dir = LoggingConfigurer.get_log_file_dir()
        filename = LoggingConfigurer.get_file_name()
        return os.path.join(logs_dir, filename)

    @staticmethod
    def get_logging_config():
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "verbose": {
                    "format": "[{asctime}] [{process:d}:{thread:d}] [{levelname}]\t{message}",
                    "style": "{",
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                }
            },
            "handlers": {
                "graypy": {
                    "level": "DEBUG",
                    "class": "graypy.GELFUDPHandler",
                    "host": "ino.isis.cclrc.ac.uk",
                    "port": 12201,
                    "formatter": "verbose",
                },
                "file": {
                    "level": "DEBUG",
                    "formatter": "verbose",
                    "class": "logging.FileHandler",
                    "filename": LoggingConfigurer.get_log_file_path(),
                    "mode": "a",
                },
            },
            "loggers": {
                "genie_python_graylogger": {
                    "handlers": ["graypy", "file"],
                    "level": "DEBUG",
                    "propagate": False,
                    "namer": LoggingConfigurer.get_file_name(),
                },
            },
        }


@contextmanager
def genie_logger():
    try:
        logging.config.dictConfig(LoggingConfigurer.get_logging_config())
        yield logging.getLogger("genie_python_graylogger")
    finally:
        logging.shutdown()


class GenieLogger:
    def __init__(self, sim_mode=False):
        self.sim_mode = sim_mode
        self.logs_dir = LoggingConfigurer.get_log_file_dir()
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)

        filter.set_sim_mode(self.sim_mode)
        with genie_logger() as logger:
            logger.addFilter(filter)

    def log_info_msg(self, message):
        with genie_logger() as logger:
            logger.info(self._get_message_with_mode(message))

    def log_command(self, function_name, arguments, command_exception, time_taken=None):
        filter.command_called = function_name
        filter.function_args = arguments
        filter.exception_text = command_exception
        if time_taken is not None:
            filter.time_taken = time_taken
        with genie_logger() as logger:
            logger.debug(self._get_message_with_mode(f"{function_name} {arguments}"))

    def log_command_error_msg(self, function_name, error_msg):
        error_msg = f"An exception has occurred as a result of the command:\n{error_msg}"
        filter.command_called = function_name
        filter.exception_text = error_msg
        with genie_logger() as logger:
            logger.error(self._get_message_with_mode(error_msg))

    def log_error_msg(self, error_msg):
        filter.exception_text = error_msg
        with genie_logger() as logger:
            logger.error(self._get_message_with_mode(error_msg))

    def log_ca_msg(self, error_msg):
        """Log the CA error (from CaChannel)"""
        filter.exception_text = error_msg
        with genie_logger() as logger:
            logger.error(self._get_message_with_mode(error_msg))

    def set_sim_mode(self, sim_mode):
        self.sim_mode = sim_mode
        filter.set_sim_mode(sim_mode)

    def _get_message_with_mode(self, msg):
        return f"(SIMULATION) {msg}" if self.sim_mode is True else msg
