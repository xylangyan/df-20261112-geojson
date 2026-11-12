"""
Tests for geojson.utils.bbox
"""

import unittest

import geojson
from geojson.utils import bbox


class BboxAntimeridianTestCase(unittest.TestCase):
    """Small coordinates straddling the antimeridian."""

    def test_linestring_crossing_antimeridian(self):
        line = geojson.LineString([(179.0, 0.0), (-179.0, 0.0)])
        self.assertEqual(bbox(line), [179.0, 0.0, -179.0, 0.0])

    def test_feature_collection_crossing_antimeridian(self):
        collection = geojson.FeatureCollection([
            geojson.Feature(geometry=geojson.Point((179.0, 0.0))),
            geojson.Feature(geometry=geojson.Point((-179.0, 5.0))),
        ])
        self.assertEqual(bbox(collection), [179.0, 0.0, -179.0, 5.0])

    def test_crossing_bbox_json_round_trip(self):
        line = geojson.LineString([(179.0, 0.0), (-179.0, 0.0)])
        line['bbox'] = bbox(line)
        restored = geojson.loads(geojson.dumps(line, sort_keys=True))
        self.assertEqual(restored['bbox'], [179.0, 0.0, -179.0, 0.0])
        self.assertEqual(restored, line)


class BboxOrdinaryRangeTestCase(unittest.TestCase):
    """Small coordinates in an ordinary longitude range."""

    def test_linestring_ordinary_range(self):
        line = geojson.LineString([(10.0, 20.0), (30.0, 40.0)])
        self.assertEqual(bbox(line), [10.0, 20.0, 30.0, 40.0])

    def test_ordinary_bbox_json_round_trip(self):
        line = geojson.LineString([(10.0, 20.0), (30.0, 40.0)])
        line['bbox'] = bbox(line)
        restored = geojson.loads(geojson.dumps(line, sort_keys=True))
        self.assertEqual(restored['bbox'], [10.0, 20.0, 30.0, 40.0])
        self.assertEqual(restored, line)


class BboxGeometryTypesTestCase(unittest.TestCase):
    def test_point(self):
        point = geojson.Point((179.0, 45.0))
        self.assertEqual(bbox(point), [179.0, 45.0, 179.0, 45.0])

    def test_polygon(self):
        polygon = geojson.Polygon([[
            (170.0, 40.0), (-170.0, 40.0),
            (-170.0, 50.0), (170.0, 50.0), (170.0, 40.0)]])
        self.assertEqual(bbox(polygon), [170.0, 40.0, -170.0, 50.0])

    def test_multipolygon(self):
        multi = geojson.MultiPolygon([
            ([(10.0, 0.0), (20.0, 0.0), (20.0, 10.0),
              (10.0, 10.0), (10.0, 0.0)],),
            ([(30.0, 20.0), (40.0, 20.0), (40.0, 30.0),
              (30.0, 30.0), (30.0, 20.0)],)])
        self.assertEqual(bbox(multi), [10.0, 0.0, 40.0, 30.0])

    def test_geometry_collection_recursive(self):
        collection = geojson.GeometryCollection([
            geojson.GeometryCollection([geojson.Point((179.0, 1.0))]),
            geojson.LineString([(-179.0, 2.0), (179.5, 3.0)]),
        ])
        self.assertEqual(bbox(collection), [179.0, 1.0, -179.0, 3.0])


class BboxAltitudeTestCase(unittest.TestCase):
    def test_3d_boundary_sample(self):
        line = geojson.LineString([(10.0, 20.0, 5.0), (30.0, 40.0, 50.0)])
        self.assertEqual(bbox(line), [10.0, 20.0, 5.0, 30.0, 40.0, 50.0])

    def test_mixed_2d_3d_drops_altitude(self):
        multi = geojson.MultiPoint([(1.0, 2.0), (3.0, 4.0, 5.0)])
        self.assertEqual(bbox(multi), [1.0, 2.0, 3.0, 4.0])


class BboxEmptyAndNullTestCase(unittest.TestCase):
    def test_empty_geometry(self):
        self.assertIsNone(bbox(geojson.Point()))

    def test_null_geometry_feature(self):
        self.assertIsNone(bbox(geojson.Feature(geometry=None)))

    def test_empty_feature_collection(self):
        self.assertIsNone(bbox(geojson.FeatureCollection([])))

    def test_null_member_in_geometry_collection(self):
        collection = geojson.GeometryCollection(
            [None, geojson.Point((1.0, 2.0))])
        self.assertEqual(bbox(collection), [1.0, 2.0, 1.0, 2.0])


class BboxExistingTestCase(unittest.TestCase):
    def test_existing_bbox_is_returned_as_is(self):
        point = geojson.Point((1.0, 2.0))
        point['bbox'] = [0, 0, 9, 9]
        self.assertEqual(bbox(point), [0, 0, 9, 9])


class BboxNonMutatingTestCase(unittest.TestCase):
    def test_coordinates_and_serialization_unchanged(self):
        line = geojson.LineString([(179.0, 0.0), (-179.0, 0.0)])
        snapshot = geojson.dumps(line, sort_keys=True)
        bbox(line)
        self.assertEqual(geojson.dumps(line, sort_keys=True), snapshot)
        self.assertNotIn('bbox', line)
        self.assertEqual(line['coordinates'], [[179.0, 0.0], [-179.0, 0.0]])


if __name__ == '__main__':
    unittest.main()
