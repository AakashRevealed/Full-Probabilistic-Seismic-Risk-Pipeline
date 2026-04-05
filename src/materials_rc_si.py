# src/materials_rc_si.py
#
# RC materials in SI units for OpenSeesPy.

import openseespy.opensees as ops
import math


def define_rc_materials_si(
    conc_core_tag=1,
    conc_cover_tag=2,
    steel_tag=3,
):
    """
    Define RC concrete (Concrete02) and reinforcing steel (Steel02)
    in SI units (N, m, s).

    Returns:
      dict with material tags and key properties.
    """

    # Concrete compressive strength ~ -4 ksi ≈ -27.6 MPa
    fc = -4.0 * 6.895e6  # Pa

    fc_MPa = abs(fc) / 1.0e6
    Ec_MPa = 4700.0 * math.sqrt(fc_MPa)   # MPa
    Ec = Ec_MPa * 1.0e6                   # Pa

    nu = 0.2
    Gc = Ec / (2.0 * (1.0 + nu))

    Kfc = 1.3   # confined / unconfined
    Kres = 0.2  # residual / peak

    # Confined
    fc1C = Kfc * fc
    eps1C = 2.0 * fc1C / Ec
    fc2C = Kres * fc1C
    eps2C = 20.0 * eps1C
    lam = 0.1

    # Unconfined
    fc1U = fc
    eps1U = -0.003
    fc2U = Kres * fc1U
    eps2U = -0.01

    # Tension
    ftC = -0.14 * fc1C
    ftU = -0.14 * fc1U
    Ets = ftU / 0.002

    # Concrete02: tag, fpc, epsc0, fpcu, epsU, lambda, ft, Ets
    ops.uniaxialMaterial('Concrete02', conc_core_tag,
                         fc1C, eps1C, fc2C, eps2C, lam, ftC, Ets)
    ops.uniaxialMaterial('Concrete02', conc_cover_tag,
                         fc1U, eps1U, fc2U, eps2U, lam, ftU, Ets)

    # Steel ~ 66.8 ksi ≈ 460 MPa; Es ~ 200 GPa
    Fy = 66.8 * 6.895e6  # Pa
    Es = 2.0e11          # Pa

    Bs  = 0.01
    R0  = 18.0
    cR1 = 0.925
    cR2 = 0.15

    ops.uniaxialMaterial('Steel02', steel_tag,
                         Fy, Es, Bs, R0, cR1, cR2)

    return {
        "conc_core": conc_core_tag,
        "conc_cover": conc_cover_tag,
        "steel": steel_tag,
        "Ec": Ec,
        "Gc": Gc,
        "Fy": Fy,
        "Es": Es
    }