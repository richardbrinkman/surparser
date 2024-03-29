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
from functools import lru_cache

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.axes_grid1.axes_divider import make_axes_area_auto_adjustable


def open_database(filename):
    """Opens the database pointed to by filename and creates the necessary tables."""

    db = sqlite3.connect(filename)
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Student(
                Referentie MEDIUMINT UNSIGNED NOT NULL PRIMARY KEY,
                Voornaam TEXT NOT NULL,
                Achternaam TEXT NOT NULL,
                Geslacht CHAR(1),
                Sleutelcode CHAR(8),
                Daadwerkelijke_markering SMALLINT UNSIGNED,
                Totaalscore SMALLINT UNSIGNED,
                Cijfer CHAR(4)
        );
    """)
    cursor.execute("DELETE FROM Student;")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Toets(
            Toetsformulier TEXT NOT NULL PRIMARY KEY,
            Toets TEXT,
            Centrum TEXT,
            Onderwerp TEXT,
            Totaalscore SMALLINT UNSIGNED
        );
    """)
    cursor.execute("DELETE FROM Toets;")
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
            Referentie MEDIUMINT UNSIGNED NOT NULL
                REFERENCES Student(Referentie)
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
    params["Daadwerkelijke_markering"] = float(params["Daadwerkelijke markering"].replace(",", "."))
    del params["Daadwerkelijke markering"]
    return cursor.execute("""
        INSERT OR REPLACE INTO Student(Referentie, Voornaam, Achternaam, Geslacht, Sleutelcode, Daadwerkelijke_markering, Totaalscore, Cijfer)
        VALUES(:Referentie, :Voornaam, :Achternaam, :Geslacht, :Sleutelcode, :Daadwerkelijke_markering, :Totaalscore, :Cijfer);
    """, params)


def insert_toetsformulier(cursor, params):
    return cursor.execute("""
        INSERT OR REPLACE INTO Toets(Toetsformulier, Toets, Centrum, Onderwerp, Totaalscore)
        VALUES(:Toetsformulier, :Toets, :Centrum, :Onderwerp, :Totaalscore)
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
        INSERT OR REPLACE INTO Answer(QuestionId, Referentie, DaadwerkelijkeMarkering, Reactie, Weergavetijd, Volgorde, Nagekeken)
        VALUES(:QuestionId, :Referentie, :DaadwerkelijkeMarkering, :Reactie, :Weergavetijd, :Volgorde, :Nagekeken);
    """, parse_answer_params(params))


def parse_question_params(params):
    for key in params:
        name = re.match(r"Naam \[(.+)\]", key)
        if name:
            question_id = name.group(1)
            if params["Cijfer"] != "Ongeldig":
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
                "Referentie": params["Referentie"],
                "DaadwerkelijkeMarkering": params["Daadwerkelijke markering [{}]".format(question_id)],
                "Reactie": params["Reactie [{}]".format(question_id)],
                "Weergavetijd": params["Weergavetijd [{}]".format(question_id)],
                "Volgorde": params["Gepresenteerde volgorde [{}]".format(question_id)],
                "Nagekeken": params["Nagekeken [{}]".format(question_id)]
            }


def read_csv(input_filename, cursor):
    with open(input_filename, newline="") as csvfile:
        for row in csv.DictReader(csvfile):
            for func in [insert_student, insert_toetsformulier, insert_question, insert_vijanden, insert_answer]:
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


def student_score(cursor, cesuur=None):
    cursor.execute("""
        SELECT Voornaam, Achternaam, Daadwerkelijke_markering, Totaalscore
        FROM Student
        NATURAL JOIN Answer
        WHERE Nagekeken = 'Ja'
        GROUP BY Referentie
        ORDER BY Daadwerkelijke_markering DESC
    """)
    for first_name, last_name, actual_score, total_score in cursor:
        if cesuur is None:
            yield first_name, last_name, actual_score, 100.0 * actual_score / total_score
        else:
            yield first_name, last_name, actual_score, 100.0 * actual_score / total_score, mark(actual_score, cesuur,
                                                                                                total_score)


def pass_percentage(cursor, cesuur):
    pass_count = 0
    count = 0
    for _, _, _, _, cijfer in student_score(cursor, cesuur):
        if float(cijfer) >= 5.5:
            pass_count += 1
        count += 1
    return 100.0 * pass_count / count


def students(cursor):
    return cursor.execute("""
        SELECT Voornaam, Achternaam, Referentie
        FROM Student
        NATURAL JOIN Answer
        WHERE Nagekeken = 'Ja'
        GROUP BY Referentie
        ORDER BY Voornaam, Achternaam
    """)


