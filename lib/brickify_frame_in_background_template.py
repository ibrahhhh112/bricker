# Pull objects and meshes from source file
import sys
n = cm.source_obj.name
scn = bpy.context.scene
scn.collection.objects.active = None
scn.cmlist_index = cmlist_index
cm = scn.cmlist[cmlist_index]
bpy.ops.bricker.brickify_anim_in_background(frame=frame if frame is not None else -1)
target_coll = bpy.data.collections.get("Bricker_%(n)s_bricks_f_%(frame)s" % locals())
parent_obj = bpy.data.objects.get("Bricker_%(n)s_parent_f_%(frame)s" % locals())


### SET 'data_blocks' EQUAL TO LIST OF OBJECT DATA TO BE SEND BACK TO THE BLENDER HOST ###

data_blocks = [target_coll, parent_obj]
