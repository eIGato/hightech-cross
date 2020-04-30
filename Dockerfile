FROM python:3.8

RUN mkdir -p /app/ && \
    pip install pipenv

COPY Pipfile /app/
COPY Pipfile.lock /app/

WORKDIR /app/

RUN pipenv install --system --ignore-pipfile --clear --deploy --dev

COPY hightech_cross/ /app/

ENV PYTHONPATH="./"

CMD ["./manage.py", "runserver", "0.0.0.0:80"]
