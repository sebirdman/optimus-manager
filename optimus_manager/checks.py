import os
import dbus
from optimus_manager.bash import exec_bash, BashError


class CheckError(Exception):
    pass


def is_gpu_powered():

    state = exec_bash("cat /proc/acpi/bbswitch | cut -d' ' -f 2").stdout.decode('utf-8')[:-1]
    return state == "ON"


def is_pat_available():
    try:
        exec_bash("grep -E '^flags.+ pat( |$)' /proc/cpuinfo")
        return True
    except BashError:
        return False


def read_gpu_mode():
    try:
        exec_bash("glxinfo")
    except BashError as e:
        raise CheckError("Cannot find the current mode : %s" % str(e))

    try:
        exec_bash("glxinfo | grep NVIDIA")
        return "nvidia"
    except BashError:
        return "intel"


def is_module_available(module_name):

    try:
        exec_bash("modinfo %s" % module_name)
    except BashError:
        return False
    else:
        return True


def get_current_display_manager():

    if not os.path.isfile("/etc/systemd/system/display-manager.service"):
        raise CheckError("No display-manager.service file found")

    dm_service_path = os.path.realpath("/etc/systemd/system/display-manager.service")
    dm_service_filename = os.path.split(dm_service_path)[-1]
    dm_name = os.path.splitext(dm_service_filename)[0]

    return dm_name


def using_patched_GDM():

    folder_path_1 = "/etc/gdm/Prime"
    folder_path_2 = "/etc/gdm3/Prime"

    return (os.path.isdir(folder_path_1) or os.path.isdir(folder_path_2))


def is_xorg_intel_module_available():
    return os.path.isfile("/usr/lib/xorg/modules/drivers/intel_drv.so")


def is_login_manager_active():
    return _is_service_active("display-manager")


def is_daemon_active():
    return _is_service_active("optimus-manager")


def is_bumblebeed_service_active():
    return _is_service_active("bumblebeed")


def _is_service_active(service_name):

    try:
        system_bus = dbus.SystemBus()
    except dbus.exceptions.DBusException:
        print("WARNING : Cannot communicate with the DBus system bus to check status of %s. Is DBus running ? Falling back to bash commands" % service_name)
        return _is_service_active_bash(service_name)
    else:
        return _is_service_active_dbus(system_bus, service_name)

def _is_service_active_dbus(system_bus, service_name):

    systemd = system_bus.get_object("org.freedesktop.systemd1", "/org/freedesktop/systemd1")

    try:
        unit_path = systemd.GetUnit("%s.service" % service_name, dbus_interface="org.freedesktop.systemd1.Manager")
    except dbus.exceptions.DBusException:
        return False

    optimus_manager_interface = system_bus.get_object("org.freedesktop.systemd1", unit_path)
    properties_manager = dbus.Interface(optimus_manager_interface, 'org.freedesktop.DBus.Properties')
    state = properties_manager.Get("org.freedesktop.systemd1.Unit", "SubState")

    return (state == "running")


def _is_service_active_bash(service_name):

    try:
        exec_bash("systemctl is-active %s" % service_name)
    except BashError:
        return False
    else:
        return True
