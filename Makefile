
repo=localhost
user=pypiadmin
password=pypiadmin

install:
	python -m pip install -U pip
	pip install -i http://$(repo):8036 --trusted-host $(repo) -U --pre -r requirements-dev.txt

.PHONY: build
build:
	rm -rf dist/*
	rm -rf *.egg-info
	rm -rf build
	python setup.py bdist_wheel

upload:
	make build
	twine upload --repository-url http://$(repo):8036 --user $(user) --password $(password) dist/*
