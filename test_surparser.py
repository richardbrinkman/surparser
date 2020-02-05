#!/usr/bin/python3

import unittest

from surparser import *


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


class MarkTest(unittest.TestCase):
    def test_lowest_mark_is_one(self):
        for cesuur in range(10, 100):
            for totalscore in range(1, 100):
                self.assertEqual(1.0, mark(0.0, cesuur / 100.0, totalscore))

    def test_highest_mark_is_ten(self):
        for cesuur in range(10, 100):
            for totalscore in range(1, 100):
                self.assertEqual(10.0,
                                 mark(totalscore, cesuur / 100.0, totalscore),
                                 msg=f"Wrong mark({totalscore}, {cesuur / 100.0}, {totalscore})")

    def test_cesuur_is_five_point_five(self):
        for cesuur in range(10, 100):
            for totalscore in range(1, 100):
                self.assertAlmostEqual(5.5,
                                       mark(totalscore * cesuur / 100.0, cesuur / 100.0, totalscore),
                                       msg=f"Wrong mark({totalscore * cesuur / 100.0}, {cesuur / 100.0}, {totalscore})")

    def test_mark_is_inverse_of_score(self):
        for cesuur in range(10, 100):
            for totalscore in range(1, 100):
                for actualscore in range(totalscore):
                    self.assertAlmostEqual(actualscore,
                                           score(mark(actualscore, cesuur / 100.0, totalscore), cesuur / 100.0,
                                                 totalscore))


if __name__ == '__main__':
    unittest.main()
