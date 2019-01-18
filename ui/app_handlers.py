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
from bpy.app.handlers import persistent
from mathutils import Vector, Euler

# Addon imports
from ..functions import *
from ..lib.bricksDict import lightToDeepCache, deepToLightCache, getDictKey
from ..lib.caches import bricker_bfm_cache
from ..buttons.customize.tools import *


def brickerRunningBlockingOp():
    wm = bpy.context.window_manager
    return hasattr(wm, "Bricker_runningBlockingOperation") and wm.Bricker_runningBlockingOperation


@persistent
def handle_animation(scene):
    scn = scene
    for i, cm in enumerate(scn.cmlist):
        if not cm.animated:
            continue
        n = getSourceName(cm)
        for cf in range(cm.lastStartFrame, cm.lastStopFrame + 1):
            curBricks = bpy.data.groups.get("Bricker_%(n)s_bricks_f_%(cf)s" % locals())
            if curBricks is None:
                continue
            adjusted_frame_current = getAnimAdjustedFrame(scn.frame_current, cm.lastStartFrame, cm.lastStopFrame)
            onCurF = adjusted_frame_current == cf
            for brick in curBricks.objects:
                # hide bricks from view and render unless on current frame
                if brick.hide == onCurF:
                    brick.hide = not onCurF
                    brick.hide_render = not onCurF
                if scn.objects.active and scn.objects.active.name.startswith("Bricker_%(n)s_bricks" % locals()) and onCurF:
                    select(brick, active=True)
                # prevent bricks from being selected on frame change
                elif brick.select:
                    brick.select = False


def isObjVisible(scn, cm, n):
    objVisible = False
    if cm.modelCreated or cm.animated:
        gn = "Bricker_%(n)s_bricks" % locals()
        if groupExists(gn) and len(bpy.data.groups[gn].objects) > 0:
            obj = bpy.data.groups[gn].objects[0]
        else:
            obj = None
    else:
        obj = cm.source_obj
    if obj:
        objVisible = False
        for i in range(20):
            if obj.layers[i] and scn.layers[i]:
                objVisible = True
    return objVisible, obj


@persistent
def handle_selections(scene):
    scn = bpy.context.scene
    if brickerRunningBlockingOp():
        return
    curLayers = str(list(scn.layers))
    # if scn.layers changes and active object is no longer visible, set scn.cmlist_index to -1
    if scn.Bricker_last_layers != curLayers:
        scn.Bricker_last_layers = curLayers
        curObjVisible = False
        if scn.cmlist_index != -1:
            cm0, n0 = getActiveContextInfo()[1:]
            curObjVisible, _ = isObjVisible(scn, cm0, n0)
        if not curObjVisible or scn.cmlist_index == -1:
            setIndex = False
            for i, cm in enumerate(scn.cmlist):
                if i != scn.cmlist_index:
                    nextObjVisible, obj = isObjVisible(scn, cm, getSourceName(cm))
                    if nextObjVisible and bpy.context.active_object == obj:
                        scn.cmlist_index = i
                        setIndex = True
                        break
            if not setIndex:
                scn.cmlist_index = -1
    # if scn.cmlist_index changes, select and make source or Brick Model active
    elif scn.Bricker_last_cmlist_index != scn.cmlist_index and scn.cmlist_index != -1:
        scn.Bricker_last_cmlist_index = scn.cmlist_index
        cm = scn.cmlist[scn.cmlist_index]
        cm, n = getActiveContextInfo()[1:]
        source = cm.source_obj
        if source and cm.version[:3] != "1_0":
            if cm.modelCreated:
                bricks = getBricks()
                if bricks and len(bricks) > 0:
                    select(bricks, active=True, only=True)
                    scn.Bricker_last_active_object_name = scn.objects.active.name
            elif cm.animated:
                cf = scn.frame_current
                if cf > cm.stopFrame:
                    cf = cm.stopFrame
                elif cf < cm.startFrame:
                    cf = cm.startFrame
                g = bpy.data.groups.get("Bricker_%(n)s_bricks_f_%(cf)s" % locals())
                if g is not None and len(g.objects) > 0:
                    select(list(g.objects), active=True, only=True)
                    scn.Bricker_last_active_object_name = scn.objects.active.name
                else:
                    scn.objects.active = None
                    deselectAll()
                    scn.Bricker_last_active_object_name = ""
            else:
                select(source, active=True, only=True)
                scn.Bricker_last_active_object_name = source.name
        else:
            for i,cm0 in enumerate(scn.cmlist):
                if getSourceName(cm0) == scn.Bricker_active_object_name:
                    deselectAll()
                    break
    # if active object changes, open Brick Model settings for active object
    elif scn.objects.active and scn.Bricker_last_active_object_name != scn.objects.active.name and len(scn.cmlist) > 0 and (scn.cmlist_index == -1 or scn.cmlist[scn.cmlist_index].source_obj is not None) and scn.objects.active.type == "MESH":
        scn.Bricker_last_active_object_name = scn.objects.active.name
        beginningString = "Bricker_"
        if scn.objects.active.name.startswith(beginningString):
            usingSource = False
            frameLoc = scn.objects.active.name.rfind("_bricks")
            if frameLoc == -1:
                frameLoc = scn.objects.active.name.rfind("_brick_")
                if frameLoc == -1:
                    frameLoc = scn.objects.active.name.rfind("_parent")
            if frameLoc != -1:
                scn.Bricker_active_object_name = scn.objects.active.name[len(beginningString):frameLoc]
        else:
            usingSource = True
            scn.Bricker_active_object_name = scn.objects.active.name
        for i,cm in enumerate(scn.cmlist):
            if createdWithUnsupportedVersion(cm) or getSourceName(cm) != scn.Bricker_active_object_name or (usingSource and cm.modelCreated):
                continue
            scn.cmlist_index = i
            scn.Bricker_last_cmlist_index = scn.cmlist_index
            active_obj = scn.objects.active
            if active_obj.isBrick:
                # adjust scn.active_brick_detail based on active brick
                x0, y0, z0 = strToList(getDictKey(active_obj.name))
                cm.activeKey = (x0, y0, z0)
            return
        # if no matching cmlist item found, set cmlist_index to -1
        scn.cmlist_index = -1


