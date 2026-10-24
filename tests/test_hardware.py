from core import hardware


def test_sim_reads(assistant):
    out = assistant.handle("hw read temp")
    assert out.startswith("temp: ") and out.endswith("C")
    assert "unknown sensor" in assistant.handle("hw read pressure")


def test_led_and_status(assistant):
    assert assistant.handle("hw led on") == "led on"
    assert hardware.get_device().led is True
    assert "sim (connected)" in assistant.handle("hw status")


def test_usage_on_bad_input(assistant):
    assert assistant.handle("hw").startswith("usage")
    assert assistant.handle("hw led maybe").startswith("usage")


def test_serial_without_port_reports_error(assistant, monkeypatch):
    monkeypatch.setenv("SPEKTRA_HW", "serial")
    monkeypatch.delenv("SPEKTRA_SERIAL_PORT", raising=False)
    hardware.reset_device()
    assert "SPEKTRA_SERIAL_PORT" in assistant.handle("hw status")
    assert hardware.snapshot()["mode"] == "error"
