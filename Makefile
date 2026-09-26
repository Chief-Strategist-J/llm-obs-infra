.PHONY: build test up down restart status logs health certs scale setup backup-purge cloudflare free-ports server clean

all: build

build:
	@$(MAKE) -C packages/platform-orchestrator build

test:
	@$(MAKE) -C packages/platform-orchestrator test

up: build
	@./bin/llmobs up $(PROFILE)

down: build
	@./bin/llmobs down

restart: build
	@./bin/llmobs restart $(PROFILE)

status: build
	@./bin/llmobs status

logs: build
	@./bin/llmobs logs $(ARGS)

health: build
	@./bin/llmobs health $(HOST)

certs: build
	@./bin/llmobs certs

scale: build
	@./bin/llmobs scale $(ARGS)

setup: build
	@./bin/llmobs setup

backup-purge: build
	@./bin/llmobs backup-purge $(ARGS)

cloudflare: build
	@./bin/llmobs cloudflare $(ARGS)

free-ports: build
	@./bin/llmobs free-ports

server: build
	@./bin/llmobs server

clean:
	@$(MAKE) -C packages/platform-orchestrator clean
