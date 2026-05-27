"""Generation primitives. See ROADMAP.md §Determinism policy.

All generators in this package must produce byte-identical output for the
same arguments + seed (M0–M3 contract). ``random.Random`` instances must
therefore be created from the explicit seed, never from the system entropy
pool.
"""
