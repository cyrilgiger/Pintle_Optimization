#%% Imports
import math
import os
import numpy as np
from pathlib import Path
import salome
from salome.geom import geomBuilder # type: ignore
from salome.smesh import smeshBuilder # type: ignore
import SMESH

salome.salome_init()
geompy = geomBuilder.New()
smeshpy = smeshBuilder.New()

#%% Inputs

# Pintle Post Values
    # Overall Dimensions
L_p = 55.5e-3           # [m]  , Skip length of pintle post
D_p = 35e-3             # [m]  , Pintle post external diameter
w_p = 2.5e-3            # [m]  , Pintle post wall thickness
    # Fluid Guide
a_i = 15 * np.pi / 180  # [rad], Guide angle
a_c = 20 * np.pi / 180  # [rad], Guide center crossing angle
r_g = 15.0e-3           # [m]  , Guide blend radius
r_t = 1.0e-3            # [m]  , Guide top radius
    # Orifice Dimensions and Values
N_o = 25                # [-]  , Number of orifices in each row
a_o = 20 * np.pi / 180  # [rad], Orifice angle
w_t = 1.2e-3            # [m]  , Orifice slit width top row
l_t = 5.0e-3            # [m]  , Orifice slit length top row
w_b = 1.0e-3            # [m]  , Orifice slit width bottom row
l_b = 2.0e-3            # [m]  , Orifice slit length bottom row
d_r = 4.0e-3            # [m]  , Orifice row spacing

# Pintle Annulus Values
t_a = 0.90e-3           # [m]  , Fuel annulus thickness

# Domain Dimensions
L_d = 100.00e-3         # [m]  , Domain length
D_d = 110.85e-3         # [m]  , Domain diameter
L_x = 10e-3             # [m]  , extension of ox and f channels in -x

#%% Define geometry points

r_i = D_p / 2.0 - w_p # internal radius
r_o = D_p / 2.0       # external radius

# Interal Geometery________________________________________________
# start top left going clock wise around the interior of the pintle
pt1 = (-L_x, r_i, 0)

dx2 = w_p * (1/np.cos(a_i) + np.tan(a_i))
pt2 = (L_p - dx2, r_i, 0)

h = r_g * np.cos(a_c)
dy3 = r_i - h + r_g * np.sin(a_i)
dx3 = dy3 * np.tan(a_i)
pt3 = (pt2[0] - dx3, pt2[1] - dy3, 0)

dxa1 = r_g * np.cos(a_i)
a1c = (pt3[0] - dxa1, h, 0)

y4 = h * r_t / (r_g + r_t)
xi = np.sqrt((r_g + r_t)**2 - h**2)
dx4 = xi * r_t / (r_g + r_t)
pt4 = (a1c[0] + xi - dx4, y4, 0)

a2c = (a1c[0] + xi, 0, 0)

pt5 = (a2c[0] - r_t, 0, 0)

pt6 = (-L_x, 0, 0)

# External Geometery_________________________________________________________________________
# start at outer edge of annular inlet going clock wise around the exterior pintle and domain
pt7 = (-L_x, r_o + t_a, 0)

pt8 = (0, r_o + t_a, 0)

pt9 = (0, D_d/2, 0)

pt10 = (L_d, D_d/2, 0)

pt11 = (L_d, 0, 0)

pt12 = (L_p, 0, 0)

pt13 = (L_p, r_o, 0)

pt14 = (-L_x, r_o, 0)

# Bottom Row Orifice Geometery_______________________________________________________
# Located on above x-axis, starting at midpoint of bottom arc on the exterior surface
dy15 = r_o - pt2[1]
pt15 = (pt2[0] + dy15 * np.tan(a_o), r_o, 0)

pt16 = (pt15[0] - np.cos(a_o) * w_b / 2, pt15[1] + np.sin(a_o) * w_b / 2, w_b / 2)

pt17 = (pt15[0] - np.cos(a_o)*(l_b - w_b/2), pt15[1] + np.sin(a_o)*(l_b -w_b/2), w_b/2)

pt18 = (pt15[0] - np.cos(a_o)*l_b, pt15[1] + np.sin(a_o)*l_b, 0)

pt19 = (pt17[0], pt17[1], -w_b/2)

pt20 = (pt16[0], pt16[1], -w_b/2)

# Top Row Orifice Geometery_____________________________________________________________________________
# Located on above x-axis (for construction), starting at midpoint of bottom arc on the exterior surface
pt21 = (pt15[0] - d_r, pt15[1], 0)

