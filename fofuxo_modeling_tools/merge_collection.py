# SPDX-License-Identifier: GPL-3.0-or-later

"""Geometry Nodes modifier that merges a whole collection into the object.

The node group reads the collection with Collection Info in Original space,
realizes the instances into real geometry and joins them with the object's
own mesh. The collection comes in as it sits around the world origin, with
no rotation, and is then carried by the object: moving or rotating the
object moves the merged mesh. It follows every change made to the sources.
"""

import bpy
from bpy.app.handlers import persistent

GROUP_NAME = "Merge Collection"
# Custom property that marks a node group as created by this tool, so a user
# group that happens to share the name is never reused. Its value is the
# version of the node setup (version 1 stored True).
GROUP_KEY = "fofuxo_merge_collection"
GROUP_VERSION = 2


def find_group():
    for group in bpy.data.node_groups:
        if group.get(GROUP_KEY):
            return group
    return None


def ensure_group():
    group = find_group()
    if group is None:
        return create_group()
    upgrade_group(group)
    return group


def upgrade_group(group):
    """Update a group from an older version in place, keeping the modifiers'
    collection choices."""
    if group[GROUP_KEY] == GROUP_VERSION:
        return
    # Version 2: the collection is placed from the world origin and carried
    # by the object, instead of staying where it is in the world (Relative).
    for node in group.nodes:
        if node.bl_idname == 'GeometryNodeCollectionInfo':
            node.transform_space = 'ORIGINAL'
    group[GROUP_KEY] = GROUP_VERSION


def create_group():
    group = bpy.data.node_groups.new(GROUP_NAME, 'GeometryNodeTree')
    group[GROUP_KEY] = GROUP_VERSION
    group.is_modifier = True

    interface = group.interface
    interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    interface.new_socket("Collection", in_out='INPUT', socket_type='NodeSocketCollection')
    interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    nodes = group.nodes
    group_input = nodes.new('NodeGroupInput')
    group_input.location = (-600, 0)
    collection_info = nodes.new('GeometryNodeCollectionInfo')
    collection_info.transform_space = 'ORIGINAL'
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


@persistent
def upgrade_on_load(_filepath=None):
    group = find_group()
    if group is not None:
        upgrade_group(group)


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
        group = ensure_group()
        modifier = context.object.modifiers.new(name=GROUP_NAME, type='NODES')
        modifier.node_group = group
        return {'FINISHED'}


classes = (FOFUXO_OT_merge_collection_add,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.app.handlers.load_post.append(upgrade_on_load)
    # The file already open when the add-on is enabled or updated.
    bpy.app.timers.register(upgrade_on_load, first_interval=0.0)


def unregister():
    bpy.app.handlers.load_post.remove(upgrade_on_load)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
