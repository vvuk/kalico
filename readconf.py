import sys
import logging

from klippy import configfile

def read_config_file(path: str):
    with open(path, "r") as f:
        return f.read().replace("\r\n", "\n")

class DummyGcode:
    def __init__(self):
        self.ready_gcode_handlers = {}

    def register_command(self, *args, **kwargs):
        pass

class DummyPrinter:
    def __init__(self, cfgfile):
        self.cfgfile = cfgfile
        self.gcode = DummyGcode()

    def get_start_args(self):
        return { 'config_file': self.cfgfile }

    def lookup_object(self, name):
        if name == "gcode":
            return self.gcode
        return None


def main():
    printer = DummyPrinter(sys.argv[1])
    prcfg = configfile.PrinterConfig(printer)
    cfg = prcfg.read_main_config()

    firmware = {}
    for section in cfg.get_prefix_sections("firmware"):
        parts = section.get_name().split()
        if len(parts) == 1:
            # main mcu
            mcu_name = "mcu"
            mcu = cfg.getsection("mcu")
        elif len(parts) == 2:
            mcu_name = parts[1]
            mcu_section_name = f"mcu {mcu_name}"
            if not cfg.has_section(mcu_section_name)
                logging.error(f"Invalid firmware section [firmware {mcu_name}]: missing [{mcu_section_name}]")
                raise
            mcu = cfg.getsection(mcu_section_name)
        else:
            logging.error(f"Invalid firmware section: [{section.get_name()}]")
            raise

        firmware[mcu_name] = { 'mcu': mcu, 'firmware': section }

def identify_mcu_version(self, mcu):
    """
    Connect to the given MCU and pull the firmware version.
    """
    pass

##
## initial-flash.py [comms] [board] 
##
## Does initial flash with either rpboot or dfu-util?
##

main()
