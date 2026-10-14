"""Base entity for Hager Witty Solar."""
from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from ..coordinator.base import WittySolarDataUpdateCoordinator

class WittySolarEntity(CoordinatorEntity[WittySolarDataUpdateCoordinator]):
    """Base representation of a Witty Solar entity."""

    def __init__(self, coordinator: WittySolarDataUpdateCoordinator, name: str, unique_id: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_name = f"Witty Solar {name}"
        self._attr_unique_id = f"witty_solar_{unique_id}"