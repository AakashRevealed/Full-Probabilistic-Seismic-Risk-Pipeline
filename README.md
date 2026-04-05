# Full-Probabilistic-Seismic-Risk-Pipeline
seismic_risk_pipeline/
│
├── main.py                         # Master pipeline controller
│
├── src/
│   ├── __init__.py
│   ├── materials_rc_si.py          # RC material models (Concrete02, Steel02)
│   ├── sections_rc_si.py           # Fiber section generation
│   ├── model_3d.py                 # 3D RC frame modeling
│   ├── analysis_dynamic.py         # Dynamic solver configuration
│   ├── gm_reader.py                # PEER AT2 reader + Sa computation
│   ├── run_dynamic.py              # Gravity + nonlinear time history analysis
│   ├── geometry_gmsh.py            # Gmsh mesh generation
│   ├── postprocess.py              # EDPs, fragility, risk, loss
│   ├── all_in_one_psha_spectra.py  # PSHA hazard computation
│
├── gm/
│   ├── GM_X/                      # X-direction ground motions
│   ├── GM_Y/                      # Y-direction ground motions
│
├── mesh/
│   ├── building.msh               # Generated mesh
│   ├── building.vtu               # ParaView file
│
├── results/
│   ├── GM_*/                      # Results per ground motion
│   ├── EDPs_all.csv               # Aggregated EDPs
│   ├── fragility_*.csv            # Fragility curves
│   ├── hazard_curve_Sa.csv        # PSHA output
│   ├── seismic_risk.csv           # Risk results
│   ├── loss_*.csv                 # Loss curves
│
├── requirements.txt               # Dependencies
└── README.md
