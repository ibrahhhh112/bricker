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

# Addon imports
from ..functions import *
from ..lib.abs_plastic_materials import *

def addMaterialToList(self, context):
    scn, cm, n = getActiveContextInfo()
    typ = "RANDOM" if cm.materialType == "RANDOM" else "ABS"
    matObj = getMatObject(cm.id, typ=typ)
    numMats = len(matObj.data.materials)
    mat = bpy.data.materials.get(cm.targetMaterial)
    brick_mats_installed = brick_materials_installed()
    if mat is None:
        return
    elif mat.name in matObj.data.materials.keys():
        cm.targetMaterial = "Already in list!"
    elif typ == "ABS" and brick_mats_installed and mat.name not in getAbsPlasticMaterialNames():
        cm.targetMaterial = "Not ABS Plastic material"
    elif matObj is not None:
        matObj.data.materials.append(mat)
        cm.targetMaterial = ""
    if numMats < len(matObj.data.materials) and not cm.lastSplitModel:
        cm.materialIsDirty = True
