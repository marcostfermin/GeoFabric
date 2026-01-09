"""Plugin registry with type-safe generics.

This module provides a type-safe registry for sources, engines, and sinks
using Python generics and protocols for improved static analysis.

Design Patterns Used:
- Factory Pattern: SourceClassFactory provides a generic way to create source factories
- Registry Pattern: ComponentRegistry provides centralized component lookup
- Plugin Architecture: Entry points enable extensibility without core modification
"""

from __future__ import annotations

import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from geofabric.errors import NotFoundError

if TYPE_CHECKING:
    from geofabric.protocols import Engine, Sink, Source

__all__ = [
    "ComponentRegistry",
    "EngineClassFactory",
    "Factory",
    "Registry",
    "SinkClassFactory",
    "SourceClassFactory",
    "SourceFactory",
]

# Type variables for generic registry
T = TypeVar("T")
SourceT = TypeVar("SourceT", bound="Source")
EngineT = TypeVar("EngineT", bound="Engine")
SinkT = TypeVar("SinkT", bound="Sink")

# Factory type aliases with better typing
Factory = Callable[[], Any]
SourceFactory = Callable[[], type["Source"]]


class SourceClassFactory(Generic[SourceT]):
    """Generic factory for source classes.

    This eliminates boilerplate by providing a reusable factory pattern.
    Instead of creating a new factory class for each source type:

        class FilesSourceFactory:
            def __call__(self) -> type[FilesSource]:
                return FilesSource

    You can use:

        FilesSourceFactory = SourceClassFactory(FilesSource)

    Design Principle: DRY (Don't Repeat Yourself)
    The factory pattern is common across all sources, so we extract it
    into a single parameterized class.

    Example:
        >>> from geofabric.sources.files import FilesSource
        >>> factory = SourceClassFactory(FilesSource)
        >>> source_cls = factory()  # Returns FilesSource class
        >>> source = source_cls.from_uri("file:///path/to/file.parquet")
    """

    __slots__ = ("_source_class",)

    def __init__(self, source_class: type[SourceT]) -> None:
        """Initialize factory with the source class to produce.

        Args:
            source_class: The source class this factory will return
        """
        self._source_class = source_class

    def __call__(self) -> type[SourceT]:
        """Return the source class.

        Returns:
            The source class passed to __init__
        """
        return self._source_class

    def __repr__(self) -> str:
        return f"SourceClassFactory({self._source_class.__name__})"


class EngineClassFactory(Generic[EngineT]):
    """Generic factory for engine instances.

    Unlike SourceClassFactory which returns a class, this returns
    an instance since engines are typically stateful singletons.

    Example:
        >>> from geofabric.engines.duckdb_engine import DuckDBEngine
        >>> factory = EngineClassFactory(DuckDBEngine)
        >>> engine = factory()  # Returns DuckDBEngine instance
    """

    __slots__ = ("_engine_class",)

    def __init__(self, engine_class: type[EngineT]) -> None:
        self._engine_class = engine_class

    def __call__(self) -> EngineT:
        """Return a new engine instance."""
        return self._engine_class()

    def __repr__(self) -> str:
        return f"EngineClassFactory({self._engine_class.__name__})"


class SinkClassFactory(Generic[SinkT]):
    """Generic factory for sink instances.

    Returns a new sink instance each time called.

    Example:
        >>> from geofabric.sinks.pmtiles import PMTilesSink
        >>> factory = SinkClassFactory(PMTilesSink)
        >>> sink = factory()  # Returns PMTilesSink instance
    """

    __slots__ = ("_sink_class",)

    def __init__(self, sink_class: type[SinkT]) -> None:
        self._sink_class = sink_class

    def __call__(self) -> SinkT:
        """Return a new sink instance."""
        return self._sink_class()

    def __repr__(self) -> str:
        return f"SinkClassFactory({self._sink_class.__name__})"


def _load_plugin_group(group: str) -> dict[str, Factory]:
    """Load plugins from an entry point group.

    Args:
        group: Entry point group name (e.g., 'geofabric.sources')

    Returns:
        Dictionary mapping plugin names to their factory callables

    Note:
        Plugin loading errors are caught and logged as warnings.
        Fatal errors (KeyboardInterrupt, SystemExit, MemoryError) propagate.
    """
    plugins: dict[str, Factory] = {}
    for ep in entry_points().select(group=group):
        try:
            plugins[ep.name] = ep.load()
        except (ImportError, AttributeError, TypeError, ModuleNotFoundError) as e:
            # These are the expected exceptions when loading plugins fails:
            # - ImportError/ModuleNotFoundError: Module not found or import cycle
            # - AttributeError: Entry point references non-existent attribute
            # - TypeError: Entry point is not callable
            plugin_type = group.split(".")[-1].rstrip("s")  # 'sources' -> 'source'
            warnings.warn(
                f"Failed to load {plugin_type} plugin '{ep.name}': {e}",
                stacklevel=3,
            )
    return plugins


