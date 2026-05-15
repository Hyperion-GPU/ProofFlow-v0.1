import pytest

from proofflow.config import test_commands_enabled as are_test_commands_enabled


@pytest.mark.parametrize("value", ["true", "1", "yes", "on", " TRUE "])
def test_test_commands_enabled_truthy_values(monkeypatch, value):
    monkeypatch.setenv("PROOFFLOW_ENABLE_TEST_COMMANDS", value)

    assert are_test_commands_enabled() is True


@pytest.mark.parametrize("value", ["", "false", "0", "no", "off", "unexpected"])
def test_test_commands_enabled_false_by_default_and_falsey_values(monkeypatch, value):
    if value:
        monkeypatch.setenv("PROOFFLOW_ENABLE_TEST_COMMANDS", value)
    else:
        monkeypatch.delenv("PROOFFLOW_ENABLE_TEST_COMMANDS", raising=False)

    assert are_test_commands_enabled() is False
