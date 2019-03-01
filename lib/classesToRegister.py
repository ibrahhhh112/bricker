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

# Addon imports
from ..ui import *
from ..buttons import *
from ..buttons.customize import *
from ..operators import *
from .preferences import *
from .reportError import *
from .. import addon_updater_ops


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
    addAbsToMatObj.BRICKER_OT_add_abs_to_mat_obj,
    bake.BRICKER_OT_bake_model,
    bevel.BRICKER_OT_bevel,
    brickify.BRICKER_OT_brickify,
    brickifyInBackground.BRICKER_OT_brickify_in_background,
    brickifyInBackground.BRICKER_OT_stop_brickifying_in_background,
    cache.BRICKER_OT_clear_cache,
    delete_model.BRICKER_OT_delete_model,
    exportLdraw.BRICKER_OT_export_ldraw,
    exportModelData.BRICKER_OT_export_model_data,
    materials.BRICKER_OT_apply_material,
    redrawCustomBricks.BRICKER_OT_redraw_custom_bricks,
    revertSettings.BRICKER_OT_revert_settings,
    # bricker/buttons/customize
    initialize.BRICKER_OT_initialize,
    BRICKER_OT_change_brick_material,
    BRICKER_OT_change_brick_type,
    BRICKER_OT_draw_adjacent,
    BRICKER_OT_merge_bricks,
    BRICKER_OT_redraw_bricks,
    BRICKER_OT_select_bricks_by_size,
    BRICKER_OT_select_bricks_by_type,
    BRICKER_OT_set_exposure,
    BRICKER_OT_split_bricks,
    BRICKER_OT_bricksculpt,
    # bricker/lib
    BRICKER_OT_test_brick_generators,
    PREFS_Bricker_Props,
    SCENE_OT_report_error,
    SCENE_OT_close_report_error,
    # bricker/operators
    delete_object.OBJECT_OT_delete_override,
    duplicate_object.OBJECT_OT_duplicate_override,
    duplicate_object.OBJECT_OT_duplicate_move_override,
    # move_to_layer.OBJECT_OT_move_to_layer_override,
    # move_to_layer.OBJECT_OT_move_to_layer,
    # bricker/ui
    BRICKER_MT_specials,
    VIEW3D_PT_bricker_brick_models,
    VIEW3D_PT_bricker_animation,
    VIEW3D_PT_bricker_model_transform,
    VIEW3D_PT_bricker_model_settings,
    VIEW3D_PT_bricker_smoke_settings,
    VIEW3D_PT_bricker_brick_types,
    VIEW3D_PT_bricker_merge_settings,
    VIEW3D_PT_bricker_customize,
    VIEW3D_PT_bricker_materials,
    VIEW3D_PT_bricker_detailing,
    VIEW3D_PT_bricker_supports,
    VIEW3D_PT_bricker_advanced,
    VIEW3D_PT_bricker_matrix_details,
    VIEW3D_PT_bricker_export,
    # bricker/ui/ (cmlist)
    CMLIST_OT_list_action,
    CMLIST_OT_copy_settings_to_others,
    CMLIST_OT_copy_settings,
    CMLIST_OT_paste_settings,
    CMLIST_OT_select_bricks,
    CMLIST_UL_items,
    CMLIST_UL_properties,
    # bricker/ui/ (matlist)
    BRICKER_OT_matlist_actions,
    MATERIAL_UL_matslots,
    # bricker/ui/ (other_property_groups)
    BRICKER_UL_collections_tuple,
)