@persistent
def prevent_user_from_viewing_storage_scene(scene):
    scn = bpy.context.scene
    if brickerRunningBlockingOp() or bpy.props.Bricker_developer_mode != 0:
        return
    if scn.name == "Bricker_storage (DO NOT MODIFY)":
        i = 0
        if bpy.data.scenes[i].name == scn.name:
            i += 1
        bpy.context.screen.scene = bpy.data.scenes[i]
        showErrorMessage("This scene is for Bricker internal use only")


def find_3dview_space():
    # Find 3D_View window and its scren space
    area = None
    for a in bpy.data.window_managers[0].windows[0].screen.areas:
        if a.type == 'VIEW_3D':
            area = a
            break

    if area:
        space = area.spaces[0]
    else:
        space = bpy.context.space_data

    return space


# clear light cache before file load
@persistent
def clear_bfm_cache(dummy):
    for key in bricker_bfm_cache.keys():
        bricker_bfm_cache[key] = None


# pull dicts from deep cache to light cache on load
@persistent
def handle_loading_to_light_cache(scene):
    deepToLightCache(bricker_bfm_cache)
    # verify caches loaded properly
    for cm in bpy.context.scene.cmlist:
        if not (cm.modelCreated or cm.animated):
            continue
        bricksDict = getBricksDict(cm=cm)[0]
        if bricksDict is None:
            cm.matrixLost = True
            cm.matrixIsDirty = True


# push dicts from light cache to deep cache on save
@persistent
def handle_storing_to_deep_cache(scene):
    lightToDeepCache(bricker_bfm_cache)


# send parent object to scene for linking scene in other file
@persistent
def safe_link_parent(scene):
    for scn in bpy.data.scenes:
        for cm in scn.cmlist:
            n = getSourceName(cm)
            Bricker_parent_on = "Bricker_%(n)s_parent" % locals()
            p = bpy.data.objects.get(Bricker_parent_on)
            if (cm.modelCreated or cm.animated) and not cm.exposeParent:
                safeLink(p)


