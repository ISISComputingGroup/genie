"""
# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2016 Science & Technology Facilities Council.
# All rights reserved.
#
# This program is distributed in the hope that it will be useful.
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License v1.0 which accompanies this distribution.
# EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM
# AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
# You should have received a copy of the Eclipse Public License v1.0
# along with this program; if not, you can obtain a copy from
# https://www.eclipse.org/org/documents/epl-v10.php or
# http://opensource.org/licenses/eclipse-1.0.php
"""

from __future__ import absolute_import

import json
import unittest
from time import sleep

from hamcrest import assert_that, has_key, has_length, is_, only_contains
from mock import Mock, patch

from genie_python.block_names import BlockNames, BlockNamesManager
from genie_python.channel_access_exceptions import UnableToConnectToPVException
from genie_python.utilities import compress_and_hex


def _activate_monitor(add_monitor_mock, expected_block_names):
    callback = add_monitor_mock.call_args[0][1]
    blockname_pv_return_value = compress_and_hex(json.dumps(expected_block_names))
    callback(blockname_pv_return_value, None, None)


def create_block_names(
    get_pv_value_mock, blocks, instrument_prefix="Prefix", get_pv_value_side_effect=None
):
    block_names = BlockNames()
    block_names_manager = BlockNamesManager(block_names, delay_before_retry_add_monitor=1)

    switch_prefix(
        get_pv_value_mock, block_names_manager, blocks, instrument_prefix, get_pv_value_side_effect
    )
    return block_names, block_names_manager


def switch_prefix(
    get_pv_value_mock,
    blocks_manager,
    blocks=None,
    instrument_prefix="Prefix",
    get_blocks_pv_value=None,
    get_pv_value_side_effect=None,
):
    """
    Switch the prefix on the pv manager, and wait for new prefix to be picked up
    :param get_pv_value_mock: mock of the get pv call
    :param blocks_manager: manager for the blocks
    :param blocks: blocks to return
    :param instrument_prefix: instruments prefix
    :param get_blocks_pv_value: string to return instead of the block names as compressed json
    """
    if get_blocks_pv_value is None:
        get_blocks_pv_value = compress_and_hex(json.dumps(blocks))
    get_pv_value_mock.return_value = get_blocks_pv_value
    get_pv_value_mock.side_effect = get_pv_value_side_effect
    original_count = get_pv_value_mock.call_count
    blocks_manager.update_prefix(instrument_prefix)

    # wait up to 3s for new pv to be accessed
    for i in range(30):
        sleep(0.1)
        if get_pv_value_mock.call_count > original_count:
            break


