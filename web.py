import hashlib
import os

import pypandoc
from flask import Flask, render_template, request, redirect

import surparser

UPLOAD_DIR = os.path.join(".", "static")
app = Flask(__name__)


@app.route("/")
def index():
    _, output_formats = pypandoc.get_pandoc_formats()
    return render_template("index.html", output_formats=output_formats)


@app.route("/convert", methods=["POST"])
def convert():
    with request.files["input"].stream as input_file:
        csv_data = input_file.read()
    md5 = hashlib.md5(csv_data).hexdigest()
    directory = os.path.join(UPLOAD_DIR, md5)
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, "ItemsDeliveredRawReport.csv"), "wb") as csv_file:
        csv_file.write(csv_data)
    argument_parser = surparser.get_argument_parser()
    arguments = argument_parser.parse_args(extract_arguments_from_request(directory))
    surparser.run(arguments)
    output_filename = os.path.join(directory, "toetsanalyse." + default_extension())
    pypandoc.convert_file(os.path.join(directory, "toetsanalyse.md"),
                          request.form["output-format"],
                          outputfile=output_filename)
    return redirect(output_filename)


def extract_checkbox_arguments_from_request():
    checkboxes = ["answer-score", "distribution", "item-type", "learning-goals", "plot", "student-detail",
                  "student-score", "test-title", "translation", "units"]
    for checkbox in checkboxes:
        if checkbox in request.form:
            yield f"--{checkbox}"


def default_extension():
    default_extensions = {
        "beamer": "pdf",
        "html5": "html",
        "latex": "tex",
        "markdown": "md",
        "markdown_github": "md",
        "markdown_mmmd": "md",
        "markdown_phpextra": "md",
        "markdown_strict": "md",
        "native": "md",
        "plain": "txt",
        "slideous": "html",
        "slidy": "html",
    }
    if "output-format" in request.form:
        return default_extensions.get(request.form["output-format"], request.form["output-format"])


def extract_arguments_from_request(directory):
    yield from extract_checkbox_arguments_from_request()

    yield "--input"
    yield os.path.join(directory, "ItemsDeliveredRawReport.csv")

    yield "--output"
    yield os.path.join(directory, "toetsanalyse.md")

    if "cesuur" in request.form:
        try:
            cesuur = float(request.form["cesuur"])
            yield "--cesuur"
            yield str(cesuur)
        except ValueError:
            pass

    if "plot" in request.form:
        yield "--plot-dir"
        yield directory

    if "output-format" in request.form and request.form["output-format"] == "pdf":
        yield "--plot-extension"
        yield "pdf"


if __name__ == "__main__":
    pypandoc.ensure_pandoc_installed()

    app.run(host='0.0.0.0', port=os.getenv('PORT', 8080), debug=True)
