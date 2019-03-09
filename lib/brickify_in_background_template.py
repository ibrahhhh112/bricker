# NOTE: Requires 'cmlist_index', 'frame', and 'action' as variables
# Pull objects and meshes from source file
import sys
scn = bpy.context.scene
scn.objects.active = None
scn.cmlist_index = cmlist_index
cm = scn.cmlist[cmlist_index]
n = cm.source_obj.name
bpy.ops.bricker.brickify_in_background(frame=frame if frame is not None else -1, action=action)
frameStr = "_f_%(frame)s" % locals() if cm.useAnimation else ""
target_group = bpy.data.groups.get("Bricker_%(n)s_bricks%(frameStr)s" % locals())
parent_obj = bpy.data.objects.get("Bricker_%(n)s_parent%(frameStr)s" % locals())

### BLEND DATA TO BE SEND BACK TO THE BLENDER HOST ###

data_blocks = [target_group, parent_obj]

### PYTHON DATA TO BE SEND BACK TO THE BLENDER HOST ###

python_data = {"bricksDict":cm.BFMCache, "brickSizesUsed":cm.brickSizesUsed, "brickTypesUsed":cm.brickTypesUsed}
