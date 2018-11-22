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

# Blender imports
import bpy
import bgl
from bpy.types import Operator
from bpy_extras.view3d_utils import region_2d_to_location_3d, region_2d_to_origin_3d, region_2d_to_vector_3d
from bpy.types import Operator, SpaceView3D, bpy_struct

# Addon imports
from .drawAdjacent import *
from ..undo_stack import *
from ..functions import *
from ...brickify import *
from ...brickify import *
from ....lib.Brick import *
from ....lib.bricksDict.functions import getDictKey
from ....functions import *


def get_view_orientation(space, view):

    if view.view_perspective == 'CAMERA':
        if space.camera.type == 'CAMERA':
            view_orientation = "Camera " + space.camera.data.type.capitalize()
        else:
            view_orientation = "Object as Camera"

    else:
        r = lambda x: round(x, 2)
        view_rot = view.view_matrix.to_euler()

        orientation_dict = {(0.0, 0.0, 0.0) : 'TOP',
                            (r(math.pi), 0.0, 0.0) : 'BOTTOM',
                            (r(-math.pi/2), 0.0, 0.0) : 'FRONT',
                            (r(math.pi/2), 0.0, r(-math.pi)) : 'BACK',
                            (r(-math.pi/2), r(math.pi/2), 0.0) : 'LEFT',
                            (r(-math.pi/2), r(-math.pi/2), 0.0) : 'RIGHT'}

        view_orientation =  orientation_dict.get(tuple(map(r, view_rot)), 'USER').capitalize()
        view_orientation += " " + view.view_perspective.capitalize()

    if space.local_view is not None:
        view_orientation += " (Local)"

    return view_orientation


def get_quadview_index(context, x, y):
    for area in context.screen.areas:
        if area.type != 'VIEW_3D':
            continue
        is_quadview = len(area.spaces.active.region_quadviews) == 0
        i = -1
        for region in area.regions:
            if region.type == 'WINDOW':
                i += 1
                if (x >= region.x and
                    y >= region.y and
                    x < region.width + region.x and
                    y < region.height + region.y):

                    return (area.spaces.active, None if is_quadview else i)
    return (None, None)


