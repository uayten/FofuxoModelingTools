# SPDX-License-Identifier: GPL-3.0-or-later

"""Arabesque: Geometry Nodes modifier that turns an edge skeleton into a relief.

Each run of edges becomes a poly spline swept with an open ridged profile: one
profile ring per skeleton vertex, all quads, no caps and no back face, a cage
meant for a Subdivision Surface placed after the modifier. Sharp lengthwise
edges, such as the crest, get a crease.

Edges with both ends in the Stem Group vertex group form the main stem, which
runs unbroken through junctions; the other edges are connected branches. At
every junction the branches' rings are welded onto one anchor ring (the main
stem's, when it passes there), so the mesh stays in one piece. The Width Group
vertex group blends each vertex from Width to Group Width.

Width and thickness are in world units: they are divided by the object's scale
and the mesh is built in local space.

Socket names are English; the add-on registers Brazilian Portuguese
translations for them.
"""

import math

import bpy

GROUP_NAME = "Arabesque"
# Custom property that marks the node group as created by this tool. Its
# value is the version of the node setup: a group from an older version is
# rebuilt in place, so modifiers already in the file pick up the changes.
GROUP_KEY = "fofuxo_arabesque"
GROUP_VERSION = 7
# Inputs renamed between versions, so their values survive the rebuild.
RENAMED_INPUTS = {"Main Stem": "Stem Group"}
# Attributes that only live inside the node group.
FREE_ATTRIBUTE = "fofuxo_free_end"
JUNCTION_ATTRIBUTE = "fofuxo_junction"
MAIN_ATTRIBUTE = "fofuxo_main"
WIDTH_ATTRIBUTE = "fofuxo_width"
SPLINE_ATTRIBUTE = "fofuxo_spline"
STEM_ATTRIBUTE = "fofuxo_stem_spline"
CENTER_ATTRIBUTE = "fofuxo_center"
TANGENT_ATTRIBUTE = "fofuxo_tangent"
TAPER_ATTRIBUTE = "fofuxo_taper"
PROFILE_ATTRIBUTE = "fofuxo_profile_point"
# Edge attribute read by the Subdivision Surface modifier.
CREASE_ATTRIBUTE = "crease_edge"

# Names Blender does not translate by itself ("Width", "Thickness",
# "Direction" and "Crease" it does).
TRANSLATIONS = {
    "pt_BR": {("*", english): portuguese for english, portuguese in (
        ("Main Stem", "Segmento Principal"),
        ("Connected Branches", "Extensões Conectadas"),
        ("Stem Group", "Grupo do Segmento"),
        ("Width Group", "Grupo de Largura"),
        ("Group Width", "Largura do Grupo"),
        ("Crest", "Crista"),
        ("Sharp Angle", "Ângulo do Vinco"),
        ("Connect to Stem", "Conectar ao Segmento"),
        ("Taper Ends", "Afinar Pontas"),
        ("Tip Width", "Largura da Ponta"),
        ("Taper Power", "Força do Afinamento"),
    )},
}


def find_group():
    for group in bpy.data.node_groups:
        if group.get(GROUP_KEY):
            return group
    return None


