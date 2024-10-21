import bpy, os, sys
from PIL import Image
from PIL import ImageFilter
import numpy as np

from bpy.props import StringProperty, CollectionProperty, IntProperty

bl_info = {
    "name": "Starfield Planet Experiments",
    "author": "Deveris256 (biom scripts by PixelRick, adjusted)",
    "version": (0, 1, 1),
    "blender": (4, 0, 0),
    "location": "3D",
    "description": "Starfield Planet Experiments",
    "category": "Development"
}

addon_folder = os.path.dirname(os.path.abspath(__file__))
utils_folder = os.path.join(addon_folder, "utils")
layers_folder = os.path.join(addon_folder, "layers")

if not os.path.isdir(utils_folder):
    os.makedirs(utils_folder)

if not os.path.isdir(layers_folder):
    os.makedirs(layers_folder)

dir = os.path.dirname(os.path.realpath(__file__))
if dir not in sys.path:
	sys.path.append(dir)

import biom
import palette

# Reloads on F8 hotkey press
if "bpy" in locals():
    import imp
    imp.reload(biom)
    imp.reload(palette)

"""
Classes
"""

class SF_UL_BiomeData(bpy.types.UIList):
    bl_idname = "SF_UL_BiomeData"
    layout_type = "DEFAULT"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.label(text=item.name)
        layout.scale_x = 0.6
        layout.label(text=str(item.biome_id))
        layout.scale_x = 0.35
        layout.operator("sf_planets.select_biome_color").index = index

class PlanetBiome(bpy.types.PropertyGroup):
    name: StringProperty(name="Name", default="NAME UNKNOWN")
    biome_id: IntProperty(name="Biome ID", default=0)

class StarfieldPlanet(bpy.types.PropertyGroup):
    name: StringProperty(name="Planet name", default="")
    biomes: CollectionProperty(type=PlanetBiome)

class SF_PT_Planets(bpy.types.Panel):
    bl_idname = "SF_PT_Planets"

    bl_label = "StarfieldPlanets"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Starfield Planets"

    def draw(self, context):
        layout = self.layout
        obj = bpy.data.objects.get("planet_sphere_unit:0")

        layout.operator("sf_planet.load_biom_file")

        mat = []

        if obj != None and len(obj.data.materials) >= 1 and obj.data.materials[0] != None:
            mat = obj.data.materials[0]

        if "planet_name" in mat:
            layout.label(text=f"Editing {mat['planet_name']}")
            layout.operator("sf_planets.open_images_folder")

            box = layout.box()
            box.label(text="Biomes")

            box.template_list(
                "SF_UL_BiomeData",
                "",
                mat, "biome_data",
                mat, "selected_biome"
            )

            box.operator("sf_planets.set_biome_id")

            box = layout.box()
            col = box.column()
            col.operator("sf_planets.gen_layer_images")
            col.operator("sf_planets.enter_texture_paint")

            row = box.row()
            row.operator("sf_planets.select_biome_image")
            row.operator("sf_planets.select_resource_image")
            box.operator("sf_planets.save_edited_images")

            layout.separator()

            layout.operator("sf_planet.save_biom_file")

"""
Operators
"""

class SelectBiomeColor(bpy.types.Operator):
    bl_idname = "sf_planets.select_biome_color"
    bl_label = "Col"
    bl_description = "Select biome color and enter texture painting mode"
    bl_options = {'UNDO'}

    index: IntProperty()

    def execute(self, context):
        obj = bpy.data.objects["planet_sphere_unit:0"]

        if not isPlanetValid(obj):
            self.report("Invalid planet: addon looks for planet_sphere_unit:0 with valid material")
            return {'CANCELLED'}
        
        mat = obj.data.materials[0]

        #palette_slice = palette.palettedata_lists[:len(mat.biome_data)]
        #palette_slice.reverse()
        col = tuple(c / 255 for c in palette.palettedata_lists[self.index])

        bpy.ops.object.mode_set(mode='TEXTURE_PAINT')
        brush = bpy.context.tool_settings.image_paint.brush
        bpy.context.scene.tool_settings.image_paint.use_normal_falloff
        brush.color = col

        return {'FINISHED'}

class MakeBrushCorrect(bpy.types.Operator):
    bl_idname = "sf_planets.enter_texture_paint"
    bl_label = "Set-up and enter texture paint"
    bl_description = "Applies correct settings to the active brush"
    bl_options = {'UNDO'}

    def execute(self, context):
        area_set = False
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'SOLID'
                        area_set = True
                        
        if area_set == False:
            self.report({'ERROR'}, "Can't find viewport")
            return {'CANCELLED'}
        
        bpy.ops.object.mode_set(mode='TEXTURE_PAINT')
        brush = bpy.context.tool_settings.image_paint.brush
        brush.curve_preset = 'CONSTANT'

        return {'FINISHED'}

