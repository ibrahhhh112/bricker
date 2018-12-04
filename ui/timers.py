"""
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
"""

# System imports
# NONE!

# Blender imports
import bpy

# Addon imports
from .app_handlers import brickerIsActive, brickerRunningBlockingOp
from ..functions import *
from ..buttons.customize.tools import *


# def isBrickerObjVisible(scn, cm, n):
#     if cm.modelCreated or cm.animated:
#         gn = "Bricker_%(n)s_bricks" % locals()
#         if collExists(gn) and len(bpy.data.collections[gn].objects) > 0:
#             obj = bpy.data.collections[gn].objects[0]
#         else:
#             obj = None
#     else:
#         obj = bpy.data.objects.get(cm.source_name)
#     objVisible = isObjVisibleInViewport(obj)
#     return objVisible, obj


def handle_selections():
    scn = bpy.context.scene
    print(1)
    if not brickerIsActive() or brickerRunningBlockingOp():
        return 0.5
    print(2)
    obj = bpy.context.object
    # curLayers = str(list(scn.layers))
    # # if scn.layers changes and active object is no longer visible, set scn.cmlist_index to -1
    # if scn.Bricker_last_layers != curLayers:
    #     scn.Bricker_last_layers = curLayers
    #     curObjVisible = False
    #     if scn.cmlist_index != -1:
    #         cm0 = scn.cmlist[scn.cmlist_index]
    #         curObjVisible, _ = isBrickerObjVisible(scn, cm0, cm0.source_name)
    #     if not curObjVisible or scn.cmlist_index == -1:
    #         setIndex = False
    #         for i, cm in enumerate(scn.cmlist):
    #             if i != scn.cmlist_index:
    #                 nextObjVisible, obj = isBrickerObjVisible(scn, cm, cm.source_name)
    #                 if nextObjVisible and bpy.context.object == obj:
    #                     scn.cmlist_index = i
    #                     setIndex = True
    #                     break
    #         if not setIndex:
    #             scn.cmlist_index = -1
    # TODO: Check if active object (with active cmlist index) is no longer visible
    # if scn.cmlist_index changes, select and make source or Brick Model active
    if scn.Bricker_last_cmlist_index != scn.cmlist_index and scn.cmlist_index != -1:
        scn.Bricker_last_cmlist_index = scn.cmlist_index
        cm = scn.cmlist[scn.cmlist_index]
        source = bpy.data.objects.get(cm.source_name)
        if source and cm.version[:3] != "1_0":
            if cm.modelCreated:
                n = cm.source_name
                bricks = getBricks()
                if bricks and len(bricks) > 0:
                    select(bricks, active=True, only=True)
                    scn.Bricker_last_active_object_name = bpy.context.object.name
            elif cm.animated:
                n = cm.source_name
                cf = scn.frame_current
                if cf > cm.stopFrame:
                    cf = cm.stopFrame
                elif cf < cm.startFrame:
                    cf = cm.startFrame
                gn = "Bricker_%(n)s_bricks_f_%(cf)s" % locals()
                if len(bpy.data.collections[gn].objects) > 0:
                    select(list(bpy.data.collections[gn].objects), active=True, only=True)
                    scn.Bricker_last_active_object_name = bpy.context.object.name
            else:
                select(source, active=True, only=True)
            scn.Bricker_last_active_object_name = source.name
        else:
            for i,cm in enumerate(scn.cmlist):
                if cm.source_name == scn.Bricker_active_object_name:
                    deselectAll()
                    break
    # if active object changes, open Brick Model settings for active object
    elif obj and scn.Bricker_last_active_object_name != obj.name and len(scn.cmlist) > 0 and (scn.cmlist_index == -1 or scn.cmlist[scn.cmlist_index].source_name != "") and bpy.context.object.type == "MESH":
        scn.Bricker_last_active_object_name = obj.name
        beginningString = "Bricker_"
        if obj.name.startswith(beginningString):
            usingSource = False
            frameLoc = obj.name.rfind("_bricks")
            if frameLoc == -1:
                frameLoc = obj.name.rfind("_brick_")
                if frameLoc == -1:
                    frameLoc = obj.name.rfind("_parent")
            if frameLoc != -1:
                scn.Bricker_active_object_name = obj.name[len(beginningString):frameLoc]
        else:
            usingSource = True
            scn.Bricker_active_object_name = obj.name
        for i,cm in enumerate(scn.cmlist):
            if createdWithUnsupportedVersion(cm) or cm.source_name != scn.Bricker_active_object_name or (usingSource and cm.modelCreated):
                continue
            scn.cmlist_index = i
            scn.Bricker_last_cmlist_index = scn.cmlist_index
            if obj.isBrick:
                # adjust scn.active_brick_detail based on active brick
                x0, y0, z0 = strToList(getDictKey(obj.name))
                cm.activeKey = (x0, y0, z0)
            return 0.2
        # if no matching cmlist item found, set cmlist_index to -1
        scn.cmlist_index = -1
    return 0.2


def prevent_user_from_viewing_storage_scene(scene):
    scn = bpy.context.scene
    if not brickerIsActive() or brickerRunningBlockingOp() or bpy.props.Bricker_developer_mode != 0:
        return 0.5
    if scn.name == "Bricker_storage (DO NOT MODIFY)":
        i = 0
        if bpy.data.scenes[i].name == scn.name:
            i += 1
        bpy.context.screen.scene = bpy.data.scenes[i]
        showErrorMessage("This scene is for Bricker internal use only")
        return 1.0
    return 0.1
