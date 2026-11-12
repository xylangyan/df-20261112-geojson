from geojson.base import GeoJSON, filter_extra, resolve_keep_extra
from geojson.mapping import deep_copy


class Feature(GeoJSON):
    """
    Represents a WGS84 GIS feature.
    """

    def __init__(self, id=None, geometry=None, properties=None,
                 keep_extra=None, preserve_extra=None, **extra):
        """
        Initialises a Feature object with the given parameters.

        :param id: Feature identifier, such as a sequential number.
        :type id: str, int
        :param geometry: Geometry corresponding to the feature.
        :param properties: Member containing properties of the feature.
        Per RFC 7946 this can be any JSON object or null; the value and its
        type (including null and a list) are preserved instead of being
        coerced into an empty dict.
        :type properties: dict, list, None
        :param keep_extra: Preserve non-standard members of the feature and
        of its nested geometry, keeping them on the same level.
        :type keep_extra: bool
        :return: Feature object
        :rtype: Feature
        """
        keep_extra = resolve_keep_extra(keep_extra, preserve_extra)
        super().__init__(**filter_extra(extra, keep_extra))
        if id is not None:
            self["id"] = id
        self["geometry"] = (self.to_instance(geometry, strict=True,
                                             keep_extra=keep_extra)
                            if geometry else None)
        self["properties"] = deep_copy(properties)

    def errors(self):
        geo = self.get('geometry')
        return geo.errors() if geo else None


class FeatureCollection(GeoJSON):
    """
    Represents a FeatureCollection, a set of multiple Feature objects.
    """

    def __init__(self, features, keep_extra=None, preserve_extra=None,
                 **extra):
        """
        Initialises a FeatureCollection object from the
        :param features: List of features to constitute the FeatureCollection.
        :type features: list
        :param keep_extra: Preserve non-standard members of the collection and
        of its nested features and geometries, keeping them on the same level.
        :type keep_extra: bool
        :return: FeatureCollection object
        :rtype: FeatureCollection
        """
        keep_extra = resolve_keep_extra(keep_extra, preserve_extra)
        super().__init__(**filter_extra(extra, keep_extra))
        self["features"] = [
            self.to_instance(f, keep_extra=keep_extra)
            if not isinstance(f, GeoJSON) else f
            for f in features
        ]

    def errors(self):
        return self.check_list_errors(lambda x: x.errors(), self.features)

    def __getitem__(self, key):
        try:
            return self.get("features", ())[key]
        except (KeyError, TypeError, IndexError):
            return super(GeoJSON, self).__getitem__(key)
