# Use the official Python image from the Docker Hub
FROM python:3.14-slim

# Set environment variables
ENV PYTHONUNBUFFERED="1"
ENV POETRY_NO_INTERACTION="1"
ENV POETRY_VIRTUALENVS_IN_PROJECT="1"
ENV POETRY_VIRTUALENVS_CREATE="1"
ENV PORT="8000"
ENV SMTP_HOST="localhost"
ENV SMTP_PORT="25"
ENV USE_STARTTLS="true"
ENV USE_LOGIN="false"
ENV SMTP_USER=""
ENV SMTP_PASSWORD=""
ENV EMAIL_FROM="no-reply@example.com"
ENV EMAIL_TO="no-reply@example.com"

WORKDIR /app

# hadolint ignore=DL3013,DL3042
RUN --mount=type=cache,target=/root/.cache/pip \
  pip install --upgrade poetry

COPY pyproject.toml /app/
COPY poetry.lock /app/
RUN --mount=type=cache,target=/root/.cache/pypoetry \
  poetry install --no-root

COPY . /app/

USER 1000
ENTRYPOINT ["poetry", "run", "python", "hook2mail.py"]