def answers(cursor, referentie):
    return cursor.execute("""
        SELECT Naam, Reactie, Sleutel, DaadwerkelijkeMarkering, TotaalScore
        FROM Question
        NATURAL JOIN Answer
        WHERE Nagekeken = 'Ja' AND Referentie = ?
    """, (referentie,))


def multiplechoice_questions(cursor):
    return cursor.execute("""
        SELECT QuestionId, Naam, Sleutel
        FROM Question
        WHERE ItemType IN ('Meerkeuzevraag', 'Meerdere antwoorden', 'Eender/of')
    """)


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


def unit_distribution(db, unit):
    sql = """
        SELECT QuestionId, Naam
        FROM Question
        WHERE Unit = ?
    """
    for question_id, name in db.cursor().execute(sql, (unit,)):
        yield name, unit_question(db.cursor(), question_id)


def question_distribution(db):
    for question_id, name in db.cursor().execute("SELECT QuestionId, Naam FROM Question"):
        yield name, unit_question(db.cursor(), question_id)


def unit_results(cursor, referentie=None):
    if referentie:
        where = " AND Referentie = {}".format(referentie)
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


def learning_goals(cursor, referentie=None):
    if referentie:
        where = " AND Referentie = {}".format(referentie)
    else:
        where = ""
    return cursor.execute("""
        SELECT LO, COUNT(DISTINCT QuestionId) AS aantal, 100.0 * SUM(DaadwerkelijkeMarkering) / SUM(Totaalscore) AS percentage
        FROM Question
        NATURAL JOIN Answer
        WHERE Nagekeken = 'Ja' AND LO IS NOT NULL{}
        GROUP BY LO
        ORDER BY percentage DESC
    """.format(where))


@lru_cache(maxsize=1)
def all_multiplechoice_answers(cursor):
    cursor.execute("""
        SELECT Reactie
        FROM Answer
        NATURAL JOIN Question
        WHERE ItemType IN ('Meerkeuzevraag', 'Meerdere antwoorden', 'Eender/of') AND Reactie != ''
        GROUP BY Reactie
    """)
    return sorted({choice for answer, in cursor for choice in answer.split('| ')})


def distribution(cursor):
    choices = all_multiplechoice_answers(cursor)
    for question_id, name, correct_answer in multiplechoice_questions(cursor.connection.cursor()):
        cursor.execute("""
            SELECT Reactie, COUNT(*)
            FROM Answer
            WHERE QuestionId = ? AND Reactie != ''
            GROUP BY Reactie
        """, (question_id,))
        result = {choice: 0 for choice in choices}
        for answer, count in cursor:
            for choice in answer.split('| '):
                result[choice] += count
        yield name, correct_answer, result


def get_toetsformulier(cursor):
    return cursor.execute("SELECT Toetsformulier, Toets, Totaalscore FROM Toets").fetchone()


def plot_student_score(cursor, cesuur, plot_dir='.', plot_extension="png"):
    cesuur /= 100.0
    x = np.arange(1, 11)
    y = np.zeros_like(x)
    fig, axes = plt.subplots()
    axes.set(title="Student score",
             xlabel="cijfer",
             ylabel="aantal",
             xticks=x)
    _, _, totaalscore = get_toetsformulier(cursor)
    for _, _, daadwerkelijke_markering, _, cijfer in student_score(cursor, cesuur):
        cijfer = round(cijfer)
        y[cijfer - 1] += 1
    axes.bar(x, y, align="center")
    filename = os.path.join(plot_dir, f"student_score.{plot_extension}")
    fig.savefig(filename)
    plt.close()
    return filename


def plot_units(db, plot_dir=".", plot_extension="png"):
    for unit, in units(db.cursor()):
        yield plot_unit(list(unit_distribution(db, unit)), plot_dir, plot_extension, unit)


def plot_questions(db, plot_dir=".", plot_extension="png"):
    return plot_unit(list(question_distribution(db)), plot_dir, plot_extension, "questions")


def plot_unit(distribution, plot_dir, plot_extension, unit):
    fig, axes = plt.subplots(figsize=(6.4, 0.85 + len(distribution) / 2))
    axes.set(title=unit,
             xlabel="aantal studenten",
             ylabel="vraag")
    for name, marks in distribution:
        left = 0
        for mark, count in marks:
            axes.barh(name, count, left=left, color=f"C{round(float(str(mark).replace(',', '.')))}")
            if int(count) > 0:
                axes.text(left + int(count) / 2, name, str(mark), verticalalignment="center")
            left += count
    make_axes_area_auto_adjustable(axes)
    filename = os.path.join(plot_dir, f"unit_{unit}.{plot_extension}")
    fig.savefig(filename)
    plt.close()
    return unit, filename


