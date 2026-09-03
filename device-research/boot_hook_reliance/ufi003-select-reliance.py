#!/usr/bin/python3
"""Ensure the built-in Reliance software MCFG is active before ModemManager."""

import sys
import time
import re
import subprocess
import gi

gi.require_version("Qmi", "1.0")
from gi.repository import Gio, GLib, Qmi


DEVICE = "/dev/wwan0qmi0"
TARGET = bytes.fromhex("F865200A379452738A569BADC13EED9FEB5C6CF4")
loop = GLib.MainLoop()
state = {"ok": False, "activation_requested": False}


def log(message):
    print(f"ufi003-reliance-mcfg: {message}", flush=True)


def fail(message):
    log(f"ERROR: {message}")
    loop.quit()


def unpack_id(value):
    if isinstance(value, tuple):
        value = value[-1]
    return bytes(value)


def request_activate(client):
    state["activation_requested"] = True
    client.connect("activate-config", on_activate_indication)
    request = Qmi.MessagePdcActivateConfigInput.new()
    request.set_config_type(Qmi.PdcConfigurationType.SOFTWARE)
    request.set_token(3)
    log("activating selected software config")
    client.activate_config(request, 10, None, on_activate_response)
    GLib.timeout_add_seconds(12, on_activation_grace)


def on_activation_grace():
    if state["activation_requested"] and not state["ok"]:
        # This MPSS intentionally drops the QMI endpoint before returning the
        # normal Activate response/indication.
        log("QMI endpoint cycled after activation; proceeding to verification")
        state["ok"] = True
        loop.quit()
    return GLib.SOURCE_REMOVE


def request_set(client):
    client.connect("set-selected-config", on_set_indication)
    request = Qmi.MessagePdcSetSelectedConfigInput.new()
    request.set_type_with_id_v2(Qmi.PdcConfigurationType.SOFTWARE, list(TARGET))
    request.set_token(2)
    log("setting Reliance as pending software config")
    client.set_selected_config(request, 10, None, on_set_response)


def on_get_indication(client, output):
    try:
        code = output.get_indication_result()
        if code != 0:
            fail(f"get-selected indication error {code}")
            return
        try:
            active = unpack_id(output.get_active_id())
        except GLib.Error:
            active = b""
        try:
            pending = unpack_id(output.get_pending_id())
        except GLib.Error:
            pending = b""
        log(f"active={active.hex().upper() or 'NONE'} pending={pending.hex().upper() or 'NONE'}")
        if active == TARGET:
            log("Reliance already active; no modem restart required")
            state["ok"] = True
            loop.quit()
        elif pending == TARGET:
            request_activate(client)
        else:
            request_set(client)
    except Exception as exc:
        fail(exc)


def on_get_response(client, result):
    try:
        client.get_selected_config_finish(result).get_result()
    except Exception as exc:
        fail(exc)


def on_set_indication(client, output):
    try:
        code = output.get_indication_result()
        if code != 0:
            fail(f"set-selected indication error {code}")
            return
        log("Reliance selected successfully")
        request_activate(client)
    except Exception as exc:
        fail(exc)


def on_set_response(client, result):
    try:
        client.set_selected_config_finish(result).get_result()
    except Exception as exc:
        fail(exc)


def on_activate_indication(client, output):
    try:
        code = output.get_indication_result()
        if code != 0:
            fail(f"activate indication error {code}")
            return
        log("activation accepted; modem restart expected")
        state["ok"] = True
        loop.quit()
    except Exception as exc:
        fail(exc)


def on_activate_response(client, result):
    try:
        client.activate_config_finish(result).get_result()
    except Exception as exc:
        # The endpoint may disappear as part of the intentional modem restart.
        if state["activation_requested"]:
            log(f"activation response ended with modem restart: {exc}")
            state["ok"] = True
            loop.quit()
        else:
            fail(exc)


def on_allocated(device, result):
    try:
        client = device.allocate_client_finish(result)
        state["client"] = client
        client.connect("get-selected-config", on_get_indication)
        request = Qmi.MessagePdcGetSelectedConfigInput.new()
        request.set_config_type(Qmi.PdcConfigurationType.SOFTWARE)
        request.set_token(1)
        client.get_selected_config(request, 10, None, on_get_response)
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


def on_timeout():
    fail("timed out")
    return GLib.SOURCE_REMOVE


for _ in range(80):
    if Gio.File.new_for_path(DEVICE).query_exists(None):
        break
    time.sleep(0.5)
else:
    log("ERROR: QMI device did not appear")
    sys.exit(1)

GLib.timeout_add_seconds(30, on_timeout)
Qmi.Device.new(Gio.File.new_for_path(DEVICE), None, on_device_new)
loop.run()

if state["ok"] and state["activation_requested"]:
    # Keep ModemManager behind the unit until the QMI node cycles and settles.
    disappeared = False
    for _ in range(20):
        if not Gio.File.new_for_path(DEVICE).query_exists(None):
            disappeared = True
            break
        time.sleep(0.5)
    if disappeared:
        for _ in range(60):
            if Gio.File.new_for_path(DEVICE).query_exists(None):
                time.sleep(3)
                break
            time.sleep(0.5)
        else:
            log("ERROR: QMI device did not return after activation")
            sys.exit(1)

    # Verify the result through a fresh PDC client after the endpoint reset.
    for _ in range(12):
        try:
            result = subprocess.run(
                ["/usr/bin/qmicli", "-d", DEVICE, "--pdc-list-configs=software"],
                text=True,
                capture_output=True,
                timeout=8,
                check=False,
            )
            if result.returncode == 0 and re.search(
                r"Description:\s+Commercial-Reliance.*?Status:\s+Active",
                result.stdout,
                re.DOTALL,
            ):
                log("verified Reliance active after modem restart")
                break
        except subprocess.TimeoutExpired:
            pass
        time.sleep(1)
    else:
        log("ERROR: Reliance was not active after activation")
        sys.exit(1)

sys.exit(0 if state["ok"] else 1)
