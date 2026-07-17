import importlib.metadata
import logging
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)


class UnitRegistry:
    """A lazy-loading registry for physical units.

    This registry allows for units to be discovered via entry points and
    loaded only when accessed, reducing startup latency and improving
    extensibility.
    """

    def __init__(self):
        """Initializes the registry with empty cache and loaders."""
        self._registry: dict[str, Any] = {}
        self._lazy_loaders: dict[str, Any] = {}
        # name -> scope module suffix, resolved to "physure.units.<scope>"
        # only when actually accessed. See register_static.
        self._static_index: dict[str, str] = {}
        self._discovered = False

    def clear(self) -> None:
        """Clears all registered units and loaders. Useful for test isolation."""
        self._registry.clear()
        self._lazy_loaders.clear()
        # Rebind, don't .clear(): _static_index may be a shared reference to
        # physure.units.UNIT_INDEX (see register_static), and clearing it in
        # place would wipe that module's own lazy resolution too.
        self._static_index = {}
        self._discovered = False

    def register(self, name: str, unit: Any) -> None:
        """Adds a concrete unit to the registry.

        Core units should be registered here. If a conflict occurs,
        the first-registered unit (typically core) wins.
        """
        if name in self._registry:
            log.warning(f"Unit '{name}' is already registered. Skipping.")
            return
        self._registry[name] = unit

    def register_lazy(self, name: str, loader_func: Callable[[], Any]) -> None:
        """Adds a lazy loader for a unit."""
        if (
            name in self._registry
            or name in self._lazy_loaders
            or name in self._static_index
        ):
            return
        self._lazy_loaders[name] = loader_func

    def register_static(self, index: dict[str, str]) -> None:
        """Registers a name -> "physure.units.<scope>" index in bulk.

        Unlike register_lazy, this stores no per-entry closures and makes
        no copy: `index` (typically `physure.units.UNIT_INDEX`) is kept by
        reference, so this registry and `physure.units.__getattr__` share
        the same ~5.5k-entry dict instead of each holding their own copy.
        The `physure.units.<scope>` import + getattr only happens in
        __getattr__, on the exact name actually requested.
        """
        self._static_index = index

    def discover_plugins(self) -> None:
        """Scans entry points for the group 'physure.units'.

        This method populates the lazy loaders without importing the modules.
        """
        if self._discovered:
            return

        try:
            # importlib.metadata.entry_points(group=...) is standard since 3.10
            eps = importlib.metadata.entry_points(group="physure.units")
            for ep in eps:
                if (
                    ep.name not in self._registry
                    and ep.name not in self._lazy_loaders
                ):
                    self._lazy_loaders[ep.name] = ep
        except Exception:
            log.exception("Error discovering unit plugins")

        self._discovered = True

    def __getattr__(self, name: str) -> Any:
        """Retrieves a unit from the registry, loading it if necessary."""
        if name in self._registry:
            return self._registry[name]

        # Trigger discovery lazily
        if not self._discovered:
            self.discover_plugins()

        if name in self._lazy_loaders:
            loader = self._lazy_loaders.pop(name)
            try:
                # If it's an EntryPoint, load it.
                if hasattr(loader, "load"):
                    obj = loader.load()
                    # If the entry point is a factory, call it
                    unit = (
                        obj()
                        if callable(obj) and not hasattr(obj, "exponents")
                        else obj
                    )
                else:
                    # Generic loader function
                    unit = loader()

                self._registry[name] = unit
                return unit
            except Exception as e:
                log.exception("Failed to load unit plugin '%s'", name)
                raise AttributeError(
                    f"Unit '{name}' failed to load: {e}"
                ) from e

        if name in self._static_index:
            scope = self._static_index[name]
            try:
                module = importlib.import_module(f"physure.units.{scope}")
                unit = getattr(module, name)
                self._registry[name] = unit
                return unit
            except Exception as e:
                log.exception("Failed to load core unit '%s'", name)
                raise AttributeError(
                    f"Unit '{name}' failed to load: {e}"
                ) from e

        raise AttributeError(f"Unit '{name}' not found in registry.")

    @property
    def available_units(self) -> list[str]:
        """Returns a list of all available unit names."""
        if not self._discovered:
            self.discover_plugins()
        return sorted(
            set(self._registry)
            | set(self._lazy_loaders)
            | set(self._static_index)
        )

    def __dir__(self) -> list[str]:
        """Lists all available units for discovery (e.g. in notebooks)."""
        if not self._discovered:
            self.discover_plugins()
        return sorted(
            set(self._registry)
            | set(self._lazy_loaders)
            | set(self._static_index)
        )
