#!/usr/bin/python3

"""Parser for ItemsDeliveredRawReport.csv file produced by Surpass.

A markdown file is outputed with the sections you indicate with
the optional arguments.

Tip: if you want to produce a pdf use:
./surparser.py --all | pandoc -o surparser.pdf -f markdown
"""

import argparse
import csv
import os
import re
import sqlite3
import sys
from mpl_toolkits.axes_grid1.axes_divider import make_axes_area_auto_adjustable
import matplotlib.pyplot as plt
import numpy as np


def open_database(filename):
    """Opens the database pointed to by filename and creates the necessary tables."""

    db = sqlite3.connect(filename)
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Student(
                Reference MEDIUMINT UNSIGNED NOT NULL PRIMARY KEY,
                FirstName TEXT NOT NULL,
                LastName TEXT NOT NULL,
                Gender CHAR(1),
                Keycode CHAR(8),
                ActualMark SMALLINT UNSIGNED,
                TotalMark SMALLINT UNSIGNED,
                Grade CHAR(4)
        );
    """)
    cursor.execute("DELETE FROM Student;")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Test(
            TestForm TEXT NOT NULL PRIMARY KEY,
            Test TEXT,
            Centre TEXT,
            Subject TEXT,
            TotalMark SMALLINT UNSIGNED
        );
    """)
    cursor.execute("DELETE FROM Test;")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Question(
            QuestionId CHAR(11) NOT NULL PRIMARY KEY,
            Naam TEXT,
            Totaalscore TINYINT,
            Sleutel TEXT,
            ItemType TEXT,
            ScoreType TEXT,
            LO TEXT,
            Unit TEXT,
            Trefwoorden TEXT
        );
    """)
    cursor.execute("DELETE FROM Question;")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Vijanden(
            QuestionId CHAR(11) NOT NULL
                REFERENCES Question(QuestionId)
                ON UPDATE CASCADE
                ON DELETE CASCADE,
            EnymyId CHAR(11) NOT NULL
                REFERENCES Question(QuestionId)
                ON UPDATE CASCADE
                ON DELETE CASCADE,
            PRIMARY KEY (QuestionId, EnymyId)
        );
    """)
    cursor.execute("DELETE FROM Vijanden;")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Answer(
            QuestionId CHAR(11) NOT NULL
                REFERENCES Question(QuestionId)
                ON UPDATE CASCADE
                ON DELETE CASCADE,
            Reference MEDIUMINT UNSIGNED NOT NULL
                REFERENCES Student(Reference)
                ON UPDATE CASCADE
                ON DELETE CASCADE,
            DaadwerkelijkeMarkering SMALLINT UNIGNED,
            Reactie TEXT,
            Weergavetijd TINYINT UNIGNED,
            Volgorde TINYINT UNSIGNED,
            Nagekeken CHAR(3)
        );
    """)
    cursor.execute("DELETE FROM Answer;")
    return db


def insert_student(cursor, params):
    params["ActualMark"] = float(params["ActualMark"].replace(",", "."))
    return cursor.execute("""
        INSERT OR REPLACE INTO Student(Reference, FirstName, LastName, Gender, Keycode, ActualMark, TotalMark, Grade)
        VALUES(:Reference, :FirstName, :LastName, :Gender, :Keycode, :ActualMark, :TotalMark, :Grade);
    """, params)


def insert_test_form(cursor, params):
    return cursor.execute("""
        INSERT OR REPLACE INTO Test(TestForm, Test, Centre, Subject, TotalMark)
        VALUES(:TestForm, :Test, :Centre, :Subject, :TotalMark)
    """, params)


def insert_question(cursor, params):
    return cursor.executemany("""
        INSERT OR REPLACE INTO Question(QuestionId, Naam, Totaalscore, Sleutel, ItemType, ScoreType, LO, Unit, Trefwoorden)
        VALUES(:QuestionId, :Naam, :Totaalscore, :Sleutel, :ItemType, :ScoreType, :LO, :Unit, :Trefwoorden);
    """, parse_question_params(params))


def insert_vijanden(cursor, params):
    pass


def insert_answer(cursor, params):
    return cursor.executemany("""
        INSERT OR REPLACE INTO Answer(QuestionId, Reference, DaadwerkelijkeMarkering, Reactie, Weergavetijd, Volgorde, Nagekeken)
        VALUES(:QuestionId, :Reference, :DaadwerkelijkeMarkering, :Reactie, :Weergavetijd, :Volgorde, :Nagekeken);
    """, parse_answer_params(params))


def parse_question_params(params):
    for key in params:
        name = re.match(r"Naam \[(.+)\]", key)
        if name:
            question_id = name.group(1)
            yield {
                "QuestionId": question_id,
                "Naam": params[key],
                "Totaalscore": params["Totaalscore [{}]".format(question_id)],
                "Sleutel": params["Sleutel [{}]".format(question_id)],
                "ItemType": params["Itemtype [{}]".format(question_id)],
                "ScoreType": params["Scoretype [{}]".format(question_id)],
                "LO": params.get("LO [{}]".format(question_id), None),
                "Unit": params.get("Unit [{}]".format(question_id), None),
                "Trefwoorden": params.get("Trefwoorden [{}]".format(question_id), None)
            }


def parse_answer_params(params):
    for key in params:
        name = re.match(r"Naam \[(.+)\]", key)
        if name:
            question_id = name.group(1)
            yield {
                "QuestionId": question_id,
                "Reference": params["Reference"],
                "DaadwerkelijkeMarkering": params["Daadwerkelijke markering [{}]".format(question_id)],
                "Reactie": params["Reactie [{}]".format(question_id)],
                "Weergavetijd": params["Weergavetijd [{}]".format(question_id)],
                "Volgorde": params["Gepresenteerde volgorde [{}]".format(question_id)],
                "Nagekeken": params["Nagekeken [{}]".format(question_id)]
            }


def read_csv(input_filename, cursor):
    with open(input_filename, newline="") as csvfile:
        for row in csv.DictReader(csvfile):
            for func in [insert_student, insert_test_form, insert_question, insert_vijanden, insert_answer]:
                func(cursor, row)


def answer_score(cursor):
    return cursor.execute("""
        SELECT Naam, Totaalscore, 100.0 * SUM(DaadwerkelijkeMarkering) / SUM(Totaalscore) AS percentage
        FROM Question
        NATURAL JOIN Answer
        WHERE Nagekeken = 'Ja'
        GROUP BY QuestionId
        ORDER BY percentage DESC
    """)


def student_score(cursor):
    return cursor.execute("""
        SELECT FirstName, LastName, ActualMark, 100.0 * ActualMark / TotalMark AS percentage
        FROM Student
        NATURAL JOIN Answer
        WHERE Nagekeken = 'Ja'
        GROUP BY Reference
        ORDER BY percentage DESC
    """)


def students(cursor):
    return cursor.execute("""
        SELECT FirstName, LastName, Reference
        FROM Student
        NATURAL JOIN Answer
        WHERE Nagekeken = 'Ja'
        GROUP BY Reference
        ORDER BY FirstName, LastName
    """)


def answers(cursor, reference):
    return cursor.execute("""
        SELECT Naam, Reactie, Sleutel, DaadwerkelijkeMarkering, TotaalScore
        FROM Question
        NATURAL JOIN Answer
        WHERE Nagekeken = 'Ja' AND Reference = ?
    """, (reference,))


def item_types(cursor):
    return cursor.execute("""
        SELECT ItemType, COUNT(DISTINCT QuestionId) AS aantal, 100.0 * SUM(DaadwerkelijkeMarkering) / SUM(TotaalScore) AS percentage
        FROM Question
        NATURAL JOIN Answer
        WHERE Nagekeken = 'Ja'
        GROUP BY ItemType
        ORDER BY percentage DESC
    """)


def units(cursor):
    return cursor.execute("""
        SELECT Unit
        FROM Question
        WHERE Unit IS NOT NULL
        GROUP BY Unit
    """)


def unit_question(cursor, question_id):
    return cursor.execute("""
        SELECT DaadwerkelijkeMarkering, COUNT(*)
        FROM Answer
        WHERE Nagekeken = 'Ja' AND QuestionId = ?
        GROUP BY DaadwerkelijkeMarkering
    """, (question_id,))


def unit_distribution(cursor, unit):
    sql = """
        SELECT QuestionId, Naam
        FROM Question
        WHERE Unit = ?
    """
    for question_id, name in list(cursor.execute(sql, (unit,))):
        yield name, list(unit_question(cursor, question_id))


def unit_results(cursor, reference=None):
    if reference:
        where = " AND Reference = {}".format(reference)
    else:
        where = ""
    return cursor.execute("""
        SELECT Unit, COUNT(DISTINCT QuestionId) AS aantal, 100.0 * SUM(DaadwerkelijkeMarkering) / SUM(Totaalscore) AS percentage
        FROM Question
        NATURAL JOIN Answer
        WHERE Nagekeken = 'Ja'{}
        GROUP BY Unit
        ORDER BY percentage DESC
    """.format(where)
    )


def learning_goals(cursor, reference=None):
    if reference:
        where = " AND Reference = {}".format(reference)
    else:
        where = ""
    return cursor.execute("""
        SELECT LO, COUNT(DISTINCT QuestionId) AS aantal, 100.0 * SUM(DaadwerkelijkeMarkering) / SUM(Totaalscore) AS percentage
        FROM Question
        NATURAL JOIN Answer
        WHERE Nagekeken = 'Ja'{}
        GROUP BY LO
        ORDER BY percentage DESC
    """.format(where)
    )


def get_testform(cursor):
    return cursor.execute("SELECT TestForm, Test, TotalMark FROM Test").fetchone()


def plot_student_score(cursor, cesuur, plot_dir='.', plot_extension="png"):
    cesuur /= 100.0
    x = np.arange(1, 11)
    y = np.zeros_like(x)
    fig, axes = plt.subplots()
    axes.set(title="Student score",
             xlabel="cijfer",
             ylabel="aantal",
             xticks=x)
    _, _, totalmark = get_testform(cursor)
    for _, _, actualmark, _ in student_score(cursor):
        if actualmark < cesuur * totalmark:
            cijfer = round(1.0 + 4.5 * actualmark / (cesuur * totalmark))
        else:
            cijfer = round(10.0 - 4.5 * (totalmark - actualmark) / ((1.0 - cesuur) * totalmark))
        y[cijfer-1] += 1
    axes.bar(x, y, align="center")
    filename = os.path.join(plot_dir, f"student_score.{plot_extension}")
    fig.savefig(filename)
    return filename


def plot_units(cursor, plot_dir=".", plot_extension="png"):
    all_units = list(units(cursor))
    for unit, in all_units:
        distribution = list(unit_distribution(cursor, unit))
        fig, axes = plt.subplots(figsize=(6.4, 0.85+len(distribution)/2))
        axes.set(title=unit,
                 xlabel="aantal studenten",
                 ylabel="vraag")
        for name, marks in distribution:
            left = 0
            for mark, count in marks:
                axes.barh(name, count, left=left, color=f"C{mark}")
                if int(count) > 0:
                    axes.text(left+int(count)/2, name, str(mark), verticalalignment="center")
                left += count

        make_axes_area_auto_adjustable(axes)
        filename = os.path.join(plot_dir, f"unit_{unit}.{plot_extension}")
        fig.savefig(filename)
        yield unit, filename


def output_answer_score(cursor, output):
    print("Gemiddelde score per vraag", file=output)
    print("==========================", file=output)
    print(file=output)
    print("Vraag | MaxScore | Percentage", file=output)
    print("----- | --------:| ----------:", file=output)
    for question, max_score, percentage in answer_score(cursor):
        print(f"{question} | {max_score:.0f} | {percentage:.1f}", file=output)
    print(file=output)


def output_student_score(cursor, output, cesuur):
    print("Student scores", file=output)
    print("==============", file=output)
    print(file=output)
    if cesuur:
        testform, test, totalmark = get_testform(cursor)
        cesuur /= 100.0
        print("Voornaam | Achternaam | Behaalde punten | Percentage | Cijfer", file=output)
        print("-------- | ---------- | ---------------:| ----------:| ------:", file=output)
        for firstname, lastname, actualmark, percentage in student_score(cursor):
            if actualmark < cesuur * totalmark:
                cijfer = 1.0 + 4.5 * actualmark / (cesuur * totalmark)
            else:
                cijfer = 10.0 - 4.5 * (totalmark - actualmark) / ((1.0 - cesuur) * totalmark)
            print(f"{firstname} | {lastname} | {actualmark} | {percentage:.1f} | {cijfer:.0f}", file=output)
    else:
        print("Voornaam | Achternaam | Behaalde punten | Percentage", file=output)
        print("-------- | ---------- | ---------------:| ----------:", file=output)
        for firstname, lastname, actualmark, percentage in student_score(cursor):
            print(f"{firstname} | {lastname} | {actualmark} | {percentage:.1f}", file=output)
    print(file=output)


def output_student_detail(cursor, output):
    print("Gemaakte toetsen", file=output)
    print("================", file=output)
    print(file=output)
    for firstname, lastname, reference in list(students(cursor)):
        name = " ".join([firstname, lastname])
        print(name, file=output)
        print("-" * len(name), file=output)
        print(file=output)
        print("Unit                            | Aantal | Percentage", file=output)
        print("------------------------------- | ------:| ----------:", file=output)
        for unit, count, percentage in unit_results(cursor, reference):
            if unit:
                print(f"{unit} | {count:.0f} | {percentage:.1f}", file=output)
        print(file=output)
        print("Leerdoel                                                  | Aantal | Percentage", file=output)
        print("--------------------------------------------------------- | ------:| -----------:", file=output)
        for lo, count, percentage in learning_goals(cursor, reference):
            if lo:
                print("{} | {:.0f} | {:.1f}".format(lo.replace("|", "/"), count, percentage), file=output)
        print(file=output)
        print("Vraag                 | Gegeven antwoord (Goede antwoord)                     | Behaalde score / Max score", file=output)
        print("--------------------- | ----------------------------------------------------- | --------------------------:", file=output)
        for Naam, Reactie, Sleutel, DaadwerkelijkeMarkering, TotaalScore in answers(cursor, reference):
            print("{} | {} ({}) | {} / {}".format(
                Naam,
                Reactie.replace("|", "/"),
                Sleutel.replace("|", "/"),
                DaadwerkelijkeMarkering,
                TotaalScore
            ), file=output)
    print(file=output)


def output_item_types(cursor, output):
    print("Item types", file=output)
    print("==========", file=output)
    print(file=output)
    print("ScoreType | Aantal | Percentage", file=output)
    print("--------- | ------:| ----------:", file=output)
    for itemtype, count, percentage in item_types(cursor):
        print(f"{itemtype} | {count:.0f} | {percentage:.1f}", file=output)
    print(file=output)


def output_units(cursor, output, plot_files=None):
    print("Units", file=output)
    print("=====", file=output)
    print(file=output)
    if plot_files:
        for unit, plot_file in plot_files:
            print(f"![{unit}]({plot_file})", file=output)
            print(file=output)
    print("Unit                                | Aantal | Percentage", file=output)
    print("----------------------------------- | ------:| ----------:", file=output)
    for unit, count, percentage in unit_results(cursor):
        if unit:
            print(f"{unit} | {count:.0f} | {percentage:.1f}", file=output)
    print(file=output)


def output_learning_goals(cursor, output):
    print("Leerdoelen", file=output)
    print("==========", file=output)
    print(file=output)
    print("Leerdoel                                                  | Aantal | Percentage", file=output)
    print("--------------------------------------------------------- | ------:| ----------:", file=output)
    for lo, count, percentage in learning_goals(cursor):
        if lo:
            print("{} | {:.0f} | {:.1f}".format(lo.replace("|", "/"), count, percentage), file=output)
    print(file=output)


def output_test(cursor, output, cesuur, plot_file=None):
    testform, test, total_mark = get_testform(cursor)
    print(testform, file=output)
    print("=" * len(testform), file=output)
    print(file=output)
    print("---------   ----", file=output)
    print("Test       ", test, file=output)
    print("Max score  ", total_mark, file=output)
    if cesuur:
        print(f"Cesuur      {cesuur:.1f}%", file=output)
        print("Voldoende   {:.1f} punten".format(total_mark*cesuur/100), file=output)
        print("Gokkans     {:.1f}%".format(2*cesuur-100), file=output)
        print("Minimaal    {:.1f} punten".format(total_mark * (cesuur / 50.0 - 1.0)), file=output)
    print("---------   ----", file=output)
    if plot_file:
        print(file=output)
        print(f"![Student score]({plot_file})", file=output)

    print(file=output)


if __name__ == "__main__":
    argumentParser = argparse.ArgumentParser(description="""
        Parser for ItemsDeliveredRawReport.csv file produced by Surpass.

        A markdown file is outputed with the sections you indicate with
        the optional arguments.

        Tip: if you want to produce a pdf use:
        ./surparser.py --all | pandoc -o surparser.pdf -f markdown
    """)
    argumentParser.add_argument("--all",
        action="store_true",
        help="Output all sections"
    )
    argumentParser.add_argument("--answer-score",
        action="store_true",
        dest="answer_score",
        help="Lists all questions ordered by the average score"
    )
    argumentParser.add_argument("--cesuur",
        help="Cesuur",
        metavar="percentage",
        type=float
    )
    argumentParser.add_argument("--db",
        default=":memory:",
        help="Name of the database file (defaults to :memory:)",
        metavar="database.db",
        type=open_database
    )
    argumentParser.add_argument("--input",
        default="ItemsDeliveredRawReport.csv",
        help="Name of the input CSV file (defaults to ItemsDeliveredRawReport.csv)",
        metavar="input_file_name.csv"
    )
    argumentParser.add_argument("--item-type",
        action="store_true",
        dest="item_type",
        help="Lists all item types with their average score"
    )
    argumentParser.add_argument("--learning-goals",
        action="store_true",
        dest="learning_goals",
        help="Lists all learning goals with their average score"
    )
    argumentParser.add_argument("--output",
        default=sys.stdout,
        help="Name of the outputfile (defaults to stdout)",
        metavar="output_filename.md",
        type=argparse.FileType("w")
    )
    argumentParser.add_argument("--plot",
        action="store_true",
        help="Include plots"
    )
    argumentParser.add_argument("--plot-dir",
        default=".",
        dest="plot_dir",
        help="Directory where plots are stored (defaults to .)",
        metavar="directory"
    )
    argumentParser.add_argument("--plot-extension",
        default="png",
        dest="plot_extension",
        help="Extension of the plots (defaults to png",
        metavar="png/jpeg/pdf/..."
    )
    argumentParser.add_argument("--student-detail",
        action="store_true",
        dest="student_detail",
        help="Lists all answers for each student"
    )
    argumentParser.add_argument("--student-score",
        action="store_true",
        dest="student_score",
        help="Lists all students ordered by their score"
    )
    argumentParser.add_argument("--test-title",
        action="store_true",
        dest="test_title",
        help="Lists the title of the test form"
    )
    argumentParser.add_argument("--units",
        action="store_true",
        help="Lists all units with their average score"
    )
    arguments = argumentParser.parse_args()

    read_csv(arguments.input, arguments.db.cursor())
    arguments.db.commit()

    if len(sys.argv) == 1:
        argumentParser.print_help()
    if arguments.test_title or arguments.all:
        if arguments.plot:
            student_score_plot_file = plot_student_score(arguments.db.cursor(), arguments.cesuur, arguments.plot_dir,
                                                         arguments.plot_extension)
        else:
            student_score_plot_file = None
        output_test(arguments.db.cursor(), arguments.output, arguments.cesuur, student_score_plot_file)
    if arguments.student_score or arguments.all:
        output_student_score(arguments.db.cursor(), arguments.output, arguments.cesuur)
    if arguments.item_type or arguments.all:
        output_item_types(arguments.db.cursor(), arguments.output)
    if arguments.units or arguments.all:
        if arguments.plot:
            unit_plot_files = plot_units(arguments.db.cursor(), arguments.plot_dir, arguments.plot_extension)
        else:
            unit_plot_files = None
        output_units(arguments.db.cursor(), arguments.output, unit_plot_files)
    if arguments.learning_goals or arguments.all:
        output_learning_goals(arguments.db.cursor(), arguments.output)
    if arguments.answer_score or arguments.all:
        output_answer_score(arguments.db.cursor(), arguments.output)
    if arguments.student_detail or arguments.all:
        output_student_detail(arguments.db.cursor(), arguments.output)
