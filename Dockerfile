FROM python

MAINTAINER Richard Brinkman <r.brinkman@saxion.nl>

ENV PORT=8080

EXPOSE $PORT

WORKDIR /srv

COPY requirements.txt /srv

RUN apt-get update\
 && apt-get install -y pandoc texlive-latex-base texlive-latex-recommended texlive-fonts-recommended\
 && rm -rf /var/lib/apt/lists/*\
 && pip install -r /srv/requirements.txt

COPY surparser.py web.py /srv/
COPY templates/ /srv/templates/

CMD python web.py
