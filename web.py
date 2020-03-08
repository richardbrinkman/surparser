from flask import Flask, render_template, request
import os
import pypandoc


app = Flask(__name__)


@app.route("/")
def index():
    _, output_formats = pypandoc.get_pandoc_formats()
    return render_template("index.html", output_formats=output_formats)


@app.route("/convert", methods=["POST"])
def convert():
    result = ""
    for key in request.form:
        result += "{} == {}\n".format(key, request.form[key])
    return result


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=os.getenv('PORT', 8080), debug=True)
