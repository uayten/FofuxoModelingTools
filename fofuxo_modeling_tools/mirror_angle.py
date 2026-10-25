# SPDX-License-Identifier: GPL-3.0-or-later

"""Angle checkbox inside the stock Mirror modifier panel.

The Mirror modifier only mirrors across the object's X/Y/Z planes, which sit
at 90 degrees from each other. Turning the checkbox on points the modifier's
Mirror Object at a hidden empty parented to the object and rotated 45 degrees
around Z, so the mirror plane is tilted and still follows the object.

The checkbox has no storage of its own: it is on whenever the Mirror Object is
one of these empties.
"""

import math

import bpy

# Custom property that marks an empty as created by this tool.
PLANE_KEY = "fofuxo_mirror_plane"
DEFAULT_ROTATION = (0.0, 0.0, math.radians(45.0))


def find_plane(modifier):
    plane = modifier.mirror_object
    if plane is not None and plane.get(PLANE_KEY) and plane.parent == modifier.id_data:
        return plane
    return None


def create_plane(obj):
    plane = bpy.data.objects.new(f"{obj.name}_MirrorPlane", None)
    plane[PLANE_KEY] = True
    plane.empty_display_type = 'ARROWS'
    plane.empty_display_size = mesh_radius(obj)
    for collection in obj.users_collection:
        collection.objects.link(plane)

    # A fresh object has an identity parent inverse, so the rotation below is
    # in the object's local space.
    plane.parent = obj
    plane.rotation_euler = DEFAULT_ROTATION
    plane.hide_viewport = True
    return plane


# Panels known to have their modifier assigned, and panels waiting for the
# redraw that assigns it. Keys are Panel pointers.
ready_panels = set()
pending_panels = set()


def panel_is_ready(panel):
    """Whether panel.custom_data is safe to read.

    A sub-panel added to a Mirror panel that already existed when the add-on
    was enabled is drawn once before Blender assigns its modifier, and reading
    custom_data then crashes Blender. The modifier is assigned again on every
    redraw, so the first draw of each panel is skipped and a new one requested.
    """
    key = panel.as_pointer()
    if key in ready_panels:
        return True
    if key not in pending_panels:
        pending_panels.add(key)
        bpy.app.timers.register(promote_pending_panels, first_interval=0.0)
    return False


def promote_pending_panels():
    ready_panels.update(pending_panels)
    pending_panels.clear()
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'PROPERTIES':
                area.tag_redraw()


def mesh_radius(obj):
    """Largest local bounding-box coordinate, used to size the empty."""
    radius = max(abs(value) for corner in obj.bound_box for value in corner)
    return radius if radius > 0.0 else 1.0


class FOFUXO_OT_mirror_angle_toggle(bpy.types.Operator):
    """Mirror across a plane rotated 45 degrees around Z instead of the X/Y/Z planes"""

    bl_idname = "object.fofuxo_mirror_angle_toggle"
    bl_label = "Toggle Mirror Angle"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        # Set by the panel header through context_pointer_set.
        modifier = getattr(context, "modifier", None)
        return modifier is not None and modifier.type == 'MIRROR'

    def execute(self, context):
        modifier = context.modifier
        plane = find_plane(modifier)
        if plane is None:
            modifier.mirror_object = create_plane(modifier.id_data)
        else:
            modifier.mirror_object = None
            bpy.data.objects.remove(plane)
        return {'FINISHED'}


class FOFUXO_PT_mirror_angle(bpy.types.Panel):
    """Sub-panel of the stock Mirror modifier panel"""

    bl_label = "Angle"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    # Panel id the Mirror modifier registers in C (MOD_PT_ + modifier idname).
    bl_parent_id = "MOD_PT_Mirror"

    def draw_header(self, context):
        # Modifiers cannot hold Python properties, so the checkbox is an
        # operator button drawn like one.
        if not panel_is_ready(self):
            return
        enabled = find_plane(self.custom_data) is not None
        layout = self.layout
        layout.context_pointer_set("modifier", self.custom_data)
        layout.operator(
            FOFUXO_OT_mirror_angle_toggle.bl_idname,
            text="",
            icon='CHECKBOX_HLT' if enabled else 'CHECKBOX_DEHLT',
            emboss=False,
        )

    def draw(self, context):
        if not panel_is_ready(self):
            return
        layout = self.layout
        layout.use_property_split = True
        plane = find_plane(self.custom_data)
        if plane is None:
            layout.active = False
            layout.label(text="Mirror plane rotated 45° around Z")
            return
        layout.prop(plane, "rotation_euler", text="Rotation")


classes = (FOFUXO_OT_mirror_angle_toggle, FOFUXO_PT_mirror_angle)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    ready_panels.clear()
    pending_panels.clear()
    if bpy.app.timers.is_registered(promote_pending_panels):
        bpy.app.timers.unregister(promote_pending_panels)
