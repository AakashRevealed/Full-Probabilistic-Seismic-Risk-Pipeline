# src/run_dynamic.py
#
# Gravity + bidirectional nonlinear dynamic analysis.

import os
import numpy as np
import openseespy.opensees as ops

from .analysis_dynamic import setup_dynamic_analysis

#------------------------------------------------------------------------
def run_gravity(params):
    """
    Simple gravity analysis placeholder.
    Add actual loads if needed.
    """
    ops.wipeAnalysis()

    # --- Load pattern ---
    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)

    g = 9.81
    mass = params["mass_per_node"]

    # Apply gravity load at all non-base nodes
    for node in ops.getNodeTags():
        if node not in params["base_nodes"]:
            ops.load(node, 0.0, 0.0, -mass * g, 0.0, 0.0, 0.0)

    # --- Analysis ---
    ops.constraints('Plain')
    ops.numberer('RCM')
    ops.system('BandGeneral')
    ops.test('NormDispIncr', 1e-6, 50, 1)   # slightly relaxed
    ops.algorithm('Newton')
    ops.integrator('LoadControl', 0.05)      # gradual loading
    ops.analysis('Static')
    ops.analyze(20)
    ops.loadConst('-time', 0.0)
    


#---------------------------------------------------------------------
def run_bidirectional_dynamic(params, acc_x, acc_y, dt_x, dt_y, scale_factor, out_dir):

    ops.wipeAnalysis()

    # -----------------------------
    # CHECK dt
    # -----------------------------
    if abs(dt_x - dt_y) > 1e-6:
        raise ValueError("Ground motions must have same dt")

    dt = dt_x

    # Trim & scale
    npts = min(len(acc_x), len(acc_y))
    acc_x = acc_x[:npts] * scale_factor
    acc_y = acc_y[:npts] * scale_factor

    # -----------------------------
    # DAMPING (Rayleigh)
    # -----------------------------
    omega1 = 2 * np.pi / params["T1_x"]
    omega2 = 2 * np.pi / params["T1_y"]

    zeta = 0.05

    alphaM = 2*zeta*omega1*omega2/(omega1+omega2)
    betaK  = 2*zeta/(omega1+omega2)

    ops.rayleigh(alphaM, 0.0, 0.0, betaK)

    # -----------------------------
    # TIME SERIES
    # -----------------------------
    ts_x = 1001
    ts_y = 1002

    ops.timeSeries('Path', ts_x, '-dt', dt, '-values', *acc_x.tolist())
    ops.timeSeries('Path', ts_y, '-dt', dt, '-values', *acc_y.tolist())

    # -----------------------------
    # EXCITATION
    # -----------------------------
    ops.pattern('UniformExcitation', 2001, 1, '-accel', ts_x)
    ops.pattern('UniformExcitation', 2002, 2, '-accel', ts_y)

    # -----------------------------
    # OUTPUT DIR
    # -----------------------------
    os.makedirs(out_dir, exist_ok=True)
    print("dt:", dt)
    print("npts:", npts)
    print("Max acc X:", np.max(np.abs(acc_x)))
    print("Max acc Y:", np.max(np.abs(acc_y)))
    # -----------------------------
    # ANALYSIS SETUP
    # -----------------------------
    setup_dynamic_analysis(
        constraints_type="Transformation",
        numberer_type="RCM",
        system_type="BandGeneral",
        test_type="NormDispIncr",
        tol=1e-4,
        max_iter=50,
        print_flag=0,
        algorithm_type="NewtonLineSearch",
        integrator_type="Newmark",
        newmark_gamma=0.5,
        newmark_beta=0.25,
        analysis_type="Transient"
    )
    
    # -----------------------------
    # RECORDERS
    # -----------------------------
    roof_node = params["roof_nodes"][0]
    base_nodes = params["base_nodes"]
    story_nodes = params["story_nodes"]

    ops.recorder('Node', '-file', os.path.join(out_dir, "roof_disp_x.out"),
                 '-time', '-node', roof_node, '-dof', 1, 'disp')

    ops.recorder('Node', '-file', os.path.join(out_dir, "roof_disp_y.out"),
                 '-time', '-node', roof_node, '-dof', 2, 'disp')

    ops.recorder('Node', '-file', os.path.join(out_dir, "story_disp_x.out"),
                 '-time', '-node', *story_nodes, '-dof', 1, 'disp')

    ops.recorder('Node', '-file', os.path.join(out_dir, "story_disp_y.out"),
                 '-time', '-node', *story_nodes, '-dof', 2, 'disp')


    # -----------------------------
    # ANALYSIS LOOP
    # -----------------------------
    substeps = 2
    dt_analysis = dt / substeps

    print("Starting dynamic analysis...")

    ok = ops.analyze(npts, dt)
    
    if ok != 0:
        print("⚠ Initial analysis failed, retrying with smaller step...")
        ok = ops.analyze(npts*2, dt/2)
    
    if ok != 0:
        print("❌ Dynamic analysis FAILED completely")
        params["collapse"] = True
        return
    
    print("✔ Dynamic analysis SUCCESS")
    print("Final time reached:", ops.getTime())