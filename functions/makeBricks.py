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
import bmesh
import math
import time
import sys
import random
import json
import numpy as np

# Blender imports
import bpy
from mathutils import Vector, Matrix

# Addon imports
from .hashObject import hash_object
from ..lib.Brick import Bricks
from ..lib.bricksDict import *
from .common import *
from .wrappers import *
from .general import bounds
from ..lib.caches import bricker_mesh_cache
from ..lib.abs_plastic_materials import getAbsPlasticMaterialNames
from .makeBricks_utils import *
from .mat_utils import *


@timed_call('Time Elapsed')
def makeBricks(source, parent, logo, logo_details, dimensions, bricksDict, action, cm=None, split=False, brickScale=None, customData=None, group_name=None, clearExistingGroup=True, frameNum=None, cursorStatus=False, keys="ALL", printStatus=True, redraw=False):
    # set up variables
    scn, cm, n = getActiveContextInfo(cm=cm)
    zStep = getZStep(cm)

    # reset brickSizes/TypesUsed
    if keys == "ALL":
        cm.brickSizesUsed = ""
        cm.brickTypesUsed = ""

    mergeVertical = keys != "ALL" or cm.brickType == "BRICKS AND PLATES"

    # get bricksDict keys in sorted order
    if keys == "ALL":
        keys = list(bricksDict.keys())
    # get dictionary of keys based on z value
    keysDict = getKeysDict(bricksDict, keys)
    denom = sum([len(keysDict[z0]) for z0 in keysDict.keys()])
    # store first key to active keys
    if cm.activeKey[0] == -1 and len(keys) > 0:
        loc = getDictLoc(bricksDict, keys[0])
        cm.activeKey = loc

    # get brick group
    group_name = group_name or 'Bricker_%(n)s_bricks' % locals()
    bGroup = bpy.data.groups.get(group_name)
    # create new group if no existing group found
    if bGroup is None:
        bGroup = bpy.data.groups.new(group_name)
    # else, replace existing group
    elif clearExistingGroup:
        for obj0 in bGroup.objects:
            bGroup.objects.unlink(obj0)

    brick_mats = []
    if cm.materialType == "RANDOM":
        matObj = getMatObject(cm.id, typ="RANDOM")
        brick_mats = list(matObj.data.materials.keys())


    # initialize cmlist attributes (prevents 'update' function from running every time)
    cm_id = cm.id
    buildIsDirty = cm.buildIsDirty
    brickType = cm.brickType
    bricksAndPlates = brickType == "BRICKS AND PLATES"
    maxWidth = cm.maxWidth
    maxDepth = cm.maxDepth
    legalBricksOnly = cm.legalBricksOnly
    mergeInconsistentMats = cm.mergeInconsistentMats
    mergeInternals = cm.mergeInternals
    mergeType = cm.mergeType
    mergeSeed = cm.mergeSeed
    materialType = cm.materialType
    materialName = cm.materialName
    randomMatSeed = cm.randomMatSeed
    studDetail = cm.studDetail
    exposedUndersideDetail = cm.exposedUndersideDetail
    hiddenUndersideDetail = cm.hiddenUndersideDetail
    lastSplitModel = cm.lastSplitModel
    randomRot = cm.randomRot
    randomLoc = cm.randomLoc
    logoType = cm.logoType
    logoScale = cm.logoScale
    logoInset = cm.logoInset
    logoResolution = cm.logoResolution
    logoDecimate = cm.logoDecimate
    loopCut = cm.loopCut
    circleVerts = cm.circleVerts
    brickHeight = cm.brickHeight
    alignBricks = cm.alignBricks
    offsetBrickLayers = cm.offsetBrickLayers
    # initialize random states
    randS1 = np.random.RandomState(cm.mergeSeed)  # for brickSize calc
    randS2 = np.random.RandomState(cm.mergeSeed+1)
    randS3 = np.random.RandomState(cm.mergeSeed+2)
    # initialize other variables
    brickSizeStrings = {}
    mats = []
    allMeshes = bmesh.new()
    lowestZ = -1
    availableKeys = []
    bricksCreated = []
    maxBrickHeight = 1 if zStep == 3 else max(legalBricks.keys())
    connectThresh = cm.connectThresh if mergableBrickType(brickType) and mergeType == "RANDOM" else 1
    # set up internal material for this object
    internalMat = None if len(source.data.materials) == 0 else bpy.data.materials.get(cm.internalMatName) or bpy.data.materials.get("Bricker_%(n)s_internal" % locals()) or bpy.data.materials.new("Bricker_%(n)s_internal" % locals())
    if internalMat is not None and cm.materialType == "SOURCE" and cm.matShellDepth < cm.shellThickness:
        mats.append(internalMat)
    # set number of times to run through all keys
    numIters = 2 if brickType == "BRICKS AND PLATES" else 1
    i = 0
    # if merging unnecessary, simply update bricksDict values
    if not cm.customized and not (mergableBrickType(brickType, up=zStep == 1) and (maxDepth != 1 or maxWidth != 1)):
        size = [1, 1, zStep]
        updateBrickSizesAndTypesUsed(cm, listToStr(size), bricksDict[keys[0]]["type"])
        availableKeys = keys
        for key in keys:
            bricksDict[key]["parent"] = "self"
            bricksDict[key]["size"] = size.copy()
            setAllBrickExposures(bricksDict, zStep, key)
            setFlippedAndRotated(bricksDict, key, [key])
            if bricksDict[key]["type"] == "SLOPE" and brickType == "SLOPES":
                setBrickTypeForSlope(bricksDict, key, [key])
    else:
        # initialize progress bar around cursor
        old_percent = updateProgressBars(printStatus, cursorStatus, 0, -1, "Merging")
        # run merge operations (twice if flat brick type)
        for timeThrough in range(numIters):
            # iterate through z locations in bricksDict (bottom to top)
            for z in sorted(keysDict.keys()):
                # skip second and third rows on first time through
                if numIters == 2 and alignBricks:
                    # initialize lowestZ if not done already
                    if lowestZ == -0.1:
                        lowestZ = z
                    if skipThisRow(timeThrough, lowestZ, z, offsetBrickLayers):
                        continue
                # get availableKeys for attemptMerge
                availableKeysBase = []
                for ii in range(maxBrickHeight):
                    if ii + z in keysDict:
                        availableKeysBase += keysDict[z + ii]
                # get small duplicate of bricksDict for variations
                if connectThresh > 1:
                    bricksDictsBase = {}
                    for k4 in availableKeysBase:
                        bricksDictsBase[k4] = bricksDict[k4]
                    bricksDicts = [deepcopy(bricksDictsBase) for j in range(connectThresh)]
                    numAlignedEdges = [0 for idx in range(connectThresh)]
                else:
                    bricksDicts = [bricksDict]
                # calculate build variations for current z level
                for j in range(connectThresh):
                    availableKeys = availableKeysBase.copy()
                    numBricks = 0
                    if mergeType == "RANDOM":
                        random.seed(mergeSeed + i)
                        random.shuffle(keysDict[z])
                    # iterate through keys on current z level
                    for key in keysDict[z]:
                        i += 1 / connectThresh
                        brickD = bricksDicts[j][key]
                        # skip keys that are already drawn or have attempted merge
                        if brickD["attempted_merge"] or brickD["parent"] not in (None, "self"):
                            # remove ignored key if it exists in availableKeys (for attemptMerge)
                            remove_item(availableKeys, key)
                            continue

                        # initialize loc
                        loc = getDictLoc(bricksDict, key)

                        # merge current brick with available adjacent bricks
                        brickSize = mergeWithAdjacentBricks(brickD, bricksDicts[j], key, availableKeys, [1, 1, zStep], zStep, randS1, buildIsDirty, brickType, maxWidth, maxDepth, legalBricksOnly, mergeInconsistentMats, mergeInternals, materialType, mergeVertical=mergeVertical)
                        brickD["size"] = brickSize
                        # iterate number aligned edges and bricks if generating multiple variations
                        if connectThresh > 1:
                            numAlignedEdges[j] += getNumAlignedEdges(bricksDict, brickSize, key, loc, zStep, bricksAndPlates)
                            numBricks += 1

                        # print status to terminal and cursor
                        cur_percent = (i / denom)
                        old_percent = updateProgressBars(printStatus, cursorStatus, cur_percent, old_percent, "Merging")

                        # remove keys in new brick from availableKeys (for attemptMerge)
                        updateKeysLists(bricksDict, brickSize, zStep, key, loc, availableKeys)

                    if connectThresh > 1:
                        # if no aligned edges / bricks found, skip to next z level
                        if numAlignedEdges[j] == 0:
                            i += (len(keysDict[z]) * connectThresh - 1) / connectThresh
                            break
                        # add double the number of bricks so connectivity threshold is weighted towards larger bricks
                        numAlignedEdges[j] += numBricks * 2

                # choose optimal variation from above for current z level
                if connectThresh > 1:
                    optimalTest = numAlignedEdges.index(min(numAlignedEdges))
                    for k3 in bricksDicts[optimalTest]:
                        bricksDict[k3] = bricksDicts[optimalTest][k3]

        # update cm.brickSizesUsed and cm.brickTypesUsed
        for key in keys:
            if bricksDict[key]["parent"] not in (None, "self"):
                continue
            brickSize = bricksDict[key]["size"]
            if brickSize is None:
                continue
            brickSizeStr = listToStr(sorted(brickSize[:2]) + [brickSize[2]])
            updateBrickSizesAndTypesUsed(cm, brickSizeStr, bricksDict[key]["type"])

        # end 'Merging' progress bar
        updateProgressBars(printStatus, cursorStatus, 1, 0, "Merging", end=True)

    # begin 'Building' progress bar
    old_percent = updateProgressBars(printStatus, cursorStatus, 0, -1, "Building")

    # draw merged bricks
    for i, k2 in enumerate(keys):
        if bricksDict[k2]["parent"] != "self" or not bricksDict[k2]["draw"]:
            continue
        loc = getDictLoc(bricksDict, k2)
        # create brick based on the current brick info
        drawBrick(cm, cm_id, bricksDict, k2, loc, i, dimensions, zStep, bricksDict[k2]["size"], brickType, split, lastSplitModel, customData, brickScale, bricksCreated, allMeshes, logo, logo_details, mats, brick_mats, internalMat, brickHeight, logoResolution, logoDecimate, loopCut, buildIsDirty, materialType, materialName, randomMatSeed, studDetail, exposedUndersideDetail, hiddenUndersideDetail, randomRot, randomLoc, logoType, logoScale, logoInset, circleVerts, randS1, randS2, randS3)
        # print status to terminal and cursor
        old_percent = updateProgressBars(printStatus, cursorStatus, i/len(bricksDict.keys()), old_percent, "Building")

    # end progress bars
    updateProgressBars(printStatus, cursorStatus, 1, 0, "Building", end=True)

    # remove duplicate of original logo
    if cm.logoType != "LEGO" and logo is not None:
        bpy.data.objects.remove(logo)

    # combine meshes, link to scene, and add relevant data to the new Blender MESH object
    if split:
        # iterate through keys
        old_percent = 0
        for i, key in enumerate(keys):
            if bricksDict[key]["parent"] != "self" or not bricksDict[key]["draw"]:
                continue
            print("A")
            # print status to terminal and cursor
            old_percent = updateProgressBars(printStatus, cursorStatus, i/len(bricksDict), old_percent, "Linking to Scene")
            print("B")
            # get brick
            name = bricksDict[key]["name"]
            brick = bpy.data.objects.get(name)
            print("C")
            # create vert group for bevel mod (assuming only logo verts are selected):
            vg = brick.vertex_groups.get("%(name)s_bvl" % locals())
            if vg:
                brick.vertex_groups.remove(vg)
            print("D")
            vg = brick.vertex_groups.new("%(name)s_bvl" % locals())
            print("E")
            vertList = [v.index for v in brick.data.vertices if not v.select]
            vg.add(vertList, 1, "ADD")
            print("F")
            # set up remaining brick info if brick object just created
            if clearExistingGroup or brick.name not in bGroup.objects.keys():
                bGroup.objects.link(brick)
            print("G")
            brick.parent = parent
            print("H")
            if not brick.isBrick:
                scn.objects.link(brick)
                brick.isBrick = True
            print("I")
        # end progress bars
        updateProgressBars(printStatus, cursorStatus, 1, 0, "Linking to Scene", end=True)
    else:
        m = bpy.data.meshes.new("newMesh")
        allMeshes.to_mesh(m)
        name = 'Bricker_%(n)s_bricks' % locals()
        if frameNum:
            name = "%(name)s_f_%(frameNum)s" % locals()
        allBricksObj = bpy.data.objects.get(name)
        if allBricksObj:
            allBricksObj.data = m
        else:
            allBricksObj = bpy.data.objects.new(name, m)
            allBricksObj.cmlist_id = cm_id
            # add edge split modifier
            if brickType != "CUSTOM":
                addEdgeSplitMod(allBricksObj)
        if brickType != "CUSTOM":
            # create vert group for bevel mod (assuming only logo verts are selected):
            vg = allBricksObj.vertex_groups.get("%(name)s_bvl" % locals())
            if vg:
                allBricksObj.vertex_groups.remove(vg)
            vg = allBricksObj.vertex_groups.new("%(name)s_bvl" % locals())
            vertList = [v.index for v in allBricksObj.data.vertices if not v.select]
            vg.add(vertList, 1, "ADD")
        if materialType == "CUSTOM":
            mat = bpy.data.materials.get(materialName)
            if mat is not None:
                addMaterial(allBricksObj, mat)
        elif materialType == "SOURCE" or (materialType == "RANDOM" and len(brick_mats) > 0):
            for mat in mats:
                addMaterial(allBricksObj, mat)
        # set parent
        allBricksObj.parent = parent
        # add bricks obj to scene and bricksCreated
        bGroup.objects.link(allBricksObj)
        if not allBricksObj.isBrickifiedObject:
            scn.objects.link(allBricksObj)
            # protect allBricksObj from being deleted
            allBricksObj.isBrickifiedObject = True
        bricksCreated.append(allBricksObj)

    # reset 'attempted_merge' for all items in bricksDict
    for key0 in bricksDict:
        bricksDict[key0]["attempted_merge"] = False

    return bricksCreated, bricksDict
