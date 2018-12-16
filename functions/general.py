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
import collections
import json
import math
import numpy as np

# Blender imports
import bpy
from mathutils import Vector, Euler, Matrix
from bpy.types import Object

# Addon imports
from .common import *


def getSafeScn():
    safeScn = bpy.data.scenes.get("Bricker_storage (DO NOT MODIFY)")
    if safeScn == None:
        safeScn = bpy.data.scenes.new("Bricker_storage (DO NOT MODIFY)")
    return safeScn


def getActiveContextInfo(cm=None, cm_id=None):
    scn = bpy.context.scene
    cm = cm or scn.cmlist[scn.cmlist_index]
    return scn, cm, getSourceName(cm)


def getSourceName(cm):
    return cm.source_obj.name if cm.source_obj is not None else ""


def centerMeshOrigin(m, dimensions, size):
    # get half width
    d0 = Vector((dimensions["width"] / 2, dimensions["width"] / 2, 0))
    # get scalar for d0 in positive xy directions
    scalar = Vector((size[0] * 2 - 1,
                     size[1] * 2 - 1,
                     0))
    # calculate center
    center = (vec_mult(d0, scalar) - d0) / 2
    # apply translation matrix to center mesh
    m.transform(Matrix.Translation(-Vector(center)))


def safeUnlink(obj, hide=True, protect=True):
    scn = bpy.context.scene
    safeScn = getSafeScn()
    try:
        scn.collection.objects.unlink(obj)
    except RuntimeError:
        pass
    safeScn.collection.objects.link(obj)
    obj.protected = protect
    if hide:
        obj.hide_viewport = True


def safeLink(obj, unhide=True, protect=False):
    scn = bpy.context.scene
    safeScn = getSafeScn()
    scn.collection.objects.link(obj)
    obj.protected = protect
    if unhide:
        obj.hide_viewport = False
    try:
        safeScn.collection.objects.unlink(obj)
    except RuntimeError:
        pass


def getBoundsBF(obj):
    """ brute force method for obtaining object bounding box """
    # initialize min and max
    min = Vector((math.inf, math.inf, math.inf))
    max = Vector((-math.inf, -math.inf, -math.inf))
    # calculate min and max verts
    for v in obj.data.vertices:
        if v.co.x > max.x:
            max.x = v.co.x
        elif v.co.x < min.x:
            min.x = v.co.x
        if v.co.y > max.y:
            max.y = v.co.y
        elif v.co.y < min.y:
            min.y = v.co.y
        if v.co.z > max.z:
            max.z = v.co.z
        elif v.co.z < min.z:
            min.z = v.co.z
    # set up bounding box list of coord lists
    bound_box = [list(min),
                 [min.x, min.y, min.z],
                 [min.x, min.y, max.z],
                 [min.x, max.y, max.z],
                 [min.x, max.y, min.z],
                 [max.x, min.y, min.z],
                 [max.y, min.y, max.z],
                 list(max),
                 [max.x, max.y, min.z]]
    return bound_box


def bounds(obj, local=False, use_adaptive_domain=True):
    """
    returns object details with the following subattribute Vectors:

    .max : maximum value of object
    .min : minimum value of object
    .mid : midpoint value of object
    .dist: distance min to max

    """

    local_coords = getBoundsBF(obj) if is_smoke(obj) and is_adaptive(obj) and not use_adaptive_domain else obj.bound_box[:]
    om = obj.matrix_world

    if not local:
        worldify = lambda p: om @ Vector(p[:])
        coords = [worldify(p).to_tuple() for p in local_coords]
    else:
        coords = [p[:] for p in local_coords]

    rotated = zip(*coords[::-1])
    getMax = lambda i: max([co[i] for co in coords])
    getMin = lambda i: min([co[i] for co in coords])

    info = lambda: None
    info.max = Vector((getMax(0), getMax(1), getMax(2)))
    info.min = Vector((getMin(0), getMin(1), getMin(2)))
    info.mid = (info.min + info.max) / 2
    info.dist = info.max - info.min

    return info