@dataclass
class ComponentRegistry(Generic[T]):
    """Generic registry for a specific component type.

    Provides type-safe access to registered components with generics.
    This is a building block for the main Registry class.

    Example:
        source_registry: ComponentRegistry[Source] = ComponentRegistry(
            items={"files": FilesSourceFactory(), ...},
            kind="source"
        )
        source_factory = source_registry.get("files")
    """

    items: dict[str, Callable[[], T]] = field(default_factory=dict)
    kind: str = "component"

    def _validate_and_get_factory(self, name: str) -> Callable[[], T]:
        """Get factory or raise NotFoundError if not found.

        Internal helper to reduce code duplication between get() and get_factory().
        """
        if name not in self.items:
            raise NotFoundError(
                f"{self.kind.title()} '{name}' not found. "
                f"Available: {sorted(self.items)}",
                component_type=self.kind,
                component_name=name,
            )
        return self.items[name]

    def get(self, name: str) -> T:
        """Get a component by name.

        Args:
            name: The registered name of the component

        Returns:
            An instance of the component

        Raises:
            NotFoundError: If the component is not registered
        """
        factory = self._validate_and_get_factory(name)
        return factory()

    def get_factory(self, name: str) -> Callable[[], T]:
        """Get the factory for a component by name.

        Args:
            name: The registered name of the component

        Returns:
            The factory callable

        Raises:
            NotFoundError: If the component is not registered
        """
        return self._validate_and_get_factory(name)

    def register(self, name: str, factory: Callable[[], T]) -> None:
        """Register a new component.

        Args:
            name: The name to register under
            factory: A callable that returns a component instance
        """
        self.items[name] = factory

    def available(self) -> list[str]:
        """Return list of available component names."""
        return sorted(self.items.keys())

    def __contains__(self, name: str) -> bool:
        """Check if a component is registered."""
        return name in self.items


@dataclass
class Registry:
    """Registry of available sources, engines, and sinks.

    Provides centralized access to all GeoFabric plugins loaded from
    entry points. Uses type-safe generic registries internally.
    """

    sources: dict[str, Factory]
    engines: dict[str, Factory]
    sinks: dict[str, Factory]

    @staticmethod
    def load() -> Registry:
        """Load all plugins from entry points.

        Returns:
            A Registry with all discovered plugins loaded
        """
        return Registry(
            sources=_load_plugin_group("geofabric.sources"),
            engines=_load_plugin_group("geofabric.engines"),
            sinks=_load_plugin_group("geofabric.sinks"),
        )

    def _get_component_or_raise(
        self,
        name: str,
        component_dict: dict[str, Factory],
        component_type: str,
        call_factory: bool = True,
    ) -> Any:
        """Get a component from a registry dict or raise NotFoundError.

        Internal helper to reduce code duplication between get_engine, get_sink, get_source_factory.
        """
        if name not in component_dict:
            raise NotFoundError(
                f"{component_type.title()} '{name}' not found. "
                f"Available: {sorted(component_dict)}",
                component_type=component_type,
                component_name=name,
            )
        factory = component_dict[name]
        return factory() if call_factory else factory

    def get_engine(self, name: str) -> Engine:
        """Get an engine instance by name.

        Args:
            name: The registered engine name (e.g., 'duckdb')

        Returns:
            An engine instance

        Raises:
            NotFoundError: If the engine is not registered
        """
        return self._get_component_or_raise(name, self.engines, "engine", call_factory=True)

    def get_sink(self, name: str) -> Sink:
        """Get a sink instance by name.

        Args:
            name: The registered sink name (e.g., 'pmtiles')

        Returns:
            A sink instance

        Raises:
            NotFoundError: If the sink is not registered
        """
        return self._get_component_or_raise(name, self.sinks, "sink", call_factory=True)

    def get_source_factory(self, name: str) -> SourceFactory:
        """Get a source factory by name.

        Args:
            name: The registered source name (e.g., 'files', 's3')

        Returns:
            A factory that returns the source class

        Raises:
            NotFoundError: If the source is not registered
        """
        return self._get_component_or_raise(name, self.sources, "source", call_factory=False)

    def available_sources(self) -> list[str]:
        """Return list of available source names."""
        return sorted(self.sources.keys())

    def available_engines(self) -> list[str]:
        """Return list of available engine names."""
        return sorted(self.engines.keys())

    def available_sinks(self) -> list[str]:
        """Return list of available sink names."""
        return sorted(self.sinks.keys())

    def has_source(self, name: str) -> bool:
        """Check if a source is registered."""
        return name in self.sources

    def has_engine(self, name: str) -> bool:
        """Check if an engine is registered."""
        return name in self.engines

    def has_sink(self, name: str) -> bool:
        """Check if a sink is registered."""
        return name in self.sinks
