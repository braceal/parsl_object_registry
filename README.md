# parsl_object_registry
Registry system for managing the lifetime of expensive objects across different calls to workflow functions.

## Installation

```console
pip install git+https://github.com/braceal/parsl_object_registry.git
```

## Usage
Register a function or class once and then get the singleton instance in future calls:

```python
from parsl_object_registry import register
from parsl_object_registry import clear_torch_cuda_memory_callback

# Example of a function that clears the memory of a torch model
# when a new object is requested from the registry
@register(shutdown_callback=clear_torch_cuda_memory_callback)
def my_expensive_torch_function(*args, **kwargs):
    # Expensive initialization
    torch_model = None
    return torch_model

# Example of a class that clears the memory of a torch model
# when a new object is requested from the registry
@register(shutdown_callback=clear_torch_cuda_memory_callback)
class MyExpensiveTorchClass:
    def __init__(self, *args, **kwargs) -> None:
        # Expensive initialization
        ...

# The first call to the class will initialize and register the object
my_object = MyExpensiveTorchClass(*args, **kwargs)

# Subsequent calls will return the same object without calling
# the __init__ method again (unless the input arguments change)
my_object = MyExpensiveTorchClass(*args, **kwargs)

# Calling a different function or class will return a new object
# and call the shutdown_callback function of the previous object.
# This allows us to manage the lifetime of expensive objects in
# a lazy way without having to explicitly call a shutdown method
# on the object. E.g., MyExpensiveTorchClass and my_expensive_torch_function
# can exist in different scopes without any knowledge of each other
# and use the same hardware resources without any conflicts.
a_new_object = my_expensive_torch_function(*args, **kwargs)

# By chaining object destruction with new object creation, we can
# ensure that the memory of the previous object is cleared before
# the new object is created while still allowing warm-starting of
# the old object.
```

## Contributing

For development, it is recommended to use a virtual environment. The following
commands will create a virtual environment, install the package in editable
mode, and install the pre-commit hooks.
```bash
python -m venv venv
source venv/bin/activate
pip install -U pip setuptools wheel
pip install -e '.[dev,docs]'
pre-commit install
```
To test the code, run the following command:
```bash
pre-commit run --all-files
tox -e py312
```
