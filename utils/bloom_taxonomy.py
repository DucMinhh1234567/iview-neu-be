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

BLOOM_TO_DIFFICULTY = {
    "REMEMBER": "EASY",
    "UNDERSTAND": "EASY",
    "APPLY": "MEDIUM",
    "ANALYZE": "MEDIUM",
    "EVALUATE": "HARD",
    "CREATE": "HARD"
}


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


def bloom_to_difficulty(bloom_level: str) -> str:
    """
    Convert Bloom level to question difficulty.
    
    Args:
        bloom_level: Bloom taxonomy level
        
    Returns:
        Difficulty level (EASY, MEDIUM, HARD)
    """
    return BLOOM_TO_DIFFICULTY.get(bloom_level, "MEDIUM")

