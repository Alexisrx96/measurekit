import configparser
from typing import Optional, Self


class Config:
    """Clase Singleton para gestionar la configuración de la librería MeasureKit."""

    _instance: Optional[Self] = None

    # --- Atributos que serán poblados desde los archivos .conf ---
    settings: dict[str, str] = {}
    dimension_definitions: dict[str, str] = {}
    prefix_definitions: dict[str, str] = {}
    unit_definitions: dict[str, str] = {}
    constant_definitions: dict[str, str] = {}

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_setting(
        self, key: str, default: Optional[str] = None
    ) -> Optional[str]:
        """Obtiene un valor de la sección [Settings]."""
        return self.settings.get(key, default)

    def clear(self) -> None:
        """Limpia la configuración cargada."""
        self.settings.clear()
        self.dimension_definitions.clear()
        self.prefix_definitions.clear()
        self.unit_definitions.clear()
        self.constant_definitions.clear()
        self.parser = configparser.ConfigParser()


config = Config()
