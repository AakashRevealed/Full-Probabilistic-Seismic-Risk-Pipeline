# src/analysis_dynamic.py
#
# Dynamic analysis setup.

import openseespy.opensees as ops


def setup_dynamic_analysis(
    constraints_type="Transformation",
    numberer_type="RCM",
    system_type="BandGeneral",

    # 🔥 FIXED HERE
    test_type="NormDispIncr",
    tol=1e-5,
    max_iter=50,
    print_flag=0,

    # 🔥 FIXED HERE
    algorithm_type="NewtonLineSearch",

    integrator_type="Newmark",
    newmark_gamma=0.5,
    newmark_beta=0.25,

    analysis_type="Transient"
):

    ops.constraints(constraints_type)
    ops.numberer(numberer_type)
    ops.system(system_type)

    # 🔥 Robust convergence test
    ops.test(test_type, tol, max_iter, print_flag)

    # 🔥 Robust algorithm
    if algorithm_type == "NewtonLineSearch":
        ops.algorithm('NewtonLineSearch', 0.8)
    else:
        ops.algorithm(algorithm_type)

    # Integrator
    if integrator_type == "Newmark":
        ops.integrator('Newmark', newmark_gamma, newmark_beta)
    else:
        raise NotImplementedError(f"Integrator {integrator_type} not implemented")

    ops.analysis(analysis_type)