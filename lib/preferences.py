'''
Copyright (C) 2018 Bricks Brought to Life
http://bblanimation.com/
chris@bblanimation.com

Created by Christopher Gearhart

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

# Blender imports
import bpy
from bpy.types import AddonPreferences
from bpy.props import *

# updater import
from .. import addon_updater_ops

class BRICKER_PT_preferences(AddonPreferences):
    bl_idname = __package__[:__package__.index(".lib")]

    # Bricker preferences
    brickHeightDefault: bpy.props.EnumProperty(
        name="Default Brick Height Setting",
        description="Method for setting default 'Model Height' value when new model is added",
        items=[("RELATIVE", "Relative (recommended)", "'Model Height' setting defaults to fixed number of bricks tall when new model is added"),
               ("ABSOLUTE", "Absolute", "'Model Height' setting defaults to fixed height in decimeters when new model is added")],
        default="RELATIVE")
    relativeBrickHeight: bpy.props.IntProperty(
        name="Model Height (bricks)",
        description="Default height for bricker models in bricks (standard deviation of 1 brick)",
        min=1,
        default=20)
    absoluteBrickHeight: bpy.props.FloatProperty(
        name="Brick Height (dm)",
        description="Default brick height in decimeters",
        min=0.00001,
        precision=3,
        default=0.096)

	# addon updater preferences
    auto_check_update: bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False)
    updater_intrval_months: bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0, min=0)
    updater_intrval_days: bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7, min=0)
    updater_intrval_hours: bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        min=0, max=23,
        default=0)
    updater_intrval_minutes: bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        min=0, max=59,
        default=0)

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        # draw addon prefs
        prefs = bpy.props.bricker_preferences
        row = col.row(align=True)
        split = row.split(align=True, factor=0.275)
        col = split.column(align=True)
        col.label(text="Default Brick Height:")
        col = split.column(align=True)
        split = col.split(align=True, factor=0.5)
        col = split.column(align=True)
        col.prop(prefs, "brickHeightDefault", text="")
        col = split.column(align=True)
        if prefs.brickHeightDefault == "RELATIVE":
            col.prop(prefs, "relativeBrickHeight")
        else:
            col.prop(prefs, "absoluteBrickHeight")

        # updater draw function
        addon_updater_ops.update_settings_ui(self,context)
