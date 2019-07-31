
install:
	pip install -e . -r requirements.txt

test:
	tox

clean:
	find ./ -type d -name __pycache__ | xargs rm -rf \
		&& find ./ -name '*.py[co]' -delete \
		&& find ./ -name '*.cache' -delete \
		&& rm -rf .cache .coverage .pytest_cache/ ./*.egg-info/ .tox/ build/ dist/

coverage:
	tox -e coverage
	codecov
