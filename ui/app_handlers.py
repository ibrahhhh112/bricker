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


def brickerIsActive():
    return hasattr(bpy.props, "bricker_module_name") and bpy.props.bricker_module_name in bpy.context.user_preferences.addons.keys()


def brickerRunningBlockingOp():
    scn = bpy.context.scene
    return hasattr(scn, "Bricker_runningBlockingOperation") and scn.Bricker_runningBlockingOperation


@persistent
def handle_animation(scene):
    scn = scene
    if not brickerIsActive():
        return
    for i, cm in enumerate(scn.cmlist):
        if not cm.animated:
            continue
        n = getSourceName(cm)
        for cf in range(cm.lastStartFrame, cm.lastStopFrame + 1):
            curBricks = bpy.data.collections.get("Bricker_%(n)s_bricks_f_%(cf)s" % locals())
            if curBricks is None:
                continue
            adjusted_frame_current = getAnimAdjustedFrame(scn.frame_current, cm.lastStartFrame, cm.lastStopFrame)
            onCurF = adjusted_frame_current == cf
            for brick in curBricks.objects:
                # hide bricks from view and render unless on current frame
                if brick.hide_viewport == onCurF:
                    brick.hide_viewport = not onCurF
                    brick.hide_render = not onCurF
                obj = bpy.context.object
                if obj and obj.name.startswith("Bricker_%(n)s_bricks" % locals()) and onCurF:
                    select(brick, active=True)
                # prevent bricks from being selected on frame change
                elif brick.select_get():
                    brick.select_set(False)


bpy.app.handlers.frame_change_pre.append(handle_animation)


# clear light cache before file load
@persistent
def clear_bfm_cache(dummy):
    if not brickerIsActive():
        return
    for key in bricker_bfm_cache.keys():
        bricker_bfm_cache[key] = None


bpy.app.handlers.load_pre.append(clear_bfm_cache)


# pull dicts from deep cache to light cache on load
@persistent
def handle_loading_to_light_cache(scene):
    if not brickerIsActive():
        return
    deepToLightCache(bricker_bfm_cache)
    # verify caches loaded properly
    for cm in bpy.context.scene.cmlist:
        if not (cm.modelCreated or cm.animated):
            continue
        bricksDict = getBricksDict(cm=cm)[0]
        if bricksDict is None:
            cm.matrixLost = True
            cm.matrixIsDirty = True


bpy.app.handlers.load_post.append(handle_loading_to_light_cache)


# push dicts from light cache to deep cache on save
@persistent
def handle_storing_to_deep_cache(scene):
    if not brickerIsActive():
        return
    lightToDeepCache(bricker_bfm_cache)


bpy.app.handlers.save_pre.append(handle_storing_to_deep_cache)


# send parent object to scene for linking scene in other file
@persistent
def safe_link_parent(scene):
    if not brickerIsActive():
        return
    for scn in bpy.data.scenes:
        for cm in scn.cmlist:
            n = getSourceName(cm)
            Bricker_parent_on = "Bricker_%(n)s_parent" % locals()
            p = bpy.data.objects.get(Bricker_parent_on)
            if (cm.modelCreated or cm.animated) and not cm.exposeParent:
                safeLink(p)


bpy.app.handlers.save_pre.append(safe_link_parent)


# send parent object to scene for linking scene in other file
@persistent
def safe_unlink_parent(scene):
    if not brickerIsActive():
        return
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


bpy.app.handlers.save_post.append(safe_unlink_parent)
bpy.app.handlers.load_post.append(safe_unlink_parent)


@persistent
def handle_upconversion(scene):
    scn = bpy.context.scene
    if not brickerIsActive():
        return
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
                for coll in bpy.data.collections:
                    if coll.name.startswith("Rebrickr"):
                        coll.name = coll.name.replace("Rebrickr", "Bricker")
            # convert from v1_3 to v1_4
            if int(cm.version[2]) < 4:
                # update "_frame_" to "_f_" in brick and group names
                n = getSourceName(cm)
                Bricker_bricks_gn = "Bricker_%(n)s_bricks" % locals()
                if cm.animated:
                    for i in range(cm.lastStartFrame, cm.lastStopFrame + 1):
                        Bricker_bricks_curF_gn = Bricker_bricks_gn + "_frame_" + str(i)
                        bColl = bpy.data.collections.get(Bricker_bricks_curF_gn)
                        if bColl is None:
                            continue
                        bColl.name = rreplace(bColl.name, "frame", "f")
                        for obj in bColl.objects:
                            obj.name = rreplace(obj.name, "frame", "f")
                elif cm.modelCreated:
                    bColl = bpy.data.collections.get(Bricker_bricks_gn)
                    if bColl is None:
                        continue
                    bColl.name = rreplace(bColl.name, "frame", "f")
                    for obj in bColl.objects:
                        obj.name = rreplace(obj.name, "frame", "f")
                # rename storage scene
                sto_scn_old = bpy.data.scenes.get("Bricker_storage (DO NOT RENAME)")
                sto_scn_new = getSafeScn()
                if sto_scn_old is not None:
                    for obj in sto_scn_old.objects:
                        if obj.name.startswith("Bricker_refLogo"):
                            bpy.data.objects.remove(obj, do_unlink=True)
                        else:
                            try:
                                sto_scn_new.collection.objects.link(obj)
                            except RuntimeError:
                                pass
                    bpy.data.scenes.remove(sto_scn_old)
                # create "Bricker_cm.id_mats" object for each cmlist idx
                matObjNames = ["Bricker_{}_RANDOM_mats".format(cm.id), "Bricker_{}_ABS_mats".format(cm.id)]
                for n in matObjNames:
                    matObj = bpy.data.objects.get(n)
                    if matObj is None:
                        matObj = bpy.data.objects.new(n, bpy.data.meshes.new(n + "_mesh"))
                        sto_scn_new.collection.objects.link(matObj)
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

bpy.app.handlers.load_post.append(handle_upconversion)
