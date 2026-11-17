FROM python:3.12.16-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /workspace
COPY requirements-runtime.lock /tmp/requirements-runtime.lock
RUN python -m pip install --disable-pip-version-check --require-hashes --only-binary=:all: -r /tmp/requirements-runtime.lock
COPY app ./app
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS tests
USER root
COPY requirements-validation.lock /tmp/requirements-validation.lock
RUN python -m pip install --disable-pip-version-check --require-hashes --only-binary=:all: -r /tmp/requirements-validation.lock
COPY tests ./tests
COPY BASELINE.json ./BASELINE.json
COPY pyproject.toml ./pyproject.toml
COPY packaging/container_tests.py ./packaging/container_tests.py
USER 10001:10001
CMD ["python", "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--basetemp", "/tmp/control-tests"]
