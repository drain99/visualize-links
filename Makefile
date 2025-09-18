.PHONY: ui

ui:
	cd ui && npm install && npm run build
	cp -r ui/dist/* src/visualize_links/static/

build: ui
	python -m build

test-publish: build
	python -m twine upload --repository testpypi --verbose dist/*