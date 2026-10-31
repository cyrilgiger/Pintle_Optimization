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
N_o = 21                # [-]  , Number of orifices in each row
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
# Located on above x-axis, starting at midpoint of botto5m arc on the exterior surface
dy15 = r_o - pt2[1]
pt15 = (pt2[0] + dy15 * np.tan(a_o), r_o, 0)

pt16 = (pt15[0] - np.cos(a_o)*w_b/2, pt15[1] + np.sin(a_o)*w_b/2, w_b/2)

pt17 = (pt15[0] - np.cos(a_o)*(l_b - w_b/2), pt15[1] + np.sin(a_o)*(l_b -w_b/2), w_b/2)

pt18 = (pt15[0] - np.cos(a_o)*l_b, pt15[1] + np.sin(a_o)*l_b, 0)

pt19 = (pt17[0], pt17[1], -w_b/2)

pt20 = (pt16[0], pt16[1], -w_b/2)


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
geompy.addToStudy(face_b, "orifice_face_bottom")

#%% Revolve x-degrees around X-axis

phi_seg = 2*np.pi / (2*N_o)
N_seg = np.floor(np.pi/2 / phi_seg)
rev_angle = N_seg * phi_seg

axis_x = geompy.MakeVectorDXDYDZ(1.0, 0.0, 0.0)

half_angle = rev_angle / 2

face_e_centered = geompy.MakeRotation(face_e, axis_x, -half_angle)
face_i_centered = geompy.MakeRotation(face_i, axis_x, -half_angle)

rev_e = geompy.MakeRevolution(face_e_centered, axis_x, rev_angle)
rev_i = geompy.MakeRevolution(face_i_centered, axis_x, rev_angle)

rev_comb = geompy.MakeCompound([rev_e, rev_i])
geompy.addToStudy(rev_comb, "Pintle_Bulk_Fluid_Domains")

if salome.sg.hasDesktop():
    salome.sg.updateObjBrowser()

#%%
