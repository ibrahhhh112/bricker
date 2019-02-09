# Pull objects and meshes from source file
import sys
scn = bpy.context.scene
scn.objects.active = None
scn.cmlist_index = cmlist_index
cm = scn.cmlist[cmlist_index]
bpy.ops.bricker.brickify_anim_in_background(frame=frame if frame is not None else -1)
target_coll = bpy.data.collections.get("Bricker_" + cm.source_obj.name + "_bricks_f_" + str(frame))
parent_obj = bpy.data.objects.get("Bricker_" + cm.source_obj.name + "_parent_f_" + str(frame))


### SET 'data_blocks' EQUAL TO LIST OF OBJECT DATA TO BE SEND BACK TO THE BLENDER HOST ###

data_blocks = [target_coll, parent_obj]
