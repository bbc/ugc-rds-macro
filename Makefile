COMPONENT_SNAPHOST="ugc-rds-macro"

SOURCES := $(shell find src -name *.py)

.PHONY: clean
clean:
	rm -rf BUILD rdsmacroinstance.zip

.PHONY: build
build: clean rdsmacroinstance.zip

# Include any _other_ dependencies you add to the requirements.txt

# Note that this must be run on a box with python3 installed!
# Also, if any of your pip dependencies have C extensions that need to be compiled
# they should be compiled in an environment that matches the target - i.e. you can't compile
# C extensions on macOS or Windows and expect them to work.
rdsmacroinstance.zip: $(SOURCES) requirements.txt venv
	mkdir -p BUILD
	cp src/lambdas/ugc_rds_macro.py BUILD/
	# use the venv to install pip dependencies into BUILD/
	./venv/bin/python3 -B -m pip install -r requirements.txt -t BUILD/
	# Remove dirs we won't need
	# Note that the lambda environment provides boto3 and its dependencies; you don't need to bundle them
	# This isn't particularly elegant; using something like `pipdeptree -p boto3 --json` (pip install pipdeptree) might be better!
	rm -rf BUILD/*.dist-info BUILD/bin BUILD/botocore BUILD/boto3 BUILD/docutils BUILD/jmespath BUILD/dateutil BUILD/s3transfer BUILD/six.py
	# remove all __pycache__ dirs too
	find BUILD -name "__pycache__" -type d -exec rm -r {} +
	cd BUILD && zip -9 -q -r ../rdsmacroinstance.zip .

.PHONY: venv
venv: requirements.txt
	python3 -m venv $@
	$@/bin/pip3 install --upgrade pip setuptools wheel
	$@/bin/pip3 install -r requirements.txt

.PHONY: release
release: build
	cosmos-release lambda --lambda-version=autoincrement "./rdsmacroinstance.zip" $(COMPONENT_SNAPHOST)

venv/%: %/requirements.txt
	(python3 -m venv $@ && \
		$@/bin/python3 -m pip install --upgrade pip setuptools wheel && \
		$@/bin/python3 -m pip install -r $<) || rm -rf $@

.PHONY: test
test: venv/test
	PYTHONPATH=$$PYTHONPATH:./src:./src/include ./venv/test/bin/python3 -m unittest discover -v -s ./test -p *_test.py