def output_answer_score(cursor, output, plot_file=None):
    print("Gemiddelde score per vraag", file=output)
    print("==========================", file=output)
    print(file=output)
    if plot_file:
        unit, file_name = plot_file
        print(f"![{unit}]({file_name})", file=output)
        print(file=output)
    print("Vraag | MaxScore | Percentage", file=output)
    print("----- | --------:| ----------:", file=output)
    for question, max_score, percentage in answer_score(cursor):
        print(f"{question} | {max_score:.0f} | {percentage:.1f}", file=output)
    print(file=output)


def format_answer(correct_answer, answer, count):
    if count == 0:
        return ""
    elif answer in correct_answer:
        return f"**{count:d}**"
    else:
        return str(count)


def output_distribution(cursor, output):
    print("Antwoord distributie meerkeuzevragen", file=output)
    print("====================================", file=output)
    print(file=output)
    print("Vraag | {}".format(" | ".join(all_multiplechoice_answers(cursor))), file=output)
    print("----- | {}".format(" | ".join(map(lambda x: "-" * len(x), all_multiplechoice_answers(cursor)))), file=output)
    for question, correct_answer, answers in distribution(cursor):
        print("{} | {}".format(question, " | ".join(
            [format_answer(correct_answer, answer, answers[answer]) for answer in answers])), file=output)
    print(file=output)


def output_student_score(cursor, output, cesuur):
    print("Student scores", file=output)
    print("==============", file=output)
    print(file=output)
    if cesuur:
        toetsformulier, toets, totaalscore = get_toetsformulier(cursor)
        cesuur /= 100.0
        print("Voornaam | Achternaam | Behaalde punten | Percentage | Cijfer", file=output)
        print("-------- | ---------- | ---------------:| ----------:| ------:", file=output)
        for voornaam, achternaam, daadwerkelijke_markering, percentage, cijfer in student_score(cursor, cesuur):
            print(f"{voornaam} | {achternaam} | {daadwerkelijke_markering} | {percentage:.1f} | {cijfer:.0f}", file=output)
    else:
        print("Voornaam | Achternaam | Behaalde punten | Percentage", file=output)
        print("-------- | ---------- | ---------------:| ----------:", file=output)
        for voornaam, achternaam, daadwerkelijke_markering, percentage in student_score(cursor):
            print(f"{voornaam} | {achternaam} | {daadwerkelijke_markering} | {percentage:.1f}", file=output)
    print(file=output)


def mark(actualscore, cesuur, totalscore):
    if actualscore < 0:
        return 1.0
    elif actualscore > totalscore:
        return 10.0
    elif actualscore < cesuur * totalscore:
        return 1.0 + 4.5 * actualscore / (cesuur * totalscore)
    else:
        return 10.0 - 4.5 * (totalscore - actualscore) / ((1.0 - cesuur) * totalscore)


def score(daadwerkelijke_markering, cesuur, totalscore):
    if daadwerkelijke_markering < 1.0:
        return 0.0
    elif daadwerkelijke_markering > 10.0:
        return totalscore
    elif daadwerkelijke_markering < 5.5:
        return (daadwerkelijke_markering - 1.0) * cesuur * totalscore / 4.5
    else:
        return totalscore - (10.0 - daadwerkelijke_markering) * (1.0 - cesuur) * totalscore / 4.5


def output_student_detail(cursor, output, show_units=True, show_learning_goals=True):
    print("Gemaakte toetsen", file=output)
    print("================", file=output)
    print(file=output)
    for voornaam, achternaam, referentie in list(students(cursor)):
        name = " ".join([voornaam, achternaam])
        print(name, file=output)
        print("-" * len(name), file=output)
        print(file=output)
        if show_units:
            print("Unit                            | Aantal | Percentage", file=output)
            print("------------------------------- | ------:| ----------:", file=output)
            for unit, count, percentage in unit_results(cursor, referentie):
                if unit:
                    print(f"{unit} | {count:.0f} | {percentage:.1f}", file=output)
            print(file=output)
        if show_learning_goals:
            print("Leerdoel                                                  | Aantal | Percentage", file=output)
            print("--------------------------------------------------------- | ------:| -----------:", file=output)
            for lo, count, percentage in learning_goals(cursor, referentie):
                if lo:
                    print("{} | {:.0f} | {:.1f}".format(lo.replace("|", "/"), count, percentage), file=output)
            print(file=output)
        print("Vraag                 | Gegeven antwoord (Goede antwoord)                     | Behaalde score / Max score", file=output)
        print("--------------------- | ----------------------------------------------------- | --------------------------:", file=output)
        for Naam, Reactie, Sleutel, DaadwerkelijkeMarkering, TotaalScore in answers(cursor, referentie):
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