# send parent object to scene for linking scene in other file
@persistent
def safe_unlink_parent(scene):
    for scn in bpy.data.scenes:
        for cm in scn.cmlist:
            n = getSourceName(cm)
            Bricker_parent_on = "Bricker_%(n)s_parent" % locals()
            p = bpy.data.objects.get(Bricker_parent_on)
            if p is not None and (cm.modelCreated or cm.animated) and not cm.exposeParent:
                try:
                    safeUnlink(p)
                except RuntimeError:
                    pass


@persistent
def handle_upconversion(scene):
    scn = bpy.context.scene
    # update storage scene name
    for cm in scn.cmlist:
        if createdWithUnsupportedVersion(cm):
            # normalize cm.version
            if cm.version[1] == ",":
                cm.version = cm.version.replace(", ", ".")
            # convert from v1_0 to v1_1
            if int(cm.version[2]) < 1:
                cm.brickWidth = 2 if cm.maxBrickScale2 > 1 else 1
                cm.brickDepth = cm.maxBrickScale2
            # convert from v1_2 to v1_3
            if int(cm.version[2]) < 3:
                if cm.colorSnapAmount == 0:
                    cm.colorSnapAmount = 0.001
                for obj in bpy.data.objects:
                    if obj.name.startswith("Rebrickr"):
                        obj.name = obj.name.replace("Rebrickr", "Bricker")
                for scn in bpy.data.scenes:
                    if scn.name.startswith("Rebrickr"):
                        scn.name = scn.name.replace("Rebrickr", "Bricker")
                for group in bpy.data.groups:
                    if group.name.startswith("Rebrickr"):
                        group.name = group.name.replace("Rebrickr", "Bricker")
            # convert from v1_3 to v1_4
            if int(cm.version[2]) < 4:
                # update "_frame_" to "_f_" in brick and group names
                n = getSourceName(cm)
                Bricker_bricks_gn = "Bricker_%(n)s_bricks" % locals()
                if cm.animated:
                    for i in range(cm.lastStartFrame, cm.lastStopFrame + 1):
                        Bricker_bricks_curF_gn = Bricker_bricks_gn + "_frame_" + str(i)
                        bGroup = bpy.data.groups.get(Bricker_bricks_curF_gn)
                        if bGroup is None:
                            continue
                        bGroup.name = rreplace(bGroup.name, "frame", "f")
                        for obj in bGroup.objects:
                            obj.name = rreplace(obj.name, "frame", "f")
                elif cm.modelCreated:
                    bGroup = bpy.data.groups.get(Bricker_bricks_gn)
                    if bGroup is None:
                        continue
                    bGroup.name = rreplace(bGroup.name, "frame", "f")
                    for obj in bGroup.objects:
                        obj.name = rreplace(obj.name, "frame", "f")
                # rename storage scene
                sto_scn_old = bpy.data.scenes.get("Bricker_storage (DO NOT RENAME)")
                sto_scn_new = getSafeScn()
                if sto_scn_old is not None:
                    for obj in sto_scn_old.objects:
                        if obj.name.startswith("Bricker_refLogo"):
                            bpy.data.objects.remove(obj, True)
                        else:
                            try:
                                sto_scn_new.objects.link(obj)
                            except RuntimeError:
                                pass
                    bpy.data.scenes.remove(sto_scn_old)
                # create "Bricker_cm.id_mats" object for each cmlist idx
                matObjNames = ["Bricker_{}_RANDOM_mats".format(cm.id), "Bricker_{}_ABS_mats".format(cm.id)]
                for n in matObjNames:
                    matObj = bpy.data.objects.get(n)
                    if matObj is None:
                        matObj = bpy.data.objects.new(n, bpy.data.meshes.new(n + "_mesh"))
                        sto_scn_new.objects.link(matObj)
                # update names of Bricker source objects
                old_source = bpy.data.objects.get(getSourceName(cm) + " (DO NOT RENAME)")
                if old_source is not None:
                    old_source = cm.source_obj
                # transfer dist offset values to new prop locations
                if cm.distOffsetX != -1:
                    cm.distOffset = (cm.distOffsetX, cm.distOffsetY, cm.distOffsetZ)
            # convert from v1_4 to v1_5
            if int(cm.version[2]) < 5:
                cm.logoType = cm.logoDetail
                cm.matrixIsDirty = True
                cm.matrixLost = True
            # convert from v1_5 to v1_6
            if int(cm.version[2]) < 6:
                cm.source_obj = bpy.data.objects.get(cm.source_name)