class paintbrush(Operator):
    """Paint additional bricks onto the Bricker model"""
    bl_idname = "bricker.paintbrush"
    bl_label = "Bricker Paintbrush"
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
            # commit changes on return key press
            if event.type == "ESC" and event.value == "PRESS":
                bpy.context.window.cursor_set("DEFAULT")
                self.cancel(context)
                self.undo_stack.undo_pop_clean()
                return{"CANCELLED"}

            # commit changes on return key press
            if event.type == "RET" and event.value == "PRESS":
                bpy.context.window.cursor_set("DEFAULT")
                self.cancel(context)
                self.commitChanges()
                return{"FINISHED"}

            # block undo action
            if event.type in ["LEFT_CTRL", "RIGHT_CTRL", "OSKEY"] and event.value == "PRESS":
                self.ctrl = True
            if event.type in ["LEFT_CTRL", "RIGHT_CTRL", "OSKEY"] and event.value == "RELEASE":
                self.ctrl = False
            if event.type == "Z" and self.ctrl:
                return {"RUNNING_MODAL"}

            # check if left_click is pressed
            if event.type == "LEFTMOUSE" and event.value == "PRESS":
                self.left_click = True
                # block left_click if not in 3D viewport
                space, i = get_quadview_index(context, event.mouse_x, event.mouse_y)
                if space is None:
                    return {"RUNNING_MODAL"}
            if event.type == "LEFTMOUSE" and event.value == "RELEASE":
                self.left_click = False

            # clear recentlyAddedBricks on mousemove when left_click not pressed
            if event.type == "MOUSEMOVE" and len(self.recentlyAddedBricks) > 0 and not self.left_click:
                self.recentlyAddedBricks = []

            # check if shift is pressed
            if event.type in ["LEFT_ALT", "RIGHT_ALT"] and event.value == "PRESS":
                self.shift = True
            if event.type in ["LEFT_ALT", "RIGHT_ALT"] and event.value == "RELEASE":
                self.shift = False

            # cast ray to calculate mouse position and travel
            if event.type in ['TIMER', 'MOUSEMOVE'] or self.left_click:
                scn, cm, n = getActiveContextInfo()
                x, y = event.mouse_region_x, event.mouse_region_y
                self.mouseTravel = abs(x - self.lastMousePos[0]) + abs(y - self.lastMousePos[1])
                self.hover_scene(context, x, y, cm.source_name, update_header=self.left_click)
                if self.obj is None:
                    bpy.context.window.cursor_set("DEFAULT")
                    return {"PASS_THROUGH"}
                else:
                    bpy.context.window.cursor_set("PAINT_BRUSH")

            # draw/remove bricks on left_click & drag
            if self.left_click and (event.type == 'LEFTMOUSE' or (event.type == "MOUSEMOVE" and (not self.shift or self.mouseTravel > 5))):
                self.lastMousePos = [x, y]
                addBrick = not (self.shift or self.obj.name in self.recentlyAddedBricks) and self.mode == "BRICK"
                removeBrick = self.shift and self.obj.name in self.addedBricks and self.mode == "BRICK"
                changeMaterial = self.obj.name not in self.addedBricks and self.mode == "MATERIAL"
                splitBrick = self.obj.name not in self.addedBricks and self.mode == "SPLIT"
                mergeBrick = self.obj.name not in self.addedBricks and self.mode == "MERGE"
                if addBrick or removeBrick or changeMaterial or splitBrick or mergeBrick:
                    # get key of current brick in bricksDict
                    curKey = getDictKey(self.obj.name)
                    curLoc = getDictLoc(self.bricksDict, curKey)
                    objSize = self.bricksDict[curKey]["size"]
                # add brick next to existing brick
                if addBrick and self.bricksDict[curKey]["name"] not in self.recentlyAddedBricks:
                    # get difference between intersection loc and object loc
                    Bricker_parent_on = "Bricker_%(n)s_parent" % locals()
                    parent = bpy.data.objects.get(Bricker_parent_on)
                    locDiff = self.loc - transformToWorld(Vector(self.bricksDict[curKey]["co"]), parent.matrix_world, self.junk_bme)
                    locDiff = transformToLocal(locDiff, parent.matrix_world)
                    nextLoc = getNearbyLocFromVector(locDiff, curLoc, self.dimensions, cm.zStep)
                    # draw brick at nextLoc location
                    nextKey, adjBrickD = drawAdjacent.getBrickD(self.bricksDict, nextLoc)
                    if not adjBrickD or not self.bricksDict[nextKey]["draw"] and self.bricksDict[curKey]["name"] not in self.recentlyAddedBricks:
                        self.adjDKLs = getAdjDKLs(cm, self.bricksDict, curKey, self.obj)
                        # add brick at nextKey location
                        status = drawAdjacent.toggleBrick(cm, self.bricksDict, self.adjDKLs, [[False]], self.dimensions, nextLoc, curKey, curLoc, objSize, self.brickType, 0, 0, self.keysToMerge, temporaryBrick=True)
                        if not status["val"]:
                            self.report({status["report_type"]}, status["msg"])
                        self.addedBricks.append(self.bricksDict[nextKey]["name"])
                        self.recentlyAddedBricks.append(self.bricksDict[nextKey]["name"])
                        self.targettedBrickKeys.append(curKey)
                    # draw created bricks
                    drawUpdatedBricks(cm, self.bricksDict, [nextKey], action="adding new brick", selectCreated=False, tempBrick=True)
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
                # change material
                elif changeMaterial and self.bricksDict[curKey]["mat_name"] != self.matName:
                    if max(objSize[:2]) > 1:
                        brickKeys = Bricks.split(self.bricksDict, curKey, cm.zStep, cm.brickType, loc=curLoc, v=self.vertical, h=self.horizontal)
                        brick = bpy.data.objects.get(self.bricksDict[curKey]["name"])
                        delete(brick)
                        # get difference between intersection loc and object loc
                        Bricker_parent_on = "Bricker_%(n)s_parent" % locals()
                        parent = bpy.data.objects.get(Bricker_parent_on)
                        minDiff = None
                        for k in brickKeys:
                            brickLoc = transformToWorld(Vector(self.bricksDict[k]["co"]), parent.matrix_world, self.junk_bme)
                            locDiff = abs(self.loc[0] - brickLoc[0]) + abs(self.loc[1] - brickLoc[1]) + abs(self.loc[2] - brickLoc[2])
                            if minDiff is None or locDiff < minDiff:
                                minDiff = locDiff
                                curKey = k
                    else:
                        brickKeys = [curKey]
                    self.bricksDict[curKey]["mat_name"] = self.matName
                    self.bricksDict[curKey]["custom_mat_name"] = True
                    self.addedBricks.append(self.bricksDict[curKey]["name"])
                    self.keysToMerge += brickKeys
                    # draw created bricks
                    drawUpdatedBricks(cm, self.bricksDict, brickKeys, action="updating material", selectCreated=False, tempBrick=True)
                # split current brick
                elif splitBrick and max(self.bricksDict[curKey]["size"][:2]) > 1:
                    brickKeys = Bricks.split(self.bricksDict, curKey, cm.zStep, cm.brickType, loc=curLoc, v=self.vertical, h=self.horizontal)
                    for k in brickKeys:
                        self.addedBricks.append(self.bricksDict[k]["name"])
                    self.allUpdatedKeys += brickKeys
                    # remove large brick
                    brick = bpy.data.objects.get(self.bricksDict[curKey]["name"])
                    delete(brick)
                    # draw split bricks
                    drawUpdatedBricks(cm, self.bricksDict, brickKeys, action="splitting bricks", selectCreated=False, tempBrick=True)
                # merge current brick
                elif mergeBrick:
                    brickKeys = getKeysInBrick(self.bricksDict, objSize, cm.zStep, curKey, curLoc)
                    self.keysToMerge += brickKeys
                    self.addedBricks.append(self.bricksDict[curKey]["name"])
                return {"RUNNING_MODAL"}

            if event.type == "LEFTMOUSE" and event.value == "RELEASE" and self.mode == "MERGE":
                scn, cm, _ = getActiveContextInfo()
                # delete outdated brick
                for obj_name in self.addedBricks:
                    delete(bpy.data.objects.get(obj_name))
                # split up bricks
                Bricks.splitAll(self.bricksDict, cm.zStep, keys=self.keysToMerge)
                # merge bricks after they've been split
                height3Only = "PLATES" in cm.brickType and self.brickType in getBrickTypes(height=3)
                mergedKeys = mergeBricks.mergeBricks(self.bricksDict, self.keysToMerge, cm, mergeVertical=self.brickType in getBrickTypes(height=3), targetType=self.brickType, height3Only=height3Only)
                self.allUpdatedKeys += mergedKeys
                # reset lists
                self.keysToMerge = []
                self.addedBricks = []
                # draw merged bricks
                drawUpdatedBricks(cm, self.bricksDict, mergedKeys, action="merging bricks", selectCreated=False, tempBrick=True)

            return {"PASS_THROUGH"}
        except:
            bpy.context.window.cursor_set("DEFAULT")
            self.cancel(context)
            handle_exception()
            return {"CANCELLED"}

    def execute(self, context):
        try:
            if self.brickType == "" or bpy.props.running_paintbrush:
                return {"CANCELLED"}
            bpy.props.running_paintbrush = True
            scn, cm, _ = getActiveContextInfo()
            # get fresh copy of self.bricksDict
            self.bricksDict, _ = getBricksDict(cm=cm)
            # create timer for modal
            wm = context.window_manager
            self._timer = wm.event_timer_add(0.01, context.window)
            wm.modal_handler_add(self)
            return{"RUNNING_MODAL"}
        except:
            handle_exception()
            return {"CANCELLED"}

    # def invoke(self, context, event):
    #     return context.window_manager.invoke_props_popup(self, event)

    ################################################
    # initialization method

    def __init__(self):
        scn, cm, _ = getActiveContextInfo()
        # push to undo stack
        self.undo_stack = UndoStack.get_instance()
        self.undo_stack.undo_push('brick_paintbrush', affected_ids=[cm.id])
        self.undo_stack.iterateStates(cm)
        # initialize vars
        self.addedBricks = []
        self.recentlyAddedBricks = []
        self.keysToMerge = []
        self.allUpdatedKeys = []
        self.dimensions = Bricks.get_dimensions(cm.brickHeight, cm.zStep, cm.gap)
        cm.customized = True
        self.left_click = False
        self.shift = False
        self.obj = None
        self.keysToMerge = []
        self.targettedBrickKeys = []
        self.brickType = "BRICK"
        self.matName = bpy.data.materials[0].name if len(bpy.data.materials) > 0 else ""
        self.vertical = False
        self.horizontal = True
        self.lastMousePos = [0, 0]
        self.mouseTravel = 0
        self.junk_bme = bmesh.new()
        self.ui_start()

    ###################################################
    # class variables

    # # get items for brickType prop
    # def get_items(self, context):
    #     scn, cm, _ = getActiveContextInfo()
    #     legalBS = bpy.props.Bricker_legal_brick_sizes
    #     items = [itemFromType(typ) for typ in legalBS[cm.zStep]]
    #     if cm.zStep == 1:
    #         items += [itemFromType(typ) for typ in legalBS[3]]
    #     # items = getAvailableTypes(by="ACTIVE", includeSizes="ALL")
    #     return items
    #
    # # define props for popup
    # brickType = bpy.props.EnumProperty(
    #     name="Brick Type",
    #     description="Type of brick to draw adjacent to current brick",
    #     items=get_items,
    #     default=None)

    # define props for popup
    mode = bpy.props.EnumProperty(
        items=[("BRICK", "BRICK", ""),
               ("MATERIAL", "MATERIAL", ""),
               ("SPLIT", "SPLIT", ""),
               ("MERGE", "MERGE", ""),
               ],
    )

    #############################################
    # class methods

    # from CG Cookie's retopoflow plugin
    def hover_scene(self, context, x, y, source_name, update_header=True):
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
        else:
            self.obj = None
            self.normal = None
            context.area.header_text_set()

    def commitChanges(self):
        scn, cm, _ = getActiveContextInfo()
        keysToUpdate = []
        # execute final operations for current mode
        if self.mode == "SPLIT":
            # set exposure of split bricks
            keysToUpdate = uniquify(self.allUpdatedKeys)
            for k in keysToUpdate:
                setAllBrickExposures(self.bricksDict, cm.zStep, k)
        if self.mode == "MERGE":
            keysToUpdate = uniquify(self.allUpdatedKeys)
            # remove bricks to be redrawn
            for k in keysToUpdate:
                delete(bpy.data.objects.get(self.bricksDict[k]["name"]))
        elif self.mode in ["MATERIAL", "BRICK"]:
            self.keysToMerge = uniquify(self.keysToMerge)
            # attempt to merge created bricks
            if mergableBrickType(self.brickType):
                height3Only = "PLATES" in cm.brickType and self.brickType in getBrickTypes(height=3)
                mergedKeys = mergeBricks.mergeBricks(self.bricksDict, self.keysToMerge, cm, mergeVertical=self.brickType in getBrickTypes(height=3), targetType=self.brickType, height3Only=height3Only)
            # set exposure of created bricks and targetted bricks
            keysToUpdate = uniquify(mergedKeys + (self.targettedBrickKeys if self.mode == "BRICK" else []))
            for k in keysToUpdate:
                setAllBrickExposures(self.bricksDict, cm.zStep, k)
            # remove merged 1x1 bricks
            for k in self.keysToMerge:
                if k not in mergedKeys:
                    delete(bpy.data.objects.get(self.bricksDict[k]["name"]))
        # draw updated bricks
        drawUpdatedBricks(cm, self.bricksDict, keysToUpdate, action="committing changes", selectCreated=False)

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        context.area.header_text_set()
        bpy.props.running_paintbrush = False
        self.ui_end()

    ##############################################
    # Draw handler function
    # from CG Cookie's retopoflow plugin

    def ui_start(self):
        # report something useful to user
        bpy.context.area.header_text_set("Click & drag to add bricks (+'ALT' to remove). Press 'RETURN' to commit changes")

        # add callback handlers
        self.cb_pr_handle = SpaceView3D.draw_handler_add(self.draw_callback_preview,   (bpy.context, ), 'WINDOW', 'PRE_VIEW')
        # self.cb_pv_handle = SpaceView3D.draw_handler_add(self.draw_callback_postview,  (bpy.context, ), 'WINDOW', 'POST_VIEW')
        # self.cb_pp_handle = SpaceView3D.draw_handler_add(self.draw_callback_postpixel, (bpy.context, ), 'WINDOW', 'POST_PIXEL')
        # darken other spaces
        self.spaces = [
            bpy.types.SpaceClipEditor,
            bpy.types.SpaceConsole,
            bpy.types.SpaceDopeSheetEditor,
            bpy.types.SpaceFileBrowser,
            bpy.types.SpaceGraphEditor,
            bpy.types.SpaceImageEditor,
            bpy.types.SpaceInfo,
            bpy.types.SpaceLogicEditor,
            bpy.types.SpaceNLA,
            bpy.types.SpaceNodeEditor,
            bpy.types.SpaceOutliner,
            bpy.types.SpaceProperties,
            bpy.types.SpaceSequenceEditor,
            bpy.types.SpaceTextEditor,
            bpy.types.SpaceTimeline,
            #bpy.types.SpaceUVEditor,       # <- does not exist?
            bpy.types.SpaceUserPreferences,
            #'SpaceView3D',                 # <- specially handled
            ]
        self.areas = [ 'WINDOW', 'HEADER' ]
        # ('WINDOW', 'HEADER', 'CHANNELS', 'TEMPORARY', 'UI', 'TOOLS', 'TOOL_PROPS', 'PREVIEW')
        self.cb_pp_tools   = SpaceView3D.draw_handler_add(self.draw_callback_cover, (bpy.context, ), 'TOOLS',      'POST_PIXEL')
        self.cb_pp_props   = SpaceView3D.draw_handler_add(self.draw_callback_cover, (bpy.context, ), 'TOOL_PROPS', 'POST_PIXEL')
        self.cb_pp_ui      = SpaceView3D.draw_handler_add(self.draw_callback_cover, (bpy.context, ), 'UI',         'POST_PIXEL')
        self.cb_pp_header  = SpaceView3D.draw_handler_add(self.draw_callback_cover, (bpy.context, ), 'HEADER',     'POST_PIXEL')
        self.cb_pp_all = [
            (s, a, s.draw_handler_add(self.draw_callback_cover, (bpy.context,), a, 'POST_PIXEL'))
            for s in self.spaces
            for a in self.areas
            ]
        self.draw_preview()
        tag_redraw_areas()

    def ui_end(self):
        # remove callback handlers
        if hasattr(self, 'cb_pr_handle'):
            SpaceView3D.draw_handler_remove(self.cb_pr_handle, "WINDOW")
            del self.cb_pr_handle
        if hasattr(self, 'cb_pv_handle'):
            SpaceView3D.draw_handler_remove(self.cb_pv_handle, "WINDOW")
            del self.cb_pv_handle
        if hasattr(self, 'cb_pp_handle'):
            SpaceView3D.draw_handler_remove(self.cb_pp_handle, "WINDOW")
            del self.cb_pp_handle
        if hasattr(self, 'cb_pp_tools'):
            SpaceView3D.draw_handler_remove(self.cb_pp_tools,  "TOOLS")
            del self.cb_pp_tools
        if hasattr(self, 'cb_pp_props'):
            SpaceView3D.draw_handler_remove(self.cb_pp_props,  "TOOL_PROPS")
            del self.cb_pp_props
        if hasattr(self, 'cb_pp_ui'):
            SpaceView3D.draw_handler_remove(self.cb_pp_ui,     "UI")
            del self.cb_pp_ui
        if hasattr(self, 'cb_pp_header'):
            SpaceView3D.draw_handler_remove(self.cb_pp_header, "HEADER")
            del self.cb_pp_header
        if hasattr(self, 'cb_pp_all'):
            for s,a,cb in self.cb_pp_all: s.draw_handler_remove(cb, a)
            del self.cb_pp_all
        tag_redraw_areas()

    def draw_callback_preview(self, context):
        bgl.glPushAttrib(bgl.GL_ALL_ATTRIB_BITS)    # save OpenGL attributes
        try:    self.draw_preview()
        except: handle_exception()
        bgl.glPopAttrib()                           # restore OpenGL attributes

    def draw_callback_cover(self, context):
        bgl.glPushAttrib(bgl.GL_ALL_ATTRIB_BITS)
        bgl.glMatrixMode(bgl.GL_PROJECTION)
        bgl.glPushMatrix()
        bgl.glLoadIdentity()
        bgl.glColor4f(0,0,0,0.5)    # TODO: use window background color??
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glDisable(bgl.GL_DEPTH_TEST)
        bgl.glBegin(bgl.GL_QUADS)   # TODO: not use immediate mode
        bgl.glVertex2f(-1, -1)
        bgl.glVertex2f( 1, -1)
        bgl.glVertex2f( 1,  1)
        bgl.glVertex2f(-1,  1)
        bgl.glEnd()
        bgl.glPopMatrix()
        bgl.glPopAttrib()

    def draw_preview(self):
        bgl.glEnable(bgl.GL_MULTISAMPLE)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glHint(bgl.GL_LINE_SMOOTH_HINT, bgl.GL_NICEST)
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_POINT_SMOOTH)
        bgl.glDisable(bgl.GL_DEPTH_TEST)

        bgl.glMatrixMode(bgl.GL_MODELVIEW)
        bgl.glPushMatrix()
        bgl.glLoadIdentity()
        bgl.glMatrixMode(bgl.GL_PROJECTION)
        bgl.glPushMatrix()
        bgl.glLoadIdentity()

        # add background gradient
        bgl.glBegin(bgl.GL_TRIANGLES)
        for i in range(0,360,10):
            r0,r1 = i*math.pi/180.0, (i+10)*math.pi/180.0
            x0,y0 = math.cos(r0)*2,math.sin(r0)*2
            x1,y1 = math.cos(r1)*2,math.sin(r1)*2
            bgl.glColor4f(0,0,0.01,0.0)
            bgl.glVertex2f(0,0)
            bgl.glColor4f(0,0,0.01,0.8)
            bgl.glVertex2f(x0,y0)
            bgl.glVertex2f(x1,y1)
        bgl.glEnd()

        bgl.glMatrixMode(bgl.GL_PROJECTION)
        bgl.glPopMatrix()
        bgl.glMatrixMode(bgl.GL_MODELVIEW)
        bgl.glPopMatrix()
