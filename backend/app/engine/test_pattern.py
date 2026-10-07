import sys
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(base_dir, '..', '..'))

from backend.app.engine.pattern_engine import get_component_engine

def test_engine():
    engine = get_component_engine()
    patterns_dir = os.path.join(base_dir, "..", "..", "patterns", "components")
    engine.load_rules(patterns_dir)
    
    # Test a Resistor
    res, rule = engine.classify(ref_des="R101", part_value="10K", description="RES, 10K 1%", package="0402", mfg_pn="", pins_count=2)
    print("R101:", res, rule)
    
    # Test an MCU
    res, rule = engine.classify(ref_des="U1", part_value="", description="IC, MCU 32-BIT", package="", mfg_pn="STM32F103", pins_count=48)
    print("U1:", res, rule)
    
    # Test a Fiducial
    res, rule = engine.classify(ref_des="FD1", part_value="", description="FIDUCIAL MARK", package="FD55_CROSS", mfg_pn="", pins_count=0)
    print("FD1:", res, rule)

if __name__ == "__main__":
    test_engine()
