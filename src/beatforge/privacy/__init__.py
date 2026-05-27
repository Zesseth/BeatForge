"""Privacy primitives.

This sub-package contains the egress allow-list and helpers the runtime test
harness uses to verify BeatForge never leaks audio.
"""

from .egress_allowlist import ALLOWED_HOSTS, is_host_allowed

__all__ = ["ALLOWED_HOSTS", "is_host_allowed"]
