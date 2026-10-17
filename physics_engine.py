import numpy as np

class ThermoMechanicalEngine:
    def __init__(self, material_props=None):
        """
        Initialize the engine with material properties.
        material_properties: dict containing CTE, modulus, etc.
        """
        if material_props is None:
            material_props = {}
        self.props = material_props
        # Example material properties for SAC305 solder.
        self.E = 50e9       # Young's modulus in Pa
        self.alpha = 21e-6  # CTE in 1/K
        self.T_melt = 490   # Melting temperature in Kelvin

    def _calculate_darveaux_life(self, delta_T, geometry):
        """
        Calculates cycles to failure using the Darveaux model for a single pad.
        """
        # Simplified Darveaux equation parameters.
        K1, K2, K3, K4 = 10.10, -1.5, 0.05, -1.2

        pad_diameter = geometry.get('equivalent_diameter', geometry.get('pad_diameter', 0.5))
        solder_height = geometry.get('solder_height', 0.08)

        # Guard clauses to prevent math errors.
        if delta_T <= 0 or solder_height <= 0 or pad_diameter <= 0:
            return float('inf')

        # Calculate inelastic strain energy density
        delta_W = (solder_height * delta_T * self.alpha) / pad_diameter

        if delta_W < 1e-10:
            return float('inf')

        # Crack initiation and propagation.
        N0 = K1 * (delta_W**K2)
        da_dN = K3 * (delta_W**K4)

        if da_dN == 0:
            return float('inf')

        cycles = N0 + (pad_diameter / da_dN)
        return int(max(0, cycles))

    def _calculate_norris_landzberg_life(self, delta_T, T_max, freq):
        """Calculates cycles to failure using the Norris-Landzberg model."""
        # Placeholder parameters.
        A = 3500.0
        n = 1.9
        m = -0.33

        if delta_T <= 0 or T_max <= 0 or freq <= 0:
            return float('inf')

        # Convert T_max to Celsius for the equation.
        T_max_C = T_max - 273.15
        if T_max <= 0:
            return float('inf')

        cycles = A * (delta_T**-n) * (freq**m) * np.exp(1414 / T_max_C)
        return int(max(0, cycles))

    def run_full_analysis(self, input_data):
        """
        Runs the analysis on a single pad or an entire board.
        If 'pads' is present in geometry, calculates for each pad and returns worst-case.
        """
        delta_T = input_data.get('delta_T', 100)    # Default 100K
        T_max = input_data.get('T_max', 350)
        freq = input_data.get('frequency', 1)
        geometry = input_data.get('geometry', {})

        pads = geometry.get('pads', [])
        solder_height = geometry.get('solder_height', 0.08)

        # Global Norris-Landzberg life (depends only on thermal conditions, not geometry)
        norris_cycles = self._calculate_norris_landzberg_life(delta_T, T_max, freq)

        if pads:
            # Per-pad Darveaux analysis.
            pad_results = []
            worst_darveaux = float('inf')
            worst_pad = None

            for pad in pads:
                pad_geom = {'equivalent_diameter': pad.get('equivalent_diameter', 0.5), 'solder_height': solder_height}
                darveaux = self._calculate_darveaux_life(delta_T, pad_geom)
                pad_results.append({
                    'x': pad.get('x', 0),
                    'y': pad.get('y', 0),
                    'diameter': pad.get('equivalent_diameter', 0.5),
                    'darveaux_cycles': darveaux
                })
                if darveaux < worst_darveaux:
                    worst_darveaux = darveaux
                    worst_pad = pad_results[-1]

            status = "PASS" if min(worst_darveaux, norris_cycles) > 5000 else "WARNING"
            # Return an average or a structured report.
            return {
                'darveaux_cycles': worst_darveaux,
                'norris_landzberg_cycles': norris_cycles,
                'status': status,
                'delta_T': delta_T,
                'pad_results': pad_results,
                'worst_pad': worst_pad,
                'pad_count': len(pads)
            }
        else:
            # Fallback for single average pad (JSON mode)
            pad_geom = {'equivalent_diameter': geometry.get('pad_diameter', 0.5), 'solder_height': solder_height}
            darveaux = self._calculate_darveaux_life(delta_T, pad_geom)
            status = "PASS" if min(darveaux, norris_cycles) > 5000 else "WARNING"

            return {
                'darveaux_cycles': darveaux,
                'norris_landzberg_cycles': norris_cycles,
                'status': status,
                'delta_T': delta_T,
                'pad_results': [],
                'worst_pad': None,
                'pad_count': 1
            }

# --- Quick test block ---
if __name__ == "__main__":
    engine = ThermoMechanicalEngine({})

    # Test with single pad (JSON mode)
    print("--- Test 1: Single Pad ---")
    single_pad_data = {
        'delta_T': 150,
        'T_max': 400,
        'frequency': 2,
        'geometry': {'solder_height': 0.08, 'pad_diameter': 0.4}
    }
    print(engine.run_full_analysis(single_pad_data))

    # Test with multiple pads (KiCad mode)
    print("\n--- Test 2: Multi-Pad Board ---")
    multi_pad_data = {
        'delta_T': 150,
        'T_max': 400,
        'frequency': 2,
        'geometry': {
            'solder_height': 0.08,
            'pads': [
                {'x': 0, 'y': 0, 'equivalent_diameter': 1.7},
                {'x': 0, 'y': 2.54, 'equivalent_diameter': 1.7},
                {'x': -1, 'y': 0, 'equivalent_diameter': 1.14},
                {'x': 1, 'y': 0, 'equivalent_diameter': 1.14},
                {'x': -2.47, 'y': -1.905, 'equivalent_diameter': 0.96},
                {'x': -2.47, 'y': 1.905, 'equivalent_diameter': 0.96}
            ]
        }
    }
    result = engine.run_full_analysis(multi_pad_data)
    print(f"Worst-case Darveaux Cycles: {result['darveaux_cycles']}")
    print(f"Norris-Landzberg Cycles: {result['norris_landzberg_cycles']}")
    print(f"Status: {result['status']}")
    print(f"Worst Pad: {result['worst_pad']}")