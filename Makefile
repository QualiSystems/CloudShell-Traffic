
repo=localhost
user=pypiadmin
password=pypiadmin

install:
	pip install -U -r requirements-dev.txt

.PHONY: build
build:
	rm -rf dist/*
	python setup.py bdist_wheel

upload:
	make build
	twine upload --repository-url http://$(repo):8036 --user $(user) --password $(password) dist/*
