"""Test strict per-object CC0 selection; mixed-license descriptions never enter."""
import csv
import gzip
import io
import json
import unittest
from unittest.mock import patch

from objaverse_cc0_catalog import source_row,read_shard,get_records,add_cap3d


def uid(i:int)->str:
    return f"{i:032x}"


class ObjaverseCatalogTests(unittest.TestCase):
    def test_license_filter_excludes_noncommercial_and_ccby(self):
        base={"name":"A detailed mechanical vehicle", "description":"A sculpted chassis with exposed engine ports",
              "tags":[{"name":"vehicle"},{"name":"metal"}],
              "uri":"https://sketchfab.com/3d-models/example"}
        self.assertIsNone(source_row(uid(1),{**base,"license":"by-nc"}))
        self.assertIsNone(source_row(uid(2),{**base,"license":"by"}))
        self.assertIsNone(source_row(uid(3),{**base,"license":"by-sa"}))
        self.assertIsNone(source_row("not-a-uid",{**base,"license":"cc0"}))
        selected=source_row(uid(4),{**base,"license":"cc0"})
        self.assertEqual(selected["object_license"],"CC0-1.0")
        self.assertEqual(selected["metadata_license"],"ODC-BY-1.0")
        self.assertEqual(selected["tags"],["vehicle","metal"])
        self.assertFalse(selected["model_geometry_inspected"])

    def test_shards_are_gzipped_metadata_not_assumed_safe(self):
        contents={
            uid(1):{"name":"Metal car","license":"cc0","description":"Mechanical car body"},
            uid(2):{"name":"Private scan","license":"by-nc","description":"Restricted scan"}
        }
        data=gzip.compress(json.dumps(contents).encode("utf-8"))
        self.assertEqual(len(read_shard(data)),2)
        with patch("objaverse_cc0_catalog.time.sleep",return_value=None):
            rows,summary=get_records(0,2,lambda url, cap:data)
        self.assertEqual(summary["annotations_read"],4)
        self.assertEqual(summary["verified_cc0_records"],1)
        self.assertEqual(rows[0]["uid"],uid(1))
        with self.assertRaises(ValueError):
            get_records(159,2,lambda url,cap:data)

    def test_generated_captions_join_only_verified_cc0_objects(self):
        rows=[
            source_row(uid(4),{"name":"CC0 machine","license":"cc0","description":"Industrial device"}),
            source_row(uid(6),{"name":"CC0 car","license":"cc0","description":"Vehicle body"})
        ]
        output=io.StringIO()
        writer=csv.writer(output)
        writer.writerow([uid(4),"A detailed mechanical motor housing with curved metallic panels."])
        writer.writerow([uid(5),"Restricted object that must not appear in the joined CC0 set."])
        writer.writerow([uid(6),"Shiny racing car with multiple vents, tires, and a cockpit."])
        report=add_cap3d(rows,output.getvalue().encode())
        self.assertEqual(report["cc0_rows_matched_with_cap3d"],2)
        self.assertTrue(all("cap3d_generated_caption" in x for x in rows))
        self.assertTrue(all(x["cap3d_caption_license"]=="ODC-BY-1.0" for x in rows))
        self.assertNotIn(uid(5),json.dumps(rows))

    def test_invalid_shard_format_rejected(self):
        with self.assertRaises((OSError,ValueError)):
            read_shard(gzip.compress(b"[]"))


if __name__=="__main__":
    unittest.main()
