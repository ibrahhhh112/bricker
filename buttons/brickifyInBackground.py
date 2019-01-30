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


class BrickerBrickifyInBackground(bpy.types.Operator):
    """ Create brick sculpture from source object mesh """
    bl_idname = "bricker.brickify_in_background"
    bl_label = "Create/Update Brick Model from Source Object"
    bl_options = {"REGISTER"}

    ################################################
    # Blender Operator methods

    def execute(self, context):
        # update data in safe_scn
        scn, cm, n = getActiveContextInfo()
        # run brickify for current frame
        if self.frame == -1:
            matrixDirty = matrixReallyIsDirty(cm)
            skipTransAndAnimData = cm.animated or (cm.splitModel or cm.lastSplitModel) and (matrixDirty or cm.buildIsDirty)
            BrickerBrickify.brickifyModel(scn, cm, n, matrixDirty, skipTransAndAnimData, source, action, origFrame)
        else:
            BrickerBrickify.brickifyCurrentFrame(self.frame, scn.frame_current, "UPDATE_ANIM" if cm.animated else "ANIMATE", cm.source_obj, inBackground=True)
        return {"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        # initialize vars
        self.safe_scn = getSafeScn()

    #############################################
    # class variables

    frame = IntProperty(default=-1)

    #############################################
