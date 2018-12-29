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
import time
import os

# Blender imports
import bpy
from bpy.types import Operator

# Addon imports
from ..functions import *


class BrickerRevertSettings(Operator):
    """Revert Matrix settings to save model customizations"""
    bl_idname = "bricker.revert_matrix_settings"
    bl_label = "Revert Matrix Settings"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns False) """
        scn = bpy.context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        if matrixReallyIsDirty(cm):
            return True
        return False

    def execute(self, context):
        try:
            self.revertMatrixSettings()
        except:
            handle_exception()
        return{"FINISHED"}

    ################################################
    # class methods

    def revertMatrixSettings(self, cm=None):
        cm = cm or getActiveContextInfo()[1]
        regularSettings = [cm.brickHeight, cm.gap, cm.brickType, cm.distOffset[0], cm.distOffset[1], cm.distOffset[2], cm.includeTransparency, cm.customObjectName1, cm.customObjectName2, cm.customObjectName3, cm.useNormals, cm.verifyExposure, cm.insidenessRayCastDir, cm.castDoubleCheckRays, cm.brickShell, cm.calculationAxes]
        settings = cm.lastMatrixSettings.split(",")
        cm.brickHeight = float(settings[0])
        cm.gap = float(settings[1])
        cm.brickType = settings[2]
        cm.distOffset[0] = float(settings[3])
        cm.distOffset[1] = float(settings[4])
        cm.distOffset[2] = float(settings[5])
        cm.includeTransparency = str_to_bool(settings[6])
        cm.customObject1 = settings[7]
        cm.customObject2 = settings[8]
        cm.customObject3 = settings[9]
        cm.useNormals = str_to_bool(settings[10])
        cm.verifyExposure = str_to_bool(settings[11])
        cm.insidenessRayCastDir = settings[12]
        cm.castDoubleCheckRays = str_to_bool(settings[13])
        cm.brickShell = settings[14]
        cm.calculationAxes = settings[15]
        if cm.lastIsSmoke:
            cm.smokeDensity = settings[16]
            cm.smokeQuality = settings[17]
            cm.smokeBrightness = settings[18]
            cm.smokeSaturation = settings[19]
            cm.flameColor = settings[20]
            cm.flameIntensity = settings[21]
        cm.matrixIsDirty = False

    ################################################
