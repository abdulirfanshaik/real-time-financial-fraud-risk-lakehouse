PYTHON ?= python3
export PYTHONPATH := src

.PHONY: generate pipeline demo test clean

generate:
	$(PYTHON) -m risk_lakehouse.generator --output data/raw --customers 500 --accounts 750 --cards 1000 --transactions 5000 --seed 20260917

pipeline:
	$(PYTHON) -m risk_lakehouse.pipeline --input data/raw --output data/processed --config config/project.json

demo: generate pipeline
	@echo "Demo complete. Review data/processed/metrics/quality_report.json"

test:
	$(PYTHON) -m unittest discover -s tests -v

clean:
	$(PYTHON) -m risk_lakehouse.cleanup --output data/processed

