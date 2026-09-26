.PHONY: build test clean lint

BINARY_NAME=llmobs
BUILD_DIR=../../bin

build:
	@mkdir -p $(BUILD_DIR)
	CGO_ENABLED=0 go build -ldflags="-s -w" -o $(BUILD_DIR)/$(BINARY_NAME) main.go

test:
	go test -v ./tests/...

clean:
	rm -f $(BUILD_DIR)/$(BINARY_NAME)

lint:
	go vet ./...
