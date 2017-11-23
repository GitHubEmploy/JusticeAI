# -*- coding: utf-8 -*-
import unittest
import re
import os
from util.constant import Path
from feature_extraction.post_processing.regex.regex_fact import TagPrecedents


class RegexFactTest(unittest.TestCase):
    def setUp(self):
        self.precedent_tagger = TagPrecedents()
        self.precedent_tagger.regexes = {"regex_facts": [("some_fact", [re.compile("fermentum", re.IGNORECASE)])],
                                         "regex_demands": [("some_demand", [re.compile("réclame", re.IGNORECASE)])]}

    def test_regex_model(self):
        self.precedent_tagger.tag_precedents(10)
        binary_model_path = Path.binary_directory + r'fact_dict.bin'
        self.assertTrue(os.path.isfile(binary_model_path))

    def test_tag_precedents(self):
        self.precedent_tagger.precedents_directory_path = Path.test_data_directory + "sample_precedent/"

        facts_found = self.precedent_tagger.tag_precedents(2)
        self.assertEqual(facts_found["1.txt"]["facts_vector"], [1])
        self.assertEqual(facts_found["2.txt"]["demands_vector"], [0])

    def test_intent_indice(self):
        regex_list = self.precedent_tagger.get_intent_indice()
        self.assertEqual(regex_list["facts_vector"][0], (0, "some_fact"))
        self.assertEqual(regex_list["demands_vector"][0], (0, "some_demand"))
