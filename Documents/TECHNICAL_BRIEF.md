# Technical Brief: Thermo-Mechanical Reliability Guardian

## 1. Executive Summary

The Thermo-Mechanical Reliability Guardian is a physics-informed DevSecOps agent that automates the reliability assessment of 2.5D/3D integrated packaging. By integrating non-linear thermal fatigue models directly into the GitLab CI/CD pipeline, this tool shifts hardware reliability testing from a post-fabrication physical process to a pre-merge virtual verification process. This drastically reduces prototyping costs and accelerates time-to-market for advanced semiconductor packaging.

The system accepts real ECAD files (KiCad `.kicad_pcb` and Gerber copper layers) and performs per-pad fatigue analysis on every solder joint on the board.

## 2. System Architecture

The system is built on a modular Python architecture:

### 2.1 Input Layer
Extracts geometrical parameters from hardware design files using two specialized libraries:
- **`kiutils`** for `.kicad_pcb` files: iterates through every footprint and pad, extracting X/Y position, width, height, and shape.
- **`gerbonara`** for Gerber files (`.gtl`, `.gbl`, `.gts`, `.gbs`, etc.): extracts `Flash` objects which represent pads and vias, along with their aperture (tool) diameters.

For each pad, the parser computes an **equivalent diameter** based on the pad area, which feeds directly into the physics engine. The parser also computes the board bounding box from pad coordinates to provide spatial context.

### 2.2 Physics Core — `physics_engine.py`
The computational heart of the system. It uses NumPy for high-performance numerical calculations and implements two industry-standard empirical models for solder joint fatigue life prediction. The engine supports **per-pad analysis**, iterating over every pad and reporting the worst-case (minimum cycles to failure) as the critical design risk.

### 2.3 Agent Layer — `agent.py`
The DevSecOps orchestrator. It authenticates with the GitLab API via `python-gitlab`, listens for Merge Request events, retrieves modified design files, runs the physics engine, and posts a formatted Markdown report back to the MR discussion thread. It supports local execution for demonstration purposes.

### 2.4 Visualization Layer — `app.py`
An interactive Streamlit dashboard. It utilizes PyVista to render:
- **Per-pad 3D cylinders** at their real (X, Y) board positions, color-coded by log-scaled cycles-to-failure using a Red-Yellow-Green colormap.
- **A board plane** for spatial context.
- **A scalar bar** showing the fatigue life distribution across the board.

## 3. Physics & Numerical Modeling

The engine assumes SAC305 (Sn-96.5%, Ag-3.0%, Cu-0.5%) material properties by default, but is parametric.

### 3.1 Darveaux Model
The Darveaux model predicts cycles to failure $(N_f)$ based on the inelastic strain energy density $(\Delta W)$ accumulated per thermal cycle. It separates the fatigue life into crack initiation $(N_0)$ and crack propagation $(N_a)$ phases:


$N_0 = K_1 (\Delta W)^{K_2}$

$\frac{da}{dN} = K_3 (\Delta W)^{K_4}$

$N_f = N_0 + \frac{a}{da/dN}$

Where:
 - $(a)$ is the characteristic crack length (approximated as the pad diameter).
 - $(K_1, K_2, K_3, K_4)$ are material constants calibrated for specific solder alloys and package geometries. In this project, they are calibrated to provide realistic cycle counts for standard PCB assemblies.

### 3.2 Norris-Landzberg Model
The Norris-Landzberg model is an acceleration factor model that accounts for the effects of temperature cycling frequency $(f)$ and maximum temperature $(T_{max})$:

$N_f = A \cdot (\Delta T)^{-n} \cdot (f)^{m} \cdot \exp\left(\frac{1414}{T_{max}}\right)$

This model is geometry-independent and therefore produces a single value per thermal condition set.

### 3.3 Assumptions and Limitations
- The current geometry uses an **equivalent diameter** to represent each pad (area-based for rectangular pads, direct for circular pads). This is a reasonable approximation for first-order fatigue estimation.
- The model assumes a **linear thermal gradient** across the solder joint. Future iterations will incorporate full FEA to capture non-linear material behavior (creep, plasticity).
- Material properties (CTE, Young's modulus) are currently set to SAC305 defaults. Stackup-based extraction is planned for a future release.

## 4. DevSecOps Integration

## 4. DevSecOps Integration

The agent is designed to run within a GitLab CI/CD pipeline. The `.gitlab-ci.yml` file defines a job that runs `agent.py` on every Merge Request that modifies a KiCad PCB file or a Gerber copper/solder-mask layer:

```yaml
rules:
  - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    changes:
      - "*.kicad_pcb"
      - "*.gtl"
      - "*.gbl"
      - "*.gts"
      - "*.gbs"
      - "design_config.json"
```

Because GitLab's shared runners are not available for all free-tier accounts, the architecture also supports **local execution mode** for demonstration purposes. The `agent.py` script is fully functional and, when authenticated with a `GITLAB_TOKEN`, posts formatted comments to a live Merge Request.

## 5. Future Scalability
 - **Full FEA Integration:** Replace empirical models with a full Finite Element Analysis solver (`FEniCS`, `CalculiX`) for complex geometries and non-linear material behavior.
 - **GitLab Orbit Integration:** Query the Orbit knowledge graph to correlate design changes with historical failure data from previous projects, enabling predictive risk flagging.
 - **Automated Layer Stackup Extraction:** Read material properties (CTE, thermal conductivity, thickness) directly from the KiCad stackup file instead of using defaults.
 - **Multi-Layer Analysis:** Extend beyond single Gerber layer parsing to analyze the full board stackup in one pass.

*Developed by Altug Remzi Akay, Ph.D. for the GitLab Transcend Hackathon 2026.*