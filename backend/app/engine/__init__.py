"""
核心線路分析引擎模組 (Schematic Analysis Engine)
"""

from backend.app.engine.archive import extract_archive, find_schematic_files
from backend.app.engine.parser import parse_orcad_xml, parse_allegro_netlist, merge_schematic_data
from backend.app.engine.graph import (
    build_schematic_graph,
    get_components_on_net,
    get_nets_of_component,
    is_power_net,
    is_ground_net,
    detect_bus_type,
)
from backend.app.engine.pre_analyzer import analyze_schematic_features
from backend.app.engine.net_classifier import classify_nets_batch, classify_single_net_heuristic
from backend.app.engine.cleaner import (
    get_directory_size_and_count,
    get_all_storage_stats,
    cleanup_expired_files,
    cleanup_task_artifacts,
)

__all__ = [
    "extract_archive",
    "find_schematic_files",
    "parse_orcad_xml",
    "parse_allegro_netlist",
    "merge_schematic_data",
    "build_schematic_graph",
    "classify_nets_batch",
    "classify_single_net_heuristic",
    "get_components_on_net",
    "get_nets_of_component",
    "is_power_net",
    "is_ground_net",
    "detect_bus_type",
    "analyze_schematic_features",
    "get_directory_size_and_count",
    "get_all_storage_stats",
    "cleanup_expired_files",
    "cleanup_task_artifacts",
]
