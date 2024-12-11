"""Testing module."""

from __future__ import annotations


def test_register() -> None:
    """Test the register function."""
    from parsl_object_registry import registry

    # Reset the registry to clear any previous state from other tests
    registry.clear()

    # Variables to track the number of calls to the constructor and shutdown
    first_constructor_calls = first_shutdown_calls = 0
    second_constructor_calls = second_shutdown_calls = 0

    def my_first_shutdown_callback(obj: int) -> None:
        print(f'First shutting down {obj}')
        nonlocal first_shutdown_calls
        first_shutdown_calls += 1

    def my_second_shutdown_callback(obj: int) -> None:
        print(f'Second shutting down {obj}')
        nonlocal second_shutdown_calls
        second_shutdown_calls += 1

    class MyFirstClass:
        def __init__(self, x: int) -> None:
            self.x = x
            print(f'My first class initialized with x={x}')
            nonlocal first_constructor_calls
            first_constructor_calls += 1

    class MySecondClass:
        def __init__(self, x: int) -> None:
            self.x = x
            print(f'My second class initialized with x={x}')
            nonlocal second_constructor_calls
            second_constructor_calls += 1

    # Register the classes
    registry.register(MyFirstClass, my_first_shutdown_callback)
    registry.register(MySecondClass, my_second_shutdown_callback)

    # Instantiate the singleton
    obj = registry.get(MyFirstClass, 1)
    obj_id = id(obj)
    # Hold a reference to this object until the end of the test because
    # id() is based on the memory location of the object and we don't want
    # another object to be allocated the same memory address once this one
    # is garbage collected.
    _obj_id_ref = obj
    assert obj.x == 1
    assert first_constructor_calls == 1
    assert first_shutdown_calls == 0

    # Another get should return the same object as before
    obj = registry.get(MyFirstClass, 1)
    assert id(obj) == obj_id
    assert obj.x == 1
    assert first_constructor_calls == 1
    assert first_shutdown_calls == 0

    # Change the value of x should return a different object and call
    # the shutdown callback
    obj = registry.get(MyFirstClass, 3)
    assert obj.x == 3
    assert id(obj) != obj_id
    assert first_constructor_calls == 2
    assert first_shutdown_calls == 1

    # Changing the class should call the shutdown hook of the first class
    obj = registry.get(MySecondClass, 4)
    assert obj.x == 4
    assert id(obj) != obj_id
    assert second_constructor_calls == 1
    assert second_shutdown_calls == 0
    assert first_constructor_calls == 2
    assert first_shutdown_calls == 2

    # Getting the first class again should call the shutdown hook of the second
    # and instantiate a fresh instance of the first class
    obj = registry.get(MyFirstClass, 1)
    assert obj.x == 1
    assert second_constructor_calls == 1
    assert second_shutdown_calls == 1
    assert first_constructor_calls == 3
    assert first_shutdown_calls == 2


def test_registry_singleton() -> None:
    """Test the registry singleton."""
    from parsl_object_registry import registry
    from parsl_object_registry import RegistrySingleton

    # Reset the registry to clear any previous state from other tests
    registry.clear()

    # Variables to track the number of calls to the constructor and shutdown
    first_constructor_calls = first_shutdown_calls = 0

    class MyFirstClass:
        def __init__(self, x: int) -> None:
            self.x = x
            print(f'My first class initialized with x={x}')
            nonlocal first_constructor_calls
            first_constructor_calls += 1

    def my_first_shutdown_callback(obj: int) -> None:
        print(f'First shutting down {obj}')
        nonlocal first_shutdown_calls
        first_shutdown_calls += 1

    # Register the the class
    registry.register(MyFirstClass, my_first_shutdown_callback)

    # Instantiate the singleton
    obj = registry.get(MyFirstClass, 1)
    obj_id = id(obj)
    assert obj.x == 1
    assert first_constructor_calls == 1
    assert first_shutdown_calls == 0

    # Make a new registry
    new_registry = RegistrySingleton()

    # Register the class again
    new_registry.register(MyFirstClass, my_first_shutdown_callback)

    # Instantiate the singleton
    obj = new_registry.get(MyFirstClass, 1)
    # The new registry should keep the old instance
    assert obj.x == 1
    assert id(obj) == obj_id
    assert first_constructor_calls == 1
    assert first_shutdown_calls == 0


