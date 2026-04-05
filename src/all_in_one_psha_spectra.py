# all_in_one_psha_final_with_output_folder.py
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt
import os
import sys
print("PSHA Python:", sys.executable)
from openquake.hazardlib.gsim.boore_atkinson_2008 import BooreAtkinson2008
from openquake.hazardlib.contexts import SitesContext, RuptureContext, DistancesContext
from openquake.hazardlib import const, imt as imt_module

# -------------------------------
# OUTPUT DIRECTORY
# -------------------------------
output_dir = r"I:\Users\NItm\OneDrive - National Institute of Technology, Meghalaya\Documents\NITM_PhD\IKELOA\New folder\New folder\results"
os.makedirs(output_dir, exist_ok=True)

# -------------------------------
# USER-CONTROLLED PLOT SETTINGS
# -------------------------------
PLOT_SETTINGS = {

    "hazard_curve": {
        "xlim": (0.01, 2.5),
        "ylim": (1e-6, 10e1),
        "xscale": "log",
        "yscale": "log"
    },

    "uhs": {
        "xlim": (0.0, 2.5),
        "ylim": (0.0, 2.0),
        "xscale": "linear",
        "yscale": "linear"
    }
}

# -------------------------------
# 1. Helpers
# -------------------------------
def logscale(min_val, max_val, n):
    return np.logspace(np.log10(min_val), np.log10(max_val), n)

def haversine(lon1, lat1, lon2, lat2):
    R = 6371.0
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

# -------------------------------
# 2. Site
# -------------------------------
site_lon, site_lat = 78.0, 22.0
vs30 = 600.0
z1pt0 = 100.0
z2pt5 = 5.0

# -------------------------------
# 3. Source
# -------------------------------
source_lon, source_lat = 78.2, 22.2

# -------------------------------
# 4. MFD
# -------------------------------
a_val, b_val = 6.5, 1.0
mmin, mmax, dm = 5.0, 7.0, 0.1

mags = np.arange(mmin, mmax + dm, dm)
rates = 10**(a_val - b_val * mags) * (1 - 10**(-b_val * dm))

# -------------------------------
# 5. Source properties
# -------------------------------
nodal_planes = [(0, 90, 0, 1.0)]
hypo_depths = [(5.0, 1.0)]

# -------------------------------
# 6. IMTs (UHRS periods)
# -------------------------------
periods_list = [0.01, 0.05, 0.15, 0.30, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5]

imtls = {
    imt_module.SA(T): logscale(0.005, 2.5, 50)
    for T in periods_list
}

# -------------------------------
# 7. GMPE
# -------------------------------
gmpe = BooreAtkinson2008()

# -------------------------------
# 8. PSHA Calculation
# -------------------------------
truncation_level = 3.0
investigation_time = 50.0

hazard_lambda = {
    imt: np.zeros_like(levels)
    for imt, levels in imtls.items()
}

for mag, rate in zip(mags, rates):

    for strike, dip, rake, np_prob in nodal_planes:
        for depth, hprob in hypo_depths:

            total_rate = rate * np_prob * hprob

            rrup_surface = haversine(site_lon, site_lat, source_lon, source_lat)
            rrup = np.sqrt(rrup_surface**2 + depth**2)

            # contexts
            sctx = SitesContext()
            sctx.sids = np.array([0])
            sctx.vs30 = np.array([vs30])
            sctx.vs30measured = np.array([True])
            sctx.z1pt0 = np.array([z1pt0])
            sctx.z2pt5 = np.array([z2pt5])

            rctx = RuptureContext()
            rctx.mag = mag
            rctx.rake = rake
            rctx.hypo_depth = depth

            dctx = DistancesContext()
            dctx.rrup = np.array([rrup])
            dctx.rjb = np.array([rrup])

            for imt, levels in imtls.items():

                mean, stddevs = gmpe.get_mean_and_stddevs(
                    sctx, rctx, dctx, imt, [const.StdDev.TOTAL]
                )

                mean = mean[0]
                sigma = stddevs[0][0]

                ln_x = np.log(levels)
                z = (ln_x - mean) / sigma

                cond_poe = norm.sf(z) / norm.sf(-truncation_level)

                hazard_lambda[imt] += total_rate * cond_poe

# -------------------------------
# 9. PGA Hazard Curve
# -------------------------------
pga_imt = imt_module.SA(0.01)
pga_levels = imtls[pga_imt]
pga_lambda = hazard_lambda[pga_imt]

# Plot
plt.figure()
plt.plot(pga_levels, pga_lambda)
plt.xscale(PLOT_SETTINGS["hazard_curve"]["xscale"])
plt.yscale(PLOT_SETTINGS["hazard_curve"]["yscale"])
plt.xlim(PLOT_SETTINGS["hazard_curve"]["xlim"])
plt.ylim(PLOT_SETTINGS["hazard_curve"]["ylim"])
plt.xlabel("PGA (g)")
plt.ylabel("Mean Annual Rate (λ)")
plt.title("PGA Hazard Curve")
plt.grid(True, which="both", ls="--")
plt.show()

# Save CSV
pga_path = os.path.join(output_dir, "hazard_curve_PGA.csv")
np.savetxt(pga_path,
           np.column_stack((pga_levels, pga_lambda)),
           delimiter=",", header="PGA(g),Lambda", comments="")

print(f"\nSaved: {pga_path}")

# Console print
print("\n--- PGA Hazard Curve ---")
for x, lam in zip(pga_levels, pga_lambda):
    print(f"{x:.4f} g -> {lam:.6e}")

# -------------------------------
# 10. UHRS FUNCTION
# -------------------------------
def compute_uhs(poe_target):

    sa_vals = []

    for imt in imtls:

        lam = hazard_lambda[imt]
        levels = imtls[imt]

        poe = 1 - np.exp(-lam * investigation_time)
        poe = np.maximum.accumulate(poe[::-1])[::-1]

        sa = np.interp(poe_target, poe[::-1], levels[::-1])
        sa_vals.append(sa)

    return np.array(sa_vals)

# -------------------------------
# 11. UHRS
# -------------------------------
targets = {"475yr": 0.10, "2475yr": 0.02}
UHRS_data = {}

for label, poe in targets.items():

    SA = compute_uhs(poe)
    UHRS_data[label] = SA

    # Plot
    plt.figure()
    plt.plot(periods_list, SA, marker='o')
    plt.xscale(PLOT_SETTINGS["uhs"]["xscale"])
    plt.yscale(PLOT_SETTINGS["uhs"]["yscale"])
    plt.xlim(PLOT_SETTINGS["uhs"]["xlim"])
    plt.ylim(PLOT_SETTINGS["uhs"]["ylim"])
    plt.xlabel("Period (s)")
    plt.ylabel("SA (g)")
    plt.title(f"UHRS ({label})")
    plt.grid(True, ls="--")
    plt.show()

    # Save CSV
    uhs_path = os.path.join(output_dir, f"UHRS_{label}.csv")
    np.savetxt(uhs_path,
               np.column_stack((periods_list, SA)),
               delimiter=",", header="T,SA", comments="")

    print(f"\nSaved: {uhs_path}")

    # Console print
    print(f"\n--- UHRS ({label}) ---")
    for T, sa in zip(periods_list, SA):
        print(f"T={T:.2f} sec -> SA={sa:.4f} g")

# -------------------------------
# 12. Python Data Storage
# -------------------------------
hazard_curve_data = {
    "PGA_levels": pga_levels,
    "Lambda": pga_lambda
}

print("\nAll outputs generated successfully.")