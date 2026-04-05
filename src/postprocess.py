# src/postprocess.py

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt   # ✅ GLOBAL IMPORT (FIXES plt ERROR)


# --------------------------------------------------
# READ RECORDER
# --------------------------------------------------
def _read_opensees_recorder_matrix(filename):
    arr = np.loadtxt(filename)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    time = arr[:, 0]
    data = arr[:, 1:]
    return time, data


# --------------------------------------------------
# STORY DRIFT
# --------------------------------------------------
def compute_story_idr(story_disp, story_heights):

    n_steps, n_stories = story_disp.shape
    story_heights = np.array(story_heights)

    base_disp = np.zeros((n_steps, 1))
    disp_with_base = np.hstack([base_disp, story_disp])

    idr_time = np.zeros((n_steps, n_stories))

    for j in range(n_stories):
        drift = (disp_with_base[:, j+1] - disp_with_base[:, j]) / story_heights[j]
        idr_time[:, j] = drift

    idr_max = np.max(np.abs(idr_time), axis=0)
    return idr_time, idr_max


# --------------------------------------------------
# SINGLE RUN POSTPROCESS
# --------------------------------------------------
def postprocess_single_run(params, results_dir="results", output_csv="results/EDPs.csv"):

    story_heights = params["story_heights"]

    story_disp_x_file = os.path.join(results_dir, "story_disp_x.out")
    story_disp_y_file = os.path.join(results_dir, "story_disp_y.out")
    roof_disp_x_file  = os.path.join(results_dir, "roof_disp_x.out")
    roof_disp_y_file  = os.path.join(results_dir, "roof_disp_y.out")

    # ---- READ ----
    _, story_disp_x = _read_opensees_recorder_matrix(story_disp_x_file)
    _, story_disp_y = _read_opensees_recorder_matrix(story_disp_y_file)

    n_steps = min(story_disp_x.shape[0], story_disp_y.shape[0])
    story_disp_x = story_disp_x[:n_steps]
    story_disp_y = story_disp_y[:n_steps]

    # ---- IDR ----
    _, idr_max_x = compute_story_idr(story_disp_x, story_heights)
    _, idr_max_y = compute_story_idr(story_disp_y, story_heights)

    MIDR_x = np.max(idr_max_x)
    MIDR_y = np.max(idr_max_y)

    # ---- ROOF ----
    _, roof_disp_x = _read_opensees_recorder_matrix(roof_disp_x_file)
    _, roof_disp_y = _read_opensees_recorder_matrix(roof_disp_y_file)

    n_r = min(len(roof_disp_x), len(roof_disp_y))

    roof_disp_x_max = np.max(np.abs(roof_disp_x[:n_r]))
    roof_disp_y_max = np.max(np.abs(roof_disp_y[:n_r]))

    # ---- SAVE ----
    data = {
        "MIDR_x": MIDR_x,
        "MIDR_y": MIDR_y,
        "Sa_x": params["Sa_x"],   # ✅ STRICT (NO get)
        "Sa_y": params["Sa_y"],
        "T1_x": params["T1_x"],
        "T1_y": params["T1_y"],
        "max_roof_disp_x": roof_disp_x_max,
        "max_roof_disp_y": roof_disp_y_max
    }

    df = pd.DataFrame([data])
    df.to_csv(output_csv, index=False)

    # ---- GLOBAL FILE ----
    summary_file = os.path.join("results", "EDPs_all.csv")

    df["GM"] = os.path.basename(results_dir)

    if not os.path.exists(summary_file):
        df.to_csv(summary_file, index=False)
    else:
        df.to_csv(summary_file, mode='a', header=False, index=False)

    print(f"✔ EDP saved for {df['GM'].iloc[0]}")
    return df


# --------------------------------------------------
# FRAGILITY
# --------------------------------------------------
def compute_fragility(results_dir="results", output_dir="results"):

    from scipy.stats import lognorm

    edp_all_file = os.path.join(results_dir, "EDPs_all.csv")

    if not os.path.exists(edp_all_file):
        print("❌ Missing EDPs_all.csv")
        return

    df = pd.read_csv(edp_all_file)

    MIDR_x = df["MIDR_x"].values
    MIDR_y = df["MIDR_y"].values
    Sa_x = df["Sa_x"].values
    Sa_y = df["Sa_y"].values

    # ✅ DAMAGE STATES (YOU MISSED THIS)
    DS = {
        "DS1": 0.002,
        "DS2": 0.005,
        "DS3": 0.008,
        "DS4": 0.01
    }

    def compute_dir(Sa, MIDR, direction):

        idx = np.argsort(Sa)
        Sa = Sa[idx]
        MIDR = MIDR[idx]

        x_vals = np.linspace(0.001, max(Sa)*1.2, 300)

        plt.figure()

        for name, limit in DS.items():

            exceed = MIDR >= limit
            if np.sum(exceed) < 3:
                continue

            Sa_ds = Sa[exceed]

            mu = np.mean(np.log(Sa_ds))
            beta = np.std(np.log(Sa_ds))

            prob = lognorm.cdf(x_vals, s=beta, scale=np.exp(mu))

            plt.plot(x_vals, prob, label=name)

            np.savetxt(
                os.path.join(output_dir, f"fragility_{direction}_{name}.csv"),
                np.column_stack((x_vals, prob)),
                delimiter=",",
                header="Sa,Probability",
                comments=""
            )

        plt.xlabel("Sa (g)")
        plt.ylabel("P(DS ≥ ds)")
        plt.legend()
        plt.grid()

        plt.savefig(os.path.join(output_dir, f"fragility_{direction}.png"))
        plt.close()

        print(f"✔ Fragility {direction} done")

    compute_dir(Sa_x, MIDR_x, "X")
    compute_dir(Sa_y, MIDR_y, "Y")

