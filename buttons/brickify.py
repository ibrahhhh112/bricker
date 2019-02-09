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

# system imports
import random
import time
import bmesh
import os
from os.path import dirname, abspath
import sys
import math
import shutil
import json

# Blender imports
import bpy
from mathutils import Matrix, Vector, Euler
from bpy.props import *

# Addon imports
from .customize.undo_stack import *
from .materials import BrickerApplyMaterial
from .delete_model import BrickerDelete
from .bevel import BrickerBevel
from .cache import *
from ..lib.bricksDict import *
from ..lib.JobManager import *
from ..functions import *


class BrickerBrickify(bpy.types.Operator):
    """Create brick sculpture from source object mesh"""
    bl_idname = "bricker.brickify"
    bl_label = "Create/Update Brick Model from Source Object"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns false) """
        scn = bpy.context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        # return brickifyShouldRun(cm)
        return True

    def modal(self, context, event):
        if event.type == "TIMER":
            scn, cm, n = getActiveContextInfo(cm=self.cm)
            for job in self.jobs.copy():
                # cancel if model was deleted before process completed
                if scn in self.source.users_scene:
                    break
                frame = int(job.split("__")[-1][:-3])
                self.JobManager.process_job(job, debug_level=1)
                if self.JobManager.job_complete(job):
                    self.report({"INFO"}, "Completed frame %(frame)s of model '%(n)s'" % locals())
                    bricker_bricks = bpy.data.objects.get("Bricker_%(n)s_bricks_f_%(frame)s" % locals())
                    bricker_parent = bpy.data.objects.get("Bricker_%(n)s_parent_f_%(frame)s" % locals())
                    scn.objects.link(bricker_bricks)
                    bricker_parent.use_fake_user = True
                    bricker_bricks.parent = bricker_parent
                    bricker_parent.parent = self.parent0
                    cm.numAnimatedFrames += 1
                    bricker_bricks.hide = frame != scn.frame_current
                    self.jobs.remove(job)
                elif self.JobManager.job_dropped(job):
                    # print(self.JobManager.get_job_status(job)["stderr"])
                    errormsg = "\n*** ISSUE WITH BACKGROUND PROCESSOR ***\n\n"
                    for line in self.JobManager.get_job_status(job)["stderr"]:
                        errormsg += line + "\n"
                    print_exception("Bricker log", errormsg=errormsg)
                    self.report({"WARNING"}, "Dropped frame %(frame)s of model '%(n)s'" % locals())
                    tag_redraw_areas("VIEW_3D")
                    cm.numAnimatedFrames += 1
                    self.jobs.remove(job)
            # cancel if model was deleted before process completed
            if scn in self.source.users_scene:
                return {"CANCELLED"}
            elif self.JobManager.jobs_complete():
                self.finishAnimation()
                self.report({"INFO"}, "Brickify Animation complete")
                stopWatch("Total Time Elapsed", self.start_time, 2)
                return {"FINISHED"}
        return {"PASS_THROUGH"}

    def execute(self, context):
        scn, cm, _ = getActiveContextInfo()
        wm = bpy.context.window_manager
        wm.Bricker_runningBlockingOperation = True
        try:
            previously_animated = cm.animated
            previously_model_created = cm.modelCreated
            self.runBrickify(context)
        except KeyboardInterrupt:
            if self.action in ("CREATE", "ANIMATE"):
                for n in self.createdObjects:
                    obj = bpy.data.objects.get(n)
                    if obj:
                        bpy.data.objects.remove(obj, True)
                for n in self.createdGroups:
                    group = bpy.data.groups.get(n)
                    if group:
                        bpy.data.groups.remove(group)
                if self.source:
                    self.source.protected = False
                    select(self.source, active=True)
                cm.animated = previously_animated
                cm.modelCreated = previously_model_created
            self.report({"WARNING"}, "Process forcably interrupted with 'KeyboardInterrupt'")
        except:
            bricker_handle_exception()
        wm.Bricker_runningBlockingOperation = False
        if cm.animated and cm.brickifyInBackground:
            cm.brickifyingInBackground = True
            cm.numAnimatedFrames = 0
            # create timer for modal
            self._timer = wm.event_timer_add(0.5, bpy.context.window)
            wm.modal_handler_add(self)
            return {"RUNNING_MODAL"}
        else:
            stopWatch("Total Time Elapsed", self.start_time, 2)
            return {"FINISHED"}

    def cancel(self, context):
        if self.JobManager.num_running_jobs() + self.JobManager.num_pending_jobs() > 0:
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
            self.JobManager.kill_all()

    ################################################
    # initialization method

    def __init__(self):
        scn, cm, _ = getActiveContextInfo()
        # push to undo stack
        self.undo_stack = UndoStack.get_instance()
        self.undo_stack.undo_push('brickify', affected_ids=[cm.id])
        self.undo_stack.iterateStates(cm)
        # initialize vars
        self.createdObjects = list()
        self.createdGroups = list()
        self.setAction(cm)
        self.source = cm.source_obj
        self.origFrame = scn.frame_current
        self.start_time = time.time()
        # initialize important vars
        self.JobManager = SCENE_OT_job_manager.get_instance(cm.id)
        self.JobManager.timeout = cm.backProcTimeout
        self.JobManager.max_workers = cm.maxWorkers
        self.JobManager.max_attempts = 1
        self.brickerAddonPath = dirname(dirname(abspath(__file__)))
        self.jobs = list()
        self.cm = cm

        if self.splitBeforeUpdate:
            cm.splitModel = True

    ###################################################
    # class variables

    splitBeforeUpdate = BoolProperty(default=False)

    #############################################
    # class methods

    def runBrickify(self, context):
        # set up variables
        scn, cm, n = getActiveContextInfo()
        Bricker_bricks_gn = "Bricker_%(n)s_bricks" % locals()

        # ensure that Bricker can run successfully
        if not self.isValid(scn, cm, n, self.source, Bricker_bricks_gn):
            return {"CANCELLED"}

        # initialize variables
        self.source.cmlist_id = cm.id
        matrixDirty = matrixReallyIsDirty(cm)
        skipTransAndAnimData = cm.animated or (cm.splitModel or cm.lastSplitModel) and (matrixDirty or cm.buildIsDirty)

        # # check if source object is smoke simulation domain
        cm.isSmoke = is_smoke(self.source)
        if cm.isSmoke != cm.lastIsSmoke:
            cm.matrixIsDirty = True

        # clear cache if updating from previous version
        if createdWithUnsupportedVersion(cm) and "UPDATE" in self.action:
            Caches.clearCache(cm)
            cm.matrixIsDirty = True

        # make sure matrix really is dirty
        if cm.matrixIsDirty:
            _, loadedFromCache = getBricksDict(dType="MODEL", cm=cm)
            if not matrixDirty and loadedFromCache:
                cm.matrixIsDirty = False

        # set layers to source layers
        oldLayers = list(scn.layers)
        sourceLayers = list(self.source.layers)
        if oldLayers != sourceLayers:
            setLayers(sourceLayers)

        if "ANIM" not in self.action:
            self.brickifyModel(scn, cm, n, matrixDirty, skipTransAndAnimData)
        else:
            self.brickifyAnimation(scn, cm, n, matrixDirty)

        # set cmlist_id for all created objects
        for obj_name in self.createdObjects:
            obj = bpy.data.objects.get(obj_name)
            if obj:
                obj.cmlist_id = cm.id

        # # set final variables
        cm.lastlogoType = cm.logoType
        cm.lastSplitModel = cm.splitModel
        cm.lastBrickType = cm.brickType
        cm.lastLegalBricksOnly = cm.legalBricksOnly
        cm.lastMaterialType = cm.materialType
        cm.lastShellThickness = cm.shellThickness
        cm.lastMatShellDepth = cm.matShellDepth
        cm.lastMatrixSettings = getMatrixSettings()
        cm.lastIsSmoke = cm.isSmoke
        cm.materialIsDirty = False
        cm.modelIsDirty = False
        cm.buildIsDirty = False
        cm.animIsDirty = False
        cm.bricksAreDirty = False
        cm.matrixIsDirty = False
        cm.matrixLost = False
        cm.internalIsDirty = False
        cm.modelCreated = "ANIM" not in self.action
        cm.animated = "ANIM" in self.action
        cm.version = bpy.props.bricker_version
        cm.exposeParent = False

        if cm.animated and not cm.brickifyInBackground:
            self.finishAnimation()

        # unlink source from scene
        if self.source.name in scn.objects.keys():
            safeUnlink(self.source)
        # reset layers
        if oldLayers != sourceLayers:
            setLayers(oldLayers)

        disableRelationshipLines()

    def brickifyModel(self, scn, cm, n, matrixDirty, skipTransAndAnimData):
        """ create brick model """
        # set up variables
        source = None
        Bricker_parent_on = "Bricker_%(n)s_parent" % locals()

        if self.action == "CREATE":
            # set modelCreatedOnFrame
            cm.modelCreatedOnFrame = scn.frame_current
        else:
            if self.origFrame != cm.modelCreatedOnFrame:
                scn.frame_set(cm.modelCreatedOnFrame)

        # if there are no changes to apply, simply return "FINISHED"
        if self.action == "UPDATE_MODEL" and not updateCanRun("MODEL"):
            return{"FINISHED"}

        if (matrixDirty or self.action != "UPDATE_MODEL") and cm.customized:
            cm.customized = False

        # delete old bricks if present
        if self.action.startswith("UPDATE") and (matrixDirty or cm.buildIsDirty or cm.lastSplitModel != cm.splitModel):
            # skip source, dupes, and parents
            trans_and_anim_data = BrickerDelete.cleanUp("MODEL", skipDupes=True, skipParents=True, skipSource=True, skipTransAndAnimData=skipTransAndAnimData)[4]
        else:
            storeTransformData(cm, None)
            trans_and_anim_data = []

        if self.action == "CREATE":
            # duplicate source
            sourceDup = duplicate(self.source, link_to_scene=True)
            sourceDup.name = self.source.name + "_duplicate"
            if cm.useLocalOrient:
                sourceDup.rotation_mode = "XYZ"
                sourceDup.rotation_euler = Euler((0, 0, 0))
            self.createdObjects.append(sourceDup.name)
            self.source.select = False
            # remove modifiers and constraints
            for mod in sourceDup.modifiers:
                sourceDup.modifiers.remove(mod)
            for constraint in sourceDup.constraints:
                sourceDup.constraints.remove(constraint)
            # remove sourceDup parent
            if sourceDup.parent:
                parent_clear(sourceDup)
            # send to new mesh
            if not cm.isSmoke:
                sourceDup.data = self.source.to_mesh(scn, True, 'PREVIEW')
            # apply transformation data
            apply_transform(sourceDup)
            scn.update()
        else:
            # get previously created source duplicate
            sourceDup = bpy.data.objects.get(n + "_duplicate")
        # if duplicate not created, sourceDup is just original source
        sourceDup = sourceDup or self.source

        # link sourceDup if it isn't in scene
        if sourceDup.name not in scn.objects.keys():
            safeLink(sourceDup)
            scn.update()

        # get sourceDup_details and dimensions
        sourceDup_details, dimensions = getDetailsAndBounds(sourceDup)

        # get parent object
        parent = bpy.data.objects.get(Bricker_parent_on)
        # if parent doesn't exist, get parent with new location
        parentLoc = sourceDup_details.mid
        if parent is None:
            parent = self.getNewParent(Bricker_parent_on, parentLoc)
            cm.parent_name = parent.name
        parent["loc_diff"] = self.source.location - parentLoc
        self.createdObjects.append(parent.name)

        # update refLogo
        logo_details, refLogo = self.getLogo(scn, cm, dimensions)

        # create new bricks
        group_name = self.createNewBricks(sourceDup, parent, sourceDup_details, dimensions, refLogo, logo_details, self.action, split=cm.splitModel, curFrame=None, sceneCurFrame=None, origSource=self.source)

        bGroup = bpy.data.groups.get(group_name)
        if bGroup:
            self.createdGroups.append(group_name)
            # transform bricks to appropriate location
            self.transformBricks(bGroup, cm, parent, self.source, sourceDup_details, self.action)
            # apply old animation data to objects
            for d0 in trans_and_anim_data:
                obj = bpy.data.objects.get(d0["name"])
                if obj is not None:
                    obj.location = d0["loc"]
                    obj.rotation_euler = d0["rot"]
                    obj.scale = d0["scale"]
                    if d0["action"] is not None:
                        obj.animation_data_create()
                        obj.animation_data.action = d0["action"]

        # unlink source duplicate if created
        if sourceDup != self.source:
            safeUnlink(sourceDup)

        # add bevel if it was previously added
        if cm.bevelAdded:
            bricks = getBricks(cm, typ="MODEL")
            BrickerBevel.runBevelAction(bricks, cm)

        # set active frame to original active frame
        if self.action != "CREATE" and scn.frame_current != self.origFrame:
            scn.frame_set(self.origFrame)

        cm.lastSourceMid = vecToStr(parentLoc)

    def brickifyAnimation(self, scn, cm, n, matrixDirty):
        """ create brick animation """
        # set up variables
        scn, cm, n = getActiveContextInfo()
        Bricker_parent_on = "Bricker_%(n)s_parent" % locals()
        sceneCurFrame = scn.frame_current
        objsToSelect = []

        if self.action == "UPDATE_ANIM":
            safeLink(self.source)
            self.source.name = n  # fixes issue with smoke simulation cache

        # if there are no changes to apply, simply return "FINISHED"
        self.updatedFramesOnly = False
        if self.action == "UPDATE_ANIM" and not updateCanRun("ANIMATION"):
            if cm.animIsDirty:
                self.updatedFramesOnly = True
            else:
                return {"FINISHED"}

        if (self.action == "ANIMATE" or cm.matrixIsDirty or cm.animIsDirty) and not self.updatedFramesOnly:
            Caches.clearCache(cm, brick_mesh=False)

        if cm.splitModel:
            cm.splitModel = False

        # delete old bricks if present
        if self.action.startswith("UPDATE") and (matrixDirty or cm.buildIsDirty or cm.lastSplitModel != cm.splitModel or self.updatedFramesOnly):
            preservedFrames = None
            if self.updatedFramesOnly:
                # preserve duplicates, parents, and bricks for frames that haven't changed
                preservedFrames = [cm.startFrame, cm.stopFrame]
            BrickerDelete.cleanUp("ANIMATION", skipDupes=not self.updatedFramesOnly, skipParents=not self.updatedFramesOnly, preservedFrames=preservedFrames, source_name=self.source.name)

        # get parent object
        self.parent0 = bpy.data.objects.get(Bricker_parent_on)
        if self.parent0 is None:
            self.parent0 = self.getNewParent(Bricker_parent_on, self.source.location)
            cm.parent_name = self.parent0.name
        self.createdObjects.append(self.parent0.name)

        # begin drawing status to cursor
        wm = bpy.context.window_manager
        wm.progress_begin(0, cm.stopFrame + 1 - cm.startFrame)

        # prepare duplicate objects for animation
        duplicates = self.getDuplicateObjects(scn, cm, n, cm.startFrame, cm.stopFrame)

        filename = bpy.path.basename(bpy.data.filepath)[:-6]
        # iterate through frames of animation and generate Brick Model
        for curFrame in range(cm.startFrame, cm.stopFrame + 1):
            if self.updatedFramesOnly and cm.lastStartFrame <= curFrame and curFrame <= cm.lastStopFrame:
                print("skipped frame %(curFrame)s" % locals())
                continue
            if cm.brickifyInBackground:
                # PULL TEMPLATE SCRIPT FROM 'brickify_anim_in_background', write to new file with frame specified, store path to file in 'curJob'
                curJob = os.path.join(*["/", "tmp", "background_processing", "%(filename)s__%(n)s__%(curFrame)s.py" % locals()][0 if sys.platform in ("linux", "linux2", "darwin") else 1:])
                script = os.path.join(self.brickerAddonPath, "lib", "brickify_frame_in_background_template.py")
                shutil.copyfile(script, curJob)
                jobAdded = self.JobManager.add_job(curJob, passed_data={"frame":curFrame, "cmlist_index":scn.cmlist_index}, use_blend_file=True, overwrite_blend=curFrame == cm.startFrame)
                if not jobAdded:
                    self.report({"WARNING"}, "Job for frame '%(curFrame)s' already added" % locals())
                    break
                self.jobs.append(curJob)
            else:
                completed = self.brickifyCurrentFrame(curFrame, sceneCurFrame, self.action, self.source)
                if not completed:
                    break

        cm.lastStartFrame = cm.startFrame
        cm.lastStopFrame = cm.stopFrame
        scn.frame_set(self.origFrame)

    @staticmethod
    def brickifyCurrentFrame(curFrame, sceneCurFrame, action, origSource, inBackground=False):
        scn, cm, n = getActiveContextInfo()
        wm = bpy.context.window_manager
        Bricker_parent_on = "Bricker_%(n)s_parent" % locals()
        parent0 = bpy.data.objects.get(Bricker_parent_on)
        if inBackground and cm.isSmoke:
            smokeMod = [mod for mod in cm.source_obj.modifiers if mod.type == "SMOKE"][0]
            point_cache = smokeMod.domain_settings.point_cache
            point_cache.name = str(curFrame)
            for frame in range(point_cache.frame_start, curFrame):
                scn.frame_set(frame)
        scn.frame_set(curFrame)
        # get duplicated source
        source = bpy.data.objects.get("Bricker_%(n)s_f_%(curFrame)s" % locals())
        # get source info to update
        if inBackground:
            scn.objects.link(source)
            scn.update()
            scn.objects.unlink(source)

        # get source_details and dimensions
        source_details, dimensions = getDetailsAndBounds(source)

        # update refLogo
        logo_details, refLogo = BrickerBrickify.getLogo(scn, cm, dimensions)

        # set up parent for this layer
        # TODO: Remove these from memory in the delete function, or don't use them at all
        p_name = "%(Bricker_parent_on)s_f_%(curFrame)s" % locals()
        parent = bpy.data.objects.get(p_name)
        if parent is None:
            m = bpy.data.meshes.new("%(p_name)s_mesh" % locals())
            parent = bpy.data.objects.new(p_name, m)
            parent.location = source_details.mid - parent0.location
            parent.parent = parent0
            # TODO: is it necessary to update this? Perhaps just set use_fake_user to True...
            safeLink(parent)
            scn.update()
            safeUnlink(parent)

        # create new bricks
        try:
            group_name = BrickerBrickify.createNewBricks(source, parent, source_details, dimensions, refLogo, logo_details, action, split=cm.splitModel, curFrame=curFrame, sceneCurFrame=sceneCurFrame, origSource=origSource, selectCreated=False)
        except KeyboardInterrupt:
            if curFrame != cm.startFrame:
                wm.progress_end()
                cm.lastStartFrame = cm.startFrame
                cm.lastStopFrame = curFrame - 1
                scn.frame_set(sceneCurFrame)
                cm.animated = True
            return False

        # get object with created bricks
        obj = bpy.data.groups[group_name].objects[0]
        # hide obj unless on scene current frame
        showCurObj = (curFrame == cm.startFrame and sceneCurFrame < cm.startFrame) or curFrame == sceneCurFrame or (curFrame == cm.stopFrame and sceneCurFrame > cm.stopFrame)
        if not showCurObj:
            obj.hide = True
            obj.hide_render = True
        # lock location, rotation, and scale of created bricks
        obj.lock_location = (True, True, True)
        obj.lock_rotation = (True, True, True)
        obj.lock_scale    = (True, True, True)

        wm.progress_update(curFrame-cm.startFrame)
        print('-'*100)
        print("completed frame " + str(curFrame))
        print('-'*100)
        return True

    def finishAnimation(self):
        scn, cm, n = getActiveContextInfo(cm=self.cm)
        wm = bpy.context.window_manager
        wm.progress_end()
        cm.brickifyingInBackground = False

        # add bevel if it was previously added
        if cm.bevelAdded:
            bricks = getBricks(cm, typ="ANIM")
            BrickerBevel.runBevelAction(bricks, cm)

    @staticmethod
    def createNewBricks(source, parent, source_details, dimensions, refLogo, logo_details, action, split=True, cm=None, curFrame=None, sceneCurFrame=None, bricksDict=None, keys="ALL", clearExistingGroup=True, selectCreated=False, printStatus=True, tempBrick=False, redraw=False, origSource=None):
        """ gets/creates bricksDict, runs makeBricks, and caches the final bricksDict """
        scn, cm, n = getActiveContextInfo(cm=cm)
        _, _, _, brickScale, customData = getArgumentsForBricksDict(cm, source=source, source_details=source_details, dimensions=dimensions)
        updateCursor = action in ("CREATE", "UPDATE_MODEL")
        if bricksDict is None:
            # multiply brickScale by offset distance
            brickScale2 = brickScale if cm.brickType != "CUSTOM" else vec_mult(brickScale, Vector(cm.distOffset))
            # get bricks dictionary
            bricksDict, loadedFromCache = getBricksDict(dType=action, source=source, source_details=source_details, dimensions=dimensions, brickScale=brickScale2, updateCursor=updateCursor, curFrame=curFrame, origSource=origSource, restrictContext=False)
        else:
            loadedFromCache = True
        # reset all values for certain keys in bricksDict dictionaries
        if cm.buildIsDirty and loadedFromCache:
            threshold = getThreshold(cm)
            for kk in bricksDict:
                bD = bricksDict[kk]
                if keys == "ALL" or kk in keys:
                    bD["size"] = None
                    bD["parent"] = None
                    bD["top_exposed"] = None
                    bD["bot_exposed"] = None
                    if cm.lastShellThickness != cm.shellThickness:
                        bD["draw"] = bD["val"] >= threshold
                else:
                    # don't merge bricks not in 'keys'
                    bD["attempted_merge"] = True
        elif redraw:
            for kk in keys:
                bricksDict[kk]["attempted_merge"] = False
        if not loadedFromCache or cm.internalIsDirty:
            updateInternal(bricksDict, cm, keys, clearExisting=loadedFromCache)
            cm.buildIsDirty = True
        # update materials in bricksDict
        if cm.materialType != "NONE" and (cm.materialIsDirty or cm.matrixIsDirty or cm.animIsDirty): bricksDict = updateMaterials(bricksDict, source, origSource, curFrame)
        # make bricks
        group_name = 'Bricker_%(n)s_bricks_f_%(curFrame)s' % locals() if curFrame is not None else "Bricker_%(n)s_bricks" % locals()
        bricksCreated, bricksDict = makeBricks(source, parent, refLogo, logo_details, dimensions, bricksDict, action, cm=cm, split=split, brickScale=brickScale, customData=customData, group_name=group_name, clearExistingGroup=clearExistingGroup, frameNum=curFrame, cursorStatus=updateCursor, keys=keys, printStatus=printStatus, tempBrick=tempBrick, redraw=redraw)
        if selectCreated and len(bricksCreated) > 0:
            select(bricksCreated)
        # store current bricksDict to cache
        cacheBricksDict(action, cm, bricksDict, curFrame=curFrame)
        return group_name

    def isValid(self, scn, cm, source_name, source, Bricker_bricks_gn):
        """ returns True if brickify action can run, else report WARNING/ERROR and return False """
        # ensure custom object(s) are valid
        if (cm.brickType == "CUSTOM" or cm.hasCustomObj1 or cm.hasCustomObj2 or cm.hasCustomObj3):
            warningMsg = customValidObject(cm)
            if warningMsg is not None:
                self.report({"WARNING"}, warningMsg)
                return False
        # ensure source is defined
        if source is None:
            self.report({"WARNING"}, "Source object '%(source_name)s' could not be found" % locals())
            return False
        # ensure source name isn't too long
        if len(source_name) > 30:
            self.report({"WARNING"}, "Source object name too long (must be <= 30 characters)")
        # ensure custom material exists
        if cm.materialType == "CUSTOM" and cm.materialName != "" and bpy.data.materials.find(cm.materialName) == -1:
            mn = cm.materialName
            self.report({"WARNING"}, "Custom material '%(mn)s' could not be found" % locals())
            return False
        if cm.materialType == "SOURCE" and cm.colorSnap == "ABS":
            # ensure ABS Plastic materials are installed
            if not hasattr(scn, "isBrickMaterialsInstalled") or not scn.isBrickMaterialsInstalled:
                self.report({"WARNING"}, "ABS Plastic Materials must be installed from Blender Market")
                return False
            # ensure ABS Plastic materials UI list is populated
            matObj = getMatObject(cm.id, typ="ABS")
            if matObj is None:
                matObj = createNewMatObjs(cm.id)[1]
            if len(matObj.data.materials) == 0:
                self.report({"WARNING"}, "No ABS Plastic Materials found in Materials to be used")
                return False

        if self.action in ("CREATE", "ANIMATE"):
            # verify function can run
            if groupExists(Bricker_bricks_gn):
                self.report({"WARNING"}, "Brickified Model already created.")
                return False
            # verify source exists and is of type mesh
            if source_name == "":
                self.report({"WARNING"}, "Please select a mesh to Brickify")
                return False
            # ensure source is not bricker model
            if source.isBrick or source.isBrickifiedObject:
                self.report({"WARNING"}, "Please bake the 'Bricker' source model before brickifying (Bricker > Bake/Export > Bake Model).")
                return False
            # ensure source exists
            if source is None:
                self.report({"WARNING"}, "'%(source_name)s' could not be found" % locals())
                return False
            # ensure object data is mesh
            if source.type != "MESH":
                self.report({"WARNING"}, "Only 'MESH' objects can be Brickified. Please select another object (or press 'ALT-C to convert object to mesh).")
                return False
            # verify source is not a rigid body
            if source.rigid_body is not None and source.rigid_body.type == "ACTIVE":
                    self.report({"WARNING"}, "First bake rigid body transformations to keyframes (SPACEBAR > Bake To Keyframes).")
                    return False

        if self.action in ("ANIMATE", "UPDATE_ANIM"):
            # verify Blender file is saved
            if cm.brickifyInBackground and bpy.data.filepath == "":
                self.report({"WARNING"}, "Please save the file first")
                return False
            # verify start frame is less than stop frame
            if cm.startFrame > cm.stopFrame:
                self.report({"ERROR"}, "Start frame must be less than or equal to stop frame (see animation tab below).")
                return False

        if self.action == "UPDATE_MODEL":
            # make sure 'Bricker_[source name]_bricks' group exists
            if not groupExists(Bricker_bricks_gn):
                self.report({"WARNING"}, "Brickified Model doesn't exist. Create one with the 'Brickify Object' button.")
                return False

        # check that custom logo object exists in current scene and is of type "MESH"
        if cm.logoType == "CUSTOM" and cm.brickType != "CUSTOM":
            if cm.logoObject is None:
                self.report({"WARNING"}, "Custom logo object not specified.")
                return False
            elif cm.logoObject.name == source_name:
                self.report({"WARNING"}, "Source object cannot be its own logo.")
                return False
            elif cm.logoObject.name.startswith("Bricker_%(source_name)s" % locals()):
                self.report({"WARNING"}, "Bricker object cannot be used as its own logo.")
                return False
            elif cm.logoObject.type != "MESH":
                self.report({"WARNING"}, "Custom logo object is not of type 'MESH'. Please select another object (or press 'ALT-C to convert object to mesh).")
                return False

        return True

    @staticmethod
    def transformBricks(bGroup, cm, parent, source, sourceDup_details, action):
        # if using local orientation and creating model for first time
        if cm.useLocalOrient and action == "CREATE":
            obj = parent if cm.splitModel else bGroup.objects[0]
            source_details = bounds(source)
            lastMode = source.rotation_mode
            obj.rotation_mode = "XYZ"
            source.rotation_mode = obj.rotation_mode
            obj.rotation_euler = source.rotation_euler
            obj.rotation_mode = lastMode
            source["local_orient_offset"] = source_details.mid - sourceDup_details.mid
            obj.location += Vector(source["local_orient_offset"])
        # if model was split but isn't now
        if cm.lastSplitModel and not cm.splitModel:
            # transfer transformation of parent to object
            parent.rotation_mode = "XYZ"
            for obj in bGroup.objects:
                obj.location = parent.location
                obj.rotation_mode = parent.rotation_mode
                obj.rotation_euler.rotate(parent.rotation_euler)
                obj.scale = parent.scale
            # reset parent transformation
            parent.location = (0, 0, 0)
            parent.rotation_euler = Euler((0, 0, 0))
            cm.transformScale = 1
            parent.scale = (1, 1, 1)
        # if model is not split
        elif not cm.splitModel:
            # apply stored transformation to bricks
            applyTransformData(cm, bGroup.objects)
        # if model wasn't split but is now
        elif not cm.lastSplitModel:
            # apply stored transformation to parent of bricks
            applyTransformData(cm, parent)
        obj = bGroup.objects[0] if len(bGroup.objects) > 0 else None
        if obj is None:
            return
        # select the bricks object unless it's massive
        if not cm.splitModel and len(obj.data.vertices) < 500000:
            select(obj, active=True)
        # if model contains armature, lock the location, rotation, and scale of created bricks object
        if not cm.splitModel and cm.armature:
            obj.lock_location = (True, True, True)
            obj.lock_rotation = (True, True, True)
            obj.lock_scale    = (True, True, True)

    @staticmethod
    def getLogo(scn, cm, dimensions):
        typ = cm.logoType
        if cm.brickType == "CUSTOM" or typ == "NONE":
            refLogo = None
            logo_details = None
        else:
            if typ == "LEGO":
                refLogo = getLegoLogo(scn, typ, cm.logoResolution, cm.logoDecimate, dimensions)
            else:
                refLogo = cm.logoObject
            # apply transformation to duplicate of logo object and normalize size/position
            logo_details, refLogo = prepareLogoAndGetDetails(scn, refLogo, typ, cm.logoScale, dimensions)
        return logo_details, refLogo

    def getDuplicateObjects(self, scn, cm, source_name, startFrame, stopFrame):
        """ returns list of duplicates from self.source with all traits applied """
        activeFrame = scn.frame_current
        soft_body = False
        smoke = False

        # set cm.armature and cm.physics
        for mod in self.source.modifiers:
            if mod.type == "ARMATURE":
                cm.armature = True
            elif mod.type in ("CLOTH", "SOFT_BODY"):
                soft_body = True
                point_cache = mod.point_cache
            elif mod.type == "SMOKE":
                smoke = True
                point_cache = mod.domain_settings.point_cache

        # step through uncached frames to run simulation
        if soft_body or smoke:
            firstUncachedFrame = getFirstUncachedFrame(self.source, point_cache)
            for curFrame in range(firstUncachedFrame, startFrame):
                scn.frame_set(curFrame)

        denom = stopFrame - startFrame
        update_progress("Applying Modifiers", 0)

        duplicates = {}
        for curFrame in range(startFrame, stopFrame + 1):
            # retrieve previously duplicated source if possible
            if self.action == "UPDATE_ANIM":
                sourceDup = bpy.data.objects.get("Bricker_" + source_name + "_f_" + str(curFrame))
                if sourceDup is not None:
                    duplicates[curFrame] = sourceDup
                    safeLink(sourceDup)
                    continue
            # set active frame for applying modifiers
            scn.frame_set(curFrame)
            # duplicate source for current frame
            sourceDup = duplicate(self.source, link_to_scene=True)
            sourceDup.name = "Bricker_" + source_name + "_f_" + str(curFrame)
            # # apply rigid body transform data
            # if cm.rigid_body:
            #     select(sourceDup, active=True, only=True)
            #     bpy.ops.object.visual_transform_apply()
            #     bpy.ops.rigidbody.object_remove()
            #     scn.update()
            # remove modifiers and constraints
            for mod in sourceDup.modifiers:
                sourceDup.modifiers.remove(mod)
            for constraint in sourceDup.constraints:
                sourceDup.constraints.remove(constraint)
            # apply parent transformation
            if sourceDup.parent:
                parent_clear(sourceDup)
            # apply animated transform data
            sourceDup.matrix_world = self.source.matrix_world
            sourceDup.animation_data_clear()
            # send to new mesh
            if not cm.isSmoke:
                sourceDup.data = self.source.to_mesh(scn, True, 'PREVIEW')
            # apply transform data
            apply_transform(sourceDup)
            duplicates[curFrame] = sourceDup
            # update progress bar
            percent = (curFrame - startFrame) / (denom + 1)
            if percent < 1:
                update_progress("Applying Modifiers", percent)
        # update progress bar
        update_progress("Applying Modifiers", 1)
        # unlink source duplicate
        scn.update()
        for obj in duplicates.values():
            safeUnlink(obj)
        return duplicates

    @staticmethod
    def getNewParent(Bricker_parent_on, loc):
        m = bpy.data.meshes.new(Bricker_parent_on + "_mesh")
        parent = bpy.data.objects.new(Bricker_parent_on, m)
        parent.location = loc
        parent.use_fake_user = True
        return parent

    def setAction(self, cm):
        """ sets self.action """
        if cm.modelCreated:
            self.action = "UPDATE_MODEL"
        elif cm.animated:
            self.action = "UPDATE_ANIM"
        elif not cm.useAnimation:
            self.action = "CREATE"
        else:
            self.action = "ANIMATE"

    #############################################