pt22 = (pt21[0] - np.cos(a_o) * w_t / 2, pt21[1] + np.sin(a_o) * w_t / 2, w_t / 2)

pt23 = (pt21[0] - np.cos(a_o) * (l_t - w_t / 2), pt21[1] + np.sin(a_o) * (l_t - w_t / 2), w_t / 2)

pt24 = (pt21[0] - np.cos(a_o) * l_t, pt21[1] + np.sin(a_o) * l_t, 0)

pt25 = (pt23[0], pt23[1], -w_t / 2)

pt26 = (pt22[0], pt22[1], -w_t / 2)

#%% Build geometry

# Interal Geometry____________________________________________________________________________________
pts_i = {"pt1": pt1, "pt2": pt2,"pt3": pt3, "a1c": a1c, "pt4": pt4, "a2c": a2c, "pt5": pt5,"pt6": pt6}
vrt_i = {name: geompy.MakeVertex(*point) for name, point in pts_i.items()}
# Each segment is (start, end, arc center); a missing center means a straight line.
seg_i = [
    ("pt1", "pt2", None),
    ("pt2", "pt3", None),
    ("pt3", "pt4", "a1c"),
    ("pt4", "pt5", "a2c"),
    ("pt5", "pt6", None),
    ("pt6", "pt1", None),
]
edge_i = []
for start, end, center in seg_i:
    if center is None:
        edge = geompy.MakeLineTwoPnt(vrt_i[start], vrt_i[end])
    else:
        edge = geompy.MakeArcCenter(
            vrt_i[center], vrt_i[start], vrt_i[end], False
        )
    edge_i.append(edge)
wire_i = geompy.MakeWire(edge_i)
face_i = geompy.MakeFaceWires([wire_i], True)

# External Geometry____________________________________________________________________________________________
pts_e = {"pt7": pt7, "pt8": pt8,"pt9": pt9, "pt10": pt10, "pt11": pt11, "pt12": pt12, "pt13": pt13, "pt14": pt14}
vrt_e = {name: geompy.MakeVertex(*point) for name, point in pts_e.items()}
# Each segment is (start, end, arc center); a missing center means a straight line.
seg_e = [
    ("pt7", "pt8", None),
    ("pt8", "pt9", None),
    ("pt9", "pt10", None),
    ("pt10", "pt11", None),
    ("pt11", "pt12", None),
    ("pt12", "pt13", None),
    ("pt13", "pt14", None),
    ("pt14", "pt7", None),
]
edge_e = []
for start, end, center in seg_e:
    if center is None:
        edge = geompy.MakeLineTwoPnt(vrt_e[start], vrt_e[end])
    else:
        edge = geompy.MakeArcCenter(
            vrt_e[center], vrt_e[start], vrt_e[end], False
        )
    edge_e.append(edge)
wire_e = geompy.MakeWire(edge_e)
face_e = geompy.MakeFaceWires([wire_e], True)

# Bottom Orifice____________________________________________________________________________________________
pts_b = {"pt15": pt15, "pt16": pt16, "pt17": pt17, "pt18": pt18, "pt19": pt19, "pt20": pt20}
vrt_b = {name: geompy.MakeVertex(*point) for name, point in pts_b.items()}
# Each segment is (start, end, arc midpoint); a missing center means a straight line.
seg_b = [
    ("pt16", "pt17", None),
    ("pt17", "pt19", "pt18"),
    ("pt19", "pt20", None),
    ("pt20", "pt16", "pt15"),
]
edge_b = []
for start, end, center in seg_b:
    if center is None:
        edge = geompy.MakeLineTwoPnt(vrt_b[start], vrt_b[end])
    else:
        edge = geompy.MakeArc(
            vrt_b[start], vrt_b[center], vrt_b[end], False
        )
    edge_b.append(edge)
wire_b = geompy.MakeWire(edge_b)
face_b = geompy.MakeFaceWires([wire_b], True)

# Top Orifice____________________________________________________________________________________________
pts_t = {"pt21": pt21, "pt22": pt22, "pt23": pt23, "pt24": pt24, "pt25": pt25, "pt26": pt26}
vrt_t = {name: geompy.MakeVertex(*point) for name, point in pts_t.items()}
# Each segment is (start, end, arc midpoint); a missing center means a straight line.
seg_t = [
    ("pt22", "pt23", None),
    ("pt23", "pt25", "pt24"),
    ("pt25", "pt26", None),
    ("pt26", "pt22", "pt21"),
]
edge_t = []
for start, end, center in seg_t:
    if center is None:
        edge = geompy.MakeLineTwoPnt(vrt_t[start], vrt_t[end])
    else:
        edge = geompy.MakeArc(
            vrt_t[start], vrt_t[center], vrt_t[end], False
        )
    edge_t.append(edge)
