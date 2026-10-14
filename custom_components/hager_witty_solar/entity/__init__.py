"""
Entity package for the Hager Witty Modbus integration.

Architecture:
    All platform entities inherit from (PlatformEntity, WittyEntity).
    MRO order matters - platform-specific class first, then the integration base.
    Entities read data from coordinator.data and NEVER call the Modbus client directly;
    writes go through WittyCoordinator.async_write_value().
    Unique IDs follow the pattern: {wallbox_id}_{description.key}

See entity/base.py for the WittyEntity base class.
"""

from .base import WittyEntity

__all__ = ["WittyEntity"]
