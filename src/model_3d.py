# src/model_3d.py
#
# 3D RC frame model in SI units using OpenSeesPy.
    
import openseespy.opensees as ops
import numpy as np
from .materials_rc_si import define_rc_materials_si
from .sections_rc_si import build_rc_rect_section

#-----------------------------------------------------
def build_3d_model(params):
    """
    Build 3D RC frame model in SI.

    Returns:
      dict with node_tag function, roof_nodes, base_nodes, story_nodes, and coords.
    """
    print("MODEL: start")
    ops.wipe()
    ops.wipeAnalysis()
    ops.model('basic', '-ndm', 3, '-ndf', 6)

    # --- Materials ---
    print("MODEL: materials")
    mats = define_rc_materials_si()
    coreID  = mats["conc_core"]
    coverID = mats["conc_cover"]
    steelID = mats["steel"]

    # --- Sections ---
    print("MODEL: materials")
    sec_col_tag  = 1
    sec_beam_tag = 2
    print("MODEL: beam section")
    HSec_col = params["col_depth"]
    BSec_col = params["col_width"]
    coverH   = params["cover_y"]
    coverB   = params["cover_z"]

    build_rc_rect_section(
        sec_col_tag,
        HSec_col, BSec_col,
        coverH, coverB,
        coreID, coverID, steelID,
        params["col_numBarsTop"], params["col_barAreaTop"],
        params["col_numBarsBot"], params["col_barAreaBot"],
        params["col_numBarsIntTot"], params["col_barAreaInt"],
        params["nfCoreY"], params["nfCoreZ"],
        params["nfCoverY"], params["nfCoverZ"]
    )

    HSec_beam = params["beam_depth"]
    BSec_beam = params["beam_width"]
    print("MODEL: beam section")
    build_rc_rect_section(
        sec_beam_tag,
        HSec_beam, BSec_beam,
        coverH, coverB,
        coreID, coverID, steelID,
        params["beam_numBarsTop"], params["beam_barAreaTop"],
        params["beam_numBarsBot"], params["beam_barAreaBot"],
        params["beam_numBarsIntTot"], params["beam_barAreaInt"],
        params["nfCoreY"], params["nfCoreZ"],
        params["nfCoverY"], params["nfCoverZ"]
    )

    # --- Geometry ---
    print("MODEL: integration")
    n_stories      = params["n_stories"]
    story_heights  = params["story_heights"]
    n_bays_x       = params["n_bays_x"]
    n_bays_y       = params["n_bays_y"]
    bay_lengths_x  = params["bay_lengths_x"]
    bay_lengths_y  = params["bay_lengths_y"]
    print("MODEL: integration")
    x_coords = [0.0]
    for L in bay_lengths_x:
        x_coords.append(x_coords[-1] + L)
    y_coords = [0.0]
    for L in bay_lengths_y:
        y_coords.append(y_coords[-1] + L)
    z_coords = [0.0]
    for h in story_heights:
        z_coords.append(z_coords[-1] + h)

    nx = len(x_coords)
    ny = len(y_coords)
    nz = len(z_coords)

    def node_tag(ix, iy, iz):
        # simple mapping
        return 1 + ix + nx * iy + nx * ny * iz

    # Nodes
    for iz, z in enumerate(z_coords):
        for iy, y in enumerate(y_coords):
            for ix, x in enumerate(x_coords):
                ops.node(node_tag(ix, iy, iz), x, y, z)

    # Fix base nodes (z=0)
    print("MODEL: fixities")
    for iy, y in enumerate(y_coords):
        for ix, x in enumerate(x_coords):
            ops.fix(node_tag(ix, iy, 0), 1, 1, 1, 1, 1, 1)

    # --- Beam integration (ADD THIS BLOCK) ---
    col_integration_tag = 1
    beam_integration_tag = 2

    ops.beamIntegration('Legendre', col_integration_tag, sec_col_tag, 5)
    ops.beamIntegration('Legendre', beam_integration_tag, sec_beam_tag, 5)    
  
    # Column transformation
    print("MODEL: transformations")
    col_transf_tag = 100
    ops.geomTransf('PDelta', col_transf_tag, 0.0, 1.0, 0.0)
    #ops.geomTransf('Linear', col_transf_tag, 1.0, 0.0, 0.0)

    elem_tag = 1
    # Columns (vertical)
    print("MODEL: transformations")
    for iz in range(nz - 1):
        for iy in range(ny):
            for ix in range(nx):
                n_bot = node_tag(ix, iy, iz)
                n_top = node_tag(ix, iy, iz + 1)
                ops.element('forceBeamColumn', elem_tag, n_bot, n_top, 
                            col_transf_tag, col_integration_tag)
                elem_tag += 1
   
    # Beam transformation
    beamX_transf_tag = 200
    ops.geomTransf('Linear', beamX_transf_tag, 0.0, 1.0, 0.0)

    # Beams in X at each floor
    print("MODEL: beams X")
    for iz in range(1, nz):
        for iy in range(ny):
            for ix in range(nx - 1):
                n1 = node_tag(ix,   iy, iz)
                n2 = node_tag(ix+1, iy, iz)
                ops.element('forceBeamColumn', elem_tag, n1, n2, 
                            beamX_transf_tag, beam_integration_tag)
                elem_tag += 1

    beamY_transf_tag = 300
    ops.geomTransf('Linear', beamY_transf_tag, 1.0, 0.0, 0.0)
    # Beams in Y at each floor
    print("MODEL: beams Y")
    for iz in range(1, nz):
        for ix in range(nx):
            for iy in range(ny - 1):
                n1 = node_tag(ix, iy,   iz)
                n2 = node_tag(ix, iy+1, iz)
                ops.element('forceBeamColumn', elem_tag, n1, n2, 
                            beamY_transf_tag, beam_integration_tag)
                elem_tag += 1

    # Lumped mass at non-base nodes
    print("MODEL: mass")
    mnode = params["mass_per_node"]
    for iz in range(1, nz):
        for iy in range(ny):
            for ix in range(nx):
                ops.mass(node_tag(ix, iy, iz),
                         mnode, mnode, mnode, 0.0, 0.0, 0.0, 0.0)

    # Node groups
    roof_nodes = []
    base_nodes = []
    story_nodes = []

    top_iz = nz - 1
    for iy in range(ny):
        for ix in range(nx):
            base_nodes.append(node_tag(ix, iy, 0))
            roof_nodes.append(node_tag(ix, iy, top_iz))
    # Compute first few modes
    n_modes = 3
    eigenvalues = ops.eigen(n_modes)

    omegas = np.sqrt(eigenvalues)
    periods = 2 * np.pi / omegas

    print("\nEigen Periods:")
    roof_node = roof_nodes[0]

    mode_dirs = []
    for i, T in enumerate(periods):
        print(f"Mode {i+1}: T = {T:.4f} sec")


    for mode in range(1, n_modes+1):

        ux = ops.nodeEigenvector(roof_node, mode, 1)  # X
        uy = ops.nodeEigenvector(roof_node, mode, 2)  # Y

        if abs(ux) > abs(uy):
            mode_dirs.append("X")
        else:
            mode_dirs.append("Y")

        print(f"Mode {mode}: ux={ux:.4e}, uy={uy:.4e} → {mode_dirs[-1]}")    
    T1_x = None
    T1_y = None

    for i in range(n_modes):
        if mode_dirs[i] == "X" and T1_x is None:
            T1_x = periods[i]
        if mode_dirs[i] == "Y" and T1_y is None:
            T1_y = periods[i]

    print(f"\n✔ T1_x = {T1_x:.4f} sec")
    print(f"✔ T1_y = {T1_y:.4f} sec")

    # One representative node per floor (x=0, y=0)
    for iz in range(1, nz):
        story_nodes.append(node_tag(0, 0, iz))

    return {
    "node_tag": node_tag,
    "roof_nodes": roof_nodes,
    "base_nodes": base_nodes,
    "story_nodes": story_nodes,
    "x_coords": x_coords,
    "y_coords": y_coords,
    "z_coords": z_coords,
    "T1_x": T1_x,
    "T1_y": T1_y
    }
    print("MODEL: completed")