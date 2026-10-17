# parser.py
import json
import os
import math
from kiutils.board import Board
import gerbonara

class DesignParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.thermal_defaults = {
            'delta_T': 150,
            'T_max': 400,
            'frequency': 2,
            'solder_height': 0.08
        }

    def parse(self):
        """
        Parses a design file based on its extension.
        Supports .json, .kicad_pcb, and various Gerber extensions (.gbr, .gtl, .gbl, etc.)
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Design file {self.file_path} not found.")

        ext = os.path.splitext(self.file_path)[1].lower()
        
        # Standard KiCad Gerber extensions
        gerber_exts = ['.gbr', '.gtl', '.gbl', '.gts', '.gbs', '.gto', '.gbo', '.gko', '.gm1', '.drl']

        if ext == '.kicad_pcb':
            return self._parse_kicad()
        elif ext in gerber_exts:
            return self._parse_gerber()
        elif ext == '.json':
            return self._parse_json()
        else:
            raise ValueError(f"Unsupported file format: {ext}. Please provide .json, .kicad_pcb, or a Gerber file.")

    def _parse_json(self):
        """Parses a simplified JSON configuration (fallback mode)."""
        with open(self.file_path, 'r') as f:
            data = json.load(f)

        return {
            'delta_T': data.get('thermal_conditions', {}).get('delta_T', self.thermal_defaults['delta_T']),
            'T_max': data.get('thermal_conditions', {}).get('max_temp', self.thermal_defaults['T_max']),
            'frequency': data.get('thermal_conditions', {}).get('frequency', self.thermal_defaults['frequency']),
            'geometry': {
                'solder_height': data.get('geometry', {}).get('solder_height', self.thermal_defaults['solder_height']),
                'pad_diameter': data.get('geometry', {}).get('pad_diameter', 0.5),
                'pads': []
            }
        }

    def _parse_kicad(self):
        """Parses a .kicad_pcb file using kiutils."""
        board = Board.from_file(self.file_path)
        
        pads = []
        total_pad_diameter = 0
        pad_count = 0

        # Iterate through all footprints to find pads
        for footprint in board.footprints:
            for pad in footprint.pads:
                pos_x = pad.position.X
                pos_y = pad.position.Y
                width = pad.size.X
                height = pad.size.Y
                
                if pad.shape in ['circle', 'rect']:
                    equivalent_diameter = math.sqrt(width * height)
                else:
                    equivalent_diameter = (width + height) / 2
                
                pads.append({
                    'x': pos_x,
                    'y': pos_y,
                    'width': width,
                    'height': height,
                    'shape': pad.shape,
                    'equivalent_diameter': equivalent_diameter
                })
                
                total_pad_diameter += equivalent_diameter
                pad_count += 1

        avg_pad_diameter = (total_pad_diameter / pad_count) if pad_count > 0 else 0.5
        
        # Approximate board size from pad bounding box
        board_size = None
        if pads:
            min_x = min(p['x'] for p in pads)
            max_x = max(p['x'] for p in pads)
            min_y = min(p['y'] for p in pads)
            max_y = max(p['y'] for p in pads)
            board_size = (max_x - min_x, max_y - min_y)

        return {
            'delta_T': self.thermal_defaults['delta_T'],
            'T_max': self.thermal_defaults['T_max'],
            'frequency': self.thermal_defaults['frequency'],
            'geometry': {
                'solder_height': self.thermal_defaults['solder_height'],
                'pad_diameter': avg_pad_diameter,
                'pads': pads,
                'pad_count': pad_count,
                'board_size': board_size
            }
        }

    def _parse_gerber(self):
        """Parses a Gerber file using gerbonara."""
        try:
            gerber = gerbonara.rs274x.GerberFile.open(self.file_path)
        except Exception as e:
            raise ValueError(f"Failed to open Gerber file: {e}")

        pads = []
        total_pad_diameter = 0
        pad_count = 0

        for obj in gerber.objects:
            if isinstance(obj, gerbonara.graphic_objects.Flash):
                aperture = obj.tool
                diameter = getattr(aperture, 'diameter', 0.5)
                
                pads.append({
                    'x': obj.x,
                    'y': obj.y,
                    'diameter': diameter,
                    'equivalent_diameter': diameter
                })
                
                total_pad_diameter += diameter
                pad_count += 1

        avg_pad_diameter = (total_pad_diameter / pad_count) if pad_count > 0 else 0.5

        return {
            'delta_T': self.thermal_defaults['delta_T'],
            'T_max': self.thermal_defaults['T_max'],
            'frequency': self.thermal_defaults['frequency'],
            'geometry': {
                'solder_height': self.thermal_defaults['solder_height'],
                'pad_diameter': avg_pad_diameter,
                'pads': pads,
                'pad_count': pad_count
            }
        }

# --- Quick test block ---
if __name__ == "__main__":
    # 1. Test JSON Parser
    dummy_data = {
        "thermal_conditions": {"delta_T": 120, "max_temp": 380, "frequency": 5},
        "geometry": {"solder_height": 0.09, "pad_diameter": 0.45}
    }
    with open("dummy_design.json", "w") as f:
        json.dump(dummy_data, f)

    print("--- Testing JSON Parser ---")
    parser_json = DesignParser("dummy_design.json")
    print(parser_json.parse())

    # 2. Test KiCad Parser
    print("\n--- Testing KiCad Parser ---")
    try:
        parser_kicad = DesignParser("Data/pcb_aerospace.kicad_pcb")
        result_kicad = parser_kicad.parse()
        print(f"Board size (approx): {result_kicad['geometry'].get('board_size', 'N/A')}")
        print(f"Extracted {result_kicad['geometry']['pad_count']} pads.")
        print(f"Average pad diameter: {result_kicad['geometry']['pad_diameter']:.4f} mm")
    except Exception as e:
        print(f"KiCad parsing failed: {e}")

    # 3. Test Gerber Parser (Top Copper layer)
    print("\n--- Testing Gerber Parser (.gtl) ---")
    try:
        parser_gerber = DesignParser("Data/gerbers/pcb_aerospace-F_Cu.gtl")
        result_gerber = parser_gerber.parse()
        print(f"Extracted {result_gerber['geometry']['pad_count']} flashes (pads).")
        print(f"Average pad diameter: {result_gerber['geometry']['pad_diameter']:.4f} mm")
    except Exception as e:
        print(f"Gerber parsing failed: {e}")