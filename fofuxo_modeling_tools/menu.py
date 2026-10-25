# SPDX-License-Identifier: GPL-3.0-or-later

"""Fofuxo submenu at the end of the Add Modifier menu."""

import bpy

from .arabesque import FOFUXO_OT_arabesque_add
from .merge_collection import FOFUXO_OT_merge_collection_add
from .spherical_bend import FOFUXO_OT_spherical_bend_add


class FOFUXO_MT_modifier_add(bpy.types.Menu):
    bl_idname = "FOFUXO_MT_modifier_add"
    bl_label = "Fofuxo"

    def draw(self, context):
        layout = self.layout
        layout.operator(FOFUXO_OT_merge_collection_add.bl_idname, icon='OUTLINER_COLLECTION')
        layout.operator(FOFUXO_OT_spherical_bend_add.bl_idname, icon='SPHERECURVE')
        layout.operator(FOFUXO_OT_arabesque_add.bl_idname, icon='CURVE_BEZCURVE')


def draw_modifier_menu(self, context):
    self.layout.menu(FOFUXO_MT_modifier_add.bl_idname)


classes = (FOFUXO_MT_modifier_add,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.OBJECT_MT_modifier_add.append(draw_modifier_menu)


def unregister():
    bpy.types.OBJECT_MT_modifier_add.remove(draw_modifier_menu)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
