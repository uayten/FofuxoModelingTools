# SPDX-License-Identifier: GPL-3.0-or-later

"""Spherical Bend: Geometry Nodes modifier that bends a flat mesh into a vault.

The node groups live in assets/spherical_bend.blend and are appended into the
file the first time the modifier is added; later modifiers reuse them.
"""

from pathlib import Path

import bpy

GROUP_NAME = "Spherical Bend"
# Custom property stored on the asset's main node group, so a user group that
# happens to share the name is never reused.
GROUP_KEY = "fofuxo_spherical_bend"
ASSET_PATH = Path(__file__).parent / "assets" / "spherical_bend.blend"


def find_group():
    for group in bpy.data.node_groups:
        if group.get(GROUP_KEY):
            return group
    return None


def append_group():
    with bpy.data.libraries.load(str(ASSET_PATH), link=False) as (_source, target):
        target.node_groups = [GROUP_NAME]
    # Name clashes are resolved on append, so the group may come back renamed.
    return target.node_groups[0]


class FOFUXO_OT_spherical_bend_add(bpy.types.Operator):
    """Add a modifier that bends a flat mesh into a vault, with optional pillars and decoration"""

    bl_idname = "object.fofuxo_spherical_bend_add"
    bl_label = "Spherical Bend"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            cls.poll_message_set("Active object must be a mesh")
            return False
        return True

    def execute(self, context):
        group = find_group() or append_group()
        modifier = context.object.modifiers.new(name=GROUP_NAME, type='NODES')
        modifier.node_group = group
        return {'FINISHED'}


classes = (FOFUXO_OT_spherical_bend_add,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
