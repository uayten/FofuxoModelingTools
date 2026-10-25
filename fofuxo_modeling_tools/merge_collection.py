# SPDX-License-Identifier: GPL-3.0-or-later

"""Geometry Nodes modifier that merges a whole collection into the object.

The node group reads the collection with Collection Info in Relative space,
realizes the instances into real geometry and joins them with the object's
own mesh. The merged mesh stays where the source objects are in the world,
wherever the carrier object sits, and follows every change made to them.
"""

import bpy

GROUP_NAME = "Merge Collection"
# Custom property that marks a node group as created by this tool, so a user
# group that happens to share the name is never reused.
GROUP_KEY = "fofuxo_merge_collection"


def find_group():
    for group in bpy.data.node_groups:
        if group.get(GROUP_KEY):
            return group
    return None


def create_group():
    group = bpy.data.node_groups.new(GROUP_NAME, 'GeometryNodeTree')
    group[GROUP_KEY] = True
    group.is_modifier = True

    interface = group.interface
    interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    interface.new_socket("Collection", in_out='INPUT', socket_type='NodeSocketCollection')
    interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    nodes = group.nodes
    group_input = nodes.new('NodeGroupInput')
    group_input.location = (-600, 0)
    collection_info = nodes.new('GeometryNodeCollectionInfo')
    collection_info.transform_space = 'RELATIVE'
    collection_info.location = (-380, -120)
    realize = nodes.new('GeometryNodeRealizeInstances')
    realize.location = (-160, -120)
    join = nodes.new('GeometryNodeJoinGeometry')
    join.location = (60, 0)
    group_output = nodes.new('NodeGroupOutput')
    group_output.location = (260, 0)

    links = group.links
    links.new(group_input.outputs["Collection"], collection_info.inputs["Collection"])
    links.new(collection_info.outputs["Instances"], realize.inputs["Geometry"])
    links.new(group_input.outputs["Geometry"], join.inputs["Geometry"])
    links.new(realize.outputs["Geometry"], join.inputs["Geometry"])
    links.new(join.outputs["Geometry"], group_output.inputs["Geometry"])
    return group


class FOFUXO_OT_merge_collection_add(bpy.types.Operator):
    """Add a modifier that merges every object of a collection into this mesh"""

    bl_idname = "object.fofuxo_merge_collection_add"
    bl_label = "Merge Collection"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            cls.poll_message_set("Active object must be a mesh (empties cannot hold modifiers)")
            return False
        return True

    def execute(self, context):
        group = find_group() or create_group()
        modifier = context.object.modifiers.new(name=GROUP_NAME, type='NODES')
        modifier.node_group = group
        return {'FINISHED'}


def draw_modifier_menu(self, context):
    self.layout.operator(FOFUXO_OT_merge_collection_add.bl_idname, icon='OUTLINER_COLLECTION')


classes = (FOFUXO_OT_merge_collection_add,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.OBJECT_MT_modifier_add_generate.append(draw_modifier_menu)


def unregister():
    bpy.types.OBJECT_MT_modifier_add_generate.remove(draw_modifier_menu)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
