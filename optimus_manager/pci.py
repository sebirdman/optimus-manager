import re

from optimus_manager.bash import exec_bash, BashError

NVIDIA_VENDOR_ID = "10de"
INTEL_VENDOR_ID = "8086"


class PCIError(Exception):
    pass


def set_power_management(enabled):

    if enabled:
        _set_mode("auto")
    else:
        _set_mode("on")

def disable_card():
    _remove()

def enable_card():
    _turn_on_card()

def get_bus_ids(notation_fix=True):

    try:
        lspci_output = exec_bash("lspci -n").stdout.decode('utf-8')
    except BashError as e:
        raise PCIError("cannot run lspci -n : %s" % str(e))

    bus_ids = {}

    for line in lspci_output.splitlines():

        items = line.split(" ")

        bus_id = items[0]

        if notation_fix:
            # Xorg expects bus IDs separated by colons in decimal instead of
            # hexadecimal format without any leading zeroes and prefixed with
            # `PCI:`, so `3c:00:0` should become `PCI:60:0:0`
            bus_id = "PCI:" + ":".join(
                str(int(field, 16)) for field in re.split("[.:]", bus_id)
            )

        pci_class = items[1]
        vendor_id, product_id = items[2].split(":")

        # Display controllers are identified by a 03xx class
        if pci_class[:2] != "03":
            continue

        if vendor_id == NVIDIA_VENDOR_ID:
            if "nvidia" in bus_ids.keys():
                raise PCIError("Multiple Nvidia GPUs found !")
            bus_ids["nvidia"] = bus_id

        elif vendor_id == INTEL_VENDOR_ID:
            if "intel" in bus_ids.keys():
                raise PCIError("Multiple Intel GPUs found !")
            bus_ids["intel"] = bus_id

    if "nvidia" not in bus_ids.keys():
        raise PCIError("Cannot find Nvidia GPU in PCI devices list.")

    if "intel" not in bus_ids.keys():
        raise PCIError("Cannot find Intel GPU in PCI devices list.")

    return bus_ids

def _write_to_pci(pci_path, contents):
    try:
        with open(pci_path, "w") as f:
            f.write(contents)
    except FileNotFoundError:
        raise PCIError("Cannot find Nvidia PCI path at %s" % pci_path)
    except IOError:
        raise PCIError("Error writing to %s" % pci_path)

def _set_mode(mode):
    bus_ids = get_bus_ids(notation_fix=False)
    pci_path = "/sys/bus/pci/devices/0000:%s/power/control" % bus_ids["nvidia"]
    _write_to_pci(pci_path, mode)

def _turn_on_card():

    _set_PCI_power_mode("ON")

    time.sleep(1)

    card_online = False
    try:
        ## See if the bus_id already exists
        bus_ids = get_bus_ids(notation_fix=False)
        card_online = True
    except PCIError:
        print("Card is already on, skipping PCI rescan.")
    
    if not card_online:
        _write_to_pci("/sys/bus/pci/rescan", "1")

    _set_PCI_power_mode("ON")

def _remove():

    bus_ids = get_bus_ids(notation_fix=False)
    pci_path = "/sys/bus/pci/devices/0000:%s/remove" % bus_ids["nvidia"]
    _write_to_pci(pci_path, "1")
