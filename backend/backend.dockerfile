FROM python:3.11.8

WORKDIR /root_app/backend/app

COPY ./backend/requirements.txt /root_app/requirements.txt
COPY pytest.ini /root_app/pytest.ini
RUN pip install --upgrade pip setuptools wheel build
RUN pip install --no-cache-dir -r /root_app/requirements.txt
COPY ./backend /root_app/backend
COPY ./common/app /root_app/common/app

WORKDIR /root_app
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
