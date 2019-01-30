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
from addon_utils import check, paths, enable
from bpy.types import Panel
from bpy.props import *
props = bpy.props

# Addon imports
from .cmlist_attrs import *
from .cmlist_actions import *
from .app_handlers import *
from .matlist_window import *
from .matlist_actions import *
from ..lib.bricksDict import *
from ..lib.Brick.test_brick_generators import *
from ..buttons.delete import BrickerDelete
from ..buttons.revertSettings import *
from ..buttons.cache import *
from ..functions import *

# updater import
from .. import addon_updater_ops


def settingsCanBeDrawn():
    scn = bpy.context.scene
    if scn.cmlist_index == -1:
        return False
    if bversion() < '002.078.00':
        return False
    if not bpy.props.bricker_initialized:
        return False
    return True


class BasicMenu(bpy.types.Menu):
    bl_idname      = "Bricker_specials_menu"
    bl_label       = "Select"

    def draw(self, context):
        layout = self.layout

        layout.operator("cmlist.copy_to_others", icon="COPY_ID", text="Copy Settings to Others")
        layout.operator("cmlist.copy_settings", icon="COPYDOWN", text="Copy Settings")
        layout.operator("cmlist.paste_settings", icon="PASTEDOWN", text="Paste Settings")
        layout.operator("cmlist.select_bricks", icon="RESTRICT_SELECT_OFF", text="Select Bricks").deselect = False
        layout.operator("cmlist.select_bricks", icon="RESTRICT_SELECT_ON", text="Deselect Bricks").deselect = True


class BrickModelsPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Brick Models"
    bl_idname      = "VIEW3D_PT_tools_Bricker_brick_models"
    bl_context     = "objectmode"
    bl_category    = "Bricker"

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        # Call to check for update in background
        # Internally also checks to see if auto-check enabled
        # and if the time interval has passed
        addon_updater_ops.check_for_update_background()
        # draw auto-updater update box
        addon_updater_ops.update_notice_box_ui(self, context)

        # if blender version is before 2.78, ask user to upgrade Blender
        if bversion() < '002.078.00':
            col = layout.column(align=True)
            col.label('ERROR: upgrade needed', icon='ERROR')
            col.label('Bricker requires Blender 2.78+')
            return

        # draw UI list and list actions
        if len(scn.cmlist) < 2:
            rows = 2
        else:
            rows = 4
        row = layout.row()
        row.template_list("Bricker_UL_cmlist_items", "", scn, "cmlist", scn, "cmlist_index", rows=rows)

        col = row.column(align=True)
        col.operator("cmlist.list_action" if bpy.props.bricker_initialized else "bricker.initialize", text="", icon="ZOOMIN").action = 'ADD'
        col.operator("cmlist.list_action", icon='ZOOMOUT', text="").action = 'REMOVE'
        col.menu("Bricker_specials_menu", icon='DOWNARROW_HLT', text="")
        if len(scn.cmlist) > 1:
            col.separator()
            col.operator("cmlist.list_action", icon='TRIA_UP', text="").action = 'UP'
            col.operator("cmlist.list_action", icon='TRIA_DOWN', text="").action = 'DOWN'

        # draw menu options below UI list
        if scn.cmlist_index == -1:
            layout.operator("cmlist.list_action" if bpy.props.bricker_initialized else "bricker.initialize", text="New Brick Model", icon="ZOOMIN").action = 'ADD'
        else:
            cm, n = getActiveContextInfo()[1:]
            if not createdWithNewerVersion(cm):
                # first, draw source object text
                source_name = " %(n)s" % locals() if cm.animated or cm.modelCreated else ""
                col1 = layout.column(align=True)
                col1.label(text="Source Object:%(source_name)s" % locals())
                if not (cm.animated or cm.modelCreated):
                    col2 = layout.column(align=True)
                    col2.prop_search(cm, "source_obj", scn, "objects", text='')

            # initialize variables
            obj = cm.source_obj
            v_str = cm.version[:3]

            # if model created with newer version, disable
            if createdWithNewerVersion(cm):
                col = layout.column(align=True)
                col.scale_y = 0.7
                col.label(text="Model was created with")
                col.label(text="Bricker v%(v_str)s. Please" % locals())
                col.label(text="update Bricker in your")
                col.label(text="addon preferences to edit")
                col.label(text="this model.")
            # if undo stack not initialized, draw initialize button
            elif not bpy.props.bricker_initialized:
                row = col1.row(align=True)
                row.operator("bricker.initialize", text="Initialize Bricker", icon="MODIFIER")
                # draw test brick generator button (for testing purposes only)
                if testBrickGenerators.drawUIButton():
                    col = layout.column(align=True)
                    col.operator("bricker.test_brick_generators", text="Test Brick Generators", icon="OUTLINER_OB_MESH")
            # if use animation is selected, draw animation options
            elif cm.useAnimation:
                if cm.animated:
                    row = col1.row(align=True)
                    row.operator("bricker.delete_model", text="Delete Brick Animation", icon="CANCEL")
                    col = layout.column(align=True)
                    row = col.row(align=True)
                    if cm.brickifyingInBackground:
                        col.scale_y = 0.75
                        row.label(text="brickifyingInBackground in background...")
                        row = col.row(align=True)
                        percentage = round(cm.numAnimatedFrames * 100 / (cm.lastStopFrame - cm.lastStartFrame + 1), 3)
                        row.label(text=str(percentage) + "% completed")
                    else:
                        row.operator("bricker.brickify", text="Update Animation", icon="FILE_REFRESH")
                    if createdWithUnsupportedVersion(cm):
                        v_str = cm.version[:3]
                        col = layout.column(align=True)
                        col.scale_y = 0.7
                        col.label(text="Model was created with")
                        col.label(text="Bricker v%(v_str)s. Please" % locals())
                        col.label(text="run 'Update Model' so")
                        col.label(text="it is compatible with")
                        col.label(text="your current version.")
                else:
                    row = col1.row(align=True)
                    row.active = obj is not None and obj.type == 'MESH' and (obj.rigid_body is None or obj.rigid_body.type == "PASSIVE")
                    row.operator("bricker.brickify", text="Brickify Animation", icon="MOD_REMESH")
                    if obj and obj.rigid_body is not None:
                        col = layout.column(align=True)
                        col.scale_y = 0.7
                        if obj.rigid_body.type == "ACTIVE":
                            col.label(text="Bake rigid body transforms")
                            col.label(text="to keyframes (SPACEBAR >")
                            col.label(text="Bake To Keyframes).")
                        else:
                            col.label(text="Rigid body settings will")
                            col.label(text="be lost.")
            # if use animation is not selected, draw modeling options
            else:
                if not cm.animated and not cm.modelCreated:
                    row = col1.row(align=True)
                    row.active = obj is not None and obj.type == 'MESH' and (obj.rigid_body is None or obj.rigid_body.type == "PASSIVE")
                    row.operator("bricker.brickify", text="Brickify Object", icon="MOD_REMESH")
                    if obj and obj.rigid_body is not None:
                        col = layout.column(align=True)
                        col.scale_y = 0.7
                        if obj.rigid_body.type == "ACTIVE":
                            col.label(text="Bake rigid body transforms")
                            col.label(text="to keyframes (SPACEBAR >")
                            col.label(text="Bake To Keyframes).")
                        else:
                            col.label(text="Rigid body settings will")
                            col.label(text="be lost.")
                else:
                    row = col1.row(align=True)
                    row.operator("bricker.delete_model", text="Delete Brickified Model", icon="CANCEL")
                    col = layout.column(align=True)
                    col.operator("bricker.brickify", text="Update Model", icon="FILE_REFRESH")
                    if createdWithUnsupportedVersion(cm):
                        col = layout.column(align=True)
                        col.scale_y = 0.7
                        col.label(text="Model was created with")
                        col.label(text="Bricker v%(v_str)s. Please" % locals())
                        col.label(text="run 'Update Model' so")
                        col.label(text="it is compatible with")
                        col.label(text="your current version.")
                    elif matrixReallyIsDirty(cm) and cm.customized:
                        row = col.row(align=True)
                        row.label(text="Customizations will be lost")
                        row = col.row(align=True)
                        row.operator("bricker.revert_matrix_settings", text="Revert Settings", icon="LOOP_BACK")

            col = layout.column(align=True)
            row = col.row(align=True)

        if bpy.data.texts.find('Bricker_log') >= 0:
            split = layout.split(align=True, percentage=0.9)
            col = split.column(align=True)
            row = col.row(align=True)
            row.operator("bricker.report_error", text="Report Error", icon="URL")
            col = split.column(align=True)
            row = col.row(align=True)
            row.operator("bricker.close_report_error", text="", icon="PANEL_CLOSE")


def is_baked(mod):
    return mod.point_cache.is_baked is not False


class AnimationPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Animation"
    bl_idname      = "VIEW3D_PT_tools_Bricker_animation"
    bl_context     = "objectmode"
    bl_category    = "Bricker"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settingsCanBeDrawn():
            return False
        scn, cm, n = getActiveContextInfo()
        if cm.modelCreated:
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = getActiveContextInfo()

        if not cm.animated:
            col = layout.column(align=True)
            col.prop(cm, "useAnimation")
        if cm.useAnimation:
            col1 = layout.column(align=True)
            col1.active = cm.animated or cm.useAnimation
            col1.scale_y = 0.85
            row = col1.row(align=True)
            split = row.split(align=True, percentage=0.5)
            col = split.column(align=True)
            col.prop(cm, "startFrame")
            col = split.column(align=True)
            col.prop(cm, "stopFrame")
            source = cm.source_obj
            self.appliedMods = False
            if source:
                for mod in source.modifiers:
                    if mod.type in ("CLOTH", "SOFT_BODY") and mod.show_viewport:
                        self.appliedMods = True
                        t = mod.type
                        if mod.point_cache.frame_end < cm.stopFrame:
                            s = str(max([mod.point_cache.frame_end+1, cm.startFrame]))
                            e = str(cm.stopFrame)
                        elif mod.point_cache.frame_start > cm.startFrame:
                            s = str(cm.startFrame)
                            e = str(min([mod.point_cache.frame_start-1, cm.stopFrame]))
                        else:
                            s = "0"
                            e = "-1"
                        totalSkipped = int(e) - int(s) + 1
                        if totalSkipped > 0:
                            row = col1.row(align=True)
                            row.label(text="Frames %(s)s-%(e)s outside of %(t)s simulation" % locals())
            col = layout.column(align=True)
            row = col.row(align=True)
            row.label(text="Background Processing:")
            row = col.row(align=True)
            row.prop(cm, "maxWorkers")
            row = col.row(align=True)
            row.prop(cm, "backProcTimeout")


class ModelTransformPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Model Transform"
    bl_idname      = "VIEW3D_PT_tools_Bricker_model_transform"
    bl_context     = "objectmode"
    bl_category    = "Bricker"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settingsCanBeDrawn():
            return False
        scn, cm, _ = getActiveContextInfo()
        if cm.modelCreated or cm.animated:
            return True
        return False

    def draw(self, context):
        layout = self.layout
        scn, cm, n = getActiveContextInfo()

        col = layout.column(align=True)
        row = col.row(align=True)

        if not (cm.animated or cm.lastSplitModel):
            col.scale_y = 0.7
            row.label(text="Use Blender's built-in")
            row = col.row(align=True)
            row.label(text="transformation manipulators")
            col = layout.column(align=True)
            return

        row.prop(cm, "applyToSourceObject")
        if cm.animated or (cm.lastSplitModel and cm.modelCreated):
            row = col.row(align=True)
            row.prop(cm, "exposeParent")
        row = col.row(align=True)
        parent = bpy.data.objects['Bricker_%(n)s_parent' % locals()]
        row = layout.row()
        row.column().prop(parent, "location")
        if parent.rotation_mode == 'QUATERNION':
            row.column().prop(parent, "rotation_quaternion", text="Rotation")
        elif parent.rotation_mode == 'AXIS_ANGLE':
            row.column().prop(parent, "rotation_axis_angle", text="Rotation")
        else:
            row.column().prop(parent, "rotation_euler", text="Rotation")
        # row.column().prop(parent, "scale")
        layout.prop(parent, "rotation_mode")
        layout.prop(cm, "transformScale")


class ModelSettingsPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Model Settings"
    bl_idname      = "VIEW3D_PT_tools_Bricker_model_settings"
    bl_context     = "objectmode"
    bl_category    = "Bricker"

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns false) """
        if not settingsCanBeDrawn():
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = getActiveContextInfo()
        source = cm.source_obj

        col = layout.column(align=True)
        # set up model dimensions variables sX, sY, and sZ
        s = Vector((-1, -1, -1))
        if -1 in cm.modelScalePreview:
            if source:
                source_details = bounds(source, use_adaptive_domain=False)
                s.x = round(source_details.dist.x, 2)
                s.y = round(source_details.dist.y, 2)
                s.z = round(source_details.dist.z, 2)
        else:
            s = Vector(cm.modelScalePreview)
        # draw Brick Model dimensions to UI if set
        if -1 not in s:
            if cm.brickType != "CUSTOM":
                dimensions = Bricks.get_dimensions(cm.brickHeight, getZStep(cm), cm.gap)
                full_d = Vector((dimensions["width"],
                                 dimensions["width"],
                                 dimensions["height"]))
                r = vec_div(s, full_d)
            elif cm.brickType == "CUSTOM":
                customObjFound = False
                customObj = cm.customObject1
                if customObj and customObj.type == "MESH":
                    custom_details = bounds(customObj)
                    if 0 not in custom_details.dist.to_tuple():
                        mult = (cm.brickHeight / custom_details.dist.z)
                        full_d = Vector((custom_details.dist.x * mult,
                                         custom_details.dist.y * mult,
                                         cm.brickHeight))
                        r = vec_div(s, full_d)
                        customObjFound = True
            if cm.brickType == "CUSTOM" and not customObjFound:
                col.label(text="[Custom object not found]")
            else:
                split = col.split(align=True, percentage=0.5)
                col1 = split.column(align=True)
                col1.label(text="Dimensions:")
                col2 = split.column(align=True)
                col2.alignment = "RIGHT"
                col2.label(text="{}x{}x{}".format(int(r.x), int(r.y), int(r.z)))
        row = col.row(align=True)
        row.prop(cm, "brickHeight")
        row = col.row(align=True)
        row.prop(cm, "gap")

        row = col.row(align=True)
        row.label(text="Randomize:")
        row = col.row(align=True)
        split = row.split(align=True, percentage=0.5)
        col1 = split.column(align=True)
        col1.prop(cm, "randomLoc", text="Loc")
        col2 = split.column(align=True)
        col2.prop(cm, "randomRot", text="Rot")

        col = layout.column(align=True)
        row = col.row(align=True)
        if not cm.useAnimation:
            row = col.row(align=True)
            row.prop(cm, "splitModel")

        row = col.row(align=True)
        row.label(text="Brick Shell:")
        row = col.row(align=True)
        row.prop(cm, "brickShell", text="")
        if cm.brickShell != "INSIDE":
            row = col.row(align=True)
            row.prop(cm, "calculationAxes", text="")
        row = col.row(align=True)
        row.prop(cm, "shellThickness", text="Thickness")
        obj = cm.source_obj
        # if obj and not cm.isWaterTight:
        #     row = col.row(align=True)
        #     # row.scale_y = 0.7
        #     row.label(text="(Source is NOT single closed mesh)")
        #     # row = col.row(align=True)
        #     # row.operator("scene.make_closed_mesh", text="Make Single Closed Mesh", icon="EDIT")



class SmokeSettingsPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Smoke Settings"
    bl_idname      = "VIEW3D_PT_tools_Bricker_smoke_settings"
    bl_context     = "objectmode"
    bl_category    = "Bricker"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns false) """
        if not settingsCanBeDrawn():
            return False
        scn = bpy.context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        source = cm.source_obj
        if source is None:
            return False
        return is_smoke(source)

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = getActiveContextInfo()
        source = cm.source_obj

        col = layout.column(align=True)
        if is_smoke(source):
            row = col.row(align=True)
            row.prop(cm, "smokeDensity", text="Density")
            row = col.row(align=True)
            row.prop(cm, "smokeQuality", text="Quality")

        if is_smoke(source):
            col = layout.column(align=True)
            row = col.row(align=True)
            row.label(text="Smoke Color:")
            row = col.row(align=True)
            row.prop(cm, "smokeBrightness", text="Brightness")
            row = col.row(align=True)
            row.prop(cm, "smokeSaturation", text="Saturation")
            row = col.row(align=True)
            row.label(text="Flame Color:")
            row = col.row(align=True)
            row.prop(cm, "flameColor", text="")
            row = col.row(align=True)
            row.prop(cm, "flameIntensity", text="Intensity")


class BrickTypesPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Brick Types"
    bl_idname      = "VIEW3D_PT_tools_Bricker_brick_types"
    bl_context     = "objectmode"
    bl_category    = "Bricker"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settingsCanBeDrawn():
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = getActiveContextInfo()

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(cm, "brickType", text="")

        if mergableBrickType(cm.brickType):
            col = layout.column(align=True)
            col.label(text="Max Brick Size:")
            row = col.row(align=True)
            row.prop(cm, "maxWidth", text="Width")
            row.prop(cm, "maxDepth", text="Depth")
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(cm, "legalBricksOnly")

        if cm.brickType == "CUSTOM":
            col = layout.column(align=True)
            col.label(text="Brick Type Object:")
        elif cm.lastSplitModel:
            col.label(text="Custom Brick Objects:")
        if cm.brickType == "CUSTOM" or cm.lastSplitModel:
            for prop in ("customObject1", "customObject2", "customObject3"):
                if prop[-1] == "2" and cm.brickType == "CUSTOM":
                    col.label(text="Distance Offset:")
                    row = col.row(align=True)
                    row.prop(cm, "distOffset", text="")
                    col = layout.column(align=True)
                    col.label(text="Other Objects:")
                split = col.split(align=True, percentage=0.825)
                col1 = split.column(align=True)
                col1.prop_search(cm, prop, scn, "objects", text="")
                col1 = split.column(align=True)
                col1.operator("bricker.redraw_custom", icon="FILE_REFRESH", text="").target_prop = prop


class MergeSettingsPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Merge Settings"
    bl_idname      = "VIEW3D_PT_tools_Bricker_merge_settings"
    bl_context     = "objectmode"
    bl_category    = "Bricker"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settingsCanBeDrawn():
            return False
        scn = bpy.context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        return mergableBrickType(cm.brickType)

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = getActiveContextInfo()

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(cm, "mergeType", text="")
        if cm.mergeType == "RANDOM":
            row = col.row(align=True)
            row.prop(cm, "mergeSeed")
            row = col.row(align=True)
            row.prop(cm, "connectThresh")
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(cm, "mergeInconsistentMats")
        # TODO: Introduce to everyone if deemed helpful
        if bpy.props.Bricker_developer_mode > 0:
            row = col.row(align=True)
            row.prop(cm, "mergeInternals")
        if cm.brickType == "BRICKS AND PLATES":
            row = col.row(align=True)
            row.prop(cm, "alignBricks")
            if cm.alignBricks:
                row = col.row(align=True)
                row.prop(cm, "offsetBrickLayers")



