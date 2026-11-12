from collections.abc import Mapping, MutableMapping, Sequence

try:
    import simplejson as json
except ImportError:
    import json

import geojson


GEO_INTERFACE_MARKER = "__geo_interface__"


def is_mapping(obj):
    """
    Checks if the object is an instance of MutableMapping.

    :param obj: Object to be checked.
    :return: Truth value of whether the object is an instance of
    MutableMapping.
    :rtype: bool
    """
    return isinstance(obj, MutableMapping)


def deep_copy(obj):
    """
    Returns an independent copy of a JSON-like value, recursively copying
    nested mappings and sequences so that mutating the source mapping cannot
    affect the converted object. Values that are not JSON containers are
    returned unchanged, so non-JSON values are reported by the JSON encoder
    at dump time rather than being silently dropped here.

    :param obj: The value to copy.
    :return: A detached copy of the value.
    """
    if isinstance(obj, Mapping):
        return {key: deep_copy(value) for key, value in obj.items()}
    if isinstance(obj, tuple):
        return [deep_copy(value) for value in obj]
    if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes)):
        return [deep_copy(value) for value in obj]
    return obj


def to_mapping(obj):

    mapping = getattr(obj, GEO_INTERFACE_MARKER, None)

    if mapping is not None:
        return mapping

    if is_mapping(obj):
        return obj

    if isinstance(obj, geojson.GeoJSON):
        return dict(obj)

    return json.loads(json.dumps(obj))
