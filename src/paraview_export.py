# -*- coding: utf-8 -*-
"""
Created on Wed Apr  1 09:55:10 2026

@author: NItm
"""

# src/paraview_export.py

import os
import numpy as np
import meshio


def build_animation_vtu(params, disp_file, drift_file, out_dir="results/animation"):

    os.makedirs(out_dir, exist_ok=True)

    # --- Geometry reconstruction ---
    x_coords = params["x_coords"]
    y_coords = params["y_coords"]
    z_coords = params["z_coords"]

    nx, ny, nz = len(x_coords), len(y_coords), len(z_coords)

    def node_index(ix, iy, iz):
        return ix + nx*iy + nx*ny*iz

    # --- Node coordinates ---
    node_coords = []
    for iz, z in enumerate(z_coords):
        for iy, y in enumerate(y_coords):
            for ix, x in enumerate(x_coords):
                node_coords.append([x, y, z])
    node_coords = np.array(node_coords)

    # --- Connectivity ---
    connectivity = []

    # Columns
    for iz in range(nz-1):
        for iy in range(ny):
            for ix in range(nx):
                connectivity.append([
                    node_index(ix, iy, iz),
                    node_index(ix, iy, iz+1)
                ])

    # Beams X
    for iz in range(1, nz):
        for iy in range(ny):
            for ix in range(nx-1):
                connectivity.append([
                    node_index(ix, iy, iz),
                    node_index(ix+1, iy, iz)
                ])

    # Beams Y
    for iz in range(1, nz):
        for ix in range(nx):
            for iy in range(ny-1):
                connectivity.append([
                    node_index(ix, iy, iz),
                    node_index(ix, iy+1, iz)
                ])

    connectivity = np.array(connectivity)

    # --- Load data ---
    if not os.path.exists(disp_file):
        raise FileNotFoundError(f"Missing: {disp_file}")

    if not os.path.exists(drift_file):
        raise FileNotFoundError(f"Missing: {drift_file}")
    try:
        disp = np.loadtxt(disp_file)
        drift = np.loadtxt(drift_file)
    except Exception as e:
        print(f"❌ Error reading files: {e}")
        return
    # ✅ Ensure 2D
    if disp.ndim == 1:
        disp = disp.reshape(1, -1)
    
    if drift.ndim == 1:
        drift = drift.reshape(1, -1)
    n_nodes = node_coords.shape[0]
    
    # ✅ NEW
    n_steps = min(disp.shape[0], drift.shape[0])
    if n_steps == 0:
        print("❌ No valid time steps for animation")
        return
    max_frames = 50
    indices = np.unique(np.linspace(0, n_steps-1, max_frames, dtype=int))
    
    for frame_id, i in enumerate(indices):
    
        if i >= disp.shape[0] or i >= drift.shape[0]:
            continue
    
        d_raw = disp[i, 1:]
        if len(d_raw) != n_nodes * 3:
            print(f"⚠ Skipping frame {i} due to size mismatch")
            continue
    
        d = d_raw.reshape(n_nodes, 3)
        deformed = node_coords + d
    
        drift_t = drift[i, 1:]
    
        if len(drift_t) == 0:
            drift_t = np.zeros(nz)
    
        node_drift = np.zeros(n_nodes)
        for iz in range(nz):
            val = drift_t[min(iz, len(drift_t)-1)]
            for iy in range(ny):
                for ix in range(nx):
                    idx = node_index(ix, iy, iz)
                    node_drift[idx] = val
    
        mesh = meshio.Mesh(
            points=deformed,
            cells=[("line", connectivity)],
            point_data={"Drift": node_drift}
        )
    
        meshio.write(os.path.join(out_dir, f"frame_{frame_id:04d}.vtu"), mesh)

    print("✔ VTU animation files created")


def generate_pvsm(out_dir="results/animation"):

    pvsm_path = os.path.join(out_dir, "animation.pvsm")

    # minimal state file
    content = f"""
<ParaView>
  <ServerManagerState>
    <Proxy group="sources" type="XMLUnstructuredGridReader" id="1">
      <Property name="FileName" number_of_elements="1">
        <Element index="0" value="{out_dir}/frame_0000.vtu"/>
      </Property>
    </Proxy>
  </ServerManagerState>
</ParaView>
"""

    with open(pvsm_path, "w") as f:
        f.write(content)

    print(f"✔ PVSM file created at: {pvsm_path}")