def getAnimAdjustedFrame(frame, startFrame, stopFrame):
    if frame < startFrame:
        curFrame = startFrame
    elif frame > stopFrame:
        curFrame = stopFrame
    else:
        curFrame = frame
    return curFrame


def setObjOrigin(obj, loc):
    # TODO: Speed up this function by not using the ops call
    # for v in obj.data.vertices:
    #     v.co += obj.location - loc
    # obj.location = loc
    scn = bpy.context.scene
    ct = time.time()
    old_loc = tuple(scn.cursor_location)
    scn.cursor_location = loc
    select(obj, active=True, only=True)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    scn.cursor_location = old_loc


# def setOriginToObjOrigin(toObj, fromObj=None, fromLoc=None, deleteFromObj=False):
#     assert fromObj or fromLoc
#     setObjOrigin(toObj, fromObj.matrix_world.to_translation().to_tuple() if fromObj else fromLoc)
#     if fromObj:
#         if deleteFromObj:
#             m = fromObj.data
#             bpy.data.objects.remove(fromObj, do_unlink=True)
#             bpy.data.meshes.remove(m)


def getBricks(cm=None, typ=None):
    """ get bricks in 'cm' model """
    scn, cm, n = getActiveContextInfo(cm=cm)
    typ = typ or ("MODEL" if cm.modelCreated else "ANIM")
    if typ == "MODEL":
        gn = "Bricker_%(n)s_bricks" % locals()
        bColl = bpy.data.collections[gn]
        bricks = list(bColl.objects)
    elif typ == "ANIM":
        bricks = []
        for cf in range(cm.lastStartFrame, cm.lastStopFrame+1):
            gn = "Bricker_%(n)s_bricks_f_%(cf)s" % locals()
            bColl = bpy.data.collections.get(gn)
            if bColl:
                bricks += list(bColl.objects)
    return bricks


def getMatObject(cm_id, typ="RANDOM"):
    mat_n = cm_id
    Bricker_mat_on = "Bricker_%(mat_n)s_%(typ)s_mats" % locals()
    matObj = bpy.data.objects.get(Bricker_mat_on)
    return matObj


def getBrickTypes(height):
    return bpy.props.Bricker_legal_brick_sizes[height].keys()


def flatBrickType(typ):
    return type(typ) == str and ("PLATE" in typ or "STUD" in typ)


def mergableBrickType(typ, up=False):
    return type(typ) == str and ("PLATE" in typ or "BRICK" in typ or "SLOPE" in typ or (up and typ == "CYLINDER"))


def getTallType(brickD, targetType=None):
    return targetType if targetType in getBrickTypes(height=3) else (brickD["type"] if brickD["type"] in getBrickTypes(height=3) else "BRICK")


def getShortType(brickD, targetType=None):
    return targetType if targetType in getBrickTypes(height=1) else (brickD["type"] if brickD["type"] in getBrickTypes(height=1) else "PLATE")


def brick_materials_installed():
    scn = bpy.context.scene
    return hasattr(scn, "isBrickMaterialsInstalled") and scn.isBrickMaterialsInstalled


def getABSPlasticMats():
    """ returns list of abs plastic materials (under different names for different versions) """
    return bpy.props.abs_mats_common if hasattr(bpy.props, "abs_mats_common") else bpy.props.abs_plastic_materials


def getMatNames(all=False):
    scn = bpy.context.scene
    materials = getABSPlasticMats().copy()
    if scn.include_transparent or all:
        materials += bpy.props.abs_mats_transparent
    if scn.include_uncommon or all:
        materials += bpy.props.abs_mats_uncommon
    return materials


def brick_materials_loaded():
    scn = bpy.context.scene
    # make sure abs_plastic_materials addon is installed
    brick_mats_installed = hasattr(scn, "isBrickMaterialsInstalled") and scn.isBrickMaterialsInstalled
    if not brick_mats_installed:
        return False
    # check if any of the colors haven't been loaded
    mats = bpy.data.materials.keys()
    for color in getMatNames():
        if color not in mats:
            return False
    return True


