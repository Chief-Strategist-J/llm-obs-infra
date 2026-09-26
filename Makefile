.PHONY: build test up down status health certs clean

all: build

build:
	@$(MAKE) -C packages/platform-orchestrator build

test:
	@$(MAKE) -C packages/platform-orchestrator test

up: build
	@./bin/llmobs up $(PROFILE)

down: build
	@./bin/llmobs down

status: build
	@./bin/llmobs status

health: build
	@./bin/llmobs health

certs: build
	@./bin/llmobs certs

scale: build
	@./bin/llmobs scale $(ARGS)

clean:
	@$(MAKE) -C packages/platform-orchestrator clean
