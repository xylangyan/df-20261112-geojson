import io
import json
import unittest

import geojson


class FeatureCollectionsTest(unittest.TestCase):
    def test_to_instance_converts_nested_features(self):
        """to_instance() should convert dict features to Feature objects in FeatureCollection."""

        feature_collection_dict = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"foo": "bar"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]],
                    },
                },
            ],
        }

        obj = geojson.GeoJSON.to_instance(feature_collection_dict)
        self.assertTrue(isinstance(obj, geojson.FeatureCollection))
        self.assertTrue(isinstance(obj.features[0], geojson.Feature))
        self.assertTrue(obj.is_valid)


class StreamingFeatureCollectionsTest(unittest.TestCase):
    @staticmethod
    def _features():
        return [
            geojson.Feature(
                id=1,
                geometry=geojson.Point((1.5, 2.5)),
                properties={"name": "é"},
                tag="extra"),
            geojson.Feature(id="two", geometry=None, properties={}),
            {
                "type": "Feature",
                "id": 3,
                "geometry": None,
                "properties": {"kind": "mapping"},
            },
        ]

    def test_stream_matches_dumps_after_decoding(self):
        features = self._features()
        metadata = {"bbox": [0, 0, 2, 3], "title": "weekly"}
        reference = geojson.loads(geojson.dumps(
            geojson.FeatureCollection(features, **metadata)))
        output = io.StringIO()

        geojson.dump_feature_collection(features, output, metadata)

        self.assertEqual(geojson.loads(output.getvalue()), reference)
        self.assertEqual(output.getvalue(), geojson.dumps(
            geojson.FeatureCollection(features, **metadata)))

    def test_empty_source_and_formatting_options(self):
        for kwargs in ({}, {"indent": 2}, {"sort_keys": True},
                       {"indent": 4, "sort_keys": True}):
            output = io.StringIO()
            geojson.dump_feature_collection(
                iter(()), output, {"bbox": [1, 2, 3, 4]}, **kwargs)
            reference = geojson.dumps(
                geojson.FeatureCollection([], bbox=[1, 2, 3, 4]), **kwargs)
            self.assertEqual(output.getvalue(), reference)

    def test_header_is_written_before_features_are_consumed(self):
        consumed = []
        first_write_at = []

        def features():
            for feature in self._features():
                consumed.append(feature)
                yield feature

        class RecordingStream(io.StringIO):
            def write(self, chunk):
                if not first_write_at:
                    first_write_at.append(len(consumed))
                return super().write(chunk)

        output = RecordingStream()
        geojson.dump_feature_collection(features(), output)

        self.assertEqual(first_write_at, [0])
        self.assertEqual(output.getvalue(), geojson.dumps(
            geojson.FeatureCollection(self._features())))

    def test_bad_feature_reports_position_and_does_not_consume_later(self):
        consumed = []

        def features():
            for feature in self._features()[:1]:
                consumed.append(feature)
                yield feature
            consumed.append("bad")
            yield object()
            consumed.append("later")
            yield self._features()[2]

        output = io.StringIO()
        with self.assertRaisesRegex(
                geojson.FeatureCollectionStreamError,
                r"index 1.*item 2"):
            geojson.dump_feature_collection(features(), output)

        self.assertEqual(consumed[-1], "bad")
        self.assertEqual(len(consumed), 2)
        self.assertTrue(output.getvalue().startswith(
            '{"type": "FeatureCollection", "features": ['))
        self.assertFalse(output.getvalue().endswith("]}"))
        self.assertEqual(output.getvalue().count('"type": "Feature"'), 1)

    def test_aliases_and_constructor_still_work(self):
        features = self._features()
        for writer in (geojson.stream_dump, geojson.dump_stream):
            output = io.StringIO()
            writer(features, output)
            self.assertEqual(geojson.loads(output.getvalue()),
                             geojson.loads(geojson.dumps(
                                 geojson.FeatureCollection(features))))

        output = io.StringIO()
        geojson.dump_feature_collection(
            features, output, header={"bbox": [0, 0, 2, 3]})
        self.assertEqual(json.loads(output.getvalue())["bbox"],
                         [0, 0, 2, 3])

        with self.assertRaises(TypeError):
            geojson.dump_feature_collection(
                features, io.StringIO(), metadata={}, header={})

        output = io.StringIO()
        geojson.dump_feature_collection(features, output, bbox=[4, 5, 6, 7])
        self.assertEqual(json.loads(output.getvalue())["bbox"],
                         [4, 5, 6, 7])

        collection = geojson.FeatureCollection(features, bbox=[0, 0, 2, 3])
        self.assertTrue(collection.is_valid)
        self.assertEqual(json.loads(geojson.dumps(collection))["bbox"],
                         [0, 0, 2, 3])
