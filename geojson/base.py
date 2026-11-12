import geojson
from geojson.mapping import deep_copy, to_mapping

# Standard members of the GeoJSON object types. Anything else is a foreign
# (non-standard) member and is only retained when keep_extra is enabled.
STANDARD_MEMBERS = frozenset((
    "type", "id", "geometry", "properties", "coordinates",
    "features", "geometries", "bbox",
))


def filter_extra(members, keep_extra):
    """
    Return the members to store on a converted object. Foreign (non-standard)
    members are only kept when keep_extra is enabled, while standard members
    survive either way.
    """
    if keep_extra:
        return dict(members)
    return {k: v for k, v in members.items() if k in STANDARD_MEMBERS}


def resolve_keep_extra(keep_extra=None, preserve_extra=None):
    """
    Resolves the field-preservation option. ``preserve_extra`` is an alias of
    ``keep_extra``. Passing both explicitly is a caller error; with neither
    given the option defaults to enabled.
    """
    if (keep_extra is not None and preserve_extra is not None
            and keep_extra != preserve_extra):
        raise ValueError(
            "keep_extra and preserve_extra are aliases; pass only one")
    if keep_extra is not None:
        return keep_extra
    if preserve_extra is not None:
        return preserve_extra
    return True


class GeoJSON(dict):
    """
    A class representing a GeoJSON object.
    """

    def __init__(self, iterable=(), **extra):
        """
        Initialises a GeoJSON object

        :param iterable: iterable from which to draw the content of the GeoJSON
        object.
        :type iterable: dict, array, tuple
        :return: a GeoJSON object
        :rtype: GeoJSON
        """
        super().__init__(iterable)
        self["type"] = getattr(self, "type", type(self).__name__)
        self.update(extra)

    def __repr__(self):
        return geojson.dumps(self, sort_keys=True)

    __str__ = __repr__

    def __getattr__(self, name):
        """
        Permit dictionary items to be retrieved like object attributes

        :param name: attribute name
        :type name: str, int
        :return: dictionary value
        """
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        """
        Permit dictionary items to be set like object attributes.

        :param name: key of item to be set
        :type name: str
        :param value: value to set item to
        """

        self[name] = value

    def __delattr__(self, name):
        """
        Permit dictionary items to be deleted like object attributes

        :param name: key of item to be deleted
        :type name: str
        """

        del self[name]

    @property
    def __geo_interface__(self):
        if self.type != "GeoJSON":
            return self

    @classmethod
    def to_instance(cls, ob, default=None, strict=False, keep_extra=None,
                    preserve_extra=None):
        """Encode a GeoJSON dict into an GeoJSON object.
        Assumes the caller knows that the dict should satisfy a GeoJSON type.

        :param cls: Dict containing the elements to be encoded into a GeoJSON
        object.
        :type cls: dict
        :param ob: GeoJSON object into which to encode the dict provided in
        `cls`.
        :type ob: GeoJSON
        :param default: A default instance to append the content of the dict
        to if none is provided.
        :type default: GeoJSON
        :param strict: Raise error if unable to coerce particular keys or
        attributes to a valid GeoJSON structure.
        :type strict: bool
        :param keep_extra: Preserve non-standard (foreign) members of the
        object and of its nested objects, keeping them on the same level in
        the hierarchy. When False, only standard GeoJSON members survive the
        conversion. Standard members are always handled with the existing
        type checks regardless of this option. Enabled by default.
        :type keep_extra: bool
        :param preserve_extra: Alias of keep_extra.
        :type preserve_extra: bool
        :return: A GeoJSON object with the dict's elements as its constituents.
        :rtype: GeoJSON
        :raises TypeError: If the input dict contains items that are not valid
        GeoJSON types.
        :raises UnicodeEncodeError: If the input dict contains items of a type
        that contain non-ASCII characters.
        :raises AttributeError: If the input dict contains items that are not
        valid GeoJSON types.
        """
        keep_extra = resolve_keep_extra(keep_extra, preserve_extra)
        if ob is None and default is not None:
            instance = default()
        elif isinstance(ob, GeoJSON):
            instance = ob
        else:
            mapping = to_mapping(ob)
            # Detach the copy from the source mapping: later changes to the
            # external mapping must never propagate into the converted object.
            d = filter_extra(deep_copy(mapping), keep_extra)
            try:
                type_ = d.pop("type")
                try:
                    type_ = str(type_)
                except UnicodeEncodeError:
                    # If the type contains non-ascii characters, we can assume
                    # it's not a valid GeoJSON type
                    raise AttributeError(f"{type_} is not a GeoJSON type")
                geojson_factory = getattr(geojson.factory, type_)
                instance = geojson_factory(keep_extra=keep_extra, **d)
            except (AttributeError, KeyError) as invalid:
                if strict:
                    raise ValueError(
                        f"Cannot coerce {ob!r} into "
                        f"a valid GeoJSON structure: {invalid}"
                    )
                instance = ob
        return instance

    @property
    def is_valid(self):
        return not self.errors()

    def check_list_errors(self, checkFunc, lst):
        """Validation helper function."""
        # check for errors on each subitem, filter only subitems with errors
        results = (checkFunc(i) for i in lst)
        return [err for err in results if err]

    def errors(self):
        """Return validation errors (if any).
        Implement in each subclass.
        """

        # make sure that each subclass implements it's own validation function
        if self.__class__ != GeoJSON:
            raise NotImplementedError(self.__class__)
