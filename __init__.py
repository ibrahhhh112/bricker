bl_info = {
    "name"        : "Bricker",
    "author"      : "Christopher Gearhart <chris@bblanimation.com>",
    "version"     : (1, 6, 0),
    "blender"     : (2, 80, 0),
    "description" : "Turn any mesh into a 3D brick sculpture or simulation with the click of a button",
    "location"    : "View3D > Tools > Bricker",
    "warning"     : "",  # used for warning icon and text in addons panel
    "wiki_url"    : "https://www.blendermarket.com/products/bricker/",
    "tracker_url" : "https://github.com/bblanimation/bricker/issues",
    "category"    : "Object"}

developer_mode = 2  # NOTE: Set to 0 for release, 1 for exposed dictionary and access to safe scene, 2 for 'BRICKER_OT_test_brick_generators' button
# NOTE: Disable "LEGO Logo" for releases
# NOTE: Disable "Slopes" brick type for releases

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
from bpy.props import *
from bpy.types import Scene, Material, Object
from bpy.utils import register_class, unregister_class

# Addon imports
from .ui import *
from .buttons import *
from .buttons.customize import *
from .operators import *
from .lib.preferences import *
# from .lib.rigid_body_props import *
from .lib.Brick.legal_brick_sizes import getLegalBrickSizes
from .lib import keymaps

# updater import
from . import addon_updater_ops

# store keymaps here to access after registration
addon_keymaps = []


