import io
import json

import geojson
import geojson.factory
from geojson.mapping import to_mapping


class GeoJSONEncoder(json.JSONEncoder):

    def default(self, obj):
        return geojson.factory.GeoJSON.to_instance(obj) # NOQA


class FeatureCollectionStreamError(ValueError, TypeError):
    """Raised when a feature source cannot be serialized while streaming."""


_JSON_ENCODER_OPTIONS = {
    "skipkeys", "ensure_ascii", "check_circular", "allow_nan", "sort_keys",
    "indent", "separators", "default",
}


def _indent_text(text, prefix):
    if not prefix:
        return text
    return text.replace("\n", f"\n{prefix}")


def dump_feature_collection(features, fp, metadata=None,
                            cls=GeoJSONEncoder, allow_nan=False,
                            ensure_ascii=False, **kwargs):
    """
    Write a FeatureCollection to ``fp`` without collecting its features.

    :param features: Iterable producing Feature objects or Feature-like
        mappings. It is consumed at most once, and iteration stops as soon as
        a member cannot be coerced into a GeoJSON object.
    :param fp: File-like object with a ``write`` method.
    :param metadata: Collection-level members such as ``bbox``. The caller is
        responsible for this header; ``type`` and ``features`` are managed by
        this function. ``header`` is accepted as an alias for this keyword,
        and unrecognized keyword arguments are also treated as metadata.
    :return: ``None``; the formatted FeatureCollection is written to ``fp``.
    :raises FeatureCollectionStreamError: if a member cannot be converted.
        The message contains its zero-based index and one-based item number.
        Already-written chunks remain in ``fp``; the document is left
        unclosed and no later feature is consumed.
    """
    header_metadata = kwargs.pop("header", None)
    if header_metadata is not None:
        if metadata is not None:
            raise TypeError(
                "provide either 'metadata' or 'header', not both")
        metadata = header_metadata

    extra_metadata = {
        key: kwargs.pop(key) for key in list(kwargs)
        if key not in _JSON_ENCODER_OPTIONS
    }
    header = to_mapping(metadata) if metadata is not None else {}
    if not isinstance(header, dict):
        raise TypeError("metadata must map to a dictionary")
    header = dict(header)
    header.update(extra_metadata)

    indent = kwargs.get("indent")
    sort_keys = kwargs.get("sort_keys", False)
    separators = kwargs.get("separators")
    indent_text = indent if isinstance(indent, str) else (
        " " * indent if isinstance(indent, int) else "")
    item_separator, key_separator = separators or (
        (",", ": ") if indent is not None else (", ", ": "))

    def newline(level):
        if indent is None:
            return ""
        return "\n" + indent_text * level

    def encode(obj, level=0):
        text = json.dumps(
            to_mapping(obj), cls=cls, allow_nan=allow_nan,
            ensure_ascii=ensure_ascii, **kwargs)
        return _indent_text(text, indent_text * level)

    header_members = [
        (key, value) for key, value in header.items()
        if key not in ("type", "features")
    ]
    if sort_keys:
        members = sorted(
            header_members
            + [("features", None), ("type", "FeatureCollection")],
            key=lambda member: member[0])
    else:
        members = (
            [("type", "FeatureCollection")]
            + header_members
            + [("features", None)])

    fp.write("{")
    first_member = True
    for key, value in members:
        if not first_member:
            fp.write(item_separator)
        first_member = False
        fp.write(newline(1))
        fp.write(json.dumps(key, ensure_ascii=ensure_ascii))
        fp.write(key_separator)

        if key != "features":
            fp.write(encode(value, 1))
            continue

        fp.write("[")
        first_feature = True
        for index, feature in enumerate(features):
            try:
                instance = (
                    feature if isinstance(feature, geojson.GeoJSON)
                    else geojson.GeoJSON.to_instance(feature))
                encoded = encode(instance, 2)
            except Exception as exc:
                raise FeatureCollectionStreamError(
                    f"Invalid feature at index {index} "
                    f"(item {index + 1}): {exc}") from exc

            if not first_feature:
                fp.write(item_separator)
            first_feature = False
            fp.write(newline(2))
            fp.write(encoded)

        if not first_feature:
            fp.write(newline(1))
        fp.write("]")

    fp.write(newline(0))
    fp.write("}")


def dumps_feature_collection(features, metadata=None,
                             cls=GeoJSONEncoder, allow_nan=False,
                             ensure_ascii=False, **kwargs):
    """Return a streamed FeatureCollection as a JSON string."""
    fp = io.StringIO()
    dump_feature_collection(
        features, fp, metadata, cls=cls, allow_nan=allow_nan,
        ensure_ascii=ensure_ascii, **kwargs)
    return fp.getvalue()


stream_dump = dump_feature_collection
dump_stream = dump_feature_collection
dump_features = dump_feature_collection
stream_feature_collection = dump_feature_collection
write_feature_collection = dump_feature_collection


# Wrap the functions from json, providing encoder, decoders, and
# object creation hooks.
# Here the defaults are set to only permit valid JSON as per RFC 4267

def _enforce_strict_numbers(obj):
    raise ValueError(f"Number {obj!r} is not JSON compliant")


def dump(obj, fp, cls=GeoJSONEncoder, allow_nan=False, **kwargs):
    return json.dump(to_mapping(obj),
                     fp, cls=cls, allow_nan=allow_nan, **kwargs)


def dumps(obj, cls=GeoJSONEncoder, allow_nan=False, ensure_ascii=False, **kwargs):
    return json.dumps(to_mapping(obj),
                      cls=cls, allow_nan=allow_nan, ensure_ascii=ensure_ascii, **kwargs)


def load(fp,
         cls=json.JSONDecoder,
         parse_constant=_enforce_strict_numbers,
         object_hook=geojson.base.GeoJSON.to_instance,
         **kwargs):
    return json.load(fp,
                     cls=cls, object_hook=object_hook,
                     parse_constant=parse_constant,
                     **kwargs)


def loads(s,
          cls=json.JSONDecoder,
          parse_constant=_enforce_strict_numbers,
          object_hook=geojson.base.GeoJSON.to_instance,
          **kwargs):
    return json.loads(s,
                      cls=cls, object_hook=object_hook,
                      parse_constant=parse_constant,
                      **kwargs)


# Backwards compatibility
PyGFPEncoder = GeoJSONEncoder
