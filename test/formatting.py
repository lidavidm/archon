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
        res = self.messages.format('third_person_female',
                                   '{test@drop}', test='a')
        self.assertEqual(res, '')
        self.assertRaises(ValueError, self.messages.format,
                          'third_person_female',
                          '{test@!@#@}', test='a')
        self.assertRaises(ValueError, self.messages.format,
                          'third_person_female',
                          '{test@i_do_not_exist}', test='a')

    def test_method(self):
        res = self.messages.format('third_person_female',
                                   '{test@.upper}', test='a')
        self.assertEqual(res, 'A')
        self.assertRaises(AttributeError, self.messages.format,
                          'third_person_female',
                          '{test@.i_do_not_exist}', test='a')

    def test_predicate(self):
        res = self.messages.format('third_person_female',
                                   '{test@empty}', test='')
        self.assertEqual(res, '')
        res = self.messages.format('third_person_female',
                                   '{test@!empty}', test='')
        self.assertEqual(res, '')

    def test_composition(self):
        res = self.messages.format('third_person_female',
                                   '{test@drop + !empty}', test='a')
        self.assertEqual(res, '')
        res = self.messages.format('third_person_female',
                                   '{test@.upper + prepend("a")}', test='b')
        self.assertEqual(res, 'AB')

    def test_regression_adjacent_directives(self):
        res = self.messages.format('third_person_female',
                                   '{first}{second@prepend("a")}', first=2,
                                   second=3)
        self.assertEqual(res, '2a3')


class TestMessages(unittest.TestCase):
    def setUp(self):
        self.ds = archon.datastore.GameDatastore('data')
        self.messages = self.ds['formatting']['templates'].attributes
        self.friendlyName = 'Cordelia'

    def test_third_female(self):
        res = self.messages.format('third_person_female',
                                   '{noun}', user=self)
        self.assertEqual(res, self.friendlyName)
        res = self.messages.format('third_person_female',
                                   '{noun} {to_be.present} {possessive}',
                                   user=self)
        self.assertEqual(res, "Cordelia is Cordelia's")


class TestFormattedMessages(unittest.TestCase):
    def setUp(self):
        self.ds = archon.datastore.GameDatastore('data')
        self.messages = self.ds['formatting']['templates'].attributes
        self.friendlyName = 'Cordelia'

    def test_first_person(self):
        text = 'Hello! {pronoun@.capitalize} {to_be.present} {noun}.'
        res = self.messages.format('first_person', text, user=self)
        self.assertEqual(res, "Hello! I am Cordelia.")

if __name__ == '__main__':
    unittest.main()
