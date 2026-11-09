"""Pre-specified analysis choices; no test-driven configuration."""

SEED = 42
TARGET = "A170"
CORE = ("X001", "X003", "X025R", "X028", "X047E_EVS5", "A009", "A165", "A173", "cntry_AN")
DEMOGRAPHIC = ("X001", "X003", "X025R", "X028", "X047E_EVS5", "cntry_AN")
WITH_HAPPINESS = (*CORE, "A008")
SUPPORT = {"X001": (1, 2), "X003": (18, 82), "X025R": (1, 3),
           "X028": (1, 8), "X047E_EVS5": (1, 10), "A009": (1, 5),
           "A165": (1, 2), "A173": (1, 10), "A008": (1, 4)}
MISSING = (-1, -2, -3, -4, -5)
SCHEMA_VERSION = 1
