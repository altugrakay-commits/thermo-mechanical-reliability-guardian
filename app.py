# app.py
import streamlit as st
import pyvista as pv
import numpy as np
import json
import os
import tempfile
from physics_engine import ThermoMechanicalEngine
from parser import DesignParser

st.set_page_config(page_title="Thermo-Mechanical Reliability Guardian", layout="wide", page_icon="🛡️")

st.title("🛡️ Thermo-Mechanical Reliability Guardian")
st.markdown("Physics-informed thermal fatigue analysis for 2.5D/3D packaging. Upload a design file or adjust parameters manually.")

# --- Sidebar Configuration ---
st.sidebar.header("⚙️ Design Input")

# File uploader for real ECAD files
uploaded_file = st.sidebar.file_uploader(
    "Upload Design File", 
    type=["json", "kicad_pcb", "gbr", "gtl", "gbl", "gts", "gbs", "gto", "gbo", "gm1"],
    help="Best results: Copper layers (.gtl, .gbl) or Solder Mask layers (.gts, .gbs)."
)

# Thermal condition inputs (always adjustable)
st.sidebar.subheader("🌡️ Thermal Conditions")
delta_T = st.sidebar.slider("Temperature Delta (K)", 50, 250, 150)
t_max = st.sidebar.slider("Max Temperature (K)", 300, 500, 400)
freq = st.sidebar.slider("Thermal Cycles per Day", 1, 10, 2)
solder_height = st.sidebar.number_input("Solder Height (mm)", 0.01, 0.5, 0.08, step=0.01)

# --- Parse the uploaded file or use defaults ---
parsed_data = None
parser_mode = "Manual Mode"
pad_count = 0

if uploaded_file is not None:
    # Save uploaded file to a temp location for the parser
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        parser = DesignParser(tmp_path)
        parsed_data = parser.parse()
        pad_count = parsed_data['geometry'].get('pad_count', 0)
        parser_mode = f"File Mode: {uploaded_file.name}"
        
        if pad_count > 0:
            st.sidebar.success(f"✅ Parsed: {pad_count} pads detected")
        else:
            st.sidebar.warning(f"⚠️ 0 pads detected. This layer contains no pads (e.g., silkscreen or edge cuts). Please upload a copper (.gtl, .gbl) or solder mask (.gts, .gbs) layer.")
    except Exception as e:
        st.sidebar.error(f"⚠️ Parse Error: {e}")
    finally:
        os.unlink(tmp_path)

# --- Build the input data for the physics engine ---
if parsed_data is not None and pad_count > 0:
    # Use geometry from file, but thermal conditions from sliders
    input_data = {
        'delta_T': delta_T,
        'T_max': t_max,
        'frequency': freq,
        'geometry': {
            'solder_height': solder_height,
            'pad_diameter': parsed_data['geometry'].get('pad_diameter', 0.5),
            'pads': parsed_data['geometry'].get('pads', [])
        }
    }
else:
    # Manual mode with single pad (fallback if file has no pads)
    pad_diameter = st.sidebar.number_input("Pad Diameter (mm)", 0.1, 2.0, 0.4, step=0.05)
    input_data = {
        'delta_T': delta_T,
        'T_max': t_max,
        'frequency': freq,
        'geometry': {
            'solder_height': solder_height,
            'pad_diameter': pad_diameter,
            'pads': []
        }
    }

# --- Run the Physics Engine ---
engine = ThermoMechanicalEngine({})
results = engine.run_full_analysis(input_data)

