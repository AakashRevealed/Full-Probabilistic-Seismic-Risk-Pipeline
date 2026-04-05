# main.py

import os

from src.model_3d import build_3d_model
from src.geometry_gmsh import build_gmsh_building
from src.run_dynamic import run_gravity, run_bidirectional_dynamic
from src.postprocess import postprocess_single_run
from src.paraview_export import build_animation_vtu, generate_pvsm
   
def main():
    # --- Model & geometry parameters (SI units) ---
    params = {
        "n_stories": 3,
        "story_heights": [3.0, 3.0, 3.0],        # m
        "n_bays_x": 2,
        "n_bays_y": 1,
        "bay_lengths_x": [5.0, 5.0],            # m
        "bay_lengths_y": [6.0],                 # m

        # RC section dimensions & reinforcement (example values)
        "col_depth": 0.5,                       # m
        "col_width": 0.5,                       # m
        "beam_depth": 0.4,                      # m
        "beam_width": 0.3,                      # m
        "cover_y": 0.05,                        # m
        "cover_z": 0.05,                        # m

        "col_numBarsTop": 4,
        "col_numBarsBot": 4,
        "col_numBarsIntTot": 4,
        "col_barAreaTop": 0.0005,               # m^2
        "col_barAreaBot": 0.0005,               # m^2
        "col_barAreaInt": 0.0004,               # m^2

        "beam_numBarsTop": 4,
        "beam_numBarsBot": 4,
        "beam_numBarsIntTot": 0,
        "beam_barAreaTop": 0.0004,
        "beam_barAreaBot": 0.0004,
        "beam_barAreaInt": 0.0,

        "nfCoreY": 10,
        "nfCoreZ": 10,
        "nfCoverY": 4,
        "nfCoverZ": 4,

        "mass_per_node": 10000.0,              # kg
        "mesh_size": 1.0                        # m, for Gmsh
    }
    # ✅ ADD THIS BLOCK HERE
    g = 9.81
    n_nodes_per_floor = (params["n_bays_x"] + 1) * (params["n_bays_y"] + 1)
    floor_weight = 3e6
    params["mass_per_node"] = (floor_weight / g) / n_nodes_per_floor
    
    # THEN BUILD MODEL
    model_info = build_3d_model(params)
    print("STEP 1: Building model")
  # ✅ ADD THIS FIRST
    params["T1_x"] = model_info["T1_x"]
    params["T1_y"] = model_info["T1_y"]
   
    print(f"T1_x = {params['T1_x']:.4f}, T1_y = {params['T1_y']:.4f}")
    
    # --------------------Calling PSHA file here------------
# -----------------------------
    print("STEP PSHA START")
    
    import subprocess
    
    # 👉 USE PYTHON FROM PSHA_env (IMPORTANT)
    PSHA_PYTHON = r"C:\Users\NItm\PSHA_env\Scripts\python.exe"
    
    result = subprocess.run(
        [PSHA_PYTHON, "src/all_in_one_psha_spectra.py"],
        capture_output=True,
        text=True
    )
    
    print("PSHA OUTPUT:\n", result.stdout)
    print("PSHA ERROR:\n", result.stderr)
    
    if result.returncode != 0:
        raise RuntimeError("PSHA failed")
    
    print("✔ PSHA DONE")
                
    # --- Bidirectional nonlinear dynamic analysis ---
    print("STEP 3: Dynamic START")

    gm_x_dir = os.path.join("gm", "GM_X")
    gm_y_dir = os.path.join("gm", "GM_Y")
    
    gm_x_files = sorted([f for f in os.listdir(gm_x_dir) if f.endswith(".AT2") or f.endswith(".txt")])
    gm_y_files = sorted([f for f in os.listdir(gm_y_dir) if f.endswith(".AT2") or f.endswith(".txt")])
    
    if len(gm_x_files) != len(gm_y_files):
        raise ValueError("Mismatch in number of GM_X and GM_Y records")
    
    n_gm = len(gm_x_files)
    print(f"Total Ground Motions: {n_gm}")
    # -----------------------------
# RESET SUMMARY FILE (IMPORTANT)
# -----------------------------
    summary_file = os.path.join("results", "EDPs_all.csv")
    
    if os.path.exists(summary_file):
        os.remove(summary_file)
        print("✔ Old EDPs_all.csv removed")
    
    #  LOOP STARTS HERE (ONLY ONE LOOP)
    for i in range(n_gm):
    
        import openseespy.opensees as ops
        print(f"\nRunning GM Pair {i+1}/{n_gm}")
        print(f"X: {gm_x_files[i]}")
        print(f"Y: {gm_y_files[i]}")
    
        #  REBUILD MODEL (CRITICAL)
        model_info = build_3d_model(params)
        # ✅ ADD HERE (RIGHT PLACE)

        params.update({
            "roof_nodes": model_info["roof_nodes"],
            "base_nodes": model_info["base_nodes"],
            "story_nodes": model_info["story_nodes"],
            "x_coords": model_info["x_coords"],
            "y_coords": model_info["y_coords"],
            "z_coords": model_info["z_coords"]
        })
    
        run_gravity(params)
        print("✔ Gravity DONE")
        gm_x = os.path.join(gm_x_dir, gm_x_files[i])
        gm_y = os.path.join(gm_y_dir, gm_y_files[i])
        # ---------------------------------------
