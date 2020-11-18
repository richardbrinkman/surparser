import argparse
import pandas


argument_parser = argparse.ArgumentParser(description="""
    Converter of ItemDeliveredRawReport.csv to toetsinzage.xlsx.

    Given an ItemsDeliveredRawReport.csv file produced by Surpass, this
    tool generates an Excel file that can be used to schedule a
    toetsinzage.
""")
argument_parser.add_argument("--input",
    default="ItemsDeliveredRawReport.csv",
    help="Name of the input CSV file (defaults to ItemsDeliveredRawReport.csv)",
    metavar="input_file_name.csv"
)
argument_parser.add_argument("--output",
    default="toetsinzage.xlsx",
    help="Name of the generated Excel file (defaults to toetsinzage.xlsx)",
    metavar="output_file_name.xlsx"
)
parser = argument_parser.parse_args()

input_df = pandas.read_csv(parser.input)
df = input_df[input_df["Cijfer"] != "Ongeldig"]
output_df = df[["Voornaam", "Achternaam", "Sleutelcode"]]
pandas.options.mode.chained_assignment = None
output_df["Email"] = df["Referentie"].astype(str) + "@student.saxion.nl"
output_df.to_excel(parser.output, index=False)
