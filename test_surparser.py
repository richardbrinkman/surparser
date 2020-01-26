#!/usr/bin/python3

import unittest

from surparser import parse_question_params


class ParamParsingTestCase(unittest.TestCase):
    def setUp(self):
        self.params = {
            "Naam [1234P5678]": "First question",
            "Naam [1234P5679]": "Second question",
            "Totaalscore [1234P5678]": "1",
            "Totaalscore [1234P5679]": "5",
            "Sleutel [1234P5678]": "A",
            "Sleutel [1234P5679]": "B",
            "Itemtype [1234P5678]": "Meerkeuze",
            "Itemtype [1234P5679]": "Meerkeuze",
            "Scoretype [1234P5678]": "Standard",
            "Scoretype [1234P5679]": "Standard"
        }

    def test_parse_question_params_with_empty_input(self):
        params = []
        output = list(parse_question_params(params))
        self.assertEqual([], output)

    def test_parse_question_params(self):
        generator = parse_question_params(self.params)
        first_question = next(generator)
        self.assertEqual("1234P5678", first_question["QuestionId"])
        self.assertEqual("First question", first_question["Naam"])
        self.assertEqual("1", first_question["Totaalscore"])
        self.assertEqual("A", first_question["Sleutel"])
        self.assertEqual("Meerkeuze", first_question["ItemType"])
        second_question = next(generator)
        self.assertEqual("1234P5679", second_question["QuestionId"])
        self.assertEqual("Second question", second_question["Naam"])
        self.assertEqual("5", second_question["Totaalscore"])
        self.assertEqual("B", second_question["Sleutel"])
        self.assertEqual("Meerkeuze", second_question["ItemType"])


if __name__ == '__main__':
    unittest.main()