class Builder:
    """Small helper to add nodes and links with less noise."""

    def __init__(self, group):
        self.nodes = group.nodes
        self.links = group.links

    def node(self, idname, location, **settings):
        node = self.nodes.new(idname)
        node.location = location
        for name, value in settings.items():
            setattr(node, name, value)
        return node

    def link(self, from_socket, to_socket):
        self.links.new(from_socket, to_socket)

    def connect(self, node, inputs):
        """Link sockets or set defaults; keys are input names or indices."""
        for key, value in inputs.items():
            socket = node.inputs[key]
            if isinstance(value, bpy.types.NodeSocket):
                self.link(value, socket)
            else:
                socket.default_value = value
        return node

    def math(self, operation, location, *values, label=""):
        node = self.node('ShaderNodeMath', location, operation=operation, label=label)
        self.connect(node, dict(enumerate(values)))
        return node.outputs[0]

    def vector_math(self, operation, location, *values):
        node = self.node('ShaderNodeVectorMath', location, operation=operation)
        self.connect(node, dict(enumerate(values)))
        return node.outputs["Value" if operation in ('LENGTH', 'DOT_PRODUCT') else "Vector"]

    def vector(self, location, x=0.0, y=0.0, z=0.0):
        node = self.node('ShaderNodeCombineXYZ', location)
        return self.connect(node, {"X": x, "Y": y, "Z": z}).outputs["Vector"]

    def switch(self, input_type, location, condition, false, true):
        node = self.node('GeometryNodeSwitch', location, input_type=input_type)
        return self.connect(node, {"Switch": condition, "False": false, "True": true}).outputs["Output"]

    def compare(self, data_type, operation, location, a, b):
        node = self.node('FunctionNodeCompare', location, data_type=data_type, operation=operation)
        return self.connect(node, {"A": a, "B": b}).outputs["Result"]

    def boolean(self, operation, location, *values):
        node = self.node('FunctionNodeBooleanMath', location, operation=operation)
        return self.connect(node, dict(enumerate(values))).outputs["Boolean"]

    def store(self, location, geometry, name, value, data_type, domain='POINT'):
        node = self.node('GeometryNodeStoreNamedAttribute', location, data_type=data_type, domain=domain)
        return self.connect(node, {"Geometry": geometry, "Name": name, "Value": value}).outputs["Geometry"]

    def attribute(self, location, name, data_type):
        node = self.node('GeometryNodeInputNamedAttribute', location, data_type=data_type)
        return self.connect(node, {"Name": name}).outputs["Attribute"]

    def separate(self, location, geometry, selection):
        node = self.node('GeometryNodeSeparateGeometry', location, domain='POINT')
        return self.connect(node, {"Geometry": geometry, "Selection": selection}).outputs["Selection"]

    def sample_index(self, data_type, location, geometry, value, index):
        node = self.node('GeometryNodeSampleIndex', location, data_type=data_type, domain='POINT')
        return self.connect(node, {"Geometry": geometry, "Value": value, "Index": index}).outputs["Value"]

    def nearest(self, location, geometry, position):
        node = self.node('GeometryNodeSampleNearest', location, domain='POINT')
        return self.connect(node, {"Geometry": geometry, "Sample Position": position}).outputs["Index"]


def ensure_group():
    group = find_group()
    if group is None:
        group = bpy.data.node_groups.new(GROUP_NAME, 'GeometryNodeTree')
    elif group[GROUP_KEY] == GROUP_VERSION:
        return group
    settings = save_modifier_inputs(group)
    build_group(group)
    restore_modifier_inputs(group, settings)
    return group


def modifier_inputs(group):
    """(modifier, {input name: identifier}) for every modifier using group."""
    names = {item.name: item.identifier for item in group.interface.items_tree
             if item.item_type == 'SOCKET' and item.in_out == 'INPUT'}
    for obj in bpy.data.objects:
        for modifier in obj.modifiers:
            if modifier.type == 'NODES' and modifier.node_group == group:
                yield modifier, names


def save_modifier_inputs(group):
    """Input values by name, so a rebuild (which renews the socket
    identifiers) keeps what the user set, attribute choices included."""
    saved = []
    for modifier, names in modifier_inputs(group):
        values = {}
        for name, identifier in names.items():
            name = RENAMED_INPUTS.get(name, name)
            if hasattr(modifier, "properties"):  # Blender 5.0+
                socket = getattr(modifier.properties.inputs, identifier, None)
                if socket is not None and hasattr(socket, "value"):
                    values[name] = (socket.value, getattr(socket, "type", None), getattr(socket, "attribute_name", None))
            elif identifier in modifier.keys():
                use_attribute = modifier.get(identifier + "_use_attribute")
                values[name] = (modifier[identifier],
                                'ATTRIBUTE' if use_attribute else 'VALUE',
                                modifier.get(identifier + "_attribute_name"))
        saved.append((modifier, values))
    return saved


def restore_modifier_inputs(group, saved):
    items = {item.name: item for item in group.interface.items_tree
             if item.item_type == 'SOCKET' and item.in_out == 'INPUT'}
    for modifier, values in saved:
        for name, item in items.items():
            identifier = item.identifier
            value, mode, attribute_name = values.get(name, (getattr(item, "default_value", None), None, None))
            # A vertex group picked through the old attribute toggle becomes
            # the text of a group-name input.
            if item.socket_type == 'NodeSocketString':
                mode, value = None, attribute_name if mode == 'ATTRIBUTE' and attribute_name else ""
            if value is None:
                continue
            # A socket may have changed type between versions: skip it then.
            try:
                if hasattr(modifier, "properties"):
                    socket = getattr(modifier.properties.inputs, identifier)
                    if mode is not None and hasattr(socket, "type"):
                        socket.type = mode
                    if attribute_name and mode == 'ATTRIBUTE' and hasattr(socket, "attribute_name"):
                        socket.attribute_name = attribute_name
                    socket.value = value
                else:
                    modifier[identifier] = value
                    if mode is not None:
                        modifier[identifier + "_use_attribute"] = mode == 'ATTRIBUTE'
                    if attribute_name and mode == 'ATTRIBUTE':
                        modifier[identifier + "_attribute_name"] = attribute_name
            except (TypeError, ValueError, AttributeError):
                pass