class SelectBiomeImage(bpy.types.Operator):
    bl_idname = "sf_planets.select_biome_image"
    bl_label = "View biomes"
    bl_description = "Selects biome map"
    bl_options = {'UNDO'}

    def execute(self, context):
        obj = bpy.data.objects["planet_sphere_unit:0"]
        
        if not isPlanetValid(obj):
            self.report("Invalid planet: addon looks for planet_sphere_unit:0 with valid material")
            return {'CANCELLED'}
        
        mat = obj.data.materials[0]
        img_node = mat.node_tree.nodes.get("biomes")

        if img_node == None:
            self.report({'ERROR'}, "Can't find biome image node")
            return {'CANCELLED'}

        mat.node_tree.nodes.active = img_node
        
        idx = mat.texture_paint_slots.find(img_node.image.name)
        mat.paint_active_slot = idx
        
        return {'FINISHED'}

class SelectResourceImage(bpy.types.Operator):
    bl_idname = "sf_planets.select_resource_image"
    bl_label = "View resources"
    bl_description = "Selects resource map"
    bl_options = {'UNDO'}

    def execute(self, context):
        obj = bpy.data.objects["planet_sphere_unit:0"]
        
        if not isPlanetValid(obj):
            self.report("Invalid planet: addon looks for planet_sphere_unit:0 with valid material")
            return {'CANCELLED'}
        
        mat = obj.data.materials[0]
        img_node = mat.node_tree.nodes.get("resources")

        if img_node == None:
            self.report({'ERROR'}, "Can't find resources image node")
            return {'CANCELLED'}

        mat.node_tree.nodes.active = img_node

        idx = mat.texture_paint_slots.find(img_node.image.name)
        mat.paint_active_slot = idx
        
        return {'FINISHED'}

class GenLayerImages(bpy.types.Operator):
    bl_idname = "sf_planets.gen_layer_images"
    bl_label = "Gen layers (for texture artists)"
    bl_description = "Separate image layers to textures (Might help you with custom texture drawing!). Please save edited images first."
    bl_options = {'UNDO'}

    old_id: IntProperty(default=0)
    new_id: StringProperty(default="")

    def execute(self, context):
        obj = bpy.data.objects["planet_sphere_unit:0"]
        
        if not isPlanetValid(obj):
            self.report("Invalid planet: addon looks for planet_sphere_unit:0 with valid material")
            return {'CANCELLED'}
        
        planet_name = obj.data.materials[0]["planet_name"]
        genLayerImages(planet_name)
        return {'FINISHED'}

class OpenImagesFolder(bpy.types.Operator):
    bl_idname = "sf_planets.open_images_folder"
    bl_label = "Open images folder"
    bl_description = "Open folder with all planet textures"
    bl_options = {'UNDO'}

    def execute(self, context):
        os.startfile(utils_folder)
        return {'FINISHED'}

class SaveEditedImages(bpy.types.Operator):
    bl_idname = "sf_planets.save_edited_images"
    bl_label = "Save edited images"
    bl_description = "Saves edited biome and resource images to disk"
    bl_options = {'UNDO'}

    def execute(self, context):
        obj = bpy.data.objects["planet_sphere_unit:0"]

        if not isPlanetValid(obj):
            self.report("Invalid planet: addon looks for planet_sphere_unit:0 with valid material")
            return {'CANCELLED'}

        mat = obj.data.materials[0]

        biom_node = mat.node_tree.nodes.get("biomes")
        res_node = mat.node_tree.nodes.get("biomes")

        if biom_node == None or res_node == None:
            self.report({'ERROR'}, "Can't find biome or resource image node in material!")
            return {'CANCELLED'}
        
        res_node.image.save()
        biom_node.image.save()
        self.report({'INFO'}, f"Images saved for {mat['planet_name']}")
        return {'FINISHED'}

class SetBiomeID(bpy.types.Operator):
    bl_idname = "sf_planets.set_biome_id"
    bl_label = "Set biome id"
    bl_description = "Set biome id for the selected biome in list"
    bl_options = {'UNDO'}

    old_id: IntProperty(default=0)
    new_id: StringProperty(default="")

    @classmethod
    def poll(cls, context):
        return True
    
    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Old ID: {f'{self.old_id:08x}'}")
        layout.prop(self, "new_id", text="New Form ID")

    def execute(self, context):
        context.object.data.materials[0].biome_data[context.object.data.materials[0].selected_biome].biome_id = int(self.new_id, 16)
        context.object.data.materials[0].biome_data[context.object.data.materials[0].selected_biome].name = biom.get_biome_names(int(self.new_id, 16))[1]
        return {'FINISHED'}

    def invoke(self, context, event):
        biome = context.object.data.materials[0].biome_data[context.object.data.materials[0].selected_biome]
        self.old_id = int(biome.biome_id)

        return context.window_manager.invoke_props_dialog(self)