def getMatrixSettings(cm=None):
    cm = cm or getActiveContextInfo()[1]
    # TODO: Maybe remove custom object names from this?
    regularSettings = [cm.brickHeight, cm.gap, cm.brickType, cm.distOffset, cm.includeTransparency, cm.customObject1, cm.customObject2, cm.customObject3, cm.useNormals, cm.verifyExposure, cm.insidenessRayCastDir, cm.castDoubleCheckRays, cm.brickShell, cm.calculationAxes]
    smokeSettings = [] if not cm.lastIsSmoke else [cm.smokeDensity, cm.smokeQuality, cm.smokeBrightness, cm.smokeSaturation, cm.flameColor, cm.flameIntensity]
    return listToStr(regularSettings + smokeSettings)


def matrixReallyIsDirty(cm):
    return (cm.matrixIsDirty and cm.lastMatrixSettings != getMatrixSettings()) or cm.matrixLost


def vecToStr(vec, separate_by=","):
    return listToStr(list(vec), separate_by=separate_by)


def listToStr(lst, separate_by=","):
    assert type(lst) in (list, tuple)
    return separate_by.join(map(str, lst))



def strToList(string, item_type=int, split_on=","):
    lst = string.split(split_on)
    assert type(string) is str and type(split_on) is str
    lst = list(map(item_type, lst))
    return lst


def strToTuple(string, item_type=int, split_on=","):
    return tuple(strToList(string, item_type, split_on))


def isUnique(lst):
    return np.unique(lst).size == len(lst)


def getZStep(cm):
    return 1 if flatBrickType(cm.brickType) else 3


def gammaCorrect(rgba, val):
    r, g, b, a = rgba
    r = math.pow(r, val)
    g = math.pow(g, val)
    b = math.pow(b, val)
    return [r, g, b, a]


def getKeysDict(bricksDict, keys=None):
    """ get dictionary of bricksDict keys based on z value """
    keys = keys or list(bricksDict.keys())
    keys.sort(key=lambda x: (getDictLoc(bricksDict, x)[0], getDictLoc(bricksDict, x)[1]))
    keysDict = {}
    for k0 in keys:
        z = getDictLoc(bricksDict, k0)[2]
        if bricksDict[k0]["draw"]:
            try:
                keysDict[z].append(k0)
            except KeyError:
                keysDict[z] = [k0]
    return keysDict


def getParentKey(bricksDict, key):
    if key not in bricksDict:
        return None
    parent_key = key if bricksDict[key]["parent"] in ("self", None) else bricksDict[key]["parent"]
    return parent_key


def createdWithUnsupportedVersion(cm):
    return cm.version[:3] != bpy.props.bricker_version[:3]


def createdWithNewerVersion(cm):
    modelVersion = cm.version.split(".")
    brickerVersion = bpy.props.bricker_version.split(".")
    return (int(modelVersion[0]) > int(brickerVersion[0])) or (int(modelVersion[0]) == int(brickerVersion[0]) and int(modelVersion[1]) > int(brickerVersion[1]))


def getLocsInBrick(bricksDict, size, zStep, key, loc=None):
    x0, y0, z0 = loc or getDictLoc(bricksDict, key)
    return [[x0 + x, y0 + y, z0 + z] for z in range(0, size[2], zStep) for y in range(size[1]) for x in range(size[0])]


def getKeysInBrick(bricksDict, size, zStep, key, loc=None):
    x0, y0, z0 = loc or getDictLoc(bricksDict, key)
    return [listToStr((x0 + x, y0 + y, z0 + z)) for z in range(0, size[2], zStep) for y in range(size[1]) for x in range(size[0])]


