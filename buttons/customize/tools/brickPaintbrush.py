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

# Blender imports
import bpy
from bpy.types import Operator
from bpy_extras.view3d_utils import region_2d_to_location_3d, region_2d_to_origin_3d, region_2d_to_vector_3d

# Addon imports
from .drawAdjacent import *
from ..undo_stack import *
from ..functions import *
from ...brickify import *
from ...brickify import *
from ....lib.Brick import *
from ....lib.bricksDict.functions import getDictKey
from ....functions import *


class brickPaintbrush(Operator):
    """Paint additional bricks onto Bricker model"""
    bl_idname = "bricker.brick_paintbrush"
    bl_label = "Brick Paintbrush"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns False) """
        if not bpy.props.bricker_initialized:
            return False
        return True

    def modal(self, context, event):
        try:
            if event.type == "RET" and event.value == "PRESS":
                bpy.context.window.cursor_set("DEFAULT")
                self.cancel(context)
                self.commitChanges()
                return{"FINISHED"}

            if event.type == "LEFTMOUSE" and event.value == "PRESS":
                self.left_click = True
            if event.type == "LEFTMOUSE" and event.value == "RELEASE":
                self.left_click = False

            if event.type == "MOUSEMOVE" and len(self.recentlyAddedBricks) > 0 and not self.left_click:
                self.recentlyAddedBricks = []

            if event.type in ["LEFT_ALT", "RIGHT_ALT"] and event.value == "PRESS":
                self.shift = True
            if event.type in ["LEFT_ALT", "RIGHT_ALT"] and event.value == "RELEASE":
                self.shift = False

            if event.type in ['TIMER', 'MOUSEMOVE'] or self.left_click:
                scn, cm, n = getActiveContextInfo()
                x, y = event.mouse_region_x, event.mouse_region_y
                self.mouseTravel = abs(x - self.lastMousePos[0]) + abs(y - self.lastMousePos[1])
                self.hover_scene(context, x, y, cm.source_name)
                if self.obj is None:
                    bpy.context.window.cursor_set("DEFAULT")
                    return {"PASS_THROUGH"}
                else:
                    bpy.context.window.cursor_set("PAINT_BRUSH")

            if self.left_click and (event.type == 'LEFTMOUSE' or (event.type == "MOUSEMOVE" and (not self.shift or self.mouseTravel > 5))):
                self.lastMousePos = [x, y]
                addBrick = not (self.shift or self.obj.name in self.recentlyAddedBricks)
                removeBrick = self.shift and self.obj.name in self.addedBricks
                if addBrick or removeBrick:
                    # get key of current brick in bricksDict
                    curKey = getDictKey(self.obj.name)
                    curLoc = getDictLoc(self.bricksDict, curKey)
                    objSize = self.bricksDict[curKey]["size"]
                    zStep = getZStep(cm)
                # add brick next to existing brick
                if addBrick and self.bricksDict[curKey]["name"] not in self.recentlyAddedBricks:
                    # get difference between intersection loc and object loc
                    Bricker_parent_on = "Bricker_%(n)s_parent" % locals()
                    parent = bpy.data.objects.get(Bricker_parent_on)
                    locDiff = self.loc - transformToWorld(Vector(self.bricksDict[curKey]["co"]), parent.matrix_world, self.junk_bme)
                    locDiff = transformToLocal(locDiff, parent.matrix_world)
                    nextLoc = getNearbyLocFromVector(locDiff, curLoc, self.dimensions, zStep)
                    print()
                    print(curLoc)
                    print(nextLoc)
                    # draw brick at nextLoc location
                    nextKey, adjBrickD = drawAdjacent.getBrickD(self.bricksDict, nextLoc)
                    if not adjBrickD or not self.bricksDict[nextKey]["draw"] and self.bricksDict[curKey]["name"] not in self.recentlyAddedBricks:
                        self.adjDKLs = getAdjDKLs(cm, self.bricksDict, curKey, self.obj)
                        # add or remove brick
                        status = drawAdjacent.toggleBrick(cm, self.bricksDict, self.adjDKLs, [[False]], self.dimensions, nextLoc, curKey, curLoc, objSize, self.brickType, 0, 0, self.keysToMerge, temporaryBrick=True)
                        if not status["val"]:
                            self.report({status["report_type"]}, status["msg"])
                        self.addedBricks.append(self.bricksDict[nextKey]["name"])
                        self.recentlyAddedBricks.append(self.bricksDict[nextKey]["name"])
                        self.targettedBrickKeys.append(curKey)
                    # disable logo and bevel detailing for temporary bricks
                    lastBricksAreDirty = cm.bricksAreDirty
                    lastLogoType = cm.logoType
                    lastBevel = cm.bevelAdded
                    cm.logoType = "NONE"
                    cm.bevelAdded = False
                    # draw created bricks
                    drawUpdatedBricks(cm, self.bricksDict, [nextKey], selectCreated=False)
                    # reset logo and bevel detailing
                    cm.logoType = lastLogoType
                    cm.bevelAdded = lastBevel
                    cm.bricksAreDirty = lastBricksAreDirty

                # remove existing brick
                elif removeBrick and self.bricksDict[curKey]["name"] in self.addedBricks:
                    self.addedBricks.remove(self.bricksDict[curKey]["name"])
                    # reset bricksDict values
                    self.bricksDict[curKey]["draw"] = False
                    self.bricksDict[curKey]["val"] = 0
                    self.bricksDict[curKey]["parent"] = None
                    self.bricksDict[curKey]["created_from"] = None
                    self.bricksDict[curKey]["flipped"] = False
                    self.bricksDict[curKey]["rotated"] = False
                    self.bricksDict[curKey]["top_exposed"] = False
                    self.bricksDict[curKey]["bot_exposed"] = False
                    brick = bpy.data.objects.get(self.bricksDict[curKey]["name"])
                    delete(brick)
                    tag_redraw_areas()
                    # draw created bricks
                return {"RUNNING_MODAL"}

            return {"PASS_THROUGH"}
        except:
            handle_exception()
            return {"CANCELLED"}

    def execute(self, context):
        if self.brickType == "" or bpy.props.running_paintbrush:
            return {"CANCELLED"}
        bpy.props.running_paintbrush = True
        scn, cm, _ = getActiveContextInfo()
        # # revert to last bricksDict
        # self.undo_stack.matchPythonToBlenderState()
        # # push to undo stack
        # if self.orig_undo_stack_length == self.undo_stack.getLength():
        #     self.undo_stack.undo_push('brick_paintbrush', affected_ids=[cm.id])
        # scn.update()
        # self.undo_stack.iterateStates(cm)
        # get fresh copy of self.bricksDict
        self.bricksDict, _ = getBricksDict(cm=cm)
        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.01, context.window)
        wm.modal_handler_add(self)
        return{"RUNNING_MODAL"}

    # def invoke(self, context, event):
    #     return context.window_manager.invoke_props_popup(self, event)

    ################################################
    # initialization method

    def __init__(self):
        scn, cm, _ = getActiveContextInfo()
        self.undo_stack = UndoStack.get_instance()
        self.orig_undo_stack_length = self.undo_stack.getLength()
        self.addedBricks = []
        self.recentlyAddedBricks = []
        zStep = getZStep(cm)
        self.dimensions = Bricks.get_dimensions(cm.brickHeight, zStep, cm.gap)
        cm.customized = True
        self.left_click = False
        self.shift = False
        self.obj = None
        self.keysToMerge = []
        self.targettedBrickKeys = []
        self.brickType = "BRICK"
        self.lastMousePos = [0, 0]
        self.mouseTravel = 0
        self.junk_bme = bmesh.new()

    ###################################################
    # class variables

    # # get items for brickType prop
    # def get_items(self, context):
    #     scn, cm, _ = getActiveContextInfo()
    #     zStep = getZStep(cm)
    #     legalBS = bpy.props.Bricker_legal_brick_sizes
    #     items = [itemFromType(typ) for typ in legalBS[zStep]]
    #     if zStep == 1:
    #         items += [itemFromType(typ) for typ in legalBS[3]]
    #     items.append(("", "", ""))
    #     # items = getAvailableTypes(by="ACTIVE", includeSizes="ALL")
    #     return items
    #
    # # define props for popup
    # brickType = bpy.props.EnumProperty(
    #     name="Brick Type",
    #     description="Type of brick to draw adjacent to current brick",
    #     items=get_items,
    #     default=None)

    #############################################
    # class methods

    # from CG Cookie's retopoflow plugin
    def hover_scene(self, context, x, y, source_name):
        """ casts ray through point x,y and sets self.obj if obj intersected """
        scn = context.scene
        region = context.region
        rv3d = context.region_data
        if rv3d is None:
            return None
        coord = x, y
        ray_max = 1000000  # changed from 10000 to 1000000 to increase accuracy
        view_vector = region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = region_2d_to_origin_3d(region, rv3d, coord)
        ray_target = ray_origin + (view_vector * ray_max)

        result, loc, normal, idx, obj, mx = scn.ray_cast(ray_origin, ray_target)

        if result and obj.name.startswith('Bricker_' + source_name):
            self.obj = obj
            self.loc = loc
            context.area.header_text_set('Painting on brick: (' + obj.name.split("__")[1] + ")")
        else:
            self.obj = None
            self.normal = None
            context.area.header_text_set()

    def commitChanges(self):
        scn, cm, _ = getActiveContextInfo()
        zStep = getZStep(cm)
        keysToUpdate = []
        # attempt to merge created bricks
        if mergableBrickType(self.brickType):
            height3Only = "PLATES" in cm.brickType and self.brickType in getBrickTypes(height=3)
            keysToUpdate = mergeBricks.mergeBricks(self.bricksDict, self.keysToMerge, cm, mergeVertical=self.brickType in getBrickTypes(height=3), targetType=self.brickType, height3Only=height3Only)

        # set exposure of created bricks and targetted bricks
        allKeysToUpdate = uniquify(keysToUpdate + self.targettedBrickKeys)
        for k in allKeysToUpdate:
            setAllBrickExposures(self.bricksDict, zStep, k)
        # remove merged 1x1 bricks
        for k in self.keysToMerge:
            if k not in keysToUpdate:
                delete(bpy.data.objects.get(self.bricksDict[k]["name"]))

        # draw updated bricks
        drawUpdatedBricks(cm, self.bricksDict, allKeysToUpdate, selectCreated=False)

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        context.area.header_text_set()
        bpy.props.running_paintbrush = False

    #############################################
