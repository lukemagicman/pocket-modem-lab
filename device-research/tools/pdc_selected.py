"""Read or set the selected software PDC config through libqmi GI.

Run as root while ModemManager is stopped. With no argument, reads active/pending
IDs. With a colon-separated ID argument, sets that ID as selected and reports
the modem indication. It intentionally does not activate or reboot the modem.
"""

import sys
import gi

gi.require_version("Qmi", "1.0")
from gi.repository import Gio, GLib, Qmi


DEVICE = "/dev/wwan0qmi0"
TARGET = sys.argv[1] if len(sys.argv) > 1 else None
loop = GLib.MainLoop()
state = {}


def fail(message):
    print("ERROR:", message, file=sys.stderr)
    state["ok"] = False
    loop.quit()


def byte_id(value):
    if value is None:
        return None
    if isinstance(value, tuple):
        value = value[-1]
    return ":".join(f"{int(x):02X}" for x in value)


def on_timeout():
    fail("timed out waiting for PDC response/indication")
    return GLib.SOURCE_REMOVE


def on_get_indication(client, output):
    try:
        print("GET indication result:", output.get_indication_result())
        print("active:", byte_id(output.get_active_id()))
        try:
            pending = byte_id(output.get_pending_id())
        except GLib.Error:
            pending = None
        print("pending:", pending)
        state["ok"] = True
        loop.quit()
    except Exception as exc:
        fail(exc)


def on_set_indication(client, output):
    try:
        print("SET indication result:", output.get_indication_result())
        state["ok"] = True
        loop.quit()
    except Exception as exc:
        fail(exc)


def on_request_done(client, result, operation):
    try:
        if operation == "get":
            output = client.get_selected_config_finish(result)
        else:
            output = client.set_selected_config_finish(result)
        print(operation.upper(), "response result:", output.get_result())
    except Exception as exc:
        fail(exc)


def start_pdc(client):
    if TARGET is None:
        client.connect("get-selected-config", on_get_indication)
        request = Qmi.MessagePdcGetSelectedConfigInput.new()
        request.set_config_type(Qmi.PdcConfigurationType.SOFTWARE)
        request.set_token(1)
        client.get_selected_config(request, 10, None, on_request_done, "get")
        return

    try:
        target_bytes = [int(part, 16) for part in TARGET.split(":")]
        if len(target_bytes) != 20:
            raise ValueError("PDC ID must contain exactly 20 bytes")
    except Exception as exc:
        fail(exc)
        return
    client.connect("set-selected-config", on_set_indication)
    request = Qmi.MessagePdcSetSelectedConfigInput.new()
    request.set_type_with_id_v2(Qmi.PdcConfigurationType.SOFTWARE, target_bytes)
    request.set_token(2)
    client.set_selected_config(request, 10, None, on_request_done, "set")


def on_allocated(device, result):
    try:
        client = device.allocate_client_finish(result)
        state["client"] = client
        start_pdc(client)
    except Exception as exc:
        fail(exc)


def on_opened(device, result):
    try:
        device.open_finish(result)
        device.allocate_client(Qmi.Service.PDC, Qmi.CID_NONE, 10, None, on_allocated)
    except Exception as exc:
        fail(exc)


def on_device_new(source, result):
    try:
        device = Qmi.Device.new_finish(result)
        state["device"] = device
        device.open(Qmi.DeviceOpenFlags.EXPECT_INDICATIONS, 10, None, on_opened)
    except Exception as exc:
        fail(exc)


GLib.timeout_add_seconds(20, on_timeout)
Qmi.Device.new(Gio.File.new_for_path(DEVICE), None, on_device_new)
loop.run()
sys.exit(0 if state.get("ok") else 1)