def output_toets(cursor, output, cesuur, plot_file=None):
    toetsformulier, toets, total_mark = get_toetsformulier(cursor)
    print(toetsformulier, file=output)
    print("=" * len(toetsformulier), file=output)
    print(file=output)
    print("------------------   ----", file=output)
    print("Toets                ", toets, file=output)
    print("Max score           ", total_mark, file=output)
    if cesuur:
        print(f"Cesuur               {cesuur:.1f}%", file=output)
        print("Voldoende            {:.1f} punten".format(total_mark * cesuur / 100), file=output)
        print("Gokkans              {:.1f}%".format(2 * cesuur - 100), file=output)
        print("Slagingspercentage   {:.1f}%".format(pass_percentage(cursor, cesuur / 100.0)), file=output)
    print("------------------   ----", file=output)
    if plot_file:
        print(file=output)
        print(f"![Student score]({plot_file})", file=output)

    print(file=output)


def output_translation(cursor, output, cesuur):
    _, _, total_mark = get_toetsformulier(cursor)
    cesuur /= 100.0
    print("Omrekeningstabel", file=output)
    print("================", file=output)
    print(file=output)
    print("Score        | Cijfer", file=output)
    print("-----------  | ------", file=output)
    for cijfer in range(1, 11):
        print("{:.1f} - {:.1f} | {:d}".format(
            score(cijfer - 0.5, cesuur, total_mark),
            score(cijfer + 0.5, cesuur, total_mark),
            cijfer
        ), file=output)
    print(file=output)


def get_argument_parser():
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
    argumentParser.add_argument("--distribution",
                                action="store_true",
                                help="Adds a table of multiple choice answers and their distribution"
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
    argumentParser.add_argument("--translation",
                                action="store_true",
                                help="Add a translation table between score and marks"
                                )
    argumentParser.add_argument("--units",
                                action="store_true",
                                help="Lists all units with their average score"
                                )
    return argumentParser


def run(arguments):
    read_csv(arguments.input, arguments.db.cursor())
    arguments.db.commit()
    unit_plot_files = None
    arguments.units = len(list(units(arguments.db.cursor()))) > 0 and (arguments.units or arguments.all)
    arguments.learning_goals = len(list(learning_goals(arguments.db.cursor()))) > 0 and (
            arguments.learning_goals or arguments.all)
    if arguments.test_title or arguments.all:
        if arguments.plot and arguments.cesuur:
            student_score_plot_file = plot_student_score(arguments.db.cursor(), arguments.cesuur, arguments.plot_dir,
                                                         arguments.plot_extension)
        else:
            student_score_plot_file = None
        output_toets(arguments.db.cursor(), arguments.output, arguments.cesuur, student_score_plot_file)
    if (arguments.translation or arguments.all) and arguments.cesuur:
        output_translation(arguments.db.cursor(), arguments.output, arguments.cesuur)
    if arguments.student_score or arguments.all:
        output_student_score(arguments.db.cursor(), arguments.output, arguments.cesuur)
    if arguments.item_type or arguments.all:
        output_item_types(arguments.db.cursor(), arguments.output)
    if arguments.units:
        if arguments.plot:
            unit_plot_files = plot_units(arguments.db, arguments.plot_dir, arguments.plot_extension)
        output_units(arguments.db.cursor(), arguments.output, unit_plot_files)
    if arguments.learning_goals:
        output_learning_goals(arguments.db.cursor(), arguments.output)
    if arguments.answer_score or arguments.all:
        if arguments.plot and not unit_plot_files:
            question_plot_file = plot_questions(arguments.db, arguments.plot_dir, arguments.plot_extension)
        else:
            question_plot_file = None
        output_answer_score(arguments.db.cursor(), arguments.output, question_plot_file)
    if arguments.distribution or arguments.all:
        output_distribution(arguments.db.cursor(), arguments.output)
    if arguments.student_detail or arguments.all:
        output_student_detail(arguments.db.cursor(), arguments.output, arguments.units, arguments.learning_goals)
    arguments.output.close()


if __name__ == "__main__":
    argumentParser = get_argument_parser()
    arguments = argumentParser.parse_args()

    if len(sys.argv) == 1:
        argumentParser.print_help()
    else:
        run(arguments)