def isOnShell(bricksDict, key, loc=None, zStep=None, shellDepth=1):
    """ check if any locations in brick are on the shell """
    size = bricksDict[key]["size"]
    brickKeys = getKeysInBrick(bricksDict, size, zStep, key, loc)
    for k in brickKeys:
        if bricksDict[k]["val"] >= 1 - (shellDepth - 1) / 100:
            return True
    return False


def getDictKey(name):
    """ get dict key details of obj """
    dictKey = name.split("__")[-1]
    return dictKey

def getDictLoc(bricksDict, key):
    try:
        loc = bricksDict[key]["loc"]
    except KeyError:
        loc = strToList(key)
    return loc


def getBrickCenter(bricksDict, key, zStep, loc=None):
    brickKeys = getKeysInBrick(bricksDict, bricksDict[key]["size"], zStep, key, loc=loc)
    coords = [bricksDict[k0]["co"] for k0 in brickKeys]
    coord_ave = Vector((mean([co[0] for co in coords]), mean([co[1] for co in coords]), mean([co[2] for co in coords])))
    return coord_ave


def getNormalDirection(normal, maxDist=0.77):
    # initialize vars
    minDist = maxDist
    minDir = None
    # skip normals that aren't within 0.3 of the z values
    if normal is None or ((normal.z > -0.2 and normal.z < 0.2) or normal.z > 0.8 or normal.z < -0.8):
        return minDir
    # set Vectors for perfect normal directions
    normDirs = {"^X+":Vector((1, 0, 0.5)),
                "^Y+":Vector((0, 1, 0.5)),
                "^X-":Vector((-1, 0, 0.5)),
                "^Y-":Vector((0, -1, 0.5)),
                "vX+":Vector((1, 0, -0.5)),
                "vY+":Vector((0, 1, -0.5)),
                "vX-":Vector((-1, 0, -0.5)),
                "vY-":Vector((0, -1, -0.5))}
    # calculate nearest
    for dir,v in normDirs.items():
        dist = (v - normal).length
        if dist < minDist:
            minDist = dist
            minDir = dir
    return minDir


def getFlipRot(dir):
    flip = dir in ("X-", "Y-")
    rot = dir in ("Y+", "Y-")
    return flip, rot


def legalBrickSize(size, type):
     return size[:2] in bpy.props.Bricker_legal_brick_sizes[size[2]][type]


def get_override(area_type, region_type):
    for area in bpy.context.screen.areas:
        if area.type == area_type:
            for region in area.regions:
                if region.type == region_type:
                    override = {'area': area, 'region': region}
                    return override
    #error message if the area or region wasn't found
    raise RuntimeError("Wasn't able to find", region_type," in area ", area_type,
                        "\n Make sure it's open while executing script.")


def getSpace():
    scr = bpy.context.window.screen
    v3d = [area for area in scr.areas if area.type == 'VIEW_3D'][0]
    return v3d.spaces[0]


def getExportPath(fn, ext, basePath, frame=-1, subfolder=False):
    path = basePath
    lastSlash = path.rfind("/")
    path = path[:len(path) if lastSlash == -1 else lastSlash + 1]
    blendPath = bpy.path.abspath("//") or "/tmp/"
    blendPathSplit = blendPath[:-1].split("/")
    # if relative path, construct path from user input
    if path.startswith("//"):
        splitPath = path[2:].split("/")
        while len(splitPath) > 0 and splitPath[0] == "..":
            splitPath.pop(0)
            blendPathSplit.pop()
        newPath = "/".join(splitPath)
        fullBlendPath = "/".join(blendPathSplit) if len(blendPathSplit) > 1 else "/"
        path = os.path.join(fullBlendPath, newPath)
    # if path is blank at this point, use default render location
    if path == "":
        path = blendPath
    # check to make sure path exists on local machine
    if not os.path.exists(path):
        return path, "Blender could not find the following path: '%(path)s'" % locals()
    # get full filename
    fn0 = fn if lastSlash in (-1, len(basePath) - 1) else basePath[lastSlash + 1:]
    frame_num = "_%(frame)s" % locals() if frame >= 0 else ""
    full_fn = fn0 + frame_num + ext
    # create subfolder
    if subfolder:
        path = os.path.join(path, fn0)
        if not os.path.exists(path):
            os.makedirs(path)
    # create full export path
    fullPath = os.path.join(path, full_fn)
    # ensure target folder has write permissions
    try:
        f = open(fullPath, "w")
        f.close()
    except PermissionError:
        return path, "Blender does not have write permissions for the following path: '%(path)s'" % locals()
    return fullPath, None


