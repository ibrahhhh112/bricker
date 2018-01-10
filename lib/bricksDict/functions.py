"""
Copyright (C) 2017 Bricks Brought to Life
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
from mathutils.interpolate import poly_3d_calc
import math
import colorsys

# Blender imports
import bpy

# Rebrickr imports
from ...functions import *
from ..Brick import Bricks


def getUVCoord(mesh, face, point, image):
    # get active uv layer data
    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        return None
    uv = uv_layer.data
    # get 3D coordinates of face's vertices
    lco = [mesh.vertices[i].co for i in face.vertices]
    # get uv coordinates of face's vertices
    luv = [uv[i].uv for i in face.loop_indices]
    # calculate barycentric weights for point
    lwts = poly_3d_calc(lco, point)
    # multiply barycentric weights by uv coordinates
    uv_loc = sum((p*w for p,w in zip(luv,lwts)), Vector((0,0)))
    # convert uv_loc in range(0,1) to uv coordinate
    image_size_x, image_size_y = image.size
    x_co = round(uv_loc.x * (image_size_x - 1))
    y_co = round(uv_loc.y * (image_size_y - 1))
    uv_coord = (x_co, y_co)

    # return resulting uv coordinate
    return Vector(uv_coord)


def getUVTextureData(obj):
    if len(obj.data.uv_textures) == 0:
        return None
    active_uv = obj.data.uv_textures.active
    if active_uv is None and len(obj.data.uv_textures) > 0:
        obj.data.uv_textures.active = obj.data.uv_textures[0]
        active_uv = obj.data.uv_textures.active
    return active_uv.data


def getFirstImgTexNode(obj):
    img = None
    for mat_slot in obj.material_slots:
        mat = mat_slot.material
        if not mat.use_nodes:
            return None
        active_node = mat.node_tree.nodes.active
        nodes_to_check = [active_node] + list(mat.node_tree.nodes)
        for node in nodes_to_check:
            if node is not None and node.type == "TEX_IMAGE":
                img = node.image
                break
    return img


# reference: https://svn.blender.org/svnroot/bf-extensions/trunk/py/scripts/addons/uv_bake_texture_to_vcols.py
def getUVImages(obj):
    scn, cm, _ = getActiveContextInfo()
    # get list of images to store
    images = []
    images.append(bpy.data.images.get(cm.uvImageName))
    uv_tex_data = getUVTextureData(obj)
    if uv_tex_data is not None:
        for uv_tex in uv_tex_data:
            images.append(uv_tex.image)
    images.append(getFirstImgTexNode(obj))
    # store images
    uv_images = {}
    for img in images:
        if not img or img.name in uv_images or not img.pixels:
            continue
        uv_images[img.name] = (img.size[0],
                               img.size[1],
                               img.pixels[:]
                               # Accessing pixels directly is far too slow.
                               #Copied to new array for massive performance-gain.
                               )
    return uv_images


# reference: https://svn.blender.org/svnroot/bf-extensions/trunk/py/scripts/addons/uv_bake_texture_to_vcols.py
def getPixel(image, uv_coord, uv_images):
    rgba = []

    image_size_x, image_size_y, uv_pixels = uv_images[image.name]
    pixelNumber = (image_size_x * int(uv_coord.y)) + int(uv_coord.x)
    r = uv_pixels[pixelNumber*4 + 0]
    g = uv_pixels[pixelNumber*4 + 1]
    b = uv_pixels[pixelNumber*4 + 2]
    a = uv_pixels[pixelNumber*4 + 3]
    return (r, g, b, a)


def getAverage(rgba0, rgba1, weight):
    r0, g0, b0, a0 = rgba0
    r1, g1, b1, a1 = rgba1
    r2 = ((r1 * weight) + r0) / (weight + 1)
    g2 = ((g1 * weight) + g0) / (weight + 1)
    b2 = ((b1 * weight) + b0) / (weight + 1)
    a2 = ((a1 * weight) + a0) / (weight + 1)
    return [r2, g2, b2, a2]



def createNewMaterial(rgba):
    scn, cm, _ = getActiveContextInfo()
    r, g, b, a = rgba
    if cm.colorSnapAmount > 0:
        # r_hsv, g_hsv, b_hsv = colorsys.rgb_to_hsv(r, g, b)
        # r0 = round(r / (1 + cm.colorSnapAmount * (60000/3)), 4)
        # g0 = round(g / (1 + cm.colorSnapAmount * (60000/5.9)), 4)
        # b0 = round(b / (1 + cm.colorSnapAmount * (60000/1.1)), 4)
        r0 = round(r / (1 + cm.colorSnapAmount * 20000), 4)
        g0 = round(g / (1 + cm.colorSnapAmount * 20000), 4)
        b0 = round(b / (1 + cm.colorSnapAmount * 20000), 4)
        a0 = round(a, 1)
    else:
        r0, g0, b0, a0 = rgba
    # get or create material with unique color
    mat_name = "Rebrickr_mat_{}-{}-{}-{}".format(r0, g0, b0, a0)
    mat = bpy.data.materials.get(mat_name)
    mat_is_new = mat is None
    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)
    # set diffuse and transparency of material
    if scn.render.engine == "BLENDER_RENDER":
        if mat_is_new:
            mat.diffuse_color = [r, g, b]
            mat.diffuse_intensity = 1.0
            if a < 1.0:
                mat.use_transparency = True
                mat.alpha = a
        else:
            r1, g1, b1 = mat.diffuse_color
            a1 = mat.alpha
            r2, g2, b2, a2 = getAverage(rgba, [r1, g1, b1, a1], mat.num_averaged)
            mat.diffuse_color = [r2, g2, b2]
            mat.alpha = a2
    elif scn.render.engine == "CYCLES":
        if mat_is_new:
            mat.use_nodes = True
            mat_nodes = mat.node_tree.nodes
            mat_links = mat.node_tree.links
            # a new material node tree already has a diffuse and material output node
            output = mat_nodes['Material Output']
            diffuse = mat_nodes['Diffuse BSDF']
            diffuse.inputs[0].default_value = rgba
        else:
            mat_nodes = mat.node_tree.nodes
            diffuse = mat_nodes['Diffuse BSDF']
            rgba1 = diffuse.inputs[0].default_value
            newRGBA = getAverage(rgba, rgba1, mat.num_averaged)
            diffuse.inputs[0].default_value = newRGBA
    mat.num_averaged += 1
    return mat_name


def getUVImage(obj, face_idx):
    scn, cm, _ = getActiveContextInfo()
    image = bpy.data.images.get(cm.uvImageName)
    if image is None and obj.data.uv_textures.active is not None:
        image = obj.data.uv_textures.active.data[face_idx].image
    if image is None:
        image = getFirstImgTexNode(obj)
    return image


def getUVPixelColor(obj, face_idx, point, uv_images):
    if face_idx is None:
        return None
    # get closest material using UV map
    scn, cm, _ = getActiveContextInfo()
    face = obj.data.polygons[face_idx]
    # get uv_texture image for face
    image = getUVImage(obj, face_idx)
    if image is None:
        return None
    # get uv coordinate based on nearest face intersection
    uv_coord = getUVCoord(obj.data, face, point, image)
    # retrieve rgba value at uv coordinate
    rgba = getPixel(image, uv_coord, uv_images)
    return rgba


def getMaterialColor(matName):
    mat = bpy.data.materials.get(matName)
    if mat is None:
        return None
    if mat.use_nodes:
        mat_nodes = mat.node_tree.nodes
        mat_links = mat.node_tree.links
        # a new material node tree already has a diffuse and material output node
        output = mat_nodes['Material Output']
        for node in mat_nodes:
            if node.type == "BSDF_DIFFUSE":
                diffuse = node
                break
        if diffuse is not None:
            r, g, b, a = diffuse.inputs[0].default_value
        else:
            return None
    else:
        r, g, b = mat.diffuse_color
        intensity = mat.diffuse_intensity
        r = r * intensity
        g = g * intensity
        b = b * intensity
        a = mat.alpha if mat.use_transparency else 1.0
    return [r, g, b, a]


def getClosestMaterial(obj, face_idx, point, uv_images):
    """ sets all matNames in bricksDict based on nearest_face """
    scn, cm, _ = getActiveContextInfo()
    if face_idx is None:
        return ""
    face = obj.data.polygons[face_idx]
    matName = ""
    # get material based on rgba value
    if uv_images is not None:
        rgba = getUVPixelColor(obj, face_idx, Vector(point), uv_images)
    else:
        rgba = None
    if rgba is not None:
        if brick_materials_loaded() and cm.snapToBrickColors:
            # pick closest brick material
            matName = findNearestBrickColorName(rgba)
        else:
            # create new material
            matName = createNewMaterial(rgba)
    # get closest material using material slot of face
    elif len(obj.material_slots) > 0:
        slot = obj.material_slots[face.material_index]
        mat = slot.material
        matName = mat.name if mat is not None else ""
        if brick_materials_loaded() and cm.snapToBrickColors:
            rgba = getMaterialColor(matName)
            if rgba is not None:
                matName = findNearestBrickColorName(rgba)
    return matName


def getDictKey(name):
    """ get dict key details of obj """
    dictKey = name.split("__")[1]
    dictLoc = strToList(dictKey)
    return dictKey, dictLoc


def getDetailsAndBounds(source, skipDimensions=False):
    scn, cm, _ = getActiveContextInfo()
    # get dimensions and bounds
    source_details = bounds(source)
    if not skipDimensions:
        zStep = getZStep(cm)
        dimensions = Bricks.get_dimensions(cm.brickHeight, zStep/3, cm.gap)
        return source_details, dimensions
    else:
        return source_details


def getArgumentsForBricksDict(cm, source=None, source_details=None, dimensions=None):
    if source is None:
        source = bpy.data.objects.get(cm.source_name)
        if source is None: source = bpy.data.objects.get(cm.source_name + " (DO NOT RENAME)")
    if source_details is None or dimensions is None:
        source_details, dimensions = getDetailsAndBounds(source)
    if cm.brickType == "Custom":
        scn = bpy.context.scene
        customObj = bpy.data.objects[cm.customObjectName]
        oldLayers = list(scn.layers) # store scene layers for later reset
        setLayers(scn, customObj.layers)
        select(customObj, active=customObj)
        bpy.ops.object.duplicate()
        customObj0 = scn.objects.active
        select(customObj0, active=customObj0)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        customObj_details = bounds(customObj0)
        customData = customObj0.data
        bpy.data.objects.remove(customObj0, True)
        scale = cm.brickHeight/customObj_details.z.dist
        R = (scale * customObj_details.x.dist + dimensions["gap"],
             scale * customObj_details.y.dist + dimensions["gap"],
             scale * customObj_details.z.dist + dimensions["gap"])
        setLayers(scn, oldLayers)
    else:
        customData = None
        customObj_details = None
        R = (dimensions["width"] + dimensions["gap"],
             dimensions["width"] + dimensions["gap"],
             dimensions["height"]+ dimensions["gap"])
    return source, source_details, dimensions, R, customData, customObj_details
