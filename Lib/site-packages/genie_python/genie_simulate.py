from __future__ import absolute_import, print_function

from builtins import object
from collections import OrderedDict

import genie_python.genie_api_setup
import genie_python.genie_simulate_impl as genie_sim


def in_sim_mode():
    """
    Get whether genie_python is in simulation mode.

    Returns (bool): True if in simulation mode, False otherwise
    """
    from genie_python.genie import _genie_api

    return isinstance(_genie_api, genie_sim.API)


class Simulate(object):
    """A context manager that will put genie_python into simulation mode and out again.
    For example:
    >>> with g.sim.Simulate():
    >>>     g.begin()
    >>>     g.cset("my_block", 10)
    >>>     g.end()
    Will run only print the results of the g. commands and not change the current experiment.
    """

    def __init__(self, populate_with_current_blocks=True, initial_block_values={}):
        """
        Create the context manager.

        Args:
            populate_with_current_blocks(bool): if True the simulated environment will be populated with the current blocks
            initial_block_values(dict): If not empty, blocks will be set initially to these values; can be plain values or cget results
        """
        from genie_python import genie
        from genie_python.genie import _genie_api

        self.genie = genie
        self.previous_api = _genie_api
        self.new_api = genie_sim.API(None, None, populate_with_current_blocks)
        if populate_with_current_blocks:
            dummy_values = ["INITIAL_VALUE"] * len(self.previous_api.get_block_names())
            self.new_api.set_multiple_blocks(self.previous_api.get_block_names(), dummy_values)
            for ky, vl in initial_block_values.items():
                if isinstance(vl, OrderedDict):
                    self.new_api.set_block_value(
                        ky, vl["value"], vl["runcontrol"], vl["lowlimit"], vl["highlimit"]
                    )
                else:
                    self.new_api.set_block_value(ky, vl)

    def __enter__(self):
        print("Entering genie_python simulation mode")
        print(
            "For more information on simulation mode see https://github.com/ISISComputingGroup/ibex_user_manual/wiki/Simulating-Scripts"
        )
        genie_python.genie_api_setup._exceptions_raised = True
        self.genie._genie_api = self.new_api
        self.previous_api.logger.set_sim_mode(in_sim_mode())

    def __exit__(self, *args):
        print("Exiting genie_python simulation mode")
        genie_python.genie_api_setup._exceptions_raised = False
        self.genie._genie_api = self.previous_api
        self.genie._genie_api.logger.set_sim_mode(in_sim_mode())
