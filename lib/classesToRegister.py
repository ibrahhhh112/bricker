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
    addAbsToMatObj.BRICKER_OT_add_abs_to_mat_bbj,
    bake.BRICKER_OT_bake_model,
    bevel.BRICKER_OT_bevel,
    brickify.BRICKER_OT_brickify,
    cache.BRICKER_OT_caches,
    delete.BRICKER_OT_delete_model,
    exportLdraw.BRICKER_OT_export_ldraw,
    exportModelData.BRICKER_OT_export_model_data,
    materials.BRICKER_OT_apply_material,
    redrawCustomBricks.BRICKER_OT_redraw_custom_bricks,
    reportError.BRICKER_OT_report_error,
    reportError.BRICKER_OT_close_error,
    revertSettings.BRICKER_OT_revert_settings,
    # bricker/buttons/customize
    initialize.BRICKER_OT_initialize_undo_stack,
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
    delete.OBJECT_OT_delete_override,
    duplicate.OBJECT_OT_duplicate_override,
    duplicate.OBJECT_OT_duplicate_move,
    # move_to_layer.OBJECT_OT_move_to_layer_override,
    # move_to_layer.OBJECT_OT_move_to_layer,
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
    # bricker/ui/ (other_property_groups)
    BRICKER_UL_collections_tuple
)