#Risk---------------------------------------
# --------------------------------------------------
# RISK
# --------------------------------------------------
def compute_seismic_risk(results_dir="results", return_period=50):

    print("\nSTEP 5: Seismic Risk START")

    hazard_file = os.path.join(results_dir, "hazard_curve_PGA.csv")

    if not os.path.exists(hazard_file):
        raise FileNotFoundError("hazard_curve_PGA.csv not found")

    hazard = np.loadtxt(hazard_file, delimiter=",", skiprows=1)

    Sa = hazard[:, 0]
    lam = hazard[:, 1]

    Sa = np.maximum(Sa, 1e-6)
    lam = np.maximum(lam, 1e-12)

    results = []

    for direction in ["X", "Y"]:

        ds_labels = []
        ds_poe = []

        for ds in ["DS1", "DS2", "DS3", "DS4"]:

            frag_file = os.path.join(results_dir, f"fragility_{direction}_{ds}.csv")

            if not os.path.exists(frag_file):
                print(f"⚠ Missing {frag_file}")
                continue

            frag = np.loadtxt(frag_file, delimiter=",", skiprows=1)

            Sa_frag = frag[:, 0]
            P_frag = frag[:, 1]

            P_interp = np.interp(Sa, Sa_frag, P_frag, left=0.0, right=1.0)

            nu = 0.0
            for i in range(len(Sa)-1):
                dlam = abs(lam[i+1] - lam[i])
                P_avg = 0.5 * (P_interp[i] + P_interp[i+1])
                nu += P_avg * dlam

            poe = 1 - np.exp(-nu * return_period)

            print(f"{direction}-{ds}: PoE = {poe:.4f}")

            ds_labels.append(ds)
            ds_poe.append(poe)
            results.append([direction, ds, nu, poe])

        plt.figure()
        plt.bar(ds_labels, ds_poe)
        plt.ylim(0, 1)
        plt.title(f"Risk - {direction}")
        plt.savefig(os.path.join(results_dir, f"risk_{direction}.png"))
        plt.close()

    df = pd.DataFrame(results, columns=["Direction", "DS", "nu", "PoE"])
    df.to_csv(os.path.join(results_dir, "seismic_risk.csv"), index=False)

    print("✔ Risk DONE")
    return df
# --------------------------------------------------
# LOSS
# --------------------------------------------------
def compute_loss_curve(results_dir="results"):

    print("\nSTEP 6: Loss START")

    LR = [0.02, 0.10, 0.50, 1.00]

    hazard = np.loadtxt(
        os.path.join(results_dir, "hazard_curve_PGA.csv"),
        delimiter=",", skiprows=1
    )

    Sa = hazard[:, 0]

    for direction in ["X", "Y"]:

        P = []

        for ds in ["DS1", "DS2", "DS3", "DS4"]:

            frag = np.loadtxt(
                os.path.join(results_dir, f"fragility_{direction}_{ds}.csv"),
                delimiter=",", skiprows=1
            )

            P.append(np.interp(Sa, frag[:,0], frag[:,1]))

        P1 = np.maximum(P[0] - P[1], 0)
        P2 = np.maximum(P[1] - P[2], 0)
        P3 = np.maximum(P[2] - P[3], 0)
        P4 = P[3]

        loss = P1*LR[0] + P2*LR[1] + P3*LR[2] + P4*LR[3]

        plt.figure()
        plt.plot(Sa, loss)
        plt.xlabel("Sa (g)")
        plt.ylabel("Loss Ratio")
        plt.grid()

        plt.savefig(os.path.join(results_dir, f"loss_{direction}.png"))
        plt.close()

        np.savetxt(
            os.path.join(results_dir, f"loss_{direction}.csv"),
            np.column_stack((Sa, loss)),
            delimiter=",",
            header="Sa,Loss",
            comments=""
        )

        print(f"✔ Loss {direction} done")