from decimal import Decimal
from numbers import Number, Real

from geojson.base import GeoJSON, filter_extra, resolve_keep_extra


DEFAULT_PRECISION = 6


class Geometry(GeoJSON):
    """
    Represents an abstract base class for a WGS84 geometry.
    """

    def __init__(self, coordinates=None, validate=False, precision=None,
                 keep_extra=None, preserve_extra=None, **extra):
        """
        Initialises a Geometry object.

        :param coordinates: Coordinates of the Geometry object.
        :type coordinates: tuple or list of tuple
        :param validate: Raise exception if validation errors are present?
        :type validate: boolean
        :param precision: Number of decimal places for lat/lon coords.
        :type precision: integer
        :param keep_extra: Preserve non-standard members of the geometry,
        keeping them on the same level. Coordinates are always validated
        and rounded to the given precision regardless of this option.
        :type keep_extra: bool
        """
        keep_extra = resolve_keep_extra(keep_extra, preserve_extra)
        super().__init__(**filter_extra(extra, keep_extra))
        if precision is None:
            precision = DEFAULT_PRECISION
        self["coordinates"] = self.clean_coordinates(
            coordinates or [], precision)

        if validate:
            errors = self.errors()
            if errors:
                raise ValueError(f'{errors}: {coordinates}')

    @classmethod
    def clean_coordinates(cls, coords, precision):
        if isinstance(coords, cls):
            return coords['coordinates']

        new_coords = []
        if isinstance(coords, Geometry):
            coords = [coords]
        for coord in coords:
            if isinstance(coord, (list, tuple)):
                new_coords.append(cls.clean_coordinates(coord, precision))
            elif isinstance(coord, Geometry):
                new_coords.append(coord['coordinates'])
            elif isinstance(coord, (Real, Decimal)):
                new_coords.append(round(coord, precision))
            else:
                raise ValueError(f"{coord!r} is not a JSON compliant number")
        return new_coords


class GeometryCollection(GeoJSON):
    """
    Represents an abstract base class for collections of WGS84 geometries.
    """

    def __init__(self, geometries=None, keep_extra=None,
                 preserve_extra=None, **extra):
        keep_extra = resolve_keep_extra(keep_extra, preserve_extra)
        super().__init__(**filter_extra(extra, keep_extra))
        self["geometries"] = [
            GeoJSON.to_instance(geometry, keep_extra=keep_extra)
            if geometry is not None and not isinstance(geometry, GeoJSON)
            else geometry
            for geometry in (geometries or [])
        ]

    def errors(self):
        errors = [geom.errors() for geom in self['geometries']]
        return [err for err in errors if err]

    def __getitem__(self, key):
        try:
            return self.get("geometries", ())[key]
        except (KeyError, TypeError, IndexError):
            return super(GeoJSON, self).__getitem__(key)


# Marker classes.

def check_point(coord):
    if not isinstance(coord, list):
        return 'each position must be a list'
    if len(coord) not in (2, 3):
        return 'a position must have exactly 2 or 3 values'
    for number in coord:
        if not isinstance(number, Number):
            return 'a position cannot have inner positions'


class Point(Geometry):
    def errors(self):
        return check_point(self['coordinates'])


class MultiPoint(Geometry):
    def errors(self):
        return self.check_list_errors(check_point, self['coordinates'])


def check_line_string(coord):
    if not isinstance(coord, list):
        return 'each line must be a list of positions'
    if len(coord) < 2:
        return ('the "coordinates" member must be an array of '
                'two or more positions')
    for pos in coord:
        error = check_point(pos)
        if error:
            return error


class LineString(MultiPoint):
    def errors(self):
        return check_line_string(self['coordinates'])


class MultiLineString(Geometry):
    def errors(self):
        return self.check_list_errors(check_line_string, self['coordinates'])


def check_polygon(coord):
    if not isinstance(coord, list):
        return 'Each polygon must be a list of linear rings'

    if not all(isinstance(elem, list) for elem in coord):
        return "Each element of a polygon's coordinates must be a list"

    lengths = all(len(elem) >= 4 for elem in coord)
    if lengths is False:
        return 'Each linear ring must contain at least 4 positions'

    isring = all(elem[0] == elem[-1] for elem in coord)
    if isring is False:
        return 'Each linear ring must end where it started'


class Polygon(Geometry):
    def errors(self):
        return check_polygon(self['coordinates'])


class MultiPolygon(Geometry):
    def errors(self):
        return self.check_list_errors(check_polygon, self['coordinates'])


class Default:
    """
    GeoJSON default object.
    """