wire_t = geompy.MakeWire(edge_t)
face_t = geompy.MakeFaceWires([wire_t], True)

#%% Revolve Bulk volumes x-degrees around X-axis

phi_seg = 2*np.pi / N_o
N_seg = np.floor(np.pi/2 / phi_seg)
rev_angle = N_seg * phi_seg

axis_x = geompy.MakeVectorDXDYDZ(1.0, 0.0, 0.0)

half_angle = rev_angle / 2

face_e_centered = geompy.MakeRotation(face_e, axis_x, -half_angle)
face_i_centered = geompy.MakeRotation(face_i, axis_x, -half_angle)

rev_e = geompy.MakeRevolution(face_e_centered, axis_x, rev_angle)
rev_i = geompy.MakeRevolution(face_i_centered, axis_x, rev_angle)

if salome.sg.hasDesktop():
    salome.sg.updateObjBrowser()

#%% Create Pintle Orifices

# Channels direction
ch_dir = geompy.MakeVectorDXDYDZ(-np.sin(a_o), -np.cos(a_o), 0.0)

# Bottom Orifice___________________________________________________________________________________
# Extrude center orifice
ch_len_b = w_p / np.cos(a_o) + l_b * np.tan(a_o)
ch_b = geompy.MakePrismVecH(face_b, ch_dir, ch_len_b)

# Pattern clock and anti-clockwise
# if N_seg odd: ... x x 0 x x ..., if N_seg even: < x ... x 0 x ... x > (i.e. end orifices cut in half)
int_N_seg = int(N_seg)
N_half_b = int_N_seg // 2 if int_N_seg % 2 == 0 else (int_N_seg - 1) // 2
ch_an_b = [k * phi_seg for k in range(-N_half_b, N_half_b + 1)]
chs_b = geompy.MakeCompound([geompy.MakeRotation(ch_b, axis_x, angle) for angle in ch_an_b])

# Top Orifice______________________________________________________________________________________
# Extrude top orifice at center location
ch_len_t = w_p / np.cos(a_o) + l_t * np.tan(a_o)
ch_t = geompy.MakePrismVecH(face_t, ch_dir, ch_len_t)

# Rotate orifice by half of segment angle to: ... x | 0 ... (| center marker, 0 this orifice)
ch_t_off = geompy.MakeRotation(ch_t, axis_x, phi_seg / 2)

# Pattern clock and anti-clockwise
# if N_seg odd: < x ... x | 0 x ... >, if N_seg even: x ... x | 0 x ... x
N_half_t = int_N_seg // 2 if int_N_seg % 2 == 0 else (int_N_seg + 1) // 2
ch_an_t = [k * phi_seg for k in range(-N_half_t, N_half_t)]
chs_t = geompy.MakeCompound([geompy.MakeRotation(ch_t_off, axis_x, angle) for angle in ch_an_t])

# Clip edge orifices to be within domain___________________________________________________________
clip_points = [(-L_x, 0, 0),(L_d, 0, 0),(L_d, D_d/2, 0),(-L_x, D_d/2, 0)]
clip_vertices = [geompy.MakeVertex(*point) for point in clip_points]
clip_edges = [geompy.MakeLineTwoPnt(clip_vertices[i], clip_vertices[(i + 1) % 4]) for i in range(4)]
clip_face = geompy.MakeFaceWires([geompy.MakeWire(clip_edges)], True)

clip_face_centered = geompy.MakeRotation(clip_face, axis_x, -half_angle)
sector_clip = geompy.MakeRevolution(clip_face_centered, axis_x, rev_angle)

# Keep only the channel portions inside the sector
chs_b_clip = geompy.MakeCommon(chs_b, sector_clip)
chs_t_clip = geompy.MakeCommon(chs_t, sector_clip)

# Boolean combine all domains into one_____________________________________________________________
fluid_domain = geompy.MakeFuse(rev_i, rev_e)
fluid_domain = geompy.MakeFuse(fluid_domain, chs_b_clip)
fluid_domain = geompy.MakeFuse(fluid_domain, chs_t_clip)

geompy.addToStudy(fluid_domain, "fluid_domain")

#%% Create named boundary groups and export multi-solid ASCII STL

FACE = geompy.ShapeType["FACE"]


def get_final_faces(source_shape):
    """Find final-domain faces that correspond to a source shape."""
    in_place = geompy.GetInPlace(fluid_domain, source_shape)
    return geompy.SubShapeAll(in_place, FACE)


