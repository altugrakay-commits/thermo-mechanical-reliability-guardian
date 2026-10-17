# 🛡️ Thermo-Mechanical Reliability Guardian

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Physics](https://img.shields.io/badge/Physics-Darveaux%20%7C%20Norris--Landzberg-green.svg)
![Formats](https://img.shields.io/badge/Formats-KiCad%20%7C%20Gerber%20%7C%20JSON-orange.svg)

An automated, physics-informed DevSecOps agent that predicts thermal fatigue life in 2.5D/3D packaging. Built for the **GitLab Transcend Hackathon 2026** (Showcase Track).

## 📖 Overview

In modern hardware development, software and hardware design are siloed. When a developer commits a change to a PCB layout, there is no automated way to check if that change will cause a thermo-mechanical failure (like solder joint fatigue) in the real world. Physical prototypes must be built and tested — a slow and expensive process.

The **Thermo-Mechanical Reliability Guardian** bridges this gap. It acts as an automated CI/CD agent that:
1.  **Parses real ECAD files** (KiCad `.kicad_pcb` and Gerber copper layers).
2.  **Runs non-linear thermal fatigue simulations** using the Darveaux and Norris-Landzberg models.
3.  **Posts the results** directly back to the GitLab Merge Request workflow.
4.  **Visualizes the thermal strain distribution** across every pad on the board.

![Dashboard Screenshot](docs/screenshot_gtl.png)
*Live analysis of a 106-pad Top Copper layer, with color-coded fatigue life per pad.*

## 🚀 Key Features

-   **Multi-Format ECAD Parsing:** Directly reads KiCad PCB files and Gerber copper layers (`.gtl`, `.gbl`, `.gts`, `.gbs`) using `kiutils` and `gerbonara`.
-   **Per-Pad Physics Simulation:** Calculates thermal fatigue life for every individual pad on the board, not just a single average.
-   **Real-Time Risk Assessment:** Identifies the critical pad (worst-case cycles to failure) and reports a clear `PASS` or `WARNING` status.
-   **Interactive 3D Dashboard:** A Streamlit + PyVista web app that renders the board layout with color-coded fatigue life per pad.
-   **GitLab CI/CD Integration:** Automatically triggers on Merge Requests that modify `.kicad_pcb`, `.gtl`, `.gbl`, `.gts`, `.gbs`, or `design_config.json` files.

## 🏗️ Architecture

The project is modularized into four core components:

| File | Role | Description |
|------|------|-------------|
| **`parser.py`** | Input | Reads `.kicad_pcb`, `.gbr`/`.gtl`/`.gbl`/etc., or `.json`. Extracts pad geometry (position, size, shape). |
| **`physics_engine.py`** | Processing | Core mathematical engine. Runs Darveaux and Norris-Landzberg models per-pad. |
| **`agent.py`** | DevSecOps | CI/CD agent. Parses the design, runs the engine, and posts results to a GitLab Merge Request. |
| **`app.py`** | Visualization | Streamlit dashboard for interactive exploration and 3D visualization. |

## 🛠️ Tech Stack

-   **Language:** Python 3.9+
-   **Numerical Modeling:** NumPy
-   **Web Framework:** Streamlit
-   **3D Visualization:** PyVista
-   **ECAD Parsing:** `kiutils` (KiCad), `gerbonara` (Gerber)
-   **DevSecOps:** GitLab CI/CD, `python-gitlab` API

## 💻 Local Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone https://gitlab.com/akay7592941/thermo-mechanical-reliability-guardian.git
    
    cd thermo-mechanical-reliability-guardian
    ```
2. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3. **Run the interactive Dashboard:**
   ```bash
   streamlit run app.py
   ```
   This will open a browser window at `http://localhost:8501` where you can tweak parameters and view the 3D thermal strain visualizations.

4. **Run the CI Agent Locally (Simulation):**
   ```bash
   python agent.py
   ```
   Note: To post comments back to GitLab, ensure the `GITLAB_TOKEN` environment is set.

## 📊 Example Output
The agent generates a report like this upon running:

  **🛡️ Thermo-Mechanical Reliability Report**
 - **Pads Analyzed:** 106
 - **Worst-Case Darveaux Cycles:** 892,638
 - **Norris-Landzberg Cycles:** 14,165
 - **Status:** PASS
 - **Critical Pad Location:** X = 5.00mm, Y = -23.00mm (Ø0.50mm)

## 📂 Supported File Formats
| Format | Extension | Best For |
|------|------|-------------|
| KiCad PCB | `.kicad_pcb` | Full board with component pads |
| Gerber Top Copper | `.gtl` | Via arrays and copper features |
| Gerber Bottom Copper | `.gbl` | Bottom-layer pads |
| Gerber Top Solder Mask | `.gts` | Solder mask openings |
| Gerber Bottom Solder Mask | `.gbs` | Bottom solder mask openings |
| JSON Config | `.json` | Manual parameter entry |

**Note:** Layers like `.gto` (silkscreen) or `.gm1` (edge cuts) do not contain pads and will display a warning. Use copper or solder mask layers for accurate results.

## 🔮 Future Work
 - **Full 3D FEA Integration:** Replace empirical models with a full Finite Element Analysis solver (e.g., FEniCS, CalculiX) for non-linear creep/plasticity.
 - **GitLab Orbit Integration:** Query the Orbit knowledge graph to correlate design changes with historical failure data.
 - **Automated Layer Stackup Extraction:** Read material properties directly from the KiCad stackup instead of using defaults.

## 📜 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE.md) file for details.

## 🙏 Acknowledgments
 - Built for the **GitLab Transcend Hackathon 2026.**
 - Physics models based on standard reliability engineering literature (Darveaux, Norris-Landzberg).
 - Developed by **Altug Remzi Akay, Ph.D.**