def add_inputs(interface, panel, specs):
    for name, socket_type, default, minimum, maximum, subtype, description in specs:
        socket = interface.new_socket(name, in_out='INPUT', socket_type=socket_type, parent=panel)
        socket.default_value = default
        if minimum is not None:
            socket.min_value = minimum
            socket.max_value = maximum
        if subtype:
            socket.subtype = subtype
        socket.description = description


def build_interface(interface):
    interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    interface.new_socket("Direction", in_out='INPUT', socket_type='NodeSocketMenu').description = (
        "Side of the skeleton plane the relief rises from")

    stem = interface.new_panel("Main Stem")
    add_inputs(interface, stem, (
        ("Stem Group", 'NodeSocketString', "", None, None, None,
         "Vertex group of the main stem, which runs unbroken through junctions. Empty: every edge is stem"),
        ("Width", 'NodeSocketFloat', 0.007, 0.0, 10.0, 'DISTANCE', "Width of the base, in world units"),
        ("Thickness", 'NodeSocketFloat', 0.005, 0.0, 10.0, 'DISTANCE', "Height from the base to the top, in world units"),
        ("Crest", 'NodeSocketFloat', 1.0, 0.0, 10.0, 'NONE',
         "How far the sides close in: 0 is a rectangle, 0.5 a top half as wide as the base, "
         "1 sides meeting in a crest, above 1 a taller crest"),
        ("Width Group", 'NodeSocketString', "", None, None, None,
         "Vertex group whose weights blend each vertex from Width (0) to Group Width (1)"),
        ("Group Width", 'NodeSocketFloat', 0.014, 0.0, 10.0, 'DISTANCE', "Width of the base where the Width Group weight is 1, in world units"),
        ("Crease", 'NodeSocketFloat', 1.0, 0.0, 1.0, 'FACTOR', "Crease given to sharp lengthwise edges, kept sharp by Subdivision Surface"),
        ("Sharp Angle", 'NodeSocketFloat', math.radians(30.0), 0.0, math.pi, 'ANGLE', "Lengthwise edges whose faces meet at more than this angle get the crease"),
    ))

    branches = interface.new_panel("Connected Branches")
    add_inputs(interface, branches, (
        ("Connect to Stem", 'NodeSocketBool', True, None, None, None, "Weld the branches onto the stem where they meet"),
        ("Taper Ends", 'NodeSocketBool', False, None, None, None, "Thin the branches towards their free ends"),
        ("Tip Width", 'NodeSocketFloat', 0.35, 0.0, 1.0, 'FACTOR', "Width at the free end relative to the branch's width"),
        ("Taper Power", 'NodeSocketFloat', 1.5, 0.1, 10.0, 'NONE', "Higher values keep the branch wide for longer before it thins"),
    ))

    interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')


