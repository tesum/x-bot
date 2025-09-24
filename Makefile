.PHONY: run test install lint format clean

run:
	python3 src/app.py

install:
	python3 -m venv .venv
	source .venv/bin/activate
	pip install -r requirements.txt

clean:
	rm -rf src/__pycache__ *.pyc

clean_db:
	rm -rf users.db