def shortenName(string:str, max_len:int=30):
    """shortens string while maintaining uniqueness"""
    if len(string) <= max_len:
        return string
    else:
        return string[:math.ceil(max_len * 0.65)] + str(hash_str(string))[:math.floor(max_len * 0.35)]


def is_smoke(ob):
    if ob is None:
        return False
    for mod in ob.modifiers:
        if mod.type == "SMOKE" and mod.domain_settings and mod.show_viewport:
            return True
    return False


def is_adaptive(ob):
    if ob is None:
        return False
    for mod in ob.modifiers:
        if mod.type == "SMOKE" and mod.domain_settings and mod.domain_settings.use_adaptive_domain:
            return True
    return False

def customValidObject(cm, targetType="Custom 0", idx=None):
    for i, customInfo in enumerate([[cm.hasCustomObj1, cm.customObject1], [cm.hasCustomObj2, cm.customObject2], [cm.hasCustomObj3, cm.customObject3]]):
        hasCustomObj, customObj = customInfo
        if idx is not None and idx != i:
            continue
        elif not hasCustomObj and not (i == 0 and cm.brickType == "CUSTOM") and int(targetType.split(" ")[-1]) != i + 1:
            continue
        if customObj is None:
            warningMsg = "Custom brick type object {} could not be found".format(i + 1)
            return warningMsg
        elif customObj.name == getSourceName(cm) and (not (cm.animated or cm.modelCreated) or customObj.protected):
            warningMsg = "Source object cannot be its own custom brick."
            return warningMsg
        elif customObj.type != "MESH":
            warningMsg = "Custom object {} is not of type 'MESH'. Please select another object (or press 'ALT-C to convert object to mesh).".format(i + 1)
            return warningMsg
        custom_details = bounds(customObj)
        zeroDistAxes = ""
        if custom_details.dist.x < 0.00001:
            zeroDistAxes += "X"
        if custom_details.dist.y < 0.00001:
            zeroDistAxes += "Y"
        if custom_details.dist.z < 0.00001:
            zeroDistAxes += "Z"
        if zeroDistAxes != "":
            axisStr = "axis" if len(zeroDistAxes) == 1 else "axes"
            warningMsg = "Custom brick type object is to small along the '%(zeroDistAxes)s' %(axisStr)s (<0.00001). Please select another object or extrude it along the '%(zeroDistAxes)s' %(axisStr)s." % locals()
            return warningMsg
    return None


def updateHasCustomObjs(cm, typ):
    # update hasCustomObj
    if typ == "CUSTOM 1":
        cm.hasCustomObj1 = True
    if typ == "CUSTOM 2":
        cm.hasCustomObj2 = True
    if typ == "CUSTOM 3":
        cm.hasCustomObj3 = True


def getSaturationMatrix(s:float):
    """ returns saturation matrix from saturation value """
    sr = (1 - s) * 0.3086  # or 0.2125
    sg = (1 - s) * 0.6094  # or 0.7154
    sb = (1 - s) * 0.0820  # or 0.0721
    return Matrix(((sr + s, sr, sr), (sg, sg + s, sg), (sb, sb, sb + s)))


def getBrickMats(materialType, cm_id):
    brick_mats = []
    if materialType == "RANDOM":
        matObj = getMatObject(cm_id, typ="RANDOM")
        brick_mats = list(matObj.data.materials.keys())
    return brick_mats
