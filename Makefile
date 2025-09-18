.PHONY: build_tests launch_test build_ui dev build publish_test

CXXFLAGS := --std=c++17 -Wno-unused-variable -g3

build_tests:
	@for src in tests/*.cpp; do \
		exe=$${src%.cpp}; \
		echo "Building test $$src..."; \
		$(CXX) $(CXXFLAGS) -o $$exe $$src; \
	done

launch_test: TARGET ?= list_reverse_k_group
launch_test: build_tests
	@echo "Launching lldb for $(TARGET)"
	visualize-links-ui
	lldb-19 --source tests/$(TARGET).lldb tests/$(TARGET)

build_ui:
	cd ui && npm install && npm run build
	rm -rf src/visualize_links/static
	mkdir src/visualize_links/static
	cp -r ui/dist/* src/visualize_links/static/

dev: build_ui
	pip install -e .

build: build_ui
	rm -r dist/*
	python -m build

publish_test: build
	python -m twine upload --verbose --repository testpypi dist/*

publish: build
	python -m twine upload --verbose --repository pypi dist/*
