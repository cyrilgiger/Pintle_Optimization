import numpy as np


def get_dim_from_non_dim(
        *,
        pcr, # pintle to chamber diameter ratio
        skd, # skip distance
        gpr, # guide to pintle radius ratio
        tgr, # top to guide radius ratio
        wpr, # wall-thickness to pintle ratio
        N_o, # number of orifices in each row
        bf,  # blockage factor
        sar, # bottom to total slit area ratio
        art, # top slit aspect ratio
        arb, # bottom slit aspect ratio
        rsl, # row-distance to pintle length ratio
        a_i, # injection angle fluid guide
        a_o, # orifice angle

        pdr, # pressure drop to chamber pressure ratio
        mdf, # fuel mass flow rate
        rof, # fuel density
        Cdf, # fuel annulus discharge coefficient

        D_d, # domain diameter (chamber diameter)
        p_c, # chamber pressure
        L_d, # domain length
        L_x, # domain backwards extension
    ):

    # Pintle overall_______________________________________
    D_p = pcr * D_d # pintle diameter
    L_p = skd * D_p # pintle length

    r_g = D_p / (2*gpr) # guide radius
    r_t = tgr * r_g     # guide top radius

    w_p = wpr * D_p / 2 # wall thickness

    # Orifices_____________________________________________
    K = np.sqrt((sar * (art + np.pi/4 - 1)) / ((1-sar)*(arb + np.pi/4 - 1)))

    w_t = 1/(1+K) * np.pi * D_p/N_o * bf # top orifice width
    w_b = K*w_t                          # bottom orifice width
    l_t = art * w_t                      # top orifice length
    l_b = arb * w_b                      # bottom orifice length
    d_r = rsl * L_p                      # row spacing

    # Fuel annulus_________________________________________
    dp = pdr * p_c
    Af = mdf / (Cdf * np.sqrt(2*rof*dp))
    t_a = np.sqrt((D_p/2)**2 + Af / np.pi) - D_p/2

    dim_dict = {"D_p": D_p, "L_p": L_p, "r_g": r_g, "r_t": r_t, "w_p": w_p, "a_i": a_i,
                "w_t": w_t, "l_t": l_t, "w_b": w_b, "l_b": l_b, "d_r": d_r, "t_a": t_a, "a_o": a_o, "N_o": N_o,
                "D_d": D_d, "L_d": L_d, "L_x": L_x}

    return dim_dict

def verify_physics(
        *,
        N_o, # number of orifices in each row
        w_t, # top slit width
        l_t, # top slit length
        w_b, # bottom slit width
        l_b, # bottom slit length
        Cdo, # oxidizer orifice discharge coefficient
        roo, # oxidizer density
        mdo, # oxidizer mass flow rate
        rof, # fuel density
        mdf, # fuel mass flow rate
        t_a, # fuel annulus gap thickness
        D_p, # pintle outer diameter
        a_i, # injection angle

        b_pdr, # target pressure drop ratio bounds [min, max]
        b_thb, # target spray angle bounds [min, max]

        p_c, # chamber pressure
    ):
    
    mssg = []
    # Check LOx predicted pressure drop________________________________________
    A_b = w_b * (l_b - w_b) + np.pi / 4 * w_b**2
    A_t = w_t * (l_t - w_t) + np.pi / 4 * w_t**2
    dp = mdo**2 / (Cdo**2 * (N_o*(A_b + A_t))**2 * 2*roo)
    pdr = dp / p_c
    ox_passed = b_pdr[0] <= pdr <= b_pdr[1]
    if not ox_passed: mssg.append(f"LOx dp FAILED: PDR {pdr:.3f} out of bounds {b_pdr}")

    # Check expected outer spray angle_________________________________________
    v_o = mdo / (roo * (N_o * (A_b + A_t)))
    v_f = mdf / (rof * np.pi * t_a * (D_p + t_a))
    mdf_e_t = w_t / (np.pi * D_p) * mdf
    mdf_e_b = w_b / (np.pi * D_p) * mdf
    mdo_e_t = A_t / (N_o * (A_b + A_t)) * mdo
    mdo_e_b = A_b / (N_o * (A_b + A_t)) * mdo
    lmr_t = (np.cos(a_i) * mdo_e_t * v_o) / (np.sin(a_i) * mdo_e_t * v_o + mdf_e_t * v_f)
    lmr_b = (np.cos(a_i) * mdo_e_b * v_o) / (np.sin(a_i) * mdo_e_b * v_o + mdf_e_b * v_f)
    th_t = np.acos(1 / (1 + lmr_t))
    th_b = np.acos(1 / (1 + lmr_b))
    th_t_passed = b_thb[0] <= th_t <= b_thb[1]
    th_b_passed = b_thb[0] <= th_b <= b_thb[1]
    if not th_t_passed: mssg.append(f"Spray FAILED: Top angle θ: {float(np.rad2deg(th_t)):.3f} out of bounds [{np.rad2deg(b_thb[0]):.1f}, {np.rad2deg(b_thb[1]):.1f}]")
    if not th_b_passed: mssg.append(f"Spray FAILED: Bottom angle θ: {float(np.rad2deg(th_b)):.3f} out of bounds [{np.rad2deg(b_thb[0]):.1f}, {np.rad2deg(b_thb[1]):.1f}]")

    # Compile results__________________________________________________________
    passed_arr = [ox_passed, th_t_passed, th_b_passed]
    passed_all = all(passed_arr)

    return passed_all, passed_arr, mssg