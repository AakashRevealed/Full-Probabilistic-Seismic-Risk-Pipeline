# src/sections_rc_si.py
#
# RC rectangular fiber section, ported from BuildRCrectSection.tcl.

import openseespy.opensees as ops


def build_rc_rect_section(
    sec_tag,
    HSec, BSec,
    coverH, coverB,
    coreID, coverID, steelID,
    numBarsTop, barAreaTop,
    numBarsBot, barAreaBot,
    numBarsIntTot, barAreaInt,
    nfCoreY, nfCoreZ,
    nfCoverY, nfCoverZ
):
    """
    Build RC rectangular fiber section in SI units.

    Args:
      sec_tag: section tag
      HSec: section depth (local y direction), m
      BSec: section width (local z direction), m
      ops.section('Fiber', sec_tag)
      coverH: cover thickness in y, m
      coverB: cover thickness in z, m
      coreID, coverID, steelID: material tags
      numBarsTop, numBarsBot, numBarsIntTot: bar counts
      barAreaTop, barAreaBot, barAreaInt: bar areas, m^2
      nfCoreY, nfCoreZ, nfCoverY, nfCoverZ: fiber counts
    """

    coverY = HSec / 2.0
    coverZ = BSec / 2.0
    coreY  = coverY - coverH
    coreZ  = coverZ - coverB
    numBarsInt = numBarsIntTot // 2
    
    # --- Add torsional stiffness for 3D model ---
    nu = 0.2
    Ec = 25e9
    G = Ec / (2 * (1 + nu))
    
    J = (BSec * HSec**3 + HSec * BSec**3) / 12  
    
    ops.section('Fiber', sec_tag, '-GJ', G * J)
    
    print("HSec =", HSec, "BSec =", BSec)
    print("coverY =", coverY, "coverZ =", coverZ)
    print("coreY =", coreY, "coreZ =", coreZ)
    print("nfCoreY =", nfCoreY, "nfCoreZ =", nfCoreZ)
    print("nfCoverY =", nfCoverY, "nfCoverZ =", nfCoverZ)
    
    # if coreY <= 0 or coreZ <= 0:
    #     raise ValueError("Invalid geometry: core dimension <= 0")

    # if coverY <= coreY or coverZ <= coreZ:
    #     raise ValueError("Invalid cover: cover must be outside core")

    # if nfCoreY <= 0 or nfCoreZ <= 0:
    #     raise ValueError("Invalid fiber mesh density (core)")

    # if nfCoverY <= 0 or nfCoverZ <= 0:
    #     raise ValueError("Invalid fiber mesh density (cover)")
    # Core patch
    ops.patch('quad', coreID, nfCoreZ, nfCoreY,
              -coreY, -coreZ,
               coreY, -coreZ,
               coreY,  coreZ,
              -coreY,  coreZ)

   # Cover patches
   # Safer cover (avoid degenerate quads)
    ops.patch('quad', coverID, nfCoverZ, nfCoverY,
                 -coverY,  coverZ,
                 -coverY, -coverZ,
                  coverY, -coverZ,
                  coverY,  coverZ)
   # # Top cover
   #  ops.patch('quad', coverID, nfCoverZ, nfCoverY,
   #           -coverY, coreZ,
   #            coverY, coreZ,
   #            coverY, coverZ,
   #           -coverY, coverZ)

   # # Bottom cover
   #  ops.patch('quad', coverID, nfCoverZ, nfCoverY,
   #           -coverY, -coverZ,
   #            coverY, -coverZ,
   #            coverY, -coreZ,
   #           -coverY, -coreZ)

   # # Left cover
   #  ops.patch('quad', coverID, nfCoverZ, nfCoverY,
   #           -coverY, -coverZ,
   #           -coreY, -coreZ,
   #           -coreY,  coreZ,
   #           -coverY,  coverZ)

   # # Right cover
   #  ops.patch('quad', coverID, nfCoverZ, nfCoverY,
   #            coreY, -coreZ,
   #            coverY, -coverZ,
   #            coverY,  coverZ,
   #            coreY,  coreZ)

    # Reinforcement layers
    eps = 1e-6  # small offset to avoid boundary issues
    # Intermediate bars
    if numBarsIntTot > 0 and barAreaInt > 0:
       numBarsInt = numBarsIntTot // 2

    if numBarsInt > 0:
        ops.layer('straight', steelID, numBarsInt, barAreaInt,
                  -coreY + eps, 0.0,
                   coreY - eps, 0.0)
    
    # Top bars
    if numBarsTop > 0 and barAreaTop > 0:
        ops.layer('straight', steelID, numBarsTop, barAreaTop,
              -coreY + eps, coreZ - eps,
               coreY - eps, coreZ - eps)
    
    # Bottom bars
    if numBarsBot > 0 and barAreaBot > 0:
        ops.layer('straight', steelID, numBarsBot, barAreaBot,
              -coreY + eps, -coreZ + eps,
               coreY - eps, -coreZ + eps)