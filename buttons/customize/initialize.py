# Copyright (C) 2018 Christopher Gearhart
# chris@bblanimation.com
# http://bblanimation.com/
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# System imports
# NONE!

# Blender imports
import bpy
from bpy.types import Operator

# Addon imports
from .undo_stack import *
from ...ui.app_handlers import brickerRunningBlockingOp
from ...functions import *
from ...ui.cmlist_actions import *


class BRICKER_OT_initialize(Operator):
    """ initializes undo stack for changes to the BFM cache """
    bl_category = "Bricker"
    bl_idname = "bricker.initialize"
    bl_label = "Initialize Bricker"
    bl_space_type  = 'VIEW_3D'
    bl_region_type = 'TOOLS'

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        if bpy.props.bricker_initialized:
            return False
        return True

    def modal(self, context, event):
        scn = bpy.context.scene
        if self.stop:
            self.cancel(context)
            return {"CANCELLED"}
        if not self.undo_stack.isUpdating() and not brickerRunningBlockingOp() and scn.cmlist_index != -1:
            global python_undo_state
            cm = scn.cmlist[scn.cmlist_index]
            if cm.id not in python_undo_state:
                python_undo_state[cm.id] = 0
            # handle undo
            elif python_undo_state[cm.id] > cm.blender_undo_state:
                self.undo_stack.undo_pop()
                tag_redraw_areas("VIEW_3D")
            # handle redo
            elif python_undo_state[cm.id] < cm.blender_undo_state:
                self.undo_stack.redo_pop()
                tag_redraw_areas("VIEW_3D")
        return {"PASS_THROUGH"}

    def execute(self, context):
        # add new scn.cmlist item
        if self.action == "ADD":
            CMLIST_OT_list_action.addItem()
        for cm in context.scene.cmlist:
            cm.customObject1 = bpy.data.objects.get("Six-Sided Cube (high)")
        # run modal
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def cancel(self, context):
        pass

    ################################################
    # initialization method

    def __init__(self):
        scn = bpy.context.scene
        self.undo_stack = UndoStack.get_instance()
        self.stop = False
        bpy.props.bricker_initialized = True
        if self.action == "NONE":
            self.report({"INFO"}, "Bricker initialized")

    ###################################################
    # class variables

    action = bpy.props.EnumProperty(
        items=(
            ("NONE", "None", ""),
            ("ADD", "Add Model", ""),
        ),
        default="NONE"
    )

    ################################################
    # class methods

    @staticmethod
    def killModal():
        self.stop = True

    ################################################
    # event handling functions

    # def in_context_region(self, context, event):
    #     e_x = event.mouse_region_x  # left/right
    #     e_y = event.mouse_region_y  # up/down
    #     r_w = context.region.width  # left/right
    #     r_h = context.region.height # up/down
    #     return e_x > 0 and e_x < r_w and e_y > 0 and e_y < r_h
    #
    # def pressed(self, action, event):
    #     # initialize kms
    #     wm = bpy.context.window_manager
    #     screen_kms = wm.keyconfigs['Blender'].keymaps['Screen']
    #
    #     # get km based on action
    #     if action.upper() == "UNDO":
    #         km = screen_kms.keymap_items['ed.undo']
    #     elif action.upper() == "REDO":
    #         km = screen_kms.keymap_items['ed.redo']
    #     else:
    #         km = None
    #
    #     # check if event equivalent to action km
    #     if (km and
    #         km.alt == event.alt and
    #         km.ctrl == event.ctrl and
    #         km.oskey == event.oskey and
    #         km.shift == event.shift and
    #         km.value == event.value and
    #         km.type == event.type):
    #         return True
    #     else:
    #         return False
