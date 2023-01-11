
repo=localhost
user=pypiadmin
password=pypiadmin

clean:
	rm -rf dist/*
	rm -rf *.egg-info
	rm -rf build

install:
	make clean
	python -m pip install -U pip
	pip install -r requirements.txt
	pip install --index-url http://$(repo):8036 --trusted-host $(repo) --pre -U shellfoundry-traffic
	pip install --index-url http://$(repo):8036 --trusted-host $(repo) --pre -U cloudshell-sandbox-rest

.PHONY: build
build:
	make clean
	python -m build . --wheel

upload:
	make build
	twine upload --repository-url http://$(repo):8036 --user $(user) --password $(password) dist/*
