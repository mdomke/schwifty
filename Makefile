.PHONY: docs
docs:
	(cd docs; make html)

.PHONY: test
test:
	@tox -e py37,py38,py39,py310

.PHONY: lint
lint:
	@tox -e lint

.PHONY: lint-docs
lint-docs:
	@tox -e lint-docs

.PHONY: fmt
fmt:
	@tox -e fmt

.PHONY: build
build:
	python -m build
