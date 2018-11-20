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
        scn = bpy.context.scene
        objs = bpy.context.selected_objects
        # check that at least 1 selected object is a brick
        for obj in objs:
            if not obj.isBrick:
                continue
            # get cmlist item referred to by object
            cm = getItemByID(scn.cmlist, obj.cmlist_id)
            if cm.lastBrickType != "CUSTOM":
                return True
        return False

    def modal(self, context, event):
        try:
            if event.type in {"ESC"} and event.value == "PRESS":
                bpy.context.window.cursor_set("DEFAULT")
                return{"CANCELLED"}

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

            if event.type == 'MOUSEMOVE' or self.left_click:
                scn, cm, _ = getActiveContextInfo()
                x, y = event.mouse_region_x, event.mouse_region_y
                self.hover_scene(context, x, y, cm.source_name)
                if self.obj is None:
                    bpy.context.window.cursor_set("DEFAULT")
                    return {"PASS_THROUGH"}
                else:
                    bpy.context.window.cursor_set("PAINT_BRUSH")

            if self.left_click:
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
                    locDiff = self.loc - Vector(self.bricksDict[curKey]["co"])
                    nextLoc = getNearbyLocFromVector(locDiff, curLoc, self.dimensions, zStep)
                    context.area.header_text_set('Target location: (' + str(int(nextLoc[0])) + ", " + str(int(nextLoc[1])) + ", " + str(int(nextLoc[2])) + ")")
                    # draw brick at nextLoc location
                    nextKey, adjBrickD = drawAdjacent.getBrickD(self.bricksDict, nextLoc)
                    if not adjBrickD or not self.bricksDict[nextKey]["draw"] and self.bricksDict[curKey]["name"] not in self.recentlyAddedBricks:
                        self.adjDKLs = getAdjDKLs(cm, self.bricksDict, curKey, self.obj)
                        targetType = self.bricksDict[curKey]["type"]
                        # add or remove brick
                        status = drawAdjacent.toggleBrick(cm, self.bricksDict, self.adjDKLs, [[False]], self.dimensions, nextLoc, curKey, curLoc, objSize, targetType, 0, 0, self.keysToMerge)
                        if not status["val"]:
                            self.report({status["report_type"]}, status["msg"])
                        self.addedBricks.append(self.bricksDict[nextKey]["name"])
                        self.recentlyAddedBricks.append(self.bricksDict[nextKey]["name"])
                    # draw created bricks
                    drawUpdatedBricks(cm, self.bricksDict, [nextKey], selectCreated=False)

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
        print("running execute")
        scn, cm, _ = getActiveContextInfo()
        # revert to last bricksDict
        self.undo_stack.matchPythonToBlenderState()
        # push to undo stack
        if self.orig_undo_stack_length == self.undo_stack.getLength():
            self.undo_stack.undo_push('brick_paintbrush', affected_ids=[cm.id])
        scn.update()
        self.undo_stack.iterateStates(cm)
        # get fresh copy of self.bricksDict
        self.bricksDict, _ = getBricksDict(cm=cm)
        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.01, context.window)
        wm.modal_handler_add(self)
        return{"RUNNING_MODAL"}

    ################################################
    # initialization method

    def __init__(self):
        print("running init")
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

    ###################################################
    # class variables

    # NONE!

    #############################################
    # class methods

    # from CG Cookie's retopoflow plugin
    def hover_scene(self, context, x, y, source_name):
        """ casts ray through point x,y and sets self.obj if obj intersected """
        scn = context.scene
        region = context.region
        rv3d = context.region_data
        coord = x, y
        ray_max = 10000
        view_vector = region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = region_2d_to_origin_3d(region, rv3d, coord)
        ray_target = ray_origin + (view_vector * ray_max)

        result, loc, normal, idx, ob, mx = scn.ray_cast(ray_origin, ray_target)

        if result and ob.name.startswith('Bricker_' + source_name):
            self.obj = ob
            self.loc = loc
        else:
            self.obj = None
            self.normal = None

    #############################################