class LoadBiomFile(bpy.types.Operator):
    bl_idname = "sf_planet.load_biom_file"
    bl_label = "Load .biom file"
    bl_description = "Load biom file and create material"
    filename: bpy.props.StringProperty(default='')
    directory: bpy.props.StringProperty(subtype="DIR_PATH")

    filter_glob: bpy.props.StringProperty(default="*.biom", options={'HIDDEN'})

    def execute(self, event):
        planet_obj_name = "planet_sphere_unit:0"

        if planet_obj_name not in [o.name for o in bpy.data.objects]:
            bpy.ops.wm.obj_import(
                filepath=os.path.join(addon_folder, "planet.obj")
            )

        elif planet_obj_name not in [o.name for o in bpy.context.scene.objects]:
            bpy.context.scene.objects.link(bpy.data.objects[planet_obj_name])
        
        bpy.context.view_layer.objects.active = bpy.data.objects["planet_sphere_unit:0"]

        planet_obj = bpy.context.view_layer.objects.active
        planet = loadPlanet(os.path.join(self.directory, self.filename))

        createPlanetMaterial(planet_obj, planet, self.filename.removesuffix(".biom"))
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class SaveBiomFile(bpy.types.Operator):
    bl_idname = "sf_planet.save_biom_file"
    bl_label = "Save .biom file and images"
    bl_description = "Save .biom file to disk. Will also save modified planet images to disk."
    filename: bpy.props.StringProperty(default='')
    directory: bpy.props.StringProperty(subtype="DIR_PATH")

    filter_glob: bpy.props.StringProperty(default="*.biom", options={'HIDDEN'})

    def execute(self, event):        
        obj = bpy.data.objects["planet_sphere_unit:0"]
        mat = obj.data.materials[0]

        biom_node = mat.node_tree.nodes.get("biomes")
        res_node = mat.node_tree.nodes.get("biomes")

        if biom_node == None or res_node == None:
            self.report({'ERROR'}, "Can't find biome or resource image node in material!")
            return {'CANCELLED'}
        
        res_node.image.save()
        biom_node.image.save()

        if not self.filename.endswith(".biom"):
            self.filename = f"{self.filename}.biom"

        saveBiom(obj, os.path.join(self.directory, self.filename))
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        obj = bpy.data.objects["planet_sphere_unit:0"]
        
        if not isPlanetValid(obj):
            self.report("Invalid planet: addon looks for planet_sphere_unit:0 with valid material")
            return {'CANCELLED'}
        
        self.filename = f"{obj.data.materials[0]['planet_name']}.biom"

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

"""
Functions
"""

def isPlanetValid(obj):
    return obj != None and len(obj.data.materials) >= 1 and obj.data.materials[0] != None and "planet_name" in obj.data.materials[0]

def saveBiom(planet, save_path):

    planet_name = planet.data.materials[0]["planet_name"]
    biomes = planet.data.materials[0].biome_data

    biom_img = Image.open(os.path.join(utils_folder, f"{planet_name}_biomes.png")).convert('RGB')
    res_img = Image.open(os.path.join(utils_folder, f"{planet_name}_resources.png")).convert('RGB')

    biom_file = biom.BiomFile()

    biom_file.res_img = res_img
    biom_file.biom_img = biom_img
    biom_file.biomeIds = [b.biome_id for b in biomes]

    biom_file.imgToArray()

    biom_file.save(save_path)
    pass

def loadPlanet(planet_file):
    planet_name = os.path.basename(planet_file).removesuffix(".biom")
    biom_file = biom.BiomFile()

    biom_file.load(planet_file)

    biom_file.texture()
    biome_img = biom_file.biome_idx_img
    resource_img = biom_file.res_idx_img

    biome_img.save(os.path.join(utils_folder, f"{planet_name}_biomes.png"))
    resource_img.save(os.path.join(utils_folder, f"{planet_name}_resources.png"))

    return biom_file

