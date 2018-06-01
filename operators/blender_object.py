import bpy
from bpy.props import IntProperty, StringProperty, EnumProperty
from .. import utils
from ..bin import pyluxcore
from .utils import (
    poll_object, poll_material, init_mat_node_tree, make_nodetree_name,
    LUXCORE_OT_set_node_tree, 
)

def LUXCORE_OT_use_proxy_switch(self, context):
    obj = context.active_object
    transformation = obj.matrix_world
    
    if not obj.luxcore.use_proxy:
        if len(obj.luxcore.proxies) > 0:            
            bpy.ops.object.select_all(action='DESELECT')

            # Reload high res object
            for p in obj.luxcore.proxies:
                bpy.ops.import_mesh.ply(filepath=p.filepath)
                
            for s in context.selected_objects:
                matIndex = obj.luxcore.proxies[s.name].matIndex
                mat = obj.material_slots[matIndex].material
                s.data.materials.append(mat)

            bpy.ops.object.join()
            context.active_object.matrix_world = transformation
            context.active_object.name = context.active_object.name[:-3]

            bpy.ops.object.select_all(action='DESELECT')
            obj.select = True
            bpy.ops.object.delete()

class LUXCORE_OT_proxy_new(bpy.types.Operator):
    bl_idname = "luxcore.proxy_new"
    bl_label = "New"
    bl_description = "Create a new proxy object"

    # hidden properties
    directory = bpy.props.StringProperty(name = 'PLY directory')
    filter_glob = bpy.props.StringProperty(default = '*.ply', options = {'HIDDEN'})
    use_filter = bpy.props.BoolProperty(default = True, options = {'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return poll_object(context)

    def invoke(self, context, event):
        obj = context.active_object
        if obj.data.users > 1:
            context.scene.luxcore.errorlog.add_error("[Object: %s] Can't make proxy from multiuser mesh" % obj.name)
            return {"FINISHED"}
            
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}        

    def execute(self, context):
        obj = context.active_object

        #TODO: Support other object types
        if obj.type in ['MESH']:
            #Copy object
            print("Create Proxy: Copy object")
            proxy = obj
            obj = proxy.copy()
            obj.data = proxy.data.copy()
            context.scene.objects.link(obj)

            # rename object
            obj.name = proxy.name
            proxy.name = obj.name + '_lux_proxy'

            # TODO: accept custom parameters for decimate modifier
            decimate = proxy.modifiers.new('proxy_decimate', 'DECIMATE')
            decimate.ratio = 0.05

            # Create low res proxy object
            print("Create Proxy: Create low res proxy object")
            proxy.select = True
            context.scene.objects.active = proxy
            #bpy.ops.object.modifier_apply(apply_as='DATA', modifier=decimate.name)
            proxy.luxcore.use_proxy = True

            bpy.ops.object.select_all(action='DESELECT')
            obj.select = True
            context.scene.objects.active = obj
            
            # clear parent
            bpy.ops.object.parent_clear(type = 'CLEAR_KEEP_TRANSFORM')

            mesh = obj.to_mesh(context.scene, True, 'RENDER')
            
            # Export object into PLY files via pyluxcore functions
            luxcore_scene = pyluxcore.Scene()
            
            faces = mesh.tessfaces[0].as_pointer()
            vertices = mesh.vertices[0].as_pointer()

            uv_textures = mesh.tessface_uv_textures
            active_uv = utils.find_active_uv(uv_textures)
            if active_uv and active_uv.data:
                texCoords = active_uv.data[0].as_pointer()
            else:
                texCoords = 0

            vertex_color = mesh.tessface_vertex_colors.active
            if vertex_color:
                vertexColors = vertex_color.data[0].as_pointer()
            else:
                vertexColors = 0            
            
            mesh_definitions = luxcore_scene.DefineBlenderMesh(obj.name, len(mesh.tessfaces), faces, len(mesh.vertices),
                                           vertices, texCoords, vertexColors, None)

            bpy.ops.object.delete()
            
            print("Create Proxy: Export high resolution geometry data into PLY files...")
            for [name, mat] in mesh_definitions:
                filepath = self.directory + name + ".ply"
                luxcore_scene.SaveMesh("Mesh-"+name, filepath);                
                new = proxy.luxcore.proxies.add()
                new.name = name
                new.matIndex = mat
                new.filepath = self.directory + name + ".ply"
                print("Saved ", self.directory + name + ".ply")
            
            bpy.ops.object.select_all(action='DESELECT')
            proxy.select = True
            context.scene.objects.active = proxy
        return {"FINISHED"}

class LUXCORE_OT_proxy_add(bpy.types.Operator):
    bl_idname = "luxcore.proxy_add"
    bl_label = "Add"
    bl_description = "Add an object to the proxy list"

    @classmethod
    def poll(cls, context):
        return poll_object(context)

    def execute(self, context):        
        obj = context.active_object
        new = obj.luxcore.proxies.add()
        new.name = obj.name  
        obj.luxcore.proxies.update()        
        return {"FINISHED"}

class LUXCORE_OT_proxy_remove(bpy.types.Operator):
    bl_idname = "luxcore.proxy_remove"
    bl_label = "Remove"
    bl_description = "Remove an object from the proxy list"

    @classmethod
    def poll(cls, context):
        return poll_object(context)

    def execute(self, context):        
        obj = context.active_object
        obj.luxcore.proxies.remove(len(obj.luxcore.proxies)-1)
        obj.luxcore.proxies.update()
        
        return {"FINISHED"}
