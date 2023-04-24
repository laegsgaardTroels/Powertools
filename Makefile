include .python-environment

#################################################################################
# ENVIRONMENT                                                                   #
#################################################################################

## Create a virtual environment for development.
.PHONY: venv
venv: .python-environment
	rm -rf venv
	${PYTHON_INTERPRETER} -c \
		'import sys; assert sys.version_info.major == ${PYTHON_MAJOR_VERSION}'
	${PYTHON_INTERPRETER} -c \
		'import sys; assert sys.version_info.minor >= ${PYTHON_MINOR_VERSION}'
	${PYTHON_INTERPRETER} -m venv venv
	. venv/bin/activate; \
		${PYTHON_INTERPRETER} -m pip install --upgrade setuptools; \
		${PYTHON_INTERPRETER} -m pip install --upgrade wheel; \
		${PYTHON_INTERPRETER} -m pip install --upgrade pip; \
		${PYTHON_INTERPRETER} -m pip install -e .[dev]

## Clean every cached file.
.PHONY: clean
clean:
	rm -rf venv
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete

#################################################################################
# DEVELOPMENT                                                                   #
#################################################################################

## Run all tests. Used to set up a new user. When running: `make` this target will run.
.PHONY: tests
tests:
	. venv/bin/activate; \
		${PYTHON_INTERPRETER} -m pytest \
			--log-cli-level=INFO \
			--cov-report term \
			--cov=src \
			tests/

## Lint using flake8.
.PHONY: lint
lint: 
	. venv/bin/activate; \
		${PYTHON_INTERPRETER} -m flake8 src
	. venv/bin/activate; \
		${PYTHON_INTERPRETER} -m flake8 tests


#################################################################################
# DOCUMENTATION                                                                 #
#################################################################################

## Create documentation using sphinx.
.PHONY: docs
docs: venv/bin/activate
	. venv/bin/activate; \
		sphinx-apidoc --force -o docs/source -t docs/source/_templates --module-first \
		transformlib \
		transformlib/exceptions.py transformlib/config.py transformlib/testing.py; \
	cd docs; \
		${MAKE} html
	touch docs/.nojekyll
