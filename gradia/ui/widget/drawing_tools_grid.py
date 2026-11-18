# Copyright (C) 2025 Alexander Vanhee, tfuxu
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Optional, Callable
from gi.repository import Gtk, GObject
from gradia.overlay.drawing_actions import DrawingMode
from gradia.backend.settings import Settings
from gradia.backend.tool_config import ToolConfig, ToolGroupConfig
settings = Settings()

class DrawingToolsGrid(Gtk.Grid):
    __gtype_name__ = "GradiaDrawingToolsGrid"

    __gsignals__ = {
        "tool-changed": (GObject.SignalFlags.RUN_FIRST, None, (object,))
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_row_spacing(9)
        self.set_column_spacing(18)
        self.set_column_homogeneous(True)
        self.set_row_homogeneous(True)

        self._buttons = {}
        self._current_tool = None
        self._tool_configs = {}
        self._groups = {group.name: group for group in ToolGroupConfig.get_all_groups()}

        self._create_tool_buttons()

        self.connect("realize", self._on_realize)

    def _on_realize(self, widget):
        initial_mode = DrawingMode(settings.draw_mode)
        self._select_tool(initial_mode)
        if initial_mode in self._tool_configs:
            self._current_tool = initial_mode
            self.emit("tool-changed", self._tool_configs[initial_mode])

        widget.disconnect_by_func(self._on_realize)

    def _create_tool_button(self, slot, icon: str, tooltip: str, column: int, row: int):
        button = Gtk.ToggleButton(
            icon_name=icon,
            tooltip_text=tooltip,
            width_request=40,
            height_request=40,
            css_classes=["flat", "circular"]
        )

        button.get_first_child().set_pixel_size(18)

        self._buttons[slot] = button

        button.connect("toggled", self._on_button_toggled, slot)

        self.attach(button, column, row, 1, 1)

    def _create_tool_buttons(self):
        tools = ToolConfig.get_all_tools_positions()

        for tool_config in tools:
            self._tool_configs[tool_config.mode] = tool_config

            if tool_config.group is None:
                self._create_tool_button(tool_config.mode, tool_config.icon, tool_config.mode.label(),
                                         tool_config.column, tool_config.row)
            elif tool_config.group not in self._buttons:
                group = self._groups[tool_config.group]
                self._create_tool_button(group.name, group.icon, group.label, group.column, group.row)

    def _get_slot(self, mode: DrawingMode):
        tool_config = self._tool_configs.get(mode)
        if tool_config and tool_config.group:
            return tool_config.group
        return mode

    def get_group_mode(self, group_name: str) -> DrawingMode:
        group = self._groups[group_name]
        try:
            mode = DrawingMode(settings.shape_mode)
        except ValueError:
            return group.default_mode
        if self._get_slot(mode) != group_name:
            return group.default_mode
        return mode

    def _on_button_toggled(self, button: Gtk.ToggleButton, slot):
        mode = self.get_group_mode(slot) if slot in self._groups else slot

        if button.get_active():
            for other_slot, other_button in self._buttons.items():
                if other_slot != slot and other_button.get_active():
                    other_button.handler_block_by_func(self._on_button_toggled)
                    other_button.set_active(False)
                    other_button.handler_unblock_by_func(self._on_button_toggled)

            self._set_current_tool(mode)
        else:
            if self._get_slot(self._current_tool) == slot:
                button.handler_block_by_func(self._on_button_toggled)
                button.set_active(True)
                button.handler_unblock_by_func(self._on_button_toggled)

    def _set_current_tool(self, mode: DrawingMode):
        old_tool = self._current_tool
        self._current_tool = mode

        settings.draw_mode = mode.value

        if old_tool != mode:
            tool_config = self._tool_configs[mode]
            self.emit("tool-changed", tool_config)

    def _select_tool(self, mode: DrawingMode):
        slot = self._get_slot(mode)
        if slot not in self._buttons:
            return

        if slot in self._groups:
            settings.shape_mode = mode.value

        button = self._buttons[slot]
        if button.get_active():
            self._set_current_tool(mode)
        else:
            button.set_active(True)

    def get_current_tool(self) -> Optional[ToolConfig]:
        if self._current_tool:
            return self._tool_configs[self._current_tool]
        return None

    def set_current_tool(self, mode: DrawingMode):
        self._select_tool(mode)

    def set_secondary_highlight_tool(self, mode: Optional[DrawingMode]):
        for button in self._buttons.values():
            button.add_css_class("flat")
            button.remove_css_class("accent")
        slot = self._get_slot(mode) if mode else None
        if slot in self._buttons:
            self._buttons[slot].remove_css_class("flat")
            self._buttons[slot].add_css_class("accent")
