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
from bpy.props import *

# Addon imports
from .customize.undo_stack import *
from .materials import BrickerApplyMaterial
from .delete import BrickerDelete
from .bevel import BrickerBevel
from .cache import *
from .brickify import *
from ..lib.bricksDict import *
from ..functions import *


class BrickerBrickifyAnimInBackground(bpy.types.Operator):
    """ Create brick sculpture from source object mesh """
    bl_idname = "bricker.brickify_anim_in_background"
    bl_label = "Create/Update Brick Model from Source Object"
    bl_options = {"REGISTER"}

    ################################################
    # Blender Operator methods

    def execute(self, context):
        scn, cm, n = getActiveContextInfo()
        Bricker_parent_on = "Bricker_%(n)s_parent" % locals()
        parent0 = bpy.data.objects.get(Bricker_parent_on)
        sceneCurFrame = scn.frame_current
        curFrame = self.frame
        scn.frame_set(curFrame)
        # get duplicated source
        source = bpy.data.objects.get("Bricker_" + self.source.name + "_f_" + str(curFrame))
        scn.objects.link(source)
        scn.update()

        # get source_details and dimensions
        source_details, dimensions = getDetailsAndBounds(source)

        # update refLogo
        logo_details, refLogo = BrickerBrickify.getLogo(scn, cm, dimensions)

        # set up parent for this layer
        # TODO: Remove these from memory in the delete function, or don't use them at all
        p_name = "%(Bricker_parent_on)s_f_%(curFrame)s" % locals()
        parent = bpy.data.objects.get(p_name)
        if parent is None:
            m = bpy.data.meshes.new("%(p_name)s_mesh" % locals())
            parent = bpy.data.objects.new(p_name, m)
            parent.location = source_details.mid - parent0.location
            parent.parent = parent0
            safeUnlink(parent)
            getSafeScn().update()

        # create new bricks
        try:
            group_name = BrickerBrickify.createNewBricks(source, parent, source_details, dimensions, refLogo, logo_details, self.action, split=cm.splitModel, curFrame=curFrame, sceneCurFrame=sceneCurFrame, origSource=self.source, selectCreated=False)
        except KeyboardInterrupt:
            self.report({"WARNING"}, "Process forcably interrupted with 'KeyboardInterrupt'")
            if curFrame != cm.startFrame:
                wm.progress_end()
                cm.lastStartFrame = cm.startFrame
                cm.lastStopFrame = curFrame - 1
                scn.frame_set(sceneCurFrame)
                cm.animated = True
            return {"CANCELLED"}

        # get object with created bricks
        obj = bpy.data.groups[group_name].objects[0]
        # hide obj unless on scene current frame
        showCurObj = (curFrame == cm.startFrame and sceneCurFrame < cm.startFrame) or curFrame == sceneCurFrame or (curFrame == cm.stopFrame and sceneCurFrame > cm.stopFrame)
        if not showCurObj:
            obj.hide = True
            obj.hide_render = True
        # lock location, rotation, and scale of created bricks
        obj.lock_location = (True, True, True)
        obj.lock_rotation = (True, True, True)
        obj.lock_scale    = (True, True, True)

        # wm.progress_update(curFrame-cm.startFrame)
        # print('-'*100)
        # print("completed frame " + str(curFrame))
        # print('-'*100)
        return {"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        scn, cm, _ = getActiveContextInfo()
        # initialize vars
        self.action = "UPDATE_ANIM" if cm.animated else "ANIMATE"
        self.source = cm.source_obj
        self.safe_scn = getSafeScn()

    #############################################
    # class variables

    frame = IntProperty(default=-1)

    #############################################
