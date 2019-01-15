#** DO NOT DELETE THIS LINE OR EDIT THE LINES ABOVE **#

### DO NOT EDIT THESE LINES ###

import bpy
import os
if bpy.data.filepath == "":
    for obj in bpy.data.objects:
        obj.name = "background_removed"
    for mesh in bpy.data.meshes:
        mesh.name = "background_removed"
objDirectory = "%(sourceBlendFile)s/Object/" % locals()
meshDirectory = "%(sourceBlendFile)s/Mesh/" % locals()
data_blocks = []

### WRITE YOUR PYTHON CODE HERE ###


# Pull objects and meshes from source file
import sys
scn = bpy.context.scene
cm = scn.cmlist[scn.cmlist_index]
bpy.ops.bricker.brickify_anim_in_background(frame=frame if frame is not None else -1)
target_group = bpy.data.groups.get("Bricker_" + cm.source_obj.name + "_bricks_f_" + str(frame))
parent_obj = bpy.data.objects.get("Bricker_" + cm.source_obj.name + "_parent_f_" + str(frame))


### SET 'data_blocks' EQUAL TO LIST OF OBJECT DATA TO BE SEND BACK TO THE BLENDER HOST ###

data_blocks = [target_group, parent_obj]

### DO NOT EDIT BEYOND THIS LINE ###

assert None not in data_blocks  # ensures that all data from data_blocks exists
if os.path.exists(storagePath):
    os.remove(storagePath)
bpy.data.libraries.write(storagePath, set(data_blocks), fake_user=True)
