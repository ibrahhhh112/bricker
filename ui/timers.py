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
from bpy.app.handlers import persistent

# Addon imports
from .app_handlers import brickerRunningBlockingOp
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
#         obj = cm.source_obj
#     objVisible = isObjVisibleInViewport(obj)
#     return objVisible, obj


def handle_selections():
    if brickerRunningBlockingOp():
        return 0.5
    scn = bpy.context.scene
    obj = bpy.context.view_layer.objects.active
    # curLayers = str(list(scn.layers))
    # # if scn.layers changes and active object is no longer visible, set scn.cmlist_index to -1
    # if scn.Bricker_last_layers != curLayers:
    #     scn.Bricker_last_layers = curLayers
    #     curObjVisible = False
    #     if scn.cmlist_index != -1:
    #         cm0 = scn.cmlist[scn.cmlist_index]
    #         curObjVisible, _ = isBrickerObjVisible(scn, cm0, getSourceName(cm0))
    #     if not curObjVisible or scn.cmlist_index == -1:
    #         setIndex = False
    #         for i, cm in enumerate(scn.cmlist):
    #             if i != scn.cmlist_index:
    #                 nextObjVisible, obj0 = isBrickerObjVisible(scn, cm, getSourceName(cm))
    #                 if nextObjVisible and obj == obj0:
    #                     scn.cmlist_index = i
    #                     setIndex = True
    #                     break
    #         if not setIndex:
    #             scn.cmlist_index = -1
    # TODO: Check if active object (with active cmlist index) is no longer visible
    # if scn.cmlist_index changes, select and make source or Brick Model active
    if scn.Bricker_last_cmlist_index != scn.cmlist_index and scn.cmlist_index != -1:
        scn.Bricker_last_cmlist_index = scn.cmlist_index
        cm, n = getActiveContextInfo()[1:]
        source = cm.source_obj
        print(1)
        if source and cm.version[:3] != "1_0":
            print(2)
            if cm.modelCreated:
                print(3)
                bricks = getBricks()
                if bricks and len(bricks) > 0:
                    print(4)
                    select(bricks, active=True, only=True)
                    scn.Bricker_last_active_object_name = obj.name
            elif cm.animated:
                cf = scn.frame_current
                if cf > cm.stopFrame:
                    cf = cm.stopFrame
                elif cf < cm.startFrame:
                    cf = cm.startFrame
                cn = "Bricker_%(n)s_bricks_f_%(cf)s" % locals()
                if len(bpy.data.collections[cn].objects) > 0:
                    select(list(bpy.data.collections[cn].objects), active=True, only=True)
                    scn.Bricker_last_active_object_name = obj.name
            else:
                select(source, active=True, only=True)
        else:
            for i,cm in enumerate(scn.cmlist):
                if getSourceName(cm) == scn.Bricker_active_object_name:
                    deselectAll()
                    break
    # if active object changes, open Brick Model settings for active object
    elif obj and scn.Bricker_last_active_object_name != obj.name and len(scn.cmlist) > 0 and (scn.cmlist_index == -1 or scn.cmlist[scn.cmlist_index].source_obj is not None) and obj.type == "MESH":
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
            if createdWithUnsupportedVersion(cm) or getSourceName(cm) != scn.Bricker_active_object_name or (usingSource and cm.modelCreated):
                continue
            scn.cmlist_index = i
            scn.Bricker_last_cmlist_index = scn.cmlist_index
            if obj.isBrick:
                # adjust scn.active_brick_detail based on active brick
                x0, y0, z0 = strToList(getDictKey(obj.name))
                cm.activeKey = (x0, y0, z0)
            tag_redraw_viewport_in_all_screens()
            return 0.05
        # if no matching cmlist item found, set cmlist_index to -1
        scn.cmlist_index = -1
        tag_redraw_viewport_in_all_screens()
    return 0.05