def createPlanetMaterial(obj, planet, planet_name):
    if planet_name not in [mat.name for mat in bpy.data.materials]:
        planet_mat = bpy.data.materials.new(planet_name)
    else:
        planet_mat = bpy.data.materials[planet_name]

    obj.data.materials[0] = planet_mat

    planet_mat["planet_name"] = planet_name

    planet_mat.biome_data.clear()
    for biome in planet.biomeIds:
        planet_biome = planet_mat.biome_data.add()
        planet_biome.biome_id = biome
        planet_biome.name = biom.get_biome_names(biome)[1]

    if f"{planet_name}_resources.png" not in bpy.data.images:
        res_img = bpy.data.images.load(
            os.path.join(utils_folder, f"{planet_name}_resources.png")
        )

    else:
        res_img = bpy.data.images[f"{planet_name}_resources.png"]

    res_img.colorspace_settings.name = "Non-Color"

    if f"{planet_name}_biomes.png" not in bpy.data.images:
        biom_img = bpy.data.images.load(
            os.path.join(utils_folder, f"{planet_name}_biomes.png")
        )

    else:
        biom_img = bpy.data.images[f"{planet_name}_biomes.png"]

    biom_img.colorspace_settings.name = "Non-Color"

    planet_mat.use_nodes = True

    node_names = [n.name for n in planet_mat.node_tree.nodes]

    if "resources" not in node_names:
        res_tex_node = planet_mat.node_tree.nodes.new('ShaderNodeTexImage')
        res_tex_node.name = "resources"
        res_tex_node.image = res_img
    else:
        res_tex_node = planet_mat.node_tree.nodes.get('resources')

    if "biomes" not in node_names:
        biom_tex_node = planet_mat.node_tree.nodes.new('ShaderNodeTexImage')
        biom_tex_node.name = "biomes"
        biom_tex_node.image = biom_img
    else:
        biom_tex_node = planet_mat.node_tree.nodes.get('biomes')

    res_tex_node.interpolation = "Closest"
    biom_tex_node.interpolation = "Closest"
    principled_BSDF = planet_mat.node_tree.nodes.get('Principled BSDF')
    principled_BSDF.inputs[2].default_value = 1.0
    planet_mat.node_tree.links.new(biom_tex_node.outputs[0], principled_BSDF.inputs[0])

    planet_mat.node_tree.nodes.active = biom_tex_node

def genLayerImages(planet_name):
    biom_img = Image.open(os.path.join(utils_folder, f"{planet_name}_biomes.png")).convert('RGB')
    res_img = Image.open(os.path.join(utils_folder, f"{planet_name}_resources.png")).convert('RGB')

    for idx, img in enumerate([biom_img, res_img]):

        img_array = np.asarray(img)
        unique = np.unique(img_array.reshape(-1, img_array.shape[2]), axis=0)

        if idx == 0:
            suffix = "biomes"
        else:
            suffix = "resources"

        for col_idx, unique_color in enumerate(unique):
            sel_img_array = np.copy(img_array)

            sel_img_array[sel_img_array == unique_color] = 255
            sel_img_array[sel_img_array != 255] = 0

            unique_img = Image.fromarray(sel_img_array)
            unique_img = unique_img.resize((1024, 2048))
            unique_img = unique_img.filter(ImageFilter.GaussianBlur(radius=2.75))
            unique_img = unique_img.filter(ImageFilter.SMOOTH_MORE)
            unique_img = unique_img.filter(ImageFilter.SMOOTH_MORE)
            unique_img = unique_img.filter(ImageFilter.EDGE_ENHANCE_MORE)
            unique_img = unique_img.filter(ImageFilter.EDGE_ENHANCE)

            unique_img.save(
                os.path.join(layers_folder, f"{planet_name}_{suffix}_layer{col_idx}.png")
            )

            unique_img = unique_img.filter(ImageFilter.FIND_EDGES)
            unique_img = unique_img.filter(ImageFilter.SMOOTH_MORE)
            unique_img.save(
                os.path.join(layers_folder, f"{planet_name}_{suffix}_layer{col_idx}_EDGE.png")
            )

"""
Register
"""

classes = [
    SetBiomeID,
    SaveBiomFile,
    PlanetBiome,
    StarfieldPlanet,
    LoadBiomFile,
    OpenImagesFolder,
    GenLayerImages,
    SelectBiomeColor,
    MakeBrushCorrect,
    SelectBiomeImage,
    SelectResourceImage,
    SaveEditedImages,
    SF_UL_BiomeData,
    SF_PT_Planets,
]

def register():
    for c in classes:
        bpy.utils.register_class(c)
    
    s = bpy.types.Scene
    m = bpy.types.Material

    m.biome_data = CollectionProperty(type=PlanetBiome)
    m.selected_biome = IntProperty(default=0)

def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
    
    m = bpy.types.Material

    del m.biome_data
    del m.selected_biome

if __name__ == "__main__":
    register()