@patch("genie_python.genie_cachannel_wrapper.CaChannelWrapper.get_pv_value")
@patch("genie_python.genie_cachannel_wrapper.CaChannelWrapper.add_monitor")
class TestGenieAutoCompletePyConsole(unittest.TestCase):
    def test_GIVEN_no_blocks_WHEN_inspect_block_names_THEN_class_is_empty(
        self, add_monitor_mock, get_pv_value_mock
    ):
        block_names = BlockNames()

        assert_that(block_names.__dict__, is_({}))

    def test_GIVEN_no_blocks_WHEN_request_blockname_THEN_name_requested_returned(
        self, add_monitor_mock, get_pv_value_mock
    ):
        block_names = BlockNames()

        result = block_names.unknown

        assert_that(result, is_("unknown"))

    def test_GIVEN_one_block_WHEN_inspect_block_THEN_class_has_attribute_was_is_block_name(
        self, add_monitor_mock, get_pv_value_mock
    ):
        expected_block_name = "block_name"
        block_names, _ = create_block_names(get_pv_value_mock, [expected_block_name])

        result = block_names.block_name

        assert_that(result, is_(expected_block_name))

    def test_GIVEN_setup_WHEN_call_callback_THEN_block_names_updated(
        self, add_monitor_mock, get_pv_value_mock
    ):
        expected_block_name = "block_name"
        block_names, _ = create_block_names(get_pv_value_mock, [])

        _activate_monitor(add_monitor_mock, [expected_block_name])
        result = block_names.block_name

        assert_that(result, is_(expected_block_name))

    def test_GIVEN_contains_blocks_WHEN_call_callback_THEN_old_block_names_deleted(
        self, add_monitor_mock, get_pv_value_mock
    ):
        expected_block_name = "block_name"
        removed_block = "to_del"
        block_names, _ = create_block_names(get_pv_value_mock, [removed_block])

        _activate_monitor(add_monitor_mock, [expected_block_name])
        result = block_names.__dict__.keys()

        assert_that(result, only_contains(expected_block_name))

    def test_GIVEN_prefix_set_WHEN_set_prefix_THEN_previous_call_back_is_cleared(
        self, add_monitor_mock, get_pv_value_mock
    ):
        call_back = Mock()
        add_monitor_mock.return_value = call_back

        block_names, blocks_name_manager = create_block_names(get_pv_value_mock, [])

        blocks_name_manager.update_prefix("new")
        sleep(1)  # wait for timer to be called

        call_back.assert_called_once()

    def test_GIVEN_pv_doesnt_exist_WHEN_setup_THEN_block_names_contains_no_blocks(
        self, add_monitor_mock, get_pv_value_mock
    ):
        block_names, _ = create_block_names(
            get_pv_value_mock,
            ["hi"],
            get_pv_value_side_effect=UnableToConnectToPVException("block name", "errro"),
        )

        result = block_names.__dict__

        assert_that(result, has_length(0))

    def test_GIVEN_pv_contains_nothing_WHEN_setup_THEN_block_names_contains_no_blocks(
        self, add_monitor_mock, get_pv_value_mock
    ):
        block_names, block_names_manager = create_block_names(get_pv_value_mock, ["hi"])
        switch_prefix(
            get_pv_value_mock, block_names_manager, instrument_prefix="", get_blocks_pv_value=""
        )

        result = block_names.__dict__

        assert_that(result, has_length(0))

    def test_GIVEN_pv_contains_non_hex_WHEN_setup_THEN_block_names_contains_no_blocks(
        self, add_monitor_mock, get_pv_value_mock
    ):
        block_names, block_names_manager = create_block_names(get_pv_value_mock, ["hi"])
        switch_prefix(
            get_pv_value_mock,
            block_names_manager,
            instrument_prefix="",
            get_blocks_pv_value="not hex",
        )

        result = block_names.__dict__

        assert_that(result, has_length(0))

    def test_GIVEN_pv_contains_non_json_WHEN_setup_THEN_block_names_contains_no_blocks(
        self, add_monitor_mock, get_pv_value_mock
    ):
        block_names, block_names_manager = create_block_names(get_pv_value_mock, ["hi"])
        get_blocks_pv_value = compress_and_hex(r"b\x\uxzlarg [  )")
        switch_prefix(
            get_pv_value_mock,
            block_names_manager,
            instrument_prefix="",
            get_blocks_pv_value=get_blocks_pv_value,
        )

        result = block_names.__dict__

        assert_that(result, has_length(0))

    def test_GIVEN_pv_doesnt_exist_on_add_monitor_WHEN_setup_THEN_add_monitor_is_retried_later(
        self, add_monitor_mock, get_pv_value_mock
    ):
        add_monitor_mock.side_effect = [UnableToConnectToPVException("block name", "errro"), None]

        expected_block = "expected_block"
        # retry happens in here while waiting for pv access
        block_names, _ = create_block_names(get_pv_value_mock, [expected_block])

        result = block_names.__dict__

        assert_that(result, only_contains(expected_block))

    def test_GIVEN_request_invalid_block_WHEN_inspect_block_THEN_attribute_error_thrown(
        self, add_monitor_mock, get_pv_value_mock
    ):
        block_names, _ = create_block_names(get_pv_value_mock, [])

        try:
            result = block_names._blocks_cant_start_with_hash
            self.fail("No exception thrown")
        except AttributeError:
            pass

    def test_GIVEN_block_is_keyword_WHEN_inspect_block_THEN_it_has_an_unscore_after_it_but_the_value_doesnt(
        self, add_monitor_mock, get_pv_value_mock
    ):
        expected_block_name = "class"
        block_names, _ = create_block_names(get_pv_value_mock, [expected_block_name])

        result = block_names.class__

        assert_that(block_names.__dict__, has_key("class__"))
        assert_that(result, is_(expected_block_name))

    def test_GIVEN_no_blocks_and_requested_block_is_followed_by_underscores_WHEN_inspect_block_THEN_it_has_an_unscore_after_it_but_the_value_doesnt(
        self, add_monitor_mock, get_pv_value_mock
    ):
        expected_block_name = "class"
        block_names, _ = create_block_names(get_pv_value_mock, [expected_block_name])

        result = block_names.class__

        assert_that(result, is_(expected_block_name))
