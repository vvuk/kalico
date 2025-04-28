# Firmware management for Klipper
#
# Copyright (C) 2025 Kalico Developers
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import logging
import klippy
import os
import difflib
from typing import Dict, List, Optional, Tuple, Any, Set

class FirmwareManager:
    def __init__(self, config) -> None:
        self.printer = config.get_printer()
        self.firmware_configs: Dict[str, Dict[str, Any]] = {}
        
        # Register commands
        self.gcode = self.printer.lookup_object('gcode')
        self.gcode.register_command(
            'FIRMWARE_QUERY', self.cmd_FIRMWARE_QUERY,
            desc=self.cmd_FIRMWARE_QUERY_help)
        self.gcode.register_command(
            'FIRMWARE_UPDATE', self.cmd_FIRMWARE_UPDATE,
            desc=self.cmd_FIRMWARE_UPDATE_help)
        
        # Register for MCU config sections
        self.printer.register_event_handler("klippy:connect", self._handle_connect)
    
    def _find_board_cfg(self, board_name: str) -> Optional[Dict[str, Any]]:
        """Find board configuration by name with fuzzy matching for suggestions"""
        board_name = board_name.lower().strip()
        # Look in the toplevel directory under boards (one level up from klippy)
        boards_dir = os.path.join(os.path.dirname(os.path.dirname(klippy.__file__)), 'boards')
        
        # Check for exact match first
        board_file = os.path.join(boards_dir, f"{board_name}.cfg")
        if os.path.exists(board_file):
            with open(board_file, 'r') as f:
                return {'name': board_name, 'path': board_file, 'content': f.read()}
        
        # No exact match, collect all board names for fuzzy matching
        board_names: Set[str] = set()
        for filename in os.listdir(boards_dir):
            if filename.endswith('.cfg'):
                board_names.add(filename[:-4].lower())  # Remove .cfg extension
        
        # Find similar board names using difflib
        similar_boards = difflib.get_close_matches(board_name, list(board_names), n=5, cutoff=0.6)
        
        # If we have similar boards, construct a helpful error message
        if similar_boards:
            similar_str = "\n  ".join(similar_boards)
            msg = f"Firmware board '{board_name}' not found. Similar boards:\n  {similar_str}"
            logging.info(msg)
        else:
            msg = f"Firmware board '{board_name}' not found and no similar boards detected"
        raise self.printer.config_error(msg)
    
    def _handle_connect(self) -> None:
        # Look for all firmware sections and associate them with their MCUs
        config = self.printer.lookup_object('configfile').config
        for section in config.get_prefix_sections('firmware '):
            section_name = section.get_name()
            mcu_name = section_name[9:] # Remove 'firmware ' prefix
            
            # Check if there is a corresponding MCU
            try:
                mcu = self.printer.lookup_object('mcu ' + mcu_name)
            except self.printer.config_error as e:
                raise self.printer.config_error(
                    f"Firmware config for non-existent MCU '{mcu_name}'")

            board_name = section.get('board')
            board = self._find_board_cfg(board_name)

            # Store firmware config for this MCU
            self.firmware_configs[mcu_name] = {
                'board_name': board_name,
                'board': board,
                'mcu': mcu,
                'config': section
            }
            logging.info(f"Registered firmware config for MCU '{mcu_name}': board={board_name}")
    
    def _get_target_mcus(self, mcu_name: Optional[str] = None) -> List[Tuple[str, Dict[str, Any]]]:
        """Helper to get a list of MCUs to operate on based on input"""
        if mcu_name is not None:
            # Specific MCU requested
            if mcu_name not in self.firmware_configs:
                raise self.gcode.error(f"No firmware config for MCU '{mcu_name}'")
            return [(mcu_name, self.firmware_configs[mcu_name])]
        
        # All MCUs requested
        if not self.firmware_configs:
            return []
        return list(self.firmware_configs.items())
    
    cmd_FIRMWARE_QUERY_help = "Query firmware information for MCUs"
    def cmd_FIRMWARE_QUERY(self, gcmd) -> None:
        mcu_name = gcmd.get('MCU', None)
        target_mcus = self._get_target_mcus(mcu_name)
        
        if not target_mcus:
            gcmd.respond_info("No firmware configurations found")
            return
            
        for mcu_name, fw_config in target_mcus:
            mcu_obj = fw_config['mcu']
            msgparser = mcu_obj._serial.get_msgparser()
            version, build_versions = msgparser.get_version_info()
            app = msgparser.get_app_info()
            
            gcmd.respond_info(
                f"MCU '{mcu_name}':\n"
                f"  Board: {fw_config['board_name']}\n"
                f"  Application: {app}\n"
                f"  Version: {version}\n"
                f"  Build: {build_versions}"
            )
    
    cmd_FIRMWARE_UPDATE_help = "Update firmware for MCUs"
    def cmd_FIRMWARE_UPDATE(self, gcmd) -> None:
        mcu_name = gcmd.get('MCU', None)
        target_mcus = self._get_target_mcus(mcu_name)
        
        if not target_mcus:
            gcmd.respond_info("No firmware configurations found")
            return
            
        for mcu_name, fw_config in target_mcus:
            gcmd.respond_info(f"Firmware update for MCU '{mcu_name}' not implemented yet")

def load_config(config) -> FirmwareManager:
    return FirmwareManager(config)
