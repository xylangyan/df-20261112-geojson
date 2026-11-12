import json

import geojson
import geojson.factory
from geojson.mapping import to_mapping


class GeoJSONEncoder(json.JSONEncoder):

    def default(self, obj):
        return geojson.factory.GeoJSON.to_instance(obj) # NOQA


# Wrap the functions from json, providing encoder, decoders, and
# object creation hooks.
# Here the defaults are set to only permit valid JSON as per RFC 4267

def _enforce_strict_numbers(obj):
    raise ValueError(f"Number {obj!r} is not JSON compliant")


def _object_hook(precision):
    if precision is None:
        def object_hook(obj):
            return geojson.base.GeoJSON.to_instance(obj)
    else:
        def object_hook(obj):
            return geojson.base.GeoJSON.to_instance(obj, precision=precision)
    object_hook.__name__ = "object_hook"
    return object_hook


def dump(obj, fp, cls=GeoJSONEncoder, allow_nan=False, **kwargs):
    return json.dump(to_mapping(obj),
                     fp, cls=cls, allow_nan=allow_nan, **kwargs)


def dumps(obj, cls=GeoJSONEncoder, allow_nan=False, ensure_ascii=False, **kwargs):
    return json.dumps(to_mapping(obj),
                      cls=cls, allow_nan=allow_nan, ensure_ascii=ensure_ascii, **kwargs)


def load(fp,
         cls=json.JSONDecoder,
         parse_constant=_enforce_strict_numbers,
         object_hook=None,
         precision=None,
         **kwargs):
    if object_hook is None:
        object_hook = _object_hook(precision)
    return json.load(fp,
                     cls=cls, object_hook=object_hook,
                     parse_constant=parse_constant,
                     **kwargs)


def loads(s,
          cls=json.JSONDecoder,
          parse_constant=_enforce_strict_numbers,
          object_hook=None,
          precision=None,
          **kwargs):
    if object_hook is None:
        object_hook = _object_hook(precision)
    return json.loads(s,
                      cls=cls, object_hook=object_hook,
                      parse_constant=parse_constant,
                      **kwargs)


# Backwards compatibility
PyGFPEncoder = GeoJSONEncoder
