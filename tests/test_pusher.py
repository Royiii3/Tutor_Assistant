import pytest
from unittest.mock import patch, MagicMock
from pusher import BarkPusher
from parser.tutor_job import TutorJob


def test_build_message():
    pusher = BarkPusher(device_keys="test_key")
    job = TutorJob(
        id="1", raw_text="", source_group="家教群",
        address="拱墅区轴承宿舍", address_coords=None,
        subjects=["语文", "数学"], grade="初三",
        student_info="男孩", time_requirement="周末两次，一次两小时",
        teacher_requirement="", salary=160, salary_max=190,
        commute_time=25, commute_distance=5.5
    )

    msg = pusher.build_message(job)
    assert "语文 数学" in msg
    assert "拱墅区" in msg
    assert "160-190" in msg
    assert "25" in msg


def test_push_success():
    pusher = BarkPusher(device_keys="test_key")
    job = TutorJob(
        id="1", raw_text="", source_group="家教群",
        address="拱墅区", address_coords=None,
        subjects=["数学"], grade="初三",
        student_info="", time_requirement="周末",
        teacher_requirement="", salary=160, salary_max=None,
        commute_time=20, commute_distance=None
    )

    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"code": 200})
        result = pusher.push(job)
        assert result is True


def test_push_no_key():
    pusher = BarkPusher(device_keys="YOUR_BARK_KEY")
    job = TutorJob(
        id="1", raw_text="", source_group="家教群",
        address="拱墅区", address_coords=None,
        subjects=["数学"], grade="初三",
        student_info="", time_requirement="周末",
        teacher_requirement="", salary=160, salary_max=None,
        commute_time=20, commute_distance=None
    )

    result = pusher.push(job)
    assert result is False
