#!/usr/bin/env python3
import unittest

import archon
import archon.datastore


class TestFormatting(unittest.TestCase):
    def setUp(self):
        self.ds = archon.datastore.GameDatastore('data')
        self.messages = self.ds['formatting']['templates'].attributes

    def test_function(self):
        res = self.messages.format('third_person_female',
                                   '{test@prepend("b")}', test='a')
        self.assertEqual(res, 'ba')
        self.assertRaises(ValueError, self.messages.format,
                          'third_person_female',
                          '{test@!@#@}', test='a')
        self.assertRaises(ValueError, self.messages.format,
                          'third_person_female',
                          '{test@i_do_not_exist}', test='a')


class TestMessages(unittest.TestCase):
    pass


class TestFormattedMessages(unittest.TestCase):
    pass


if __name__ == '__main__':
    unittest.main()
