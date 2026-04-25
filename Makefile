PY ?= python3
PYTHONPATH := src

.PHONY: test regen-golden train-pinn

test:
	PYTHONPATH=$(PYTHONPATH) $(PY) -m pytest tests/engine -q

regen-golden:
	PYTHONPATH=$(PYTHONPATH) $(PY) scripts/regen_golden.py

train-pinn:
	PYTHONPATH=$(PYTHONPATH) $(PY) scripts/train_pinn.py