def build_group(group):
    group.nodes.clear()
    group.interface.clear()
    group[GROUP_KEY] = GROUP_VERSION
    group.is_modifier = True
    build_interface(group.interface)

    b = Builder(group)
    group_input = b.node('NodeGroupInput', (-2200, 0))
    group_output = b.node('NodeGroupOutput', (5200, 200))
    gi = group_input.outputs

    # Direction: +1 for the object's +Z side, -1 for the -Z side.
    direction = b.node('GeometryNodeMenuSwitch', (-2000, 600), data_type='FLOAT')
    direction.enum_items[0].name = "Up"
    direction.enum_items[1].name = "Down"
    b.connect(direction, {"Menu": gi["Direction"], "Up": 1.0, "Down": -1.0})
    sign = direction.outputs[0]

    # On the skeleton: free ends, junctions, the main stem and the width of
    # each vertex, carried over to the splines as point attributes.
    neighbors = b.node('GeometryNodeInputMeshVertexNeighbors', (-2000, -250)).outputs["Vertex Count"]
    skeleton = b.store((-1600, 0), gi["Geometry"], FREE_ATTRIBUTE,
                       b.compare('INT', 'EQUAL', (-1800, -250), neighbors, 1), 'BOOLEAN')
    skeleton = b.store((-1560, 0), skeleton, JUNCTION_ATTRIBUTE,
                       b.compare('INT', 'GREATER_EQUAL', (-1800, -400), neighbors, 3), 'BOOLEAN')
    stem_group = b.node('GeometryNodeInputNamedAttribute', (-1800, 300), data_type='BOOLEAN')
    b.connect(stem_group, {"Name": gi["Stem Group"]})
    # Without a stem group every vertex is stem.
    on_stem = b.switch('BOOLEAN', (-1600, 300), stem_group.outputs["Exists"], True, stem_group.outputs["Attribute"])
    skeleton = b.store((-1520, 0), skeleton, MAIN_ATTRIBUTE, on_stem, 'BOOLEAN')
    width_weight = b.node('GeometryNodeInputNamedAttribute', (-1800, 500), data_type='FLOAT')
    b.connect(width_weight, {"Name": gi["Width Group"]})
    width_blend = b.node('ShaderNodeMix', (-1600, 500), data_type='FLOAT', clamp_factor=True)
    b.connect(width_blend, {"Factor": width_weight.outputs["Attribute"], "A": gi["Width"], "B": gi["Group Width"]})
    skeleton = b.store((-1480, 0), skeleton, WIDTH_ATTRIBUTE, width_blend.outputs["Result"], 'FLOAT')

    # Main stem edges (both ends on it) become their own splines, so the stem
    # runs unbroken through the junctions where branches leave it.
    main = b.attribute((-1700, -700), MAIN_ATTRIBUTE, 'BOOLEAN')
    edge_ends = b.node('GeometryNodeInputMeshEdgeVertices', (-1700, -900))
    main_1 = b.node('GeometryNodeFieldAtIndex', (-1500, -700), domain='POINT', data_type='BOOLEAN')
    b.connect(main_1, {"Index": edge_ends.outputs["Vertex Index 1"], "Value": main})
    main_2 = b.node('GeometryNodeFieldAtIndex', (-1500, -900), domain='POINT', data_type='BOOLEAN')
    b.connect(main_2, {"Index": edge_ends.outputs["Vertex Index 2"], "Value": main})
    main_edge = b.boolean('AND', (-1300, -800), main_1.outputs["Value"], main_2.outputs["Value"])
    branch_edge = b.boolean('NOT', (-1300, -1000), main_edge)
    stem_curves = b.node('GeometryNodeMeshToCurve', (-1400, 100))
    b.connect(stem_curves, {"Mesh": skeleton, "Selection": main_edge})
    branch_curves = b.node('GeometryNodeMeshToCurve', (-1400, -100))
    b.connect(branch_curves, {"Mesh": skeleton, "Selection": branch_edge})
    stem_marked = b.store((-1300, 150), stem_curves.outputs["Curve"], STEM_ATTRIBUTE, True, 'BOOLEAN')
    all_curves = b.node('GeometryNodeJoinGeometry', (-1250, 0))
    b.link(branch_curves.outputs["Curve"], all_curves.inputs["Geometry"])
    b.link(stem_marked, all_curves.inputs["Geometry"])

    # The mesh is built in the object's local space; Width and Thickness are
    # in world units, so divide them by the object's scale, measured as the
    # world length of each local axis. (Separate Transform cannot decompose
    # the matrix of a mirrored object and returns a scale of 1 for it.)
    self_object = b.node('GeometryNodeSelfObject', (-1600, -1300))
    object_info = b.node('GeometryNodeObjectInfo', (-1400, -1300), transform_space='ORIGINAL')
    b.connect(object_info, {"Object": self_object.outputs[0], "As Instance": False})
    axis_sizes = []
    for row, axis in enumerate(((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))):
        world_axis = b.node('FunctionNodeTransformDirection', (-1200, -1300 - 150 * row))
        b.connect(world_axis, {"Direction": axis, "Transform": object_info.outputs["Transform"]})
        axis_sizes.append(b.vector_math('LENGTH', (-1000, -1300 - 150 * row), world_axis.outputs["Direction"]))
    plane_scale = b.math('MULTIPLY', (-800, -1300), b.math('ADD', (-900, -1300), axis_sizes[0], axis_sizes[1]), 0.5)
    plane_scale = b.math('MAXIMUM', (-700, -1300), plane_scale, 0.000001)
    up_scale = b.math('MAXIMUM', (-700, -1450), axis_sizes[2], 0.000001)
    local_width = b.math('DIVIDE', (-600, -1300), gi["Width"], plane_scale, label="Width in local units")
    local_thickness = b.math('DIVIDE', (-600, -1450), gi["Thickness"], up_scale, label="Thickness in local units")

    # Poly splines: one profile ring per skeleton vertex.
    normal = b.node('GeometryNodeSetCurveNormal', (-400, 0))
    b.connect(normal, {"Curve": all_curves.outputs["Geometry"], "Mode": 'Z Up'})

    # The profile is built at Width: scale it to each point's own width, and
    # taper the branches if asked.
    point_width = b.attribute((600, -300), WIDTH_ATTRIBUTE, 'FLOAT')
    safe_width = b.math('MAXIMUM', (600, -500), gi["Width"], 0.000001)
    width_factor = b.math('DIVIDE', (800, -300), point_width, safe_width)
    is_stem = b.attribute((800, -500), STEM_ATTRIBUTE, 'BOOLEAN')
    branch_taper = b.switch('FLOAT', (1000, -500), is_stem, build_taper(b, gi), 1.0)
    taper = b.math('MULTIPLY', (1000, -300), branch_taper, width_factor)
    curves = b.store((1000, 0), normal.outputs["Curve"], TAPER_ATTRIBUTE, taper, 'FLOAT')
    curve_of_point = b.node('GeometryNodeCurveOfPoint', (1000, 200))
    curves = b.store((1100, 0), curves, SPLINE_ATTRIBUTE, curve_of_point.outputs["Curve Index"], 'INT')
    # Each ring remembers its skeleton point and direction, to weld junctions.
    center = b.node('GeometryNodeInputPosition', (1100, 300))
    curves = b.store((1150, 0), curves, CENTER_ATTRIBUTE, center.outputs["Position"], 'FLOAT_VECTOR')
    tangent = b.node('GeometryNodeInputTangent', (1150, 300))
    curves = b.store((1200, 0), curves, TANGENT_ATTRIBUTE, tangent.outputs["Tangent"], 'FLOAT_VECTOR')

    # Open profile, no caps: every face is a quad and the mesh stays open.
    profile = build_profile(b, local_width, local_thickness, gi["Crest"])
    curve_to_mesh = b.node('GeometryNodeCurveToMesh', (1400, 0))
    b.connect(curve_to_mesh, {"Curve": curves, "Profile Curve": profile, "Scale": taper, "Fill Caps": False})

    # Place the relief on the chosen side of the skeleton plane at the full
    # Thickness: Scale changed the height together with the width.
    taper_attribute = b.attribute((1400, -400), TAPER_ATTRIBUTE, 'FLOAT')
    plane = b.node('GeometryNodeAttributeStatistic', (1400, -600), data_type='FLOAT', domain='POINT')
    position_in = b.node('GeometryNodeInputPosition', (1200, -700))
    separate_in = b.node('ShaderNodeSeparateXYZ', (1300, -800))
    b.connect(separate_in, {"Vector": position_in.outputs["Position"]})
    b.connect(plane, {"Geometry": curves, "Attribute": separate_in.outputs["Z"]})
    position = b.node('GeometryNodeInputPosition', (1600, -500))
    separate = b.node('ShaderNodeSeparateXYZ', (1800, -500))
    b.connect(separate, {"Vector": position.outputs["Position"]})
    height = b.math('SUBTRACT', (1800, -700), separate.outputs["Z"], plane.outputs["Mean"])
    safe_taper = b.math('MAXIMUM', (1800, -900), taper_attribute, 0.0001)
    relief = b.math('DIVIDE', (2000, -900), 1.0, safe_taper, label="undo the height scaling")
    # Which side of the plane Curve to Mesh put the profile on varies with
    # each spline's direction: take the distance from the plane and send
    # every point to the side Direction asks for.
    distance = b.math('ABSOLUTE', (2000, -700), height)
    signed_relief = b.math('MULTIPLY', (2200, -900), relief, sign)
    new_z = b.math('MULTIPLY_ADD', (2200, -700), distance, signed_relief, plane.outputs["Mean"])
    combine = b.node('ShaderNodeCombineXYZ', (2400, -500))
    b.connect(combine, {"X": separate.outputs["X"], "Y": separate.outputs["Y"], "Z": new_z})
    set_position = b.node('GeometryNodeSetPosition', (1800, 0))
    b.connect(set_position, {"Geometry": curve_to_mesh.outputs["Mesh"], "Position": combine.outputs["Vector"]})

    # Face winding follows each spline's direction, which varies: per spline,
    # flip the faces when they point, on the whole, towards the plane.
    face_normal = b.node('GeometryNodeInputNormal', (1800, 500))
    normal_z = b.node('ShaderNodeSeparateXYZ', (2000, 500))
    b.connect(normal_z, {"Vector": face_normal.outputs["Normal"]})
    spline = b.attribute((1800, 700), SPLINE_ATTRIBUTE, 'INT')
    facing = b.node('GeometryNodeAccumulateField', (2200, 500), data_type='FLOAT', domain='FACE')
    b.connect(facing, {"Value": normal_z.outputs["Z"], "Group ID": spline})
    towards_relief = b.math('MULTIPLY', (2400, 500), facing.outputs["Total"], sign)
    flip = b.node('GeometryNodeFlipFaces', (2000, 0))
    b.connect(flip, {"Mesh": set_position.outputs["Geometry"],
                     "Selection": b.compare('FLOAT', 'LESS_THAN', (2400, 300), towards_relief, 0.0)})

    welded = build_weld(b, flip.outputs["Mesh"], local_width)
    mesh = b.switch('GEOMETRY', (4600, 0), gi["Connect to Stem"], flip.outputs["Mesh"], welded)

    # Crease on lengthwise edges (both vertices from the same profile point)
    # where the faces meet sharply, such as the crest. Ring edges stay soft
    # so Subdivision Surface still rounds the bends.
    profile_point = b.attribute((4400, 900), PROFILE_ATTRIBUTE, 'INT')
    edge_vertices = b.node('GeometryNodeInputMeshEdgeVertices', (4400, 700))
    first = b.node('GeometryNodeFieldAtIndex', (4600, 900), domain='POINT', data_type='INT')
    b.connect(first, {"Index": edge_vertices.outputs["Vertex Index 1"], "Value": profile_point})
    second = b.node('GeometryNodeFieldAtIndex', (4600, 700), domain='POINT', data_type='INT')
    b.connect(second, {"Index": edge_vertices.outputs["Vertex Index 2"], "Value": profile_point})
    lengthwise = b.compare('INT', 'EQUAL', (4800, 800), first.outputs["Value"], second.outputs["Value"])
    edge_angle = b.node('GeometryNodeInputMeshEdgeAngle', (4600, 500))
    sharp = b.compare('FLOAT', 'GREATER_THAN', (4800, 600), edge_angle.outputs["Unsigned Angle"], gi["Sharp Angle"])
    crease = b.switch('FLOAT', (5000, 700), b.boolean('AND', (4900, 700), lengthwise, sharp), 0.0, gi["Crease"])
    mesh = b.store((4800, 200), mesh, CREASE_ATTRIBUTE, crease, 'FLOAT', domain='EDGE')

    remove_attributes = b.node('GeometryNodeRemoveAttribute', (5000, 200))
    b.connect(remove_attributes, {"Geometry": mesh, "Pattern Mode": 'Wildcard', "Name": "fofuxo_*"})
    b.link(remove_attributes.outputs["Geometry"], group_output.inputs["Geometry"])


