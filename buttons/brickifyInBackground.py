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
from .bevel import BRICKER_OT_bevel
from .cache import *
from .brickify import *
from ..lib.bricksDict import *
from ..functions import *


class BRICKER_OT_brickify_in_background(bpy.types.Operator):
    """ Create brick sculpture from source object mesh """
    bl_idname = "bricker.brickify_in_background"
    bl_label = "Create/Update Brick Model from Source Object"
    bl_options = {"REGISTER"}

    ################################################
    # Blender Operator methods

    def execute(self, context):
        # get active context info
        scn, cm, n = getActiveContextInfo()
        # run brickify for current frame
        if "ANIM" in self.action:
            BrickerBrickify.brickifyCurrentFrame(self.frame, self.action, inBackground=True)
        else:
            BrickerBrickify.brickifyActiveFrame(self.action)
        # save last cache to cm.BFMCache
        cm.BFMCache = json.dumps(bricker_bfm_cache[cm.id])
        return {"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        pass

    #############################################
    # class variables

    frame = IntProperty(default=-1)
    action = StringProperty(default="CREATE")

    #############################################
