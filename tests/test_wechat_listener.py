import pytest
from unittest.mock import MagicMock, patch
from wechat_listener import WeChatListener


def test_listener_initialization():
    listener = WeChatListener()
    assert listener is not None


def test_should_process_group_message():
    listener = WeChatListener(target_groups=["家教群1"])
    msg = {"is_group": True, "name": "家教群1", "text": "测试"}
    assert listener._should_process(msg) is True


def test_should_not_process_non_target_group():
    listener = WeChatListener(target_groups=["家教群1"])
    msg = {"is_group": True, "name": "其他群", "text": "测试"}
    assert listener._should_process(msg) is False