def build_weld(b, mesh, local_width):
    """At every junction, weld the rings of the splines that meet there onto
    one anchor ring: the main stem's when it passes there, otherwise the ring
    of the spline with the lowest index.

    Rings are looked up with Sample Nearest in a "key space": the junction
    position stretched so junctions sit far apart, plus a small offset per
    spline. That finds the vertex of a given spline at a given junction."""
    x, y = 2600, 1600
    junction = b.attribute((x, y), JUNCTION_ATTRIBUTE, 'BOOLEAN')
    spline = b.attribute((x, y - 150), SPLINE_ATTRIBUTE, 'INT')
    stem = b.attribute((x, y - 300), STEM_ATTRIBUTE, 'BOOLEAN')
    profile_point = b.attribute((x, y - 450), PROFILE_ATTRIBUTE, 'INT')
    center = b.attribute((x, y - 600), CENTER_ATTRIBUTE, 'FLOAT_VECTOR')
    tangent = b.attribute((x, y - 750), TANGENT_ATTRIBUTE, 'FLOAT_VECTOR')
    position = b.node('GeometryNodeInputPosition', (x, y - 900)).outputs["Position"]

    # Junctions are at least about a stem width apart: 100 key units.
    stretch = b.math('DIVIDE', (x + 200, y + 200), 100.0, b.math('MAXIMUM', (x + 100, y + 200), local_width, 0.000001))
    stretched = b.node('ShaderNodeVectorMath', (x + 200, y), operation='SCALE')
    junction_key = b.connect(stretched, {0: center, "Scale": stretch}).outputs["Vector"]
    spline_offset = b.math('MULTIPLY', (x + 200, y - 200), spline, 0.01)
    rings = b.separate((x + 200, y - 400), mesh, junction)

    # The anchor at each junction: stem rings first (offset 0), then other
    # splines (offset 20), lowest spline index first. Crest points only.
    not_stem = b.boolean('NOT', (x + 400, y - 300), stem)
    class_offset = b.math('MULTIPLY_ADD', (x + 400, y - 200), b.switch('FLOAT', (x + 300, y - 300), not_stem, 0.0, 1.0), 20.0, spline_offset)
    crests = b.separate((x + 400, y - 500), rings, b.compare('INT', 'EQUAL', (x + 300, y - 500), profile_point, 2))
    anchor_keys = b.node('GeometryNodeSetPosition', (x + 600, y - 500))
    b.connect(anchor_keys, {"Geometry": crests,
                            "Position": b.vector_math('ADD', (x + 500, y - 600), junction_key, b.vector((x + 400, y - 700), z=class_offset))})
    anchor_index = b.nearest((x + 800, y - 500), anchor_keys.outputs["Geometry"], junction_key)
    anchor = b.sample_index('INT', (x + 1000, y - 500), crests, spline, anchor_index)
    anchor_tangent = b.sample_index('FLOAT_VECTOR', (x + 1000, y - 650), crests, tangent, anchor_index)

    # A ring running against the anchor has its profile mirrored.
    same_way = b.compare('FLOAT', 'GREATER_EQUAL', (x + 1200, y - 650),
                         b.vector_math('DOT_PRODUCT', (x + 1100, y - 650), tangent, anchor_tangent), 0.0)
    mirrored_point = b.math('SUBTRACT', (x + 1200, y - 800), 4.0, profile_point)
    matching = b.switch('INT', (x + 1400, y - 700), same_way, mirrored_point, profile_point)

    # For each profile point, where the anchor ring has it.
    anchor_key = b.vector_math('ADD', (x + 1200, y - 300), junction_key,
                               b.vector((x + 1100, y - 300), z=b.math('MULTIPLY', (x + 1000, y - 300), anchor, 0.01)))
    targets = []
    for i in range(5):
        row = y - 1100 - 200 * i
        ring_points = b.separate((x + 400, row), rings, b.compare('INT', 'EQUAL', (x + 300, row), profile_point, i))
        keyed = b.node('GeometryNodeSetPosition', (x + 600, row))
        b.connect(keyed, {"Geometry": ring_points,
                          "Position": b.vector_math('ADD', (x + 500, row - 100), junction_key, b.vector((x + 400, row - 100), z=spline_offset))})
        found = b.nearest((x + 800, row), keyed.outputs["Geometry"], anchor_key)
        targets.append(b.sample_index('FLOAT_VECTOR', (x + 1000, row), ring_points, position, found))
    target = b.node('GeometryNodeIndexSwitch', (x + 1600, y - 1100), data_type='VECTOR')
    for _ in range(3):
        target.index_switch_items.new()
    b.connect(target, {"Index": matching, **{i + 1: socket for i, socket in enumerate(targets)}})

    other_spline = b.compare('INT', 'NOT_EQUAL', (x + 1400, y - 400), spline, anchor)
    move = b.node('GeometryNodeSetPosition', (x + 1800, y - 600))
    b.connect(move, {"Geometry": mesh, "Selection": b.boolean('AND', (x + 1600, y - 400), junction, other_spline),
                     "Position": target.outputs[0]})
    merge = b.node('GeometryNodeMergeByDistance', (x + 2000, y - 600))
    b.connect(merge, {"Geometry": move.outputs["Geometry"], "Distance": 0.00001})
    return merge.outputs["Geometry"]