class CustomizeModel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Customize Model"
    bl_idname      = "VIEW3D_PT_tools_Bricker_customize_mode"
    bl_context     = "objectmode"
    bl_category    = "Bricker"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settingsCanBeDrawn():
            return False
        scn, cm, _ = getActiveContextInfo()
        if createdWithUnsupportedVersion(cm):
            return False
        if not (cm.modelCreated or cm.animated):
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = getActiveContextInfo()

        if matrixReallyIsDirty(cm):
            layout.label(text="Matrix is dirty!")
            return
        if cm.animated:
            layout.label(text="Not available for animations")
            return
        if not cm.lastSplitModel:
            layout.label(text="Split model to customize")
            return
        if cm.buildIsDirty:
            layout.label(text="Run 'Update Model' to customize")
            return
        if not Caches.cacheExists(cm):
            layout.label(text="Matrix not cached!")
            return
        # if not bpy.props.bricker_initialized:
        #     layout.operator("bricker.initialize", icon="MODIFIER")
        #     return

        col1 = layout.column(align=True)
        col1.label(text="Selection:")
        split = col1.split(align=True, percentage=0.5)
        # set top exposed
        col = split.column(align=True)
        col.operator("bricker.select_bricks_by_type", text="By Type")
        # set bottom exposed
        col = split.column(align=True)
        col.operator("bricker.select_bricks_by_size", text="By Size")

        col1 = layout.column(align=True)
        col1.label(text="Toggle Exposure:")
        split = col1.split(align=True, percentage=0.5)
        # set top exposed
        col = split.column(align=True)
        col.operator("bricker.set_exposure", text="Top").side = "TOP"
        # set bottom exposed
        col = split.column(align=True)
        col.operator("bricker.set_exposure", text="Bottom").side = "BOTTOM"

        col1 = layout.column(align=True)
        col1.label(text="Brick Operations:")
        split = col1.split(align=True, percentage=0.5)
        # split brick into 1x1s
        col = split.column(align=True)
        col.operator("bricker.split_bricks", text="Split")
        # merge selected bricks
        col = split.column(align=True)
        col.operator("bricker.merge_bricks", text="Merge")
        # Add identical brick on +/- x/y/z
        row = col1.row(align=True)
        row.operator("bricker.draw_adjacent", text="Draw Adjacent Bricks")
        # change brick type
        row = col1.row(align=True)
        row.operator("bricker.change_brick_type", text="Change Type")
        # change material type
        row = col1.row(align=True)
        row.operator("bricker.change_brick_material", text="Change Material")
        # additional controls
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(cm, "autoUpdateOnDelete")
        # row = col.row(align=True)
        # row.operator("bricker.redraw_bricks")


class MaterialsPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Materials"
    bl_idname      = "VIEW3D_PT_tools_Bricker_materials"
    bl_context     = "objectmode"
    bl_category    = "Bricker"
    bl_options     = {"DEFAULT_CLOSED"}
    # COMPAT_ENGINES = {"CYCLES", "BLENDER_RENDER"}

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns false) """
        if not settingsCanBeDrawn():
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = getActiveContextInfo()
        obj = cm.source_obj

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(cm, "materialType", text="")

        if cm.materialType == "CUSTOM":
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop_search(cm, "materialName", bpy.data, "materials", text="")
            if brick_materials_installed():
                if bpy.context.scene.render.engine != 'CYCLES':
                    row = col.row(align=True)
                    row.label(text="Switch to 'Cycles' for Brick materials")
                elif not brick_materials_loaded():
                    row = col.row(align=True)
                    row.operator("scene.append_abs_plastic_materials", text="Import Brick Materials", icon="IMPORT")
                    # import settings
                    if hasattr(bpy.props, "abs_mats_common"): # checks that ABS plastic mats are at least v2.1
                        col = layout.column(align=True)
                        row = col.row(align=True)
                        row.prop(scn, "include_transparent")
                        row = col.row(align=True)
                        row.prop(scn, "include_uncommon")
            if cm.modelCreated or cm.animated:
                col = layout.column(align=True)
                row = col.row(align=True)
                row.operator("bricker.apply_material", icon="FILE_TICK")
        elif cm.materialType == "RANDOM":
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(cm, "randomMatSeed")
            if cm.modelCreated or cm.animated:
                if cm.materialIsDirty and not cm.lastSplitModel:
                    col = layout.column(align=True)
                    row = col.row(align=True)
                    row.label(text="Run 'Update Model' to apply changes")
                elif cm.lastMaterialType == cm.materialType or (not cm.useAnimation and cm.lastSplitModel):
                    col = layout.column(align=True)
                    row = col.row(align=True)
                    row.operator("bricker.apply_material", icon="FILE_TICK")
            col = layout.column(align=True)
        elif cm.materialType == "SOURCE" and obj:
            col = layout.column(align=True)
            col.active = len(obj.data.uv_layers) > 0
            row = col.row(align=True)
            row.prop(cm, "useUVMap", text="UV Map")
            if cm.useUVMap:
                split = row.split(align=True, percentage=0.75)
                split.prop_search(cm, "uvImageName", bpy.data, "images", text="")
                split.operator("image.open", icon="FILESEL", text="")
            if len(obj.data.vertex_colors) > 0:
                col = layout.column(align=True)
                col.scale_y = 0.7
                col.label(text="(Vertex colors not supported)")
            if cm.shellThickness > 1 or cm.internalSupports != "NONE":
                if len(obj.data.uv_layers) <= 0 or len(obj.data.vertex_colors) > 0:
                    col = layout.column(align=True)
                row = col.row(align=True)
                row.label(text="Internal Material:")
                row = col.row(align=True)
                row.prop_search(cm, "internalMatName", bpy.data, "materials", text="")
                row = col.row(align=True)
                row.prop(cm, "matShellDepth")
                if cm.modelCreated:
                    row = col.row(align=True)
                    if cm.matShellDepth <= cm.lastMatShellDepth:
                        row.operator("bricker.apply_material", icon="FILE_TICK")
                    else:
                        row.label(text="Run 'Update Model' to apply changes")

            col = layout.column(align=True)
            row = col.row(align=True)
            row.label(text="Color Snapping:")
            row = col.row(align=True)
            row.prop(cm, "colorSnap", text="")
            if cm.colorSnap == "RGB":
                row = col.row(align=True)
                row.prop(cm, "colorSnapAmount")
            if cm.colorSnap == "ABS":
                row = col.row(align=True)
                row.prop(cm, "transparentWeight", text="Transparent Weight")
                if hasattr(bpy.props, "abs_mats_common"): # checks that ABS plastic mats are at least v2.1
                    row.active = False if not brick_materials_installed() else scn.include_transparent

        if cm.materialType == "RANDOM" or (cm.materialType == "SOURCE" and cm.colorSnap == "ABS"):
            matObj = getMatObject(cm.id, typ="RANDOM" if cm.materialType == "RANDOM" else "ABS")
            if matObj is not None:
                if not brick_materials_installed():
                    col.label(text="'ABS Plastic Materials' not installed")
                elif scn.render.engine != 'CYCLES':
                    col.label(text="Switch to 'Cycles' for Brick Materials")
                else:
                    # draw materials UI list and list actions
                    numMats = len(matObj.data.materials)
                    rows = 5 if numMats > 5 else (numMats if numMats > 2 else 2)
                    split = col.split(align=True, percentage=0.85)
                    col1 = split.column(align=True)
                    col1.template_list("MATERIAL_UL_matslots_example", "", matObj, "material_slots", matObj, "active_material_index", rows=rows)
                    col1 = split.column(align=True)
                    col1.operator("bricker.mat_list_action", icon='ZOOMOUT', text="").action = 'REMOVE'
                    col1.scale_y = 1 + rows
                    if not brick_materials_loaded():
                        col.operator("scene.append_abs_plastic_materials", text="Import Brick Materials", icon="IMPORT")
                    else:
                        col.operator("bricker.add_abs_plastic_materials", text="Add ABS Plastic Materials", icon="ZOOMIN")
                    # import settings
                    if hasattr(bpy.props, "abs_mats_common"): # checks that ABS plastic mats are at least v2.1
                        col = layout.column(align=True)
                        row = col.row(align=True)
                        row.prop(scn, "include_transparent")
                        row = col.row(align=True)
                        row.prop(scn, "include_uncommon")

                    col = layout.column(align=True)
                    split = col.split(align=True, percentage=0.25)
                    col = split.column(align=True)
                    col.label(text="Add:")
                    col = split.column(align=True)
                    col.prop_search(cm, "targetMaterial", bpy.data, "materials", text="")

        if cm.materialType == "SOURCE" and obj:
            noUV = scn.render.engine == "CYCLES" and cm.colorSnap != "NONE" and (not cm.useUVMap or len(obj.data.uv_layers) == 0)
            if noUV:
                col = layout.column(align=True)
                col.scale_y = 0.5
                col.label(text="Based on RGB value of first")
                col.separator()
                if scn.render.engine == "octane":
                    nodeNamesStr = "'Octane Diffuse' node"
                elif scn.render.engine == "LUXCORE":
                    nodeNamesStr = "'Matte Material' node"
                else:
                    nodeNamesStr = "'Diffuse' or 'Principled' node"
                col.label(nodeNamesStr)
            if cm.colorSnap == "RGB" or (cm.useUVMap and len(obj.data.uv_layers) > 0 and cm.colorSnap == "NONE"):
                if scn.render.engine in ["CYCLES", "octane"]:
                    col = layout.column(align=True)
                    col.label(text="Material Properties:")
                    row = col.row(align=True)
                    row.prop(cm, "colorSnapSpecular")
                    row = col.row(align=True)
                    row.prop(cm, "colorSnapRoughness")
                    row = col.row(align=True)
                    row.prop(cm, "colorSnapIOR")
                if scn.render.engine == "CYCLES":
                    row = col.row(align=True)
                    row.prop(cm, "colorSnapSubsurface")
                    row = col.row(align=True)
                    row.prop(cm, "colorSnapSubsurfaceSaturation")
                    row = col.row(align=True)
                    row.prop(cm, "colorSnapTransmission")
                if scn.render.engine in ["CYCLES", "octane"]:
                    row = col.row(align=True)
                    row.prop(cm, "includeTransparency")
                col = layout.column(align=False)
                col.scale_y = 0.5
                col.separator()
            elif noUV:
                col.separator()



class DetailingPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Detailing"
    bl_idname      = "VIEW3D_PT_tools_Bricker_detailing"
    bl_context     = "objectmode"
    bl_category    = "Bricker"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settingsCanBeDrawn():
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = getActiveContextInfo()

        if cm.brickType == "CUSTOM":
            col = layout.column(align=True)
            col.scale_y = 0.7
            row = col.row(align=True)
            row.label(text="(not applied to custom")
            row = col.row(align=True)
            row.label(text="brick types)")
            layout.separator()
        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text="Studs:")
        row = col.row(align=True)
        row.prop(cm, "studDetail", text="")
        row = col.row(align=True)
        row.label(text="Logo:")
        row = col.row(align=True)
        row.prop(cm, "logoType", text="")
        if cm.logoType != "NONE":
            if cm.logoType == "LEGO":
                row = col.row(align=True)
                row.prop(cm, "logoResolution", text="Resolution")
                row.prop(cm, "logoDecimate", text="Decimate")
                row = col.row(align=True)
            else:
                row = col.row(align=True)
                row.prop_search(cm, "logoObject", scn, "objects", text="")
                row = col.row(align=True)
                row.prop(cm, "logoScale", text="Scale")
            row.prop(cm, "logoInset", text="Inset")
            col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text="Underside:")
        row = col.row(align=True)
        row.prop(cm, "hiddenUndersideDetail", text="")
        row.prop(cm, "exposedUndersideDetail", text="")
        row = col.row(align=True)
        row.label(text="Cylinders:")
        row = col.row(align=True)
        row.prop(cm, "circleVerts")
        row = col.row(align=True)
        row.prop(cm, "loopCut")
        row.active = not (cm.studDetail == "NONE" and cm.exposedUndersideDetail == "FLAT" and cm.hiddenUndersideDetail == "FLAT")

        row = col.row(align=True)
        row.label(text="Bevel:")
        row = col.row(align=True)
        if not (cm.modelCreated or cm.animated):
            row.prop(cm, "bevelAdded", text="Bevel Bricks")
            return
        try:
            testBrick = getBricks()[0]
            testBrick.modifiers[testBrick.name + '_bvl']
            row.prop(cm, "bevelWidth", text="Width")
            row = col.row(align=True)
            row.prop(cm, "bevelSegments", text="Segments")
            row = col.row(align=True)
            row.prop(cm, "bevelProfile", text="Profile")
            row = col.row(align=True)
            row.operator("bricker.bevel", text="Remove Bevel", icon="CANCEL")
        except (IndexError, KeyError):
            row.operator("bricker.bevel", text="Bevel bricks", icon="MOD_BEVEL")


class SupportsPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Supports"
    bl_idname      = "VIEW3D_PT_tools_Bricker_supports"
    bl_context     = "objectmode"
    bl_category    = "Bricker"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settingsCanBeDrawn():
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = getActiveContextInfo()

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(cm, "internalSupports", text="")
        col = layout.column(align=True)
        row = col.row(align=True)
        if cm.internalSupports == "LATTICE":
            row.prop(cm, "latticeStep")
            row = col.row(align=True)
            row.active == cm.latticeStep > 1
            row.prop(cm, "latticeHeight")
            row = col.row(align=True)
            row.prop(cm, "alternateXY")
        elif cm.internalSupports == "COLUMNS":
            row.prop(cm, "colThickness")
            row = col.row(align=True)
            row.prop(cm, "colStep")
        obj = cm.source_obj
        # if obj and not cm.isWaterTight:
        #     row = col.row(align=True)
        #     # row.scale_y = 0.7
        #     row.label(text="(Source is NOT single closed mesh)")


class AdvancedPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Advanced"
    bl_idname      = "VIEW3D_PT_tools_Bricker_advanced"
    bl_context     = "objectmode"
    bl_category    = "Bricker"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settingsCanBeDrawn():
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, n = getActiveContextInfo()

        # Alert user that update is available
        if addon_updater_ops.updater.update_ready:
            col = layout.column(align=True)
            col.scale_y = 0.7
            col.label(text="Bricker update available!", icon="INFO")
            col.label(text="Install from Bricker addon prefs")
            layout.separator()

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("bricker.clear_cache", text="Clear Cache")
        row = col.row(align=True)
        row.label(text="Insideness:")
        row = col.row(align=True)
        row.prop(cm, "insidenessRayCastDir", text="")
        row = col.row(align=True)
        row.prop(cm, "castDoubleCheckRays")
        row = col.row(align=True)
        row.prop(cm, "useNormals")
        row = col.row(align=True)
        row.prop(cm, "verifyExposure")
        if not cm.useAnimation and not (cm.modelCreated or cm.animated):
            row = col.row(align=True)
            row.label(text="Model Orientation:")
            row = col.row(align=True)
            row.prop(cm, "useLocalOrient", text="Use Source Local")
        row = col.row(align=True)
        row.label(text="Other:")
        row = col.row(align=True)
        row.prop(cm, "brickifyInBackground")
        # draw test brick generator button (for testing purposes only)
        if testBrickGenerators.drawUIButton():
            col = layout.column(align=True)
            col.operator("bricker.test_brick_generators", text="Test Brick Generators", icon="OUTLINER_OB_MESH")


class BrickDetailsPanel(Panel):
    """ Display Matrix details for specified brick location """
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Brick Details"
    bl_idname      = "VIEW3D_PT_tools_Bricker_brick_details"
    bl_context     = "objectmode"
    bl_category    = "Bricker"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if bpy.props.Bricker_developer_mode < 1:
            return False
        if not settingsCanBeDrawn():
            return False
        scn, cm, _ = getActiveContextInfo()
        if createdWithUnsupportedVersion(cm):
            return False
        if not (cm.modelCreated or cm.animated):
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = getActiveContextInfo()

        if matrixReallyIsDirty(cm):
            layout.label(text="Matrix is dirty!")
            return
        if not Caches.cacheExists(cm):
            layout.label(text="Matrix not cached!")
            return

        col1 = layout.column(align=True)
        row = col1.row(align=True)
        row.prop(cm, "activeKey", text="")

        if cm.animated:
            bricksDict, _ = getBricksDict(dType="ANIM", cm=cm, curFrame=getAnimAdjustedFrame(scn.frame_current, cm.lastStartFrame, cm.lastStopFrame))
        elif cm.modelCreated:
            bricksDict, _ = getBricksDict(cm=cm)
        if bricksDict is None:
            layout.label(text="Matrix not available")
            return
        try:
            dictKey = listToStr(tuple(cm.activeKey))
            brickD = bricksDict[dictKey]
        except Exception as e:
            layout.label(text="No brick details available")
            if len(bricksDict) == 0:
                print("[Bricker] Skipped drawing Brick Details")
            elif str(e)[1:-1] == dictKey:
                pass
                # print("[Bricker] Key '" + str(dictKey) + "' not found")
            elif dictKey is None:
                print("[Bricker] Key not set (entered else)")
            else:
                print("[Bricker] Error fetching brickD:", e)
            return

        col1 = layout.column(align=True)
        split = col1.split(align=True, percentage=0.35)
        # hard code keys so that they are in the order I want
        keys = ["name", "val", "draw", "co", "near_face", "near_intersection", "near_normal", "mat_name", "rgba", "parent", "size", "attempted_merge", "top_exposed", "bot_exposed", "type", "flipped", "rotated", "created_from"]
        # draw keys
        col = split.column(align=True)
        col.scale_y = 0.65
        row = col.row(align=True)
        row.label(text="key:")
        for key in keys:
            row = col.row(align=True)
            row.label(key + ":")
        # draw values
        col = split.column(align=True)
        col.scale_y = 0.65
        row = col.row(align=True)
        row.label(dictKey)
        for key in keys:
            row = col.row(align=True)
            row.label(str(brickD[key]))

class ExportPanel(Panel):
    """ Export Bricker Model """
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Bake/Export"
    bl_idname      = "VIEW3D_PT_tools_Bricker_export"
    bl_context     = "objectmode"
    bl_category    = "Bricker"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settingsCanBeDrawn():
            return False
        scn, cm, _ = getActiveContextInfo()
        if createdWithUnsupportedVersion(cm):
            return False
        if not (cm.modelCreated or cm.animated):
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = getActiveContextInfo()

        col = layout.column(align=True)
        col.operator("bricker.bake_model", icon="OBJECT_DATA")
        col = layout.column(align=True)
        col.prop(cm, "exportPath", text="")
        col = layout.column(align=True)
        if (cm.modelCreated or cm.animated) and cm.brickType != "CUSTOM":
            row = col.row(align=True)
            row.operator("bricker.export_ldraw", text="Export Ldraw", icon="EXPORT")
        if bpy.props.Bricker_developer_mode > 0:
            row = col.row(align=True)
            row.operator("bricker.export_model_data", text="Export Model Data", icon="EXPORT")
