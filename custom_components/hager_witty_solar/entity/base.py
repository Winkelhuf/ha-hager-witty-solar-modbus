"""Basis-Entitätsklasse für die Hager Witty Modbus Integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from homeassistant.helpers.entity import EntityDescription

    from ..coordinator import WittyCoordinator


class WittyEntity(CoordinatorEntity["WittyCoordinator"]):
    """Basis-Entität: Geräteinformationen, eindeutige ID und Übersetzungsschlüssel."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WittyCoordinator,
        entity_description: EntityDescription,
        data_key: str | None = None,
    ) -> None:
        """Initialisierung der Entität.

        ``data_key`` is the key in ``coordinator.data`` that must be present for the
        entity to be available (defaults to the description key).
        """
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._data_key = data_key or entity_description.key

        # Der Name kommt ausschließlich aus translations/<sprache>.json
        # (entity.<plattform>.<key>.name). Home Assistant setzt den Gerätenamen
        # wegen has_entity_name automatisch davor.
        self._attr_translation_key = entity_description.translation_key or entity_description.key
        self._attr_unique_id = f"{coordinator.wallbox_id}_{entity_description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Entity is available if the last update worked and its register was read."""
        return super().available and self.coordinator.data.get(self._data_key) is not None
