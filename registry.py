import functools
import inspect
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Type, Union

# Represents a function or class type
ClassFn = Union[Callable[..., object], Type[object]]


class RegistrySingleton:
    """A registry for managing singleton objects.
    Only one object in the registry can be active at a time.

    Example
    -------
    Register a class once and then get the singleton instance:

    >>> from viral_ppi_llm.registry import registry, clear_torch_cuda_memory_callback

    >>> registry.register(MyExpensiveTorchClass, clear_torch_cuda_memory_callback)
    >>> my_object = registry.get(MyExpensiveTorchClass, *args, **kwargs)
    """

    @dataclass
    class Instance:
        """Store an instance of an object and a shutdown hook."""

        shutdown_callback: Callable
        obj: Optional[object] = None
        arg_hash: int = 0

        def shutdown(self) -> None:
            """Shutdown the object."""
            if self.obj is not None:
                self.shutdown_callback(self.obj)
                self.obj = None
                self.arg_hash = 0

    _registry: Dict[str, Instance]
    _active: str

    def __new__(cls):
        """Create a singleton instance of the registry."""
        if not hasattr(cls, "_instance"):
            cls._instance = super(RegistrySingleton, cls).__new__(cls)
            cls._instance._registry = {}
            cls._instance._active = ""
        return cls._instance

    def __contains__(self, cls_fn: ClassFn) -> bool:
        """Check if an object type is in the registry."""
        return cls_fn.__name__ in self._registry

    def clear(self) -> None:
        """Clear the registry."""
        for obj in self._registry.values():
            obj.shutdown_callback(obj.obj)
        self._registry = {}
        self._active = ""

    def register(
        self, cls_fn: ClassFn, shutdown_callback: Callable = lambda x: x
    ) -> None:
        """Register an object type with the registry."""
        name = cls_fn.__name__
        if name not in self._registry:
            self._registry[name] = RegistrySingleton.Instance(shutdown_callback)

    def get(self, cls_fn: ClassFn, *args, **kwargs) -> Any:
        """Get an object from the registry."""

        # Get the hash of the input arguments to effectively implment an LRU cache
        # with size 1 but with the ability to handle multiple function/class types
        # while only keeping one object active at a time.
        name = cls_fn.__name__
        key = hash(functools._make_key((name,) + args, kwargs, typed=False))

        # Raise an error if the object is not registered
        if name not in self._registry:
            raise ValueError(f"Object {name} not registered.")

        # If the object is already active, then return the previously instantiated object
        if name == self._active and key == self._registry[name].arg_hash:
            return self._registry[name].obj

        # Shutdown the current active object, if it exists
        active = self._registry.get(self._active, None)
        if active is not None:
            active.shutdown()

        # Instantiate the new object
        obj = cls_fn(*args, **kwargs)

        # Set the new active object
        self._active = name
        self._registry[name].obj = obj
        self._registry[name].arg_hash = key

        return obj


# Singleton registry
registry = RegistrySingleton()


def _register_fn_decorator(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return registry.get(fn, *args, **kwargs)

    return wrapper


def _register_cls_decorator(cls):
    @functools.wraps(cls, updated=())
    class SingletonWrapper(cls):
        def __new__(__cls, *args, **kwargs):
            # Note: We are always calling the registry with the original class.
            # If we called it with this __cls then we would get an infinite recursion
            # loop because __cls is a subclass of cls and the registry would try to
            # instantiate the subclass which would call this method, and the registry
            # again, etc. Instead, we want to instantiate the original class by calling
            # the cls.__init__ in the registry.get method.
            return registry.get(cls, *args, **kwargs)

    return SingletonWrapper


def register(shutdown_callback: Callable = lambda x: x):
    """Register a function or class with the registry.

    Example
    -------
    Register a function once and then get the singleton instance in future calls:

    >>> @register(shutdown_callback=clear_torch_cuda_memory_callback)
    >>> def my_expensive_torch_function(*args, **kwargs):
    ...     # Expensive initialization
    ...     return torch_model

    >>> my_object = my_expensive_torch_function(*args, **kwargs)

    Register a class once and then get the singleton instance in future calls:

    >>> @register(shutdown_callback=clear_torch_cuda_memory_callback)
    >>> class MyExpensiveTorchClass:
    ...     def __init__(self, *args, **kwargs) -> None:
    ...         # Expensive initialization
    ...         ...

    >>> my_object = MyExpensiveTorchClass(*args, **kwargs)
    """

    # Note: If a type hint is used, it messes up the intelisense of the
    # decorated function/class. The type should be ClassFn.
    def decorator(cls_fn):
        # Register the class/fn immediately when the module is imported
        registry.register(cls_fn, shutdown_callback)

        if inspect.isclass(cls_fn):
            return _register_cls_decorator(cls_fn)
        else:
            return _register_fn_decorator(cls_fn)

    return decorator


def clear_torch_cuda_memory_callback(obj: object) -> None:
    """Clear the torch cuda memory of a given object."""
    import gc

    import torch

    del obj
    gc.collect()
    torch.cuda.empty_cache()
