"""Inspect the libqmi PDC API exposed through GObject Introspection."""

import gi

gi.require_version("Qmi", "1.0")
from gi.repository import Gio, GLib, Qmi


def public_names(obj, needle=""):
    return [name for name in dir(obj) if not name.startswith("_") and needle in name.lower()]


print("Qmi module loaded:", Qmi)
print("Device constructors:", public_names(Qmi.Device, "new"))
print("Device methods:", public_names(Qmi.Device, "client"))
print("PDC client methods:", public_names(Qmi.ClientPdc))
print("Get-selected input:", public_names(Qmi.MessagePdcGetSelectedConfigInput))
print("Set-selected input:", public_names(Qmi.MessagePdcSetSelectedConfigInput))
print("Enums:", public_names(Qmi, "pdc"))
for item in (
    Qmi.Device.new,
    Qmi.Device.open,
    Qmi.Device.allocate_client,
    Qmi.ClientPdc.get_selected_config,
    Qmi.ClientPdc.get_selected_config_finish,
    Qmi.ClientPdc.set_selected_config,
    Qmi.MessagePdcGetSelectedConfigOutput,
    Qmi.IndicationPdcGetSelectedConfigOutput,
    Qmi.IndicationPdcSetSelectedConfigOutput,
):
    print("DOC", item, "\n", getattr(item, "__doc__", None))
print("Get-selected response methods:", public_names(Qmi.MessagePdcGetSelectedConfigOutput))
print("Get-selected indication methods:", public_names(Qmi.IndicationPdcGetSelectedConfigOutput))
print("Set-selected indication methods:", public_names(Qmi.IndicationPdcSetSelectedConfigOutput))
print("Device flags:", public_names(Qmi.DeviceOpenFlags), [(n, int(getattr(Qmi.DeviceOpenFlags, n))) for n in public_names(Qmi.DeviceOpenFlags) if n.isupper()])
print("Services:", [(n, int(getattr(Qmi.Service, n))) for n in public_names(Qmi.Service) if n in ("PDC", "DMS", "UNKNOWN")])
print("Config types:", [(n, int(getattr(Qmi.PdcConfigurationType, n))) for n in public_names(Qmi.PdcConfigurationType) if n.isupper()])
print("CID_NONE:", getattr(Qmi, "CID_NONE", "missing"))
print("Finish docs:", Qmi.Device.new_finish.__doc__, Qmi.Device.open_finish.__doc__, Qmi.Device.allocate_client_finish.__doc__)
print("Activate input:", public_names(Qmi.MessagePdcActivateConfigInput))
print("Activate output:", public_names(Qmi.MessagePdcActivateConfigOutput))
print("Activate indication:", public_names(Qmi.IndicationPdcActivateConfigOutput))
print("Activate docs:", Qmi.ClientPdc.activate_config.__doc__, Qmi.ClientPdc.activate_config_finish.__doc__)