# Extract Sa (IM) from GM
# ---------------------------------------
        
        from src.gm_reader import process_ground_motion
        
        gm_data_x = process_ground_motion(gm_x, T=params["T1_x"])
        gm_data_y = process_ground_motion(gm_y, T=params["T1_y"])
        
        Sa_x = gm_data_x["Sa_g"]
        Sa_y = gm_data_y["Sa_g"]
        
        acc_x = gm_data_x["acc"]
        acc_y = gm_data_y["acc"]
        
        dt_x = gm_data_x["dt"]
        dt_y = gm_data_y["dt"] 
        params["Sa_x"] = Sa_x
        params["Sa_y"] = Sa_y
    
        out_dir_i = os.path.join("results", f"GM_{i+1}")    
# ---- RUN DYNAMIC ----
        try:
            run_bidirectional_dynamic(
                params,
                acc_x, acc_y,
                dt_x, dt_y,
                scale_factor=1.0,
                out_dir=out_dir_i
            )
        except Exception as e:
            print(f"❌ Dynamic failed GM {i+1}:", e)
            continue
        
        # ---- DEBUG ----
        print("Sa_x:", params.get("Sa_x"))
        print("Sa_y:", params.get("Sa_y"))
        
        # ---- POSTPROCESS ----
        try:
            postprocess_single_run(
                params,
                results_dir=out_dir_i,
                output_csv=os.path.join(out_dir_i, "EDPs.csv")
            )
        except Exception as e:
            print(f"❌ Postprocess failed GM {i+1}:", e)
    
    print("✔ Dynamic DONE")    

    # -----------------------------
# STEP 4: FRAGILITY (ADD HERE)
# -----------------------------
    print("STEP 4: Fragility START")

    from src.postprocess import compute_fragility

    compute_fragility(results_dir="results", output_dir="results")

    print("✔ Fragility DONE")

#---------------Risk calculation-----------------   
    print("STEP 5: Risk START")

    from src.postprocess import compute_seismic_risk
    
    compute_seismic_risk(results_dir="results", return_period=50)
    
    print("✔ Risk DONE")
    
    print("STEP 6: Loss Estimation START")

    from src.postprocess import compute_loss_curve
    
    compute_loss_curve(results_dir="results")
    
    print("✔ Loss DONE")

    # --- Build 3D Gmsh mesh for visualization ---
    print("STEP 5: Gmsh START")
    geom_params = {
        "n_stories": params["n_stories"],
        "story_heights": params["story_heights"],
        "n_bays_x": params["n_bays_x"],
        "n_bays_y": params["n_bays_y"],
        "bay_lengths_x": params["bay_lengths_x"],
        "bay_lengths_y": params["bay_lengths_y"],
        "mesh_size": params["mesh_size"]
    }

    build_gmsh_building(geom_params,
                        msh_path=os.path.join("mesh", "building.msh"),
                        vtu_path=os.path.join("mesh", "building.vtu"))
           
    print("Gmsh DONE")
# ----------- STEP 6: ParaView pipeline -----------
    print("STEP 6: ParaView pipeline")

    gm_list = sorted([
        d for d in os.listdir("results")
        if d.startswith("GM_") and os.path.isdir(os.path.join("results", d))
    ])
    
    gm_vis = None
    for gm in gm_list:
        if os.path.exists(os.path.join("results", gm, "story_drift_x.out")):
            gm_vis = gm
            break
    
    if gm_vis is None:
        raise ValueError("No valid GM found for visualization")
    
    print(f"Using GM: {gm_vis}")
    
    build_animation_vtu(
        params,
        disp_file=os.path.join("results", gm_vis, "all_node_disp.out"),
        drift_file=os.path.join("results", gm_vis, "story_drift_x.out"),
        out_dir="results/animation/X"
    )
    
    build_animation_vtu(
        params,
        disp_file=os.path.join("results", gm_vis, "all_node_disp.out"),
        drift_file=os.path.join("results", gm_vis, "story_drift_y.out"),
        out_dir="results/animation/Y"
    )
    
    generate_pvsm()
    
    print("✔ ParaView files ready")
    print("ALL DONE")

# -------Run-------------------------
if __name__ == "__main__":
    main()
