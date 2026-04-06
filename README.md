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
----------------------------------------------------------------------------
Overview of the Probabilistic Seismic Risk Pipeline
1. Project Objective

This project develops a fully integrated probabilistic seismic risk assessment (PSRA) pipeline that unifies:
Modeling of a 3D reinforced-concrete (RC) building frame 
Seismic hazard analysis (PSHA) using an event-based classical approach
Nonlinear structural response simulation
Engineering demand parameter (EDP) extraction, e.g., storey displacement and Interstorey drift ratio (IDR)
Fragility, risk, and loss estimation

The objective is to eliminate fragmentation between traditionally disconnected tools and provide a reproducible, end-to-end Python-based workflow for seismic risk quantification.

2. Building Model Description
2.1 Structural Typology

The structure modeled in this pipeline is a 3D RC Moment-Resisting Frame (MRF) with 3-storey 2 bay in x-direction and 1 bay in y-direction, with a bay length of 5 m in x-direction along with 6 m in y-direction, with a regular rectangular grid layout. While modelling the column, the column size is kept at 0.5m*0.5m, and the beam size at 0.3m*0.4m. Cover of the member is considered as 0.05m. Mass per node is considered as 10000 kg with mesh size of 1 m. The 4 bars are considered at the top, bottom, and intermediate locations of the column. A rigid diaphragm is assumed at each floor level. The 4 numbers of bars are considered at the top and bottom of the beam. This typology represents mid-rise urban residential/commercial buildings in the seismic regions of India.

2.2 Material Modeling

The structural materials are defined using nonlinear constitutive models. Concrete is modeled using nonlinear stress-strain behavior (e.g., Concrete02 in OpenSees), which includes cracking, crushing, and stiffness degradation. However, reinforcing Steel is modeled using cyclic plasticity (e.g., Steel02), which captures yielding, strain hardening, and the Bauschinger effect.
Structural members (beams and columns) are modeled using fiber-section discretization, which allows explicit representation of concrete core, cover, reinforcement layers, accurate simulation of nonlinear flexural behavior, and spread of plasticity.

2.3 Element Formulation
Nonlinear beam-column elements are used for a distributed plasticity formulation that captures P-Δ (geometric nonlinearity) and cyclic degradation effects. Lumped masses are assigned at floor nodes, and gravity loads are applied prior to dynamic analysis. Also, static analysis is performed to establish the initial equilibrium.

3. Seismic Hazard Characterization
3.1 Hazard Framework
The pipeline uses an event-based Probabilistic Seismic Hazard Analysis (PSHA) approach to quantify seismic demand.
Input ground motions are taken from recorded accelerograms (PEER NGA database) with AT2 format in two orthogonal components:
GM_X → X-direction excitation and GM_Y → Y-direction excitation. 

3.2 Hazard Assumptions

The hazard is estimated by developing the uniform hazard response spectra (UHRS)  for a 475-year return period (10% probability of exceedance (PoE) and seismic hazard curve, which represents the mean annual rate of exceedance. The UHRS is further utilized for the ground motions selection that effectively represents the site-specific seismic hazards, and the hazard curve is utilized for further risk assessment of the building.
	​
3.3 Ground Motion Set
A suite of 22 near-field (NF) without pulse and 11 far-field (FF) with pulse ground motion pairs is used to represent moderate-to-strong shaking levels with variability in frequency content and duration. The ground motions are selected based on the requirement that the mean of selected ground motions should match the uniform hazard response spectra generated from PSHA for a 475-year return period without scaling.

