"""
Copyright (C) 2017 Bricks Brought to Life
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
"""

# System imports
# NONE!

# Blender imports
import bpy
from bpy.types import Operator
from bpy.props import *

# Addon imports
from ..functions.common import *


class move_to_layer_override(Operator):
    """Move to Layer"""
    bl_idname = "object.move_to_layer"
    bl_label = "Move to Layer"
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        # return context.active_object is not None
        return True

    def execute(self, context):
        try:
            self.runMove(context)
        except:
            handle_exception()
        return {'FINISHED'}

    def invoke(self, context, event):
        idxs = [i for i in range(20)]
        for obj in context.selected_objects:
            for i in idxs:
                layer = obj.layers[i]
                if layer:
                    self.layers[i] = True
                    idxs.remove(i)
        # Run confirmation popup for delete action
        return context.window_manager.invoke_props_popup(self, event)

    ###################################################
    # class variables

    # This does not behave like scn.layers.
    # only one should be selected unless shift is held
    layers = BoolVectorProperty(
		name="Layers",
		subtype="LAYER",
		description="Object Layers",
		size=20,
		)

    ################################################
    # class methods

    def runMove(self, context):
        scn = context.scene
        for obj in bpy.context.selected_objects:
            obj.layers = self.layers
            if obj.isBrickifiedObject:
                continue
            if obj.cmlist_id == -1:
                continue
            cm = getItemByID(scn.cmlist, obj.cmlist_id)
            if not cm.animated:
                continue
            n = cm.source_name
            for f in range(cm.lastStartFrame, cm.lastStopFrame + 1):
                bricksCurF = bpy.data.objects.get("Bricker_%(n)s_bricks_f_%(f)s" % locals())
                if bricksCurF.name != obj.name:
                    bricksCurF.layers = self.layers
