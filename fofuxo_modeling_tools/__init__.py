# SPDX-License-Identifier: GPL-3.0-or-later

from . import arabesque, menu, merge_collection, mirror_angle, spherical_bend

# Registration order: operators before the menu that references them.
modules = (mirror_angle, merge_collection, spherical_bend, arabesque, menu)


def register():
    for module in modules:
        module.register()


def unregister():
    for module in reversed(modules):
        module.unregister()
