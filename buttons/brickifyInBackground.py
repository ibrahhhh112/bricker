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

# system imports
import random
import time
import bmesh
import os
import sys
import math
import json

# Blender imports
import bpy
from mathutils import Matrix, Vector, Euler
props = bpy.props

# Addon imports
from .customize.undo_stack import *
from .materials import BrickerApplyMaterial
from .delete import BrickerDelete
from .bevel import BrickerBevel
from .cache import *
from ..lib.bricksDict import *
# from ..lib.rigid_body_props import *
from ..functions import *
from ..background_processing.classes import *


class BrickerBrickifyInBackground(bpy.types.Operator):
    """ Create brick sculpture from source object mesh """
    bl_idname = "bricker.brickify_in_background"
    bl_label = "Create/Update Brick Model from Source Object"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    def execute(self, context):
        jobAdded = self.JobManager.add_job(self.job)
        if not jobAdded:
            self.report({"WARNING"}, "Job already added")
            return {"CANCELLED"}
        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.5, context.window)
        wm.modal_handler_add(self)
        return{"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type == "TIMER":
            self.JobManager.process_job(self.job, use_blend_file=True)
            job_name = self.JobManager.get_job_name(self.job)
            if self.JobManager.job_complete(self.job):
                self.report({"INFO"}, "Background process '" + job_name + "' was finished")
                scn, cm, _ = getActiveContextInfo()
                bricker_bricks = bpy.data.objects.get("Bricker_" + cm.source_obj.name + "_bricks")
                bricker_parent = bpy.data.objects.get("Bricker_" + cm.source_obj.name + "_parent")
                scn.objects.link(bricker_bricks)
                self.safe_scn.objects.link(bricker_parent)
                bricker_bricks.parent = bricker_parent
                return {"FINISHED"}
            if self.JobManager.job_dropped(self.job):
                self.report({"WARNING"}, "Background process '" + job_name + "' was dropped")
                return {"CANCELLED"}
        return {"PASS_THROUGH"}

    ################################################
    # initialization method

    def __init__(self):
        self.safe_scn = getSafeScn()
        self.JobManager = SCENE_OT_job_manager.get_instance()
        self.JobManager.timeout = 0
        brickerAddonPath = os.path.join(bpy.utils.user_resource('SCRIPTS', "addons").replace(" ", "\ "), bpy.props.bricker_module_name)
        self.job = os.path.join(brickerAddonPath, "buttons/brickifyExecution.py")
        # push to undo stack
        self.undo_stack = UndoStack.get_instance()
        self.undo_stack.undo_push('brickify', affected_ids=[cm.id])

    #############################################
