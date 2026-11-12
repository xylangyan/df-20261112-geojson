from geojson.base import GeoJSON


class Feature(GeoJSON):
    """
    Represents a WGS84 GIS feature.
    """

    def __init__(self, id=None, geometry=None, properties=None,
                 precision=None, **extra):
        """
        Initialises a Feature object with the given parameters.

        :param id: Feature identifier, such as a sequential number.
        :type id: str, int
        :param geometry: Geometry corresponding to the feature.
        :param properties: Dict containing properties of the feature.
        :type properties: dict
        :param precision: Number of decimal places for lat/lon coords of the
            geometry when it is supplied as a raw GeoJSON structure. ``None``
            preserves coordinates as-is.
        :type precision: integer or None
        :return: Feature object
        :rtype: Feature
        """
        super().__init__(**extra)
        if id is not None:
            self["id"] = id
        self["geometry"] = (self.to_instance(
            geometry, strict=True, precision=precision)
            if geometry else None)
        self["properties"] = properties or {}

    def errors(self):
        geo = self.get('geometry')
        return geo.errors() if geo else None


class FeatureCollection(GeoJSON):
    """
    Represents a FeatureCollection, a set of multiple Feature objects.
    """

    def __init__(self, features, precision=None, **extra):
        """
        Initialises a FeatureCollection object from the
        :param features: List of features to constitute the FeatureCollection.
        :type features: list
        :param precision: Number of decimal places for lat/lon coords of
            geometries supplied as raw GeoJSON structures. ``None`` preserves
            coordinates as-is.
        :type precision: integer or None
        :return: FeatureCollection object
        :rtype: FeatureCollection
        """
        super().__init__(**extra)
        self["features"] = [
            self.to_instance(f, precision=precision)
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