# --- Layout ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📊 Simulation Results")
    st.caption(f"Mode: {parser_mode}")
    
    if pad_count > 0:
        st.metric("Pads Analyzed", results.get('pad_count', 0))
    
    st.metric("Worst-Case Darveaux Cycles", f"{results['darveaux_cycles']:,}")
    st.metric("Norris-Landzberg Cycles", f"{results['norris_landzberg_cycles']:,}")
    
    if results['status'] == "PASS":
        st.success("✅ Design Status: PASS - Reliability threshold met.")
    else:
        st.error("⚠️ Design Status: WARNING - High Risk of Thermal Fatigue Failure.")
    
    # Show worst pad details if available
    if results.get('worst_pad'):
        wp = results['worst_pad']
        st.markdown(f"**🔴 Critical Pad Location:** X={wp['x']:.2f}mm, Y={wp['y']:.2f}mm (Ø{wp['diameter']:.2f}mm)")
    
    st.markdown("---")
    st.markdown("""
    **Physics Models:**
    *   **Darveaux:** Crack initiation & propagation from inelastic strain energy density.
    *   **Norris-Landzberg:** Temperature cycling frequency & max temperature effects.
    """)

with col2:
    st.subheader("🔬 3D Thermal Strain Visualization")
    
    plotter = pv.Plotter(notebook=False, off_screen=True)
    
    pads = results.get('pad_results', [])
    
    if pads:
        # Render every pad as a small cylinder at its (x, y) location
        for pad in pads:
            x, y = pad['x'], pad['y']
            d = pad['diameter']
            pad_mesh = pv.Cylinder(
                center=(x, y, 0), direction=(0, 0, 1),
                radius=d / 2, height=solder_height, resolution=20
            )
            pad_mesh['Log Cycles'] = np.full(pad_mesh.n_points, np.log10(max(pad['darveaux_cycles'], 1)))
            
            # Use scalar_bar_args to position the legend on the right side
            plotter.add_mesh(
                pad_mesh, 
                scalars='Log Cycles', 
                cmap='RdYlGn', 
                clim=(3, 7), 
                show_edges=False, 
                lighting=True,
                scalar_bar_args={
                    'title': 'Cycles to Failure (log10)',
                    'vertical': True,
                    'position_x': 0.85, 
                    'position_y': 0.1,
                    'width': 0.05, 
                    'height': 0.8
                }
            )
        
        # Add a board outline (flat plane) for context
        xs = [p['x'] for p in pads]
        ys = [p['y'] for p in pads]
        pad_margin = 5
        plane = pv.Plane(
            center=((min(xs)+max(xs))/2, (min(ys)+max(ys))/2, -solder_height/2),
            direction=(0, 0, 1),
            i_size=(max(xs)-min(xs)) + pad_margin,
            j_size=(max(ys)-min(ys)) + pad_margin
        )
        # Changed plane color to dark grey for better contrast with green/red pads
        plotter.add_mesh(plane, color='#2b2b2b', opacity=0.8, show_edges=True)
        
    else:
        # Single pad fallback (manual mode or file with no pads)
        mesh = pv.Cylinder(center=(0, 0, 0), direction=(0, 0, 1), 
                           radius=input_data['geometry']['pad_diameter']/2, 
                           height=solder_height)
        z_vals = mesh.points[:, 2]
        thermal_strain = (z_vals - z_vals.min()) / (z_vals.max() - z_vals.min()) * (delta_T / 100)
        mesh['Thermal Strain'] = thermal_strain
        
        # Position the legend on the right side for the single cylinder as well
        plotter.add_mesh(
            mesh, 
            scalars='Thermal Strain', 
            cmap='coolwarm', 
            show_edges=True, 
            lighting=True,
            scalar_bar_args={
                'title': 'Thermal Strain',
                'vertical': True,
                'position_x': 0.85, 
                'position_y': 0.1,
                'width': 0.05, 
                'height': 0.8
            }
        )
    
    plotter.add_axes()
    plotter.camera_position = 'iso'
    plotter.camera.zoom(0.9)
    plotter.show_grid()
    
    plotter.screenshot("thermal_strain_render.png")
    st.image("thermal_strain_render.png", 
             caption=f"Pad-Level Thermal Fatigue Map (ΔT = {delta_T}K)", 
             use_container_width=True)

st.markdown("---")
st.caption("Built for the GitLab Transcend Hackathon 2026 | Physics-Informed DevSecOps")