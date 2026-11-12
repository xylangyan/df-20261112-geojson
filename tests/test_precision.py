"""
Tests for coordinate precision handling.
"""
import json
import unittest

import geojson
from geojson.geometry import DEFAULT_PRECISION


PRECISE_COORDS = [
    [
        [
            [100.123456789123, 0.987654321987],
            [100.987654321987, 0.123456789123],
            [100.555555555555, 0.777777777777],
            [100.123456789123, 0.987654321987],
        ]
    ],
    [
        [
            [-10.111111111111, 20.222222222222],
            [-9.999999999999, 20.000000000001],
            [-10.333333333333, 20.444444444444],
            [-10.111111111111, 20.222222222222],
        ]
    ],
]


def _feature_document(coords):
    return {
        "type": "Feature",
        "properties": {"name": "alpha", "count": 1717},
        "geometry": {"type": "MultiPolygon", "coordinates": coords},
    }


class DirectConstructionPrecisionTest(unittest.TestCase):
    def test_default_precision_applies_to_python_values(self):
        point = geojson.Point((1.123456789123, 2.987654321987))
        self.assertEqual(
            point["coordinates"],
            [round(1.123456789123, DEFAULT_PRECISION),
             round(2.987654321987, DEFAULT_PRECISION)])

    def test_explicit_precision_applies_to_python_values(self):
        point = geojson.Point((1.123456789123, 2.987654321987), precision=8)
        self.assertEqual(point["coordinates"], [1.12345679, 2.98765432])

    def test_none_precision_preserves_python_values(self):
        point = geojson.Point((1.123456789123, 2.987654321987),
                              precision=None)
        self.assertEqual(point["coordinates"],
                         [1.123456789123, 2.987654321987])

    def test_validation_still_runs_with_none_precision(self):
        with self.assertRaises(ValueError):
            geojson.Point((10, 20, 30, 40), validate=True, precision=None)


class RecursiveConstructionPrecisionTest(unittest.TestCase):
    def test_feature_preserves_raw_geometry(self):
        feature = geojson.Feature(
            geometry={"type": "MultiPolygon", "coordinates": PRECISE_COORDS},
            properties={"a": 1, "b": 2})
        self.assertIsInstance(feature.geometry, geojson.MultiPolygon)
        self.assertEqual(feature.geometry["coordinates"], PRECISE_COORDS)

    def test_feature_quantizes_raw_geometry(self):
        feature = geojson.Feature(
            geometry={"type": "MultiPolygon", "coordinates": PRECISE_COORDS},
            properties={"a": 1, "b": 2},
            precision=4)
        self.assertEqual(
            feature.geometry["coordinates"][0][0][0],
            [round(c, 4) for c in PRECISE_COORDS[0][0][0]])

    def test_geometry_collection_preserves_raw_geometries(self):
        collection = geojson.GeometryCollection(
            [{"type": "Point",
              "coordinates": [1.123456789, 2.987654321]}])
        self.assertIsInstance(collection[0], geojson.Point)
        self.assertEqual(collection[0]["coordinates"],
                         [1.123456789, 2.987654321])
        self.assertTrue(collection.is_valid)

    def test_geometry_collection_quantizes_raw_geometries(self):
        collection = geojson.GeometryCollection(
            [{"type": "Point",
              "coordinates": [1.123456789, 2.987654321]}],
            precision=3)
        self.assertEqual(collection[0]["coordinates"], [1.123, 2.988])

    def test_feature_collection_preserves_nested_raw_geometries(self):
        collection = geojson.FeatureCollection(
            [_feature_document(PRECISE_COORDS)])
        self.assertIsInstance(collection[0], geojson.Feature)
        self.assertEqual(
            collection[0].geometry["coordinates"], PRECISE_COORDS)


class LoadPrecisionTest(unittest.TestCase):
    def test_loads_preserves_coordinates_through_property_update(self):
        text = json.dumps(_feature_document(PRECISE_COORDS))
        feature = geojson.loads(text)
        self.assertIsInstance(feature, geojson.Feature)
        self.assertIsInstance(feature.geometry, geojson.MultiPolygon)
        self.assertEqual(feature.geometry["coordinates"], PRECISE_COORDS)

        feature["properties"]["count"] = 1718
        decoded = json.loads(geojson.dumps(feature))
        self.assertEqual(
            decoded["properties"], {"name": "alpha", "count": 1718})
        self.assertEqual(
            decoded["geometry"]["coordinates"], PRECISE_COORDS)

    def test_loads_with_explicit_precision_quantizes(self):
        text = json.dumps(_feature_document(PRECISE_COORDS))
        feature = geojson.loads(text, precision=6)
        expected = [
            [[[round(value, 6) for value in position]
              for position in ring]
             for ring in polygon]
            for polygon in PRECISE_COORDS]
        self.assertEqual(feature.geometry["coordinates"], expected)
        self.assertNotEqual(feature.geometry["coordinates"], PRECISE_COORDS)
        self.assertEqual(
            json.loads(geojson.dumps(feature))["geometry"]["coordinates"],
            expected)
