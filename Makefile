
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

sync:
	if [ ! -d "data" ]; \
	then \
		mkdir ./data \
		&& cd data; \
	else \
		cd data \
		&& rm -rf .git; \
		if [ -d "examples" ]; \
		then \
			cd examples \
			&& rm -rf v2.0/ \
			&& rm -rf v3.0/ \
			&& cd ..; \
		fi; \
		if [ -d "schemas" ]; \
		then \
			rm -rf schemas/; \
		fi; \
	fi; \
	git init \
	&& git config core.sparsecheckout true \
	&& echo "schemas/*" > .git/info/sparse-checkout \
	&& echo "examples/*" >> .git/info/sparse-checkout \
	&& git remote add -f origin https://github.com/OAI/OpenAPI-Specification \
	&& git pull origin master \
	&& rm -rf .git \
	&& cd ..
