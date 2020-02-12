[![Build Status](https://travis-ci.org/richardbrinkman/surparser.svg?branch=master)](https://travis-ci.org/richardbrinkman/surparser)

Surparser
=========

```
usage: surparser.py [-h] [--all] [--answer-score] [--cesuur percentage]
                    [--db database.db] [--input input_file_name.csv]
                    [--item-type] [--learning-goals]
                    [--output output_filename.md] [--plot]
                    [--plot-dir directory] [--plot-extension png/jpeg/pdf/...]
                    [--student-detail] [--student-score] [--test-title]
                    [--translation] [--units]

Parser for ItemsDeliveredRawReport.csv file produced by Surpass. A markdown
file is outputed with the sections you indicate with the optional arguments.
Tip: if you want to produce a pdf use: ./surparser.py --all | pandoc -o
surparser.pdf -f markdown

optional arguments:

  -h, --help            show this help message and exit
  --all                 Output all sections
  --answer-score        Lists all questions ordered by the average score
  --cesuur percentage   Cesuur
  --db database.db      Name of the database file (defaults to :memory:)
  --input input_file_name.csv
                        Name of the input CSV file (defaults to
                        ItemsDeliveredRawReport.csv)
  --item-type           Lists all item types with their average score
  --learning-goals      Lists all learning goals with their average score
  --output output_filename.md
                        Name of the outputfile (defaults to stdout)
  --plot                Include plots
  --plot-dir directory  Directory where plots are stored (defaults to .)
  --plot-extension png/jpeg/pdf/...
                        Extension of the plots (defaults to png
  --student-detail      Lists all answers for each student
  --student-score       Lists all students ordered by their score
  --test-title          Lists the title of the test form
  --translation         Add a translation table between score and marks
  --units               Lists all units with their average score
```
