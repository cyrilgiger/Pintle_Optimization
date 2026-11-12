#%% Imports
import logging
import math
import numpy as np
from pathlib import Path
import salome
from salome.geom import geomBuilder # type: ignore

salome.salome_init()
geompy = geomBuilder.New()
logger = logging.getLogger(__name__)

def build_pintle_stl(
    *,
    L_p,
    D_p,
    w_p,
    a_i,
    r_g,
    r_t,
    N_o,
    a_o,
    w_t,
    l_t,
    w_b,
    l_b,
    d_r,
    t_a,
    L_d,
    D_d,
    L_x,
    output_stl,
):
    """Build the fluid-domain geometry and export named ASCII STL patches.

    All dimensions use meters and all angles use radians. ``output_stl`` must
    be the complete destination path, including the STL filename.
    """
    if a_i > a_o: 
        raise RuntimeError("Orifice angle a_o has to be larger than guide angle")

    #%% Define geometry points

    r_i = D_p / 2.0 - w_p # internal radius
    r_o = D_p / 2.0       # external radius

    # Interal Geometery________________________________________________
    # start top left going clock wise around the interior of the pintle
    pt1 = (-L_x, r_i, 0)

    pt2 = (L_p, r_i, 0)

    a1c = (pt2[0] - r_g * np.cos(a_i), pt2[1] + r_g * np.sin(a_i), 0)

    y3 = a1c[1] * r_t / (r_g + r_t)
    xi = np.sqrt((r_g + r_t)**2 - a1c[1]**2)
    dx3 = xi * r_t / (r_g + r_t)
    pt3 = (a1c[0] + xi - dx3, y3, 0)

    a2c = (a1c[0] + xi, 0, 0)

    pt4 = (a2c[0] - r_t, 0, 0)

    pt5 = (-L_x, 0, 0)

    # External Geometery_________________________________________________________________________
    # start at outer edge of annular inlet going clock wise around the exterior pintle and domain
    pt6 = (-L_x, r_o + t_a, 0)

    pt7 = (0, r_o + t_a, 0)

    pt8 = (0, D_d/2, 0)

    pt9 = (L_d, D_d/2, 0)

    pt10 = (L_d, 0, 0)

    dx11 = np.sqrt((r_g + w_p)**2 - (r_o - a1c[1])**2)
    pt11 = (a1c[0] + dx11, 0, 0)

    pt12 = (pt11[0], r_o, 0)

    pt13 = (-L_x, r_o, 0)

    # Bottom Row Orifice Geometery_______________________________________________________
    # Located on above x-axis, starting at midpoint of bottom arc on the exterior surface
    dy14 = r_o - pt2[1]
    pt14 = (pt2[0] + dy14 * np.tan(a_o), r_o, 0)

    pt15 = (pt14[0] - np.cos(a_o) * w_b / 2, pt14[1] + np.sin(a_o) * w_b / 2, w_b / 2)

    pt16 = (pt14[0] - np.cos(a_o)*(l_b - w_b/2), pt14[1] + np.sin(a_o)*(l_b -w_b/2), w_b/2)

    pt17 = (pt14[0] - np.cos(a_o)*l_b, pt14[1] + np.sin(a_o)*l_b, 0)

    pt18 = (pt16[0], pt16[1], -w_b/2)

    pt19 = (pt15[0], pt15[1], -w_b/2)

    # Top Row Orifice Geometery_____________________________________________________________________________
    # Located on above x-axis (for construction), starting at midpoint of bottom arc on the exterior surface
    pt20 = (pt14[0] - d_r, pt14[1], 0)

    pt21 = (pt20[0] - np.cos(a_o) * w_t / 2, pt20[1] + np.sin(a_o) * w_t / 2, w_t / 2)

    pt22 = (pt20[0] - np.cos(a_o) * (l_t - w_t / 2), pt20[1] + np.sin(a_o) * (l_t - w_t / 2), w_t / 2)

    pt23 = (pt20[0] - np.cos(a_o) * l_t, pt20[1] + np.sin(a_o) * l_t, 0)

    pt24 = (pt22[0], pt22[1], -w_t / 2)

    pt25 = (pt21[0], pt21[1], -w_t / 2)

    #%% Build geometry

    # Interal Geometry____________________________________________________________________________________
    pts_i = {"pt1": pt1, "pt2": pt2, "pt3": pt3, "a1c": a1c, "pt4": pt4, "a2c": a2c, "pt5": pt5}
    vrt_i = {name: geompy.MakeVertex(*point) for name, point in pts_i.items()}
    # Each segment is (start, end, arc center); a missing center means a straight line.
    seg_i = [
        ("pt1", "pt2", None),
        ("pt2", "pt3", "a1c"),
        ("pt3", "pt4", "a2c"),
        ("pt4", "pt5", None),
        ("pt5", "pt1", None),
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

    for name, point in pts_i.items():
        logger.debug("%s: %s", name, point)

    # External Geometry____________________________________________________________________________________________
    pts_e = {"pt6": pt6, "pt7": pt7, "pt8": pt8, "pt9": pt9, "pt10": pt10, "pt11": pt11, "pt12": pt12, "pt13": pt13}
    vrt_e = {name: geompy.MakeVertex(*point) for name, point in pts_e.items()}
    # Each segment is (start, end, arc center); a missing center means a straight line.
    seg_e = [
        ("pt6", "pt7", None),
        ("pt7", "pt8", None),
        ("pt8", "pt9", None),
        ("pt9", "pt10", None),
        ("pt10", "pt11", None),
        ("pt11", "pt12", None),
        ("pt12", "pt13", None),
        ("pt13", "pt6", None),
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

    for name, point in pts_e.items():
        logger.debug("%s: %s", name, point)

    # Bottom Orifice____________________________________________________________________________________________
    pts_b = {"pt14": pt14, "pt15": pt15, "pt16": pt16, "pt17": pt17, "pt18": pt18, "pt19": pt19}
    vrt_b = {name: geompy.MakeVertex(*point) for name, point in pts_b.items()}
    # Each segment is (start, end, arc midpoint); a missing center means a straight line.
    seg_b = [
        ("pt15", "pt16", None),
        ("pt16", "pt18", "pt17"),
        ("pt18", "pt19", None),
        ("pt19", "pt15", "pt14"),
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

    for name, point in pts_b.items():
        logger.debug("%s: %s", name, point)

    # Top Orifice____________________________________________________________________________________________
    pts_t = {"pt20": pt20, "pt21": pt21, "pt22": pt22, "pt23": pt23, "pt24": pt24, "pt25": pt25}
    vrt_t = {name: geompy.MakeVertex(*point) for name, point in pts_t.items()}
    # Each segment is (start, end, arc midpoint); a missing center means a straight line.
    seg_t = [
        ("pt21", "pt22", None),
        ("pt22", "pt24", "pt23"),
        ("pt24", "pt25", None),
        ("pt25", "pt21", "pt20"),
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

    for name, point in pts_t.items():
        logger.debug("%s: %s", name, point)

    #%% Revolve Bulk volumes x-degrees around X-axis

    phi_seg = 2*np.pi / N_o
    N_seg = np.floor(np.pi/2 / phi_seg)
    rev_angle = N_seg * phi_seg

    half_angle = rev_angle / 2

    logger.debug("Angular values:")
    logger.debug("phi_seg: %s", phi_seg)
    logger.debug("N_seg: %s", N_seg)
    logger.debug("rev_angle: %s", rev_angle)
    logger.debug("half_angle: %s", half_angle)

    axis_x = geompy.MakeVectorDXDYDZ(1.0, 0.0, 0.0)

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

    logger.debug("Bottom orifice channel:")
    logger.debug("ch_len_b: %s", ch_len_b)
    logger.debug("int_N_seg: %s", int_N_seg)
    logger.debug("N_half_b: %s", N_half_b)
    logger.debug("ch_an_b: %s (°)", np.degrees(ch_an_b))

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

    logger.debug("Top orifice channel:")
    logger.debug("ch_len_t: %s", ch_len_t)
    logger.debug("N_half_t: %s", N_half_t)
    logger.debug("ch_an_t: %s (°)", np.degrees(ch_an_t))

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
        logger.debug("%s: %s face(s)", name, len(added_ids))
        return group


    # Revolve the profile edges and map those surfaces onto the final Boolean result.
    wall_i_edges = [
        *edge_i[:3],
        edge_e[0],  # outer boundary of the fuel annulus
        edge_e[5],  # injector end face
        edge_e[6],  # outside of the pintle
    ]

    wall_ch_edges = [
        edge_e[2]   # cylindrical chamber wall
    ]

    patch_faces = {
        "wall_i": get_revolved_faces(wall_i_edges),
        "wall_inj_pl": get_revolved_faces([edge_e[1]]), # injector face at x = 0
        "wall_ch": get_revolved_faces(wall_ch_edges),
        "inlet_o": get_revolved_faces([edge_i[4]]),     # oxygen inlet plane
        "inlet_f": get_revolved_faces([edge_e[7]]),     # fuel inlet plane
        "outlet": get_revolved_faces([edge_e[3]]),      # outlet plane
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
    if output_stl is not None:
        combined_stl_path = Path(output_stl).expanduser()
        if not combined_stl_path.is_absolute():
            raise ValueError("output_stl must be an absolute path")
        combined_stl_path.parent.mkdir(parents=True, exist_ok=True)
        deflection = 1.0e-5  # model units (metres)
        with combined_stl_path.open("w", encoding="ascii") as outfile:
            for patch_name, group in patch_groups.items():
                temp_stl = combined_stl_path.parent / f"_temp_{patch_name}.stl"

                try:
                    # Map the model's longitudinal +X axis onto global +Y for export.
                    rotated_group = geompy.MakeRotation(group, axis_x, half_angle)
                    geompy.ExportSTL(rotated_group, str(temp_stl), True, deflection, True)

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

        logger.info("Named STL exported to: %s", combined_stl_path)
        # %%
        return combined_stl_path, rev_angle
    else:
        return None, rev_angle
