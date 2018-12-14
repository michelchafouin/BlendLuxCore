import bpy
from bpy.props import PointerProperty
from . import LuxCoreNode, TREE_ICONS
from ..utils import ui as utils_ui
from ..ui import icons


class LuxCoreNodeTreePointer(LuxCoreNode, bpy.types.Node):
    """ Pointer to a node tree """
    bl_label = "Pointer"
    bl_width_default = 210
    suffix = "pointer"

    def update_node_tree(self, context):
        if self.node_tree:
            self.outputs["Material"].enabled = self.node_tree.bl_idname == "luxcore_material_nodes"
            self.outputs["Color"].enabled = self.node_tree.bl_idname == "luxcore_texture_nodes"
            self.outputs["Volume"].enabled = self.node_tree.bl_idname == "luxcore_volume_nodes"
        else:
            self.outputs["Material"].enabled = False
            self.outputs["Color"].enabled = False
            self.outputs["Volume"].enabled = False

    node_tree: PointerProperty(name="Node Tree", type=bpy.types.NodeTree, update=update_node_tree,
                                description="Use the output of the selected node tree in this node tree")

    def init(self, context):
        self.outputs.new("LuxCoreSocketMaterial", "Material")
        self.outputs["Material"].enabled = False
        self.outputs.new("LuxCoreSocketColor", "Color")
        self.outputs["Color"].enabled = False
        self.outputs.new("LuxCoreSocketVolume", "Volume")
        self.outputs["Volume"].enabled = False

    def draw_label(self):
        if self.node_tree:
            return 'Pointer to "%s"' % self.node_tree.name
        else:
            return self.bl_label

    def draw_buttons(self, context, layout):
        if self.node_tree:
            icon = TREE_ICONS[self.node_tree.bl_idname]
        else:
            icon = "NODETREE"

        utils_ui.template_node_tree(layout, self, "node_tree", icon,
                                    "LUXCORE_MT_pointer_select_node_tree",
                                    "luxcore.pointer_show_node_tree",
                                    "",  # Do not offer to create a node tree
                                    "luxcore.pointer_unlink_node_tree")

        if self.node_tree == self.id_data:
            layout.label(text="Recursion!", icon=icons.WARNING)

    def sub_export(self, exporter, props, luxcore_name=None):
        if self.node_tree == self.id_data:
            raise Exception("Recursion (pointer referencing its own node tree)")

        # Import statement here to prevent circular imports
        from .output import get_active_output
        output = get_active_output(self.node_tree)

        if output is None:
            print("ERROR: no active output found in node tree", self.node_tree.name)
            return None

        if luxcore_name is None:
            luxcore_name = self.make_name()

        output.export(exporter, props, luxcore_name)
        return luxcore_name