def test_registry_class_decorator() -> None:
    """Test the registry class decorator."""
    from parsl_object_registry import register
    from parsl_object_registry import registry

    # Reset the registry to clear any previous state from other tests
    registry.clear()

    # Variables to track the number of calls to the constructor and shutdown
    first_constructor_calls = first_shutdown_calls = 0
    second_constructor_calls = second_shutdown_calls = 0

    def my_first_shutdown_callback(obj: int) -> None:
        print(f'First shutting down {obj}')
        nonlocal first_shutdown_calls
        first_shutdown_calls += 1

    def my_second_shutdown_callback(obj: int) -> None:
        print(f'Second shutting down {obj}')
        nonlocal second_shutdown_calls
        second_shutdown_calls += 1

    @register(shutdown_callback=my_first_shutdown_callback)
    class MyFirstClass:
        def __init__(self, x: int) -> None:
            self.x = x
            print(f'My first class initialized with x={x}')
            nonlocal first_constructor_calls
            first_constructor_calls += 1

    @register(shutdown_callback=my_second_shutdown_callback)
    class MySecondClass:
        def __init__(self, x: int) -> None:
            self.x = x
            print(f'My second class initialized with x={x}')
            nonlocal second_constructor_calls
            second_constructor_calls += 1

    # Instantiate the singleton
    obj = MyFirstClass(1)
    obj_id = id(obj)
    # Hold a reference to this object until the end of the test because
    # id() is based on the memory location of the object and we don't want
    # another object to be allocated the same memory address once this one
    # is garbage collected.
    _obj_id_ref = obj
    assert obj.x == 1
    assert first_constructor_calls == 1
    assert first_shutdown_calls == 0

    # Another get should return the same object as before
    obj = MyFirstClass(1)
    assert id(obj) == obj_id
    assert obj.x == 1
    assert first_constructor_calls == 1
    assert first_shutdown_calls == 0

    # Change the value of x should return a different object and call the shutdown callback
    obj = MyFirstClass(3)
    assert obj.x == 3
    assert id(obj) != obj_id
    assert first_constructor_calls == 2
    assert first_shutdown_calls == 1

    # Changing the class should call the shutdown hook of the first class
    obj = MySecondClass(4)
    assert obj.x == 4
    assert id(obj) != obj_id
    assert second_constructor_calls == 1
    assert second_shutdown_calls == 0
    assert first_constructor_calls == 2
    assert first_shutdown_calls == 2

    # Getting the first class again should call the shutdown hook of the second
    # and instantiate a fresh instance of the first class
    obj = MyFirstClass(1)
    assert obj.x == 1
    assert second_constructor_calls == 1
    assert second_shutdown_calls == 1
    assert first_constructor_calls == 3
    assert first_shutdown_calls == 2


def test_registry_fn_decorators() -> None:
    """Test the registry function decorators."""
    from parsl_object_registry import register
    from parsl_object_registry import registry

    # Reset the registry to clear any previous state from other tests
    registry.clear()

    # Variables to track the number of calls to the constructor and shutdown
    first_fn_calls = first_shutdown_calls = 0
    second_fn_calls = second_shutdown_calls = 0

    def my_first_shutdown_callback(obj) -> None:
        print(f'First shutting down {obj}')
        nonlocal first_shutdown_calls
        first_shutdown_calls += 1

    def my_second_shutdown_callback(obj) -> None:
        print(f'Second shutting down {obj}')
        nonlocal second_shutdown_calls
        second_shutdown_calls += 1

    @register(shutdown_callback=my_first_shutdown_callback)
    def my_first_fn(x: int) -> int:
        print(f'my_first_fn called with x={x}')
        nonlocal first_fn_calls
        first_fn_calls += 1
        return x

    @register(shutdown_callback=my_second_shutdown_callback)
    def my_second_fn(x: int) -> int:
        print(f'my_first_fn called with x={x}')
        nonlocal second_fn_calls
        second_fn_calls += 1
        return x

    # Instantiate the singleton
    obj = my_first_fn(1)
    obj_id = id(obj)
    # Hold a reference to this object until the end of the test because
    # id() is based on the memory location of the object and we don't want
    # another object to be allocated the same memory address once this one
    # is garbage collected.
    _obj_id_ref = obj
    assert obj == 1
    assert first_fn_calls == 1
    assert first_shutdown_calls == 0

    # Another get should return the same object as before
    obj = my_first_fn(1)
    assert id(obj) == obj_id
    assert obj == 1
    assert first_fn_calls == 1
    assert first_shutdown_calls == 0

    # Change the value of x should return a different object and call the shutdown callback
    obj = my_first_fn(3)
    assert obj == 3
    assert id(obj) != obj_id
    assert first_fn_calls == 2
    assert first_shutdown_calls == 1

    # Changing the class should call the shutdown hook of the first class
    obj = my_second_fn(4)
    assert obj == 4
    assert id(obj) != obj_id
    assert second_fn_calls == 1
    assert second_shutdown_calls == 0
    assert first_fn_calls == 2
    assert first_shutdown_calls == 2

    # Getting the first class again should call the shutdown hook of the second
    # and instantiate a fresh instance of the first class
    obj = my_first_fn(1)
    assert obj == 1
    assert second_fn_calls == 1
    assert second_shutdown_calls == 1
    assert first_fn_calls == 3
    assert first_shutdown_calls == 2


def test_default_shutdown_callback() -> None:
    """Test the default shutdown callback."""
    from parsl_object_registry import register
    from parsl_object_registry import registry

    # Reset the registry to clear any previous state from other tests
    registry.clear()

    # Variables to track the number of calls to the constructor and shutdown
    first_fn_calls = 0

    @register()
    def my_first_fn(x: int) -> int:
        print(f'my_first_fn called with x={x}')
        nonlocal first_fn_calls
        first_fn_calls += 1
        return x

    # Instantiate the singleton
    obj = my_first_fn(1)
    obj_id = id(obj)
    # Hold a reference to this object until the end of the test because
    # id() is based on the memory location of the object and we don't want
    # another object to be allocated the same memory address once this one
    # is garbage collected.
    _obj_id_ref = obj

    assert obj == 1
    assert first_fn_calls == 1

    # Another get should return the same object as before
    obj = my_first_fn(1)
    assert id(obj) == obj_id
    assert obj == 1
    assert first_fn_calls == 1

    # Change the value of x should return a different object and call the shutdown callback
    obj = my_first_fn(3)
    assert obj == 3
    assert id(obj) != obj_id
    assert first_fn_calls == 2
