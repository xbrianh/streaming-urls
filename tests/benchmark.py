#!/usr/bin/env python
import os
import sys
import time
import base64
import hashlib
import unittest
from random import randint

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # noqa
sys.path.insert(0, pkg_root)  # noqa

import getm
from tests.infra import GS, S3, suppress_warnings


def setUpModule():
    suppress_warnings()
    GS.setup()
    S3.setup()

def tearDownModule():
    GS.client._http.close()

class TestBenchmark(unittest.TestCase):
    def duration_subtests(self, tests):
        print()
        for t in tests:
            start_time = time.time()
            try:
                with self.subTest(t[0]):
                    yield t
            except GeneratorExit:
                return
            print(self.id(), "duration", f"{t[0]}", time.time() - start_time)

    @classmethod
    def setUpClass(cls):
        cls.key, cls.size = GS.put_fixture()
        cls.expected_md5 = GS.bucket.get_blob(cls.key).md5_hash

    def setUp(self):
        self.url = GS.generate_presigned_GET_url(self.key)

    def test_read(self):
        tests = [(f"concurrency={concurrency}", concurrency) for concurrency in [None, 4]]
        for test_name, concurrency in self.duration_subtests(tests):
            md5 = hashlib.md5()
            with getm.urlopen(self.url, concurrency=concurrency) as raw:
                md5.update(raw.read())
                while True:
                    d = raw.read()
                    md5.update(d)
                    if not d:
                        break
            self.assertEqual(self.expected_md5, base64.b64encode(md5.digest()).decode("utf-8"))

    def test_read_keep_alive(self):
        tests = [("1", 1024 * 1024 * 1),
                 ("5", 1024 * 1024 * 5),
                 ("7", 1024 * 1024 * 7)]
        for test_name, chunk_size in self.duration_subtests(tests):
            md5 = hashlib.md5()
            with getm.urlopen(self.url, chunk_size, concurrency=1) as raw:
                while True:
                    d = raw.read(chunk_size)
                    if not d:
                        break
                    md5.update(d)
            self.assertEqual(self.expected_md5, base64.b64encode(md5.digest()).decode("utf-8"))

    def test_iter_content(self):
        tests = [(f"concurrency={concurrency}", concurrency) for concurrency in [None, 4]]
        for test_name, concurrency in self.duration_subtests(tests):
            md5 = hashlib.md5()
            for chunk in getm.iter_content(self.url, concurrency=concurrency):
                md5.update(chunk)
                chunk.release()
            self.assertEqual(self.expected_md5, base64.b64encode(md5.digest()).decode("utf-8"))

    def test_iter_content_keep_alive(self):
        tests = [(f"concurrency={concurrency}", concurrency) for concurrency in [1]]
        for test_name, concurrency in self.duration_subtests(tests):
            md5 = hashlib.md5()
            for chunk in getm.iter_content(self.url, 1024 * 1024 * 5, concurrency=concurrency):
                md5.update(chunk)
                chunk.release()
            self.assertEqual(self.expected_md5, base64.b64encode(md5.digest()).decode("utf-8"))

    def test_iter_content_unordered(self):
        tests = [(f"concurrency={concurrency}", concurrency) for concurrency in range(2,5)]
        for test_name, concurrency in self.duration_subtests(tests):
            md5 = hashlib.md5()
            for i, chunk in getm.reader.iter_content_unordered(self.url, getm.default_chunk_size, concurrency):
                md5.update(chunk)
                chunk.release()

if __name__ == '__main__':
    unittest.main()
