from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("czi-extract-slices")
except PackageNotFoundError:
    # package is not installed
    pass
