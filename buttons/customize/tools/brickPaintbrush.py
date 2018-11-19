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

            if event.type == "OPTION" and event.value == "PRESS":
                self.shift = True
            if event.type == "OPTION" and event.value == "RELEASE":
                self.shift = False

            if event.type == 'MOUSEMOVE':
                bpy.context.window.cursor_set("PAINT_BRUSH")

            if self.left_click:
                scn, cm, _ = getActiveContextInfo()
                x, y = event.mouse_region_x, event.mouse_region_y
                self.hover_scene(context, x, y, cm.source_name, exclude_added=not self.shift)
                if self.obj is not None:
                    if self.shift:
                        print("remove brick")
                    else:
                        print("add brick")
                    # get key of current brick in bricksDict
                    curKey = getDictKey(self.obj.name)
                    curLoc = getDictLoc(self.bricksDict, curKey)
                    objSize = self.bricksDict[curKey]["size"]
                    zStep = getZStep(cm)
                    # get difference between intersection loc and object loc
                    locDiff = self.loc - Vector(self.bricksDict[curKey]["co"])
                    nextLoc = getNearbyLocFromVector(locDiff, curLoc, self.dimensions, zStep)
                    print(nextLoc)
                    context.area.header_text_set('Target location: (' + str(int(nextLoc[0])) + ", " + str(int(nextLoc[1])) + ", " + str(int(nextLoc[2])) + ")")
                    # # if difference is significantly to one side, draw brick on that side
                    # if nextLoc is not None:
                    #     self.adjDKLs = getAdjDKLs(cm, self.bricksDict, curKey, self.obj)
                    #     # add or remove bricks in all adjacent locations in current direction
                    #     for j,adjDictLoc in enumerate(self.adjDKLs[i]):
                    #         if decriment != 0:
                    #             adjDictLoc = adjDictLoc.copy()
                    #             adjDictLoc[2] -= decriment
                    #         status = drawAdjacent.toggleBrick(cm, self.bricksDict, [[False] * len(self.adjDKLs[i]) for i in range(6)], self.dimensions, adjDictLoc, curKey, objSize, targetType, i, j, keysToMerge, addBrick=createAdjBricks[i])
                    #         if not status["val"]:
                    #             self.report({status["report_type"]}, status["msg"])
                    #     # after ALL bricks toggled, check exposure of bricks above and below new ones
                    #     for j,adjDictLoc in enumerate(self.adjDKLs[i]):
                    #         self.bricksDict = verifyBrickExposureAboveAndBelow(scn, zStep, adjDictLoc.copy(), self.bricksDict, decriment=decriment + 1, zNeg=self.zNeg, zPos=self.zPos)

                    # self.addedBricks.append(brick.name)
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
        self._timer = wm.event_timer_add(0.1, context.window)
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
        zStep = getZStep(cm)
        self.dimensions = Bricks.get_dimensions(cm.brickHeight, zStep, cm.gap)
        cm.customized = True
        self.left_click = False
        self.shift = False
        self.obj = None

    ###################################################
    # class variables

    # NONE!

    #############################################
    # class methods

    # from CG Cookie's retopoflow plugin
    def hover_scene(self, context, x, y, source_name, exclude_added=False):
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

        if result and ob.name.startswith('Bricker_' + source_name) and not (exclude_added and ob.name in self.addedBricks):
            self.obj = ob
            self.loc = loc
        else:
            self.obj = None
            self.normal = None

    #############################################
