import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(base_dir, '..', '..'))

from backend.app.engine.pattern_engine import get_component_engine

def debug():
    engine = get_component_engine()
    patterns_dir = os.path.join(base_dir, "..", "..", "patterns", "components")
    engine.load_rules(patterns_dir)
    print(f"Loaded {len(engine.rules)} rules.")
    
    for rule in engine.rules:
        print(f"- {rule.name} (Priority: {rule.priority})")
        
    print("\nTesting with dummy resistor:")
    comp_data = {
        "ref_des": "R1",
        "part_value": "10K",
        "description": "RES, 10K",
        "package": "0402",
        "mfg_pn": "",
        "pins_count": 2
    }
    assign, rule_name = engine.classify(**comp_data)
    print(f"Result: {rule_name} -> {assign}")

if __name__ == "__main__":
    debug()
