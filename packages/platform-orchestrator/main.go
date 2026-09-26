/*
Package main provides the executable entrypoint for the platform orchestrator package.

ALGORITHM BLUEPRINT:
1. Entrypoint Execution: Delegates command-line arguments to cmd.Execute().
2. Invariants:
   - Exits with operating system status code 1 upon fatal execution failure.
*/
package main

import "github.com/llm-observability/platform/packages/platform-orchestrator/src/cmd"

func main() {
	cmd.Execute()
}
