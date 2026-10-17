"""Gemeinsame Basis-Entity für die Witty-Solar-Integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WittySolarCoordinator


class WittySolarEntity(CoordinatorEntity[WittySolarCoordinator]):
    """Basisklasse, die allen Entities dieser Integration das DeviceInfo liefert."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WittySolarCoordinator,
        description: EntityDescription,
        entry_id: str,
    ) -> None:
        """Initialisiere die Entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

        serial = coordinator.device_info_data.get("serial_number") or entry_id
        product = coordinator.device_info_data.get("product_reference")
        manufacturer = coordinator.device_info_data.get("manufacturer") or "Hager"
        sw_version = coordinator.device_info_data.get("software_version")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Witty Solar Wallbox",
            manufacturer=manufacturer,
            model=product or "Witty (EVCS/B1280)",
            sw_version=sw_version,
            serial_number=serial,
            configuration_url=f"http://{coordinator.host}",
        )