classes = (
    # bricker/addon_updater_ops.py
    addon_updater_ops.OBJECT_OT_addon_updater_install_popup,
    addon_updater_ops.OBJECT_OT_addon_updater_check_now,
    addon_updater_ops.OBJECT_OT_addon_updater_update_now,
    addon_updater_ops.OBJECT_OT_addon_updater_update_target,
    addon_updater_ops.OBJECT_OT_addon_updater_install_manually,
    addon_updater_ops.OBJECT_OT_addon_updater_updated_successful,
    addon_updater_ops.OBJECT_OT_addon_updater_restore_backup,
    addon_updater_ops.OBJECT_OT_addon_updater_ignore,
    addon_updater_ops.OBJECT_OT_addon_updater_end_background,
    # bricker/buttons
    buttons.addAbsToMatObj.BRICKER_OT_add_abs_to_mat_bbj,
    buttons.bake.BRICKER_OT_bake_model,
    buttons.bevel.BRICKER_OT_bevel,
    buttons.brickify.BRICKER_OT_brickify,
    buttons.cache.BRICKER_OT_caches,
    buttons.delete.BRICKER_OT_delete_model,
    buttons.exportLdraw.BRICKER_OT_export_ldraw,
    buttons.exportModelData.BRICKER_OT_export_model_data,
    buttons.eyedropper.OBJECT_OT_eye_dropper,
    buttons.materials.BRICKER_OT_apply_material,
    buttons.redrawCustomBricks.BRICKER_OT_redraw_custom_bricks,
    buttons.reportError.BRICKER_OT_report_error,
    buttons.reportError.BRICKER_OT_close_error,
    buttons.revertSettings.BRICKER_OT_revert_settings,
    # bricker/buttons/customize
    customize.initialize.BRICKER_OT_initialize_undo_stack,
    BRICKER_OT_change_material,
    BRICKER_OT_change_type,
    BRICKER_OT_draw_adjacent,
    BRICKER_OT_merge_bricks,
    BRICKER_OT_redraw_bricks,
    BRICKER_OT_select_bricks_by_size,
    BRICKER_OT_select_bricks_by_type,
    BRICKER_OT_set_exposure,
    BRICKER_OT_split_bricks,
    # bricker/lib
    BRICKER_OT_test_brick_generators,
    BRICKER_PT_preferences,
    # bricker/operators
    operators.delete.OBJECT_OT_delete_override,
    operators.duplicate.BRICKER_OT_duplicate_override,
    operators.duplicate.BRICKER_OT_duplicate_move,
    operators.move_to_layer.BRICKER_OT_move_to_layer_override,
    operators.move_to_layer.BRICKER_OT_move_to_layer,
    # bricker/ui
    BRICKER_MT_specials,
    BRICKER_PT_brick_models,
    BRICKER_PT_animation,
    BRICKER_PT_model_transform,
    BRICKER_PT_model_settings,
    BRICKER_PT_smoke_settings,
    BRICKER_PT_brick_types,
    BRICKER_PT_merge_settings,
    BRICKER_PT_customize_model,
    BRICKER_PT_materials,
    BRICKER_PT_detailing,
    BRICKER_PT_supports,
    BRICKER_PT_advanced,
    BRICKER_PT_matrix_details,
    BRICKER_PT_export,
    # bricker/ui/ (cmlist)
    BRICKER_OT_cmlist_actions,
    BRICKER_OT_copy_settings_to_others,
    BRICKER_OT_copy_settings,
    BRICKER_OT_paste_settings,
    BRICKER_OT_select_bricks,
    BRICKER_UL_cmlist_items,
    BRICKER_UL_created_models,
    # bricker/ui/ (matlist)
    BRICKER_OT_matlist_actions,
    MATERIAL_UL_matslots_example,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.props.bricker_module_name = __name__
    bpy.props.bricker_version = str(bl_info["version"])[1:-1].replace(", ", ".")
    bpy.props.bricker_preferences = bpy.context.user_preferences.addons[__package__].preferences

    bpy.props.bricker_initialized = False
    bpy.props.bricker_undoUpdating = False
    bpy.props.Bricker_developer_mode = developer_mode

    Object.protected: BoolProperty(name='protected', default=False)
    Object.isBrickifiedObject: BoolProperty(name='Is Brickified Object', default=False)
    Object.isBrick: BoolProperty(name='Is Brick', default=False)
    Object.cmlist_id: IntProperty(name='Custom Model ID', description="ID of cmlist entry to which this object refers", default=-1)
    Material.num_averaged: IntProperty(name='Colors Averaged', description="Number of colors averaged together", default=0)

    Scene.Bricker_runningBlockingOperation: BoolProperty(default=False)

    Scene.Bricker_last_layers: StringProperty(default="")
    Scene.Bricker_last_cmlist_index: IntProperty(default=-2)
    Scene.Bricker_active_object_name: StringProperty(default="")
    Scene.Bricker_last_active_object_name: StringProperty(default="")

    Scene.Bricker_copy_from_id: IntProperty(default=-1)

    # define legal brick sizes (key:height, val:[width,depth])
    bpy.props.Bricker_legal_brick_sizes = getLegalBrickSizes()

    # Add attribute for Bricker Instructions addon
    Scene.isBrickerInstalled: BoolProperty(default=True)

    if not hasattr(Scene, "include_transparent"):
        Scene.include_transparent = False
    if not hasattr(Scene, "include_uncommon"):
        Scene.include_uncommon = False

    # Scene.Bricker_snapping: BoolProperty(
    #     name="Bricker Snap",
    #     description="Snap to brick dimensions",
    #     default=False)
    # bpy.types.VIEW3D_HT_header.append(Bricker_snap_button)

    # handle the keymap
    wm = bpy.context.window_manager
    # Note that in background mode (no GUI available), keyconfigs are not available either, so we have
    # to check this to avoid nasty errors in background case.
    if wm.keyconfigs.addon:
        km = wm.keyconfigs.addon.keymaps.new(name='Object Mode', space_type='EMPTY')
        keymaps.addKeymaps(km)
        addon_keymaps.append(km)

    # other things (UI List)
    Scene.cmlist: CollectionProperty(type=BRICKER_UL_created_models)
    Scene.cmlist_index: IntProperty(default=-1)

    # addon updater code and configurations
    addon_updater_ops.register(bl_info)


def unregister():

    # addon updater unregister
    addon_updater_ops.unregister()

    del Scene.cmlist_index
    del Scene.cmlist
    # bpy.types.VIEW3D_HT_header.remove(Bricker_snap_button)
    # del Scene.Bricker_snapping
    del Scene.isBrickerInstalled
    del Scene.Bricker_copy_from_id
    del Scene.Bricker_last_active_object_name
    del Scene.Bricker_active_object_name
    del Scene.Bricker_last_cmlist_index
    del Scene.Bricker_last_layers
    del Scene.Bricker_runningBlockingOperation
    del Material.num_averaged
    del Object.cmlist_id
    del Object.isBrick
    del Object.isBrickifiedObject
    del Object.protected
    del bpy.props.Bricker_developer_mode
    del bpy.props.bricker_undoUpdating
    del bpy.props.bricker_initialized
    del bpy.props.bricker_preferences
    del bpy.props.bricker_version
    del bpy.props.bricker_module_name

    # handle the keymaps
    wm = bpy.context.window_manager
    for km in addon_keymaps:
        wm.keyconfigs.addon.keymaps.remove(km)
    addon_keymaps.clear()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
