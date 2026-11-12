"""
Encoding/decoding custom objects with __geo_interface__
"""
import json
import unittest
from io import StringIO

import geojson
from geojson.mapping import to_mapping


class MappingOnlySource:
    """
    A small stand-in for an external data source that exposes nothing but the
    mapping protocol through ``__geo_interface__``.
    """

    __slots__ = ("_mapping",)

    def __init__(self, mapping):
        self._mapping = mapping

    @property
    def __geo_interface__(self):
        return self._mapping


class MappingOnlySourceTest(unittest.TestCase):
    def test_exposes_only_mapping_protocol(self):
        source = MappingOnlySource(make_source())
        self.assertFalse(isinstance(source, dict))
        self.assertFalse(hasattr(source, "__getitem__"))
        self.assertFalse(hasattr(source, "keys"))
        self.assertEqual(source.__geo_interface__["type"],
                         "FeatureCollection")


def make_source():
    return {
        "type": "FeatureCollection",
        "provenance": "ingest-service",
        "features": [
            {
                "type": "Feature",
                "ingest_id": 42,
                "geometry": {
                    "type": "Point",
                    "coordinates": [1.0, 2.0],
                    "survey": "gps",
                    "accuracy": {"value": 3.5, "unit": "m"},
                },
                "properties": {
                    "name": "alpha",
                    "note": None,
                    "tags": ["field", "verified"],
                    "readings": [1.5, 2.5],
                },
            }
        ],
    }


class EncodingDecodingTest(unittest.TestCase):

    def setUp(self):
        class Restaurant:
            """
            Basic Restaurant class
            """
            def __init__(self, name, latlng):
                super().__init__()
                self.name = name
                self.latlng = latlng

        class Restaurant1(Restaurant):
            """
            Extends Restaurant with __geo_interface__ returning dict
            """
            @property
            def __geo_interface__(self):
                return {'type': "Point", 'coordinates': self.latlng}

        class Restaurant2(Restaurant):
            """
            Extends Restaurant with __geo_interface__ returning another
            __geo_interface__ object
            """
            @property
            def __geo_interface__(self):
                return geojson.Point(self.latlng)

        class RestaurantFeature1(Restaurant):
            """
            Extends Restaurant with __geo_interface__ returning dict
            """
            @property
            def __geo_interface__(self):
                return {
                    'geometry': {
                        'type': "Point",
                        'coordinates': self.latlng,
                    },
                    'type': "Feature",
                    'properties': {
                        'name': self.name,
                    },
                }

        class RestaurantFeature2(Restaurant):
            """
            Extends Restaurant with __geo_interface__ returning another
            __geo_interface__ object
            """
            @property
            def __geo_interface__(self):
                return geojson.Feature(
                    geometry=geojson.Point(self.latlng),
                    properties={'name': self.name})

        self.name = "In N Out Burger"
        self.latlng = [-54.0, 4.0]

        self.restaurant_nogeo = Restaurant(self.name, self.latlng)

        self.restaurant1 = Restaurant1(self.name, self.latlng)
        self.restaurant2 = Restaurant2(self.name, self.latlng)

        self.restaurant_str = ('{"coordinates": [-54.0, 4.0],'
                               ' "type": "Point"}')

        self.restaurant_feature1 = RestaurantFeature1(self.name, self.latlng)
        self.restaurant_feature2 = RestaurantFeature2(self.name, self.latlng)

        self.restaurant_feature_str = ('{"geometry":'
                                       ' {"coordinates": [-54.0, 4.0],'
                                       ' "type": "Point"},'
                                       ' "properties":'
                                       ' {"name": "In N Out Burger"},'
                                       ' "type": "Feature"}')

    def test_encode(self):
        """
        Ensure objects that implement __geo_interface__ can be encoded into
        GeoJSON strings
        """
        actual = geojson.dumps(self.restaurant1, sort_keys=True)
        self.assertEqual(actual, self.restaurant_str)

        actual = geojson.dumps(self.restaurant2, sort_keys=True)
        self.assertEqual(actual, self.restaurant_str)

        # Classes that don't implement geo interface should raise TypeError
        with self.assertRaises(TypeError):
            geojson.dumps(self.restaurant_nogeo)

    def test_encode_nested(self):
        """
        Ensure nested objects that implement __geo_interface__ can be encoded
        into GeoJSON strings
        """
        actual = geojson.dumps(self.restaurant_feature1, sort_keys=True)
        self.assertEqual(actual, self.restaurant_feature_str)

        actual = geojson.dumps(self.restaurant_feature2, sort_keys=True)
        self.assertEqual(actual, self.restaurant_feature_str)

    def test_decode(self):
        """
        Ensure a GeoJSON string can be decoded into GeoJSON objects
        """
        actual = geojson.loads(self.restaurant_str)
        expected = self.restaurant1.__geo_interface__
        self.assertEqual(expected, actual)

    def test_decode_nested(self):
        """
        Ensure a GeoJSON string can be decoded into nested GeoJSON objects
        """
        actual = geojson.loads(self.restaurant_feature_str)
        expected = self.restaurant_feature1.__geo_interface__
        self.assertEqual(expected, actual)

        nested = expected['geometry']
        expected = self.restaurant1.__geo_interface__
        self.assertEqual(nested, expected)

    def test_invalid(self):
        with self.assertRaises(ValueError) as cm:
            geojson.loads('{"type":"Point", "coordinates":[[-Infinity, 4.0]]}')

        self.assertIn('is not JSON compliant', str(cm.exception))

    def test_mapping(self):
        self.assertEqual(to_mapping(geojson.Point([1.0, 2.0])),
                         {"coordinates": [1.0, 2.0], "type": "Point"})

    def test_GeoJSON(self):
        self.assertEqual(None, geojson.GeoJSON().__geo_interface__)

        self.assertEqual({"type": "GeoJSON"}, to_mapping(geojson.GeoJSON()))


