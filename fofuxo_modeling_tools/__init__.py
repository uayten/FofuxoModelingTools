# SPDX-License-Identifier: GPL-3.0-or-later

from . import merge_collection, mirror_angle

modules = (mirror_angle, merge_collection)


def register():
    for module in modules:
        module.register()


def unregister():
    for module in reversed(modules):
        module.unregister()
