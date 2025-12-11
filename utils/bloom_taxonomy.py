"""
Bloom taxonomy utilities for difficulty level management.
"""
from typing import List

BLOOM_LEVELS = [
    "REMEMBER",
    "UNDERSTAND",
    "APPLY",
    "ANALYZE",
    "EVALUATE",
    "CREATE"
]


def get_included_levels(selected_level: str) -> List[str]:
    """
    Get all Bloom levels included when a level is selected.
    Higher levels include all lower levels.
    
    Args:
        selected_level: Selected Bloom level
        
    Returns:
        List of included levels
    """
    if selected_level not in BLOOM_LEVELS:
        return []
    
    selected_index = BLOOM_LEVELS.index(selected_level)
    return BLOOM_LEVELS[:selected_index + 1]