def get_revolved_faces(edges):
    """Map revolutions of profile edges onto the final fluid-domain faces."""
    faces = []
    for edge in edges:
        centered_edge = geompy.MakeRotation(edge, axis_x, -half_angle)
        surface = geompy.MakeRevolution(centered_edge, axis_x, rev_angle)
        faces.extend(get_final_faces(surface))
    return faces

def face_lies_on_sector_plane(face, theta):
    VERTEX = geompy.ShapeType["VERTEX"]
    vertices = geompy.SubShapeAll(face, VERTEX)
    plane_tol = 1e-7  # model units: meters
    if not vertices:
        return False

    sin_theta = math.sin(theta)
    cos_theta = math.cos(theta)

    for vertex in vertices:
        _, y, z = geompy.PointCoordinates(vertex)

        # Distance from the X-axis plane at angle theta.
        if abs(z * cos_theta - y * sin_theta) > plane_tol:
            return False

        # Keep the positive-radius side, not the opposite half-plane.
        if y * cos_theta + z * sin_theta < -plane_tol:
            return False

    return True


def make_face_group(name, faces):
    """Create a GEOM face group, deduplicating final-domain subshapes."""
    group = geompy.CreateGroup(fluid_domain, FACE)
    added_ids = set()

    for face in faces:
        face_id = geompy.GetSubShapeID(fluid_domain, face)
        if face_id > 0 and face_id not in added_ids:
            geompy.AddObject(group, face_id)
            added_ids.add(face_id)

    if not added_ids:
        raise RuntimeError(f"Boundary group {name!r} is empty")

    geompy.addToStudyInFather(fluid_domain, group, name)
    print(f"{name}: {len(added_ids)} face(s)")
    return group


# Revolve the profile edges and map those surfaces onto the final Boolean result.
wall_i_edges = [
    *edge_i[:4],
    edge_e[0],  # outer boundary of the fuel annulus
    edge_e[5],  # injector end face
    edge_e[6],  # outside of the pintle
]

wall_ch_edges = [
    edge_e[1],  # injector face at x = 0
    edge_e[2]   # cylindrical chamber wall
]

patch_faces = {
    "wall_i": get_revolved_faces(wall_i_edges),
    "wall_ch": get_revolved_faces(wall_ch_edges),
    "inlet_o": get_revolved_faces([edge_i[5]]), # oxygen inlet plane
    "inlet_f": get_revolved_faces([edge_e[7]]), # fuel inlet plane
    "outlet": get_revolved_faces([edge_e[3]]),  # outlet plane
}

# The channel side faces become the orifice walls after the channel volumes
# are fused into the fluid domain. Map the un-clipped patterned cutters so
# the clip-created periodic faces are not intentionally treated as walls.
channel_faces = []
for channels in (chs_b, chs_t):
    for cutter_face in geompy.SubShapeAll(channels, FACE):
        channel_faces.extend(get_final_faces(cutter_face))
patch_faces["wall_orifice"] = channel_faces

# The cross-section faces at the two angular ends form the periodic patches.
final_faces = geompy.SubShapeAll(fluid_domain, FACE)
for patch_name, theta in (
    ("periodic_0", -half_angle),
    ("periodic_rev", half_angle),
):
    periodic_faces = [
        face for face in final_faces
        if face_lies_on_sector_plane(face, theta)
    ]
    patch_faces[patch_name] = periodic_faces

patch_groups = {
    name: make_face_group(name, faces)
    for name, faces in patch_faces.items()
}

# Export one ASCII STL solid per group, then combine the solids into one file.
output_dir = (
    Path.cwd()
)
output_dir.mkdir(parents=True, exist_ok=True)

name = "pintle"
combined_stl = output_dir / f"{name}.stl"
deflection = 1.0e-5  # model units (metres)

with combined_stl.open("w", encoding="ascii") as outfile:
    for patch_name, group in patch_groups.items():
        temp_stl = output_dir / f"_temp_{patch_name}.stl"

        try:
            geompy.ExportSTL(group, str(temp_stl), True, deflection, True)

            with temp_stl.open("r", encoding="ascii") as infile:
                for line in infile:
                    stripped = line.strip()
                    if stripped.startswith("solid"):
                        outfile.write(f"solid {patch_name}\n")
                    elif stripped.startswith("endsolid"):
                        outfile.write(f"endsolid {patch_name}\n")
                    else:
                        outfile.write(line)
        finally:
            if temp_stl.exists():
                temp_stl.unlink()

print(f"Named STL exported to: {combined_stl}")
# %%