class ForeignMembersPreservationTest(unittest.TestCase):
    """
    Foreign (non-standard) members must survive the adaptation path at the
    level where they were provided, while standard members keep going through
    the existing type checks.
    """

    def setUp(self):
        self.source = make_source()
        self.collection = geojson.GeoJSON.to_instance(
            MappingOnlySource(self.source))

    def test_converted_types(self):
        self.assertIsInstance(self.collection, geojson.FeatureCollection)
        feature = self.collection["features"][0]
        self.assertIsInstance(feature, geojson.Feature)
        self.assertIsInstance(feature["geometry"], geojson.Point)

    def test_foreign_members_kept_at_each_level(self):
        feature = self.collection["features"][0]
        geometry = feature["geometry"]

        self.assertEqual(self.collection["provenance"], "ingest-service")
        self.assertEqual(feature["ingest_id"], 42)
        self.assertEqual(geometry["survey"], "gps")
        self.assertEqual(geometry["accuracy"],
                         {"value": 3.5, "unit": "m"})

    def test_standard_members_still_checked(self):
        self.assertEqual(self.collection["type"], "FeatureCollection")
        self.assertEqual(self.collection["features"][0]["type"], "Feature")
        point = self.collection["features"][0]["geometry"]
        self.assertEqual(point["type"], "Point")
        self.assertEqual(point["coordinates"], [1.0, 2.0])
        self.assertTrue(self.collection.is_valid)

    def test_properties_keep_null_and_list_types(self):
        cases = [
            (None, type(None)),
            (["field", "verified"], list),
            ({"name": "alpha"}, dict),
        ]
        for properties, expected_type in cases:
            feature = geojson.GeoJSON.to_instance({
                "type": "Feature",
                "geometry": None,
                "properties": properties,
            })
            self.assertIsInstance(feature, geojson.Feature)
            self.assertIs(type(feature["properties"]), expected_type)
            self.assertEqual(feature["properties"], properties)

    def test_conversion_is_detached_from_source_mapping(self):
        feature = self.collection["features"][0]
        geometry = feature["geometry"]

        # Mutate every level of the external mapping after conversion.
        self.source["provenance"] = "changed"
        source_feature = self.source["features"][0]
        source_feature["ingest_id"] = 99
        source_feature["geometry"]["coordinates"][0] = 7.0
        source_feature["geometry"]["survey"] = "manual"
        source_feature["geometry"]["accuracy"]["value"] = 99.0
        source_feature["properties"]["tags"].append("dropped")
        source_feature["properties"]["readings"][0] = 9.9
        source_feature["properties"]["note"] = "filled"

        self.assertEqual(self.collection["provenance"], "ingest-service")
        self.assertEqual(feature["ingest_id"], 42)
        self.assertEqual(geometry["coordinates"], [1.0, 2.0])
        self.assertEqual(geometry["survey"], "gps")
        self.assertEqual(geometry["accuracy"]["value"], 3.5)
        self.assertEqual(feature["properties"]["tags"],
                         ["field", "verified"])
        self.assertEqual(feature["properties"]["readings"], [1.5, 2.5])
        self.assertIsNone(feature["properties"]["note"])
        self.assertIsNot(feature["properties"],
                         source_feature["properties"])
        self.assertIsNot(geometry["coordinates"],
                         source_feature["geometry"]["coordinates"])

    def test_export_and_reload_roundtrip(self):
        encoded = geojson.dumps(self.collection, sort_keys=True)
        reloaded = geojson.loads(encoded)

        self.assertEqual(reloaded["provenance"], "ingest-service")
        feature = reloaded["features"][0]
        self.assertEqual(feature["ingest_id"], 42)
        self.assertEqual(feature["geometry"]["survey"], "gps")
        self.assertEqual(feature["geometry"]["accuracy"],
                         {"value": 3.5, "unit": "m"})
        self.assertIsNone(feature["properties"]["note"])
        self.assertEqual(feature["properties"]["tags"],
                         ["field", "verified"])

        self.assertEqual(json.loads(encoded), make_source())

    def test_keep_extra_false_drops_only_foreign_members(self):
        source = MappingOnlySource(make_source())
        stripped = geojson.GeoJSON.to_instance(source, keep_extra=False)

        self.assertNotIn("provenance", stripped)
        feature = stripped["features"][0]
        self.assertNotIn("ingest_id", feature)
        geometry = feature["geometry"]
        self.assertNotIn("survey", geometry)
        self.assertNotIn("accuracy", geometry)

        # Standard members keep their normal checks and contents.
        self.assertEqual(stripped["type"], "FeatureCollection")
        self.assertEqual(geometry["type"], "Point")
        self.assertEqual(geometry["coordinates"], [1.0, 2.0])
        self.assertEqual(feature["properties"]["tags"],
                         ["field", "verified"])
        self.assertTrue(stripped.is_valid)

    def test_preserve_extra_alias(self):
        source = MappingOnlySource(make_source())
        stripped = geojson.GeoJSON.to_instance(source, preserve_extra=False)
        self.assertNotIn("provenance", stripped)
        self.assertNotIn("ingest_id", stripped.features[0])

        point = geojson.Point((1.0, 2.0), survey="gps", preserve_extra=False)
        self.assertNotIn("survey", point)

    def test_conflicting_preservation_options_raise(self):
        with self.assertRaises(ValueError):
            geojson.GeoJSON.to_instance(
                make_source(), keep_extra=True, preserve_extra=False)

        # The same value on both aliases is not a conflict.
        kept = geojson.GeoJSON.to_instance(
            make_source(), keep_extra=False, preserve_extra=False)
        self.assertNotIn("provenance", kept)

    def test_standard_bbox_member_is_kept_without_extra(self):
        point = geojson.Point((1.0, 2.0), bbox=[1.0, 2.0, 1.0, 2.0],
                              survey="gps", keep_extra=False)
        self.assertEqual(point["bbox"], [1.0, 2.0, 1.0, 2.0])
        self.assertNotIn("survey", point)

    def test_geometry_collection_foreign_members_and_detachment(self):
        source = {
            "type": "GeometryCollection",
            "source": "hub",
            "geometries": [
                {"type": "Point", "coordinates": [3.0, 4.0], "origin": "uav"}
            ],
        }
        collection = geojson.GeoJSON.to_instance(MappingOnlySource(source))

        self.assertIsInstance(collection, geojson.GeometryCollection)
        geometry = collection["geometries"][0]
        self.assertIsInstance(geometry, geojson.Point)
        self.assertEqual(collection["source"], "hub")
        self.assertEqual(geometry["origin"], "uav")

        source["geometries"][0]["coordinates"][0] = 9.0
        source["source"] = "changed"
        self.assertEqual(collection["source"], "hub")
        self.assertEqual(collection["geometries"][0]["coordinates"],
                         [3.0, 4.0])

    def test_non_json_value_fails_at_json_encoding(self):
        bad_value = object()
        feature = geojson.GeoJSON.to_instance({
            "type": "Feature",
            "geometry": None,
            "properties": {"payload": bad_value},
        })

        # Conversion stores the value; only JSON encoding rejects it.
        self.assertIs(feature["properties"]["payload"], bad_value)
        with self.assertRaises(TypeError):
            geojson.dumps(feature)
        with self.assertRaises(TypeError):
            geojson.dump(feature, StringIO())

        nested = geojson.GeoJSON.to_instance({
            "type": "Point",
            "coordinates": [1.0, 2.0],
            "meta": [{"payload": bad_value}],
        })
        with self.assertRaises(TypeError):
            geojson.dumps(nested)

    def test_non_json_foreign_member_kept_until_encoding(self):
        bad_value = object()
        feature = geojson.GeoJSON.to_instance({
            "type": "Feature",
            "geometry": None,
            "properties": None,
            "source_record": bad_value,
        })
        self.assertIs(feature["source_record"], bad_value)
        with self.assertRaises(TypeError):
            geojson.dumps(feature)