def build_profile(b, width, thickness, crest):
    """Open five-point profile from one base corner over the crest to the
    other: base corners on the plane, two shoulders and the crest. Profile X
    lies in the skeleton plane and Y points away from it (curve normals are
    Z Up). Each point stores its index, to find lengthwise edges later."""
    half = b.math('MULTIPLY', (200, 900), width, 0.5)
    quarter = b.math('MULTIPLY', (200, 1100), width, 0.25)
    closing = b.math('MINIMUM', (200, 1300), crest, 1.0)
    crest_height = b.math('MULTIPLY', (400, 1300), thickness, b.math('MAXIMUM', (200, 1500), crest, 1.0))

    # Crest below 1: flat top at Thickness, shoulders closing in with Crest.
    flat_x = b.math('MULTIPLY', (400, 900), half, b.math('SUBTRACT', (400, 1100), 1.0, closing))
    # Crest from 1: a ridge; shoulders at the middle of the sloped sides.
    ridge_y = b.math('MULTIPLY', (600, 1500), crest_height, 0.5)
    flat_top = b.compare('FLOAT', 'LESS_THAN', (600, 1700), crest, 1.0)
    shoulder_x = b.switch('FLOAT', (800, 1000), flat_top, quarter, flat_x)
    shoulder_y = b.switch('FLOAT', (800, 1200), flat_top, ridge_y, thickness)
    minus_half = b.math('MULTIPLY', (800, 800), half, -1.0)
    minus_shoulder_x = b.math('MULTIPLY', (1000, 1000), shoulder_x, -1.0)

    corners = b.node('GeometryNodeIndexSwitch', (1200, 1000), data_type='VECTOR')
    for _ in range(3):
        corners.index_switch_items.new()
    index = b.node('GeometryNodeInputIndex', (1000, 1300))
    b.connect(corners, {
        "Index": index.outputs["Index"],
        1: b.vector((1000, 1500), minus_half, 0.0),
        2: b.vector((1000, 1650), minus_shoulder_x, shoulder_y),
        3: b.vector((1000, 1800), 0.0, crest_height),
        4: b.vector((1000, 1950), shoulder_x, shoulder_y),
        5: b.vector((1000, 2100), half, 0.0),
    })
    points = b.node('GeometryNodePoints', (1400, 1000))
    b.connect(points, {"Count": 5, "Position": corners.outputs[0]})
    numbered = b.store((1500, 1000), points.outputs["Points"], PROFILE_ATTRIBUTE, index.outputs["Index"], 'INT')
    points_to_curves = b.node('GeometryNodePointsToCurves', (1600, 1000))
    b.connect(points_to_curves, {"Points": numbered})
    return points_to_curves.outputs["Curves"]


def build_taper(b, gi):
    """Taper factor along a spline: 1 unless Taper Ends thins it towards its
    free ends (both halves when both ends are free)."""
    curve_index = b.node('GeometryNodeCurveOfPoint', (-1000, -900)).outputs["Curve Index"]
    free_attribute = b.attribute((-1000, -700), FREE_ATTRIBUTE, 'BOOLEAN')
    first_point = b.node('GeometryNodePointsOfCurve', (-800, -900))
    b.connect(first_point, {"Curve Index": curve_index, "Sort Index": 0})
    last_index = b.math('SUBTRACT', (-800, -1100), first_point.outputs["Total"], 1.0)
    last_point = b.node('GeometryNodePointsOfCurve', (-600, -1100))
    b.connect(last_point, {"Curve Index": curve_index, "Sort Index": last_index})
    start_free = b.node('GeometryNodeFieldAtIndex', (-400, -800), domain='POINT', data_type='BOOLEAN')
    b.connect(start_free, {"Index": first_point.outputs["Point Index"], "Value": free_attribute})
    end_free = b.node('GeometryNodeFieldAtIndex', (-400, -1000), domain='POINT', data_type='BOOLEAN')
    b.connect(end_free, {"Index": last_point.outputs["Point Index"], "Value": free_attribute})

    # t goes from 0 at a junction to 1 at a free end.
    factor = b.node('GeometryNodeSplineParameter', (-400, -1250)).outputs["Factor"]
    to_end = b.math('MULTIPLY', (-200, -1000), factor, end_free.outputs["Value"], label="towards a free end")
    to_start = b.math('MULTIPLY', (-200, -800), b.math('SUBTRACT', (-200, -1200), 1.0, factor),
                      start_free.outputs["Value"], label="towards a free start")
    one_sided = b.math('MAXIMUM', (0, -900), to_end, to_start)
    both_free = b.boolean('AND', (0, -700), start_free.outputs["Value"], end_free.outputs["Value"])
    centered = b.math('MAXIMUM', (200, -1100), b.math('MULTIPLY_ADD', (0, -1100), one_sided, 2.0, -1.0), 0.0)
    t = b.switch('FLOAT', (400, -900), both_free, one_sided, centered)

    t_power = b.math('POWER', (600, -900), t, gi["Taper Power"])
    tip_loss = b.math('SUBTRACT', (600, -1100), 1.0, gi["Tip Width"])
    tapered = b.math('MULTIPLY_ADD', (800, -900), t_power, b.math('MULTIPLY', (800, -1100), tip_loss, -1.0), 1.0, label="taper")
    return b.switch('FLOAT', (1000, -900), gi["Taper Ends"], 1.0, tapered)


class FOFUXO_OT_arabesque_add(bpy.types.Operator):
    """Add a modifier that turns the edges of this mesh into an arabesque relief"""

    bl_idname = "object.fofuxo_arabesque_add"
    bl_label = "Arabesque"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            cls.poll_message_set("Active object must be a mesh")
            return False
        return True

    def execute(self, context):
        group = ensure_group()
        modifier = context.object.modifiers.new(name=GROUP_NAME, type='NODES')
        modifier.node_group = group
        return {'FINISHED'}


classes = (FOFUXO_OT_arabesque_add,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.app.translations.register(__name__, TRANSLATIONS)


def unregister():
    bpy.app.translations.unregister(__name__)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
