# src/gm_reader.py
#
# Read PEER AT2 files + compute Sa (single source of IM)

import numpy as np


# --------------------------------------------------
# 1. Read PEER AT2
# --------------------------------------------------
def read_peer_at2(filename, unit="g"):
    dt = None
    acc_values = []

    with open(filename, 'r') as f:
        header_parsed = False
        for line in f:
            line_s = line.strip()
            if not line_s:
                continue

            if not header_parsed and ("NPTS=" in line_s and "DT=" in line_s):
                parts = line_s.replace(',', ' ').split()
                for i, token in enumerate(parts):
                    if "DT=" in token:
                        if token == "DT=" and i+1 < len(parts):
                            dt = float(parts[i+1])
                        else:
                            dt = float(token.split('=')[1])
                header_parsed = True
                continue

            if header_parsed:
                vals = [float(v) for v in line_s.split()]
                acc_values.extend(vals)

    if dt is None:
        raise RuntimeError(f"Could not find DT in header of {filename}")

    acc_values = np.array(acc_values, dtype=float)

    # Convert to m/s^2
    if unit == "g":
        accel = acc_values * 9.81
    else:
        accel = acc_values

    return dt, accel


# --------------------------------------------------
# 2. Compute Spectral Acceleration Sa(T)
# --------------------------------------------------
def compute_sa(acc, dt, T, xi=0.05):
    omega = 2 * np.pi / T
    m = 1.0
    k = omega**2 * m
    c = 2 * xi * omega * m

    u = 0.0
    udot = 0.0
    uddot = 0.0
    umax = 0.0

    gamma = 0.5
    beta = 0.25

    a0 = m/(beta*dt**2) + gamma*c/(beta*dt)
    a1 = m/(beta*dt) + (gamma/beta - 1)*c
    a2 = (1/(2*beta)-1)*m + dt*(gamma/(2*beta)-1)*c

    keff = k + a0

    for i in range(len(acc)):
        p = -m * acc[i]

        peff = p + a0*u + a1*udot + a2*uddot

        u_new = peff / keff
        udot_new = gamma/(beta*dt)*(u_new - u) + (1 - gamma/beta)*udot + dt*(1 - gamma/(2*beta))*uddot
        uddot_new = (u_new - u)/(beta*dt**2) - udot/(beta*dt) - (1/(2*beta)-1)*uddot

        u, udot, uddot = u_new, udot_new, uddot_new

        umax = max(umax, abs(u))

    Sa = omega**2 * umax  # m/s^2
    return Sa


# --------------------------------------------------
# 3. MAIN FUNCTION (USE THIS EVERYWHERE)
# --------------------------------------------------
def process_ground_motion(filename, T, xi=0.05):
    dt, acc = read_peer_at2(filename)

    Sa = compute_sa(acc, dt, T, xi)

    return {
        "dt": dt,
        "acc": acc,
        "Sa": Sa,           # m/s^2
        "Sa_g": Sa / 9.81   # in g (for fragility)
    }