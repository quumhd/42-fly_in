CC = Python3
SRCS = src
MAP ?= maps/easy/01_linear_path.txt


all: install run

run:
	$(CC) $(SRCS)/main.py $(MAP)

debug:
	$(CC) -m pdb $(SRCS)/main.py $(MAP)

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

install:
	$(CC) -m pip install -r requirements.txt

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	rm -rf .mypy_cache

.PHONY: all install run debug clean lint