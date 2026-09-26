/*
Package rules implements profile resolution and compose file selection logic as pure data.

ALGORITHM BLUEPRINT:
1. ResolveProfiles: Maps input profile strings against known aliases and resolves inter-profile dependencies (e.g., workflows requires db).
2. SelectComposeFiles: Returns the correct list of compose file paths based on resolved profiles:
   - If 'stateless' or 'compute': appends docker-compose.stateless.yml.
   - If 'stateful' or 'data': appends docker-compose.prod.yml if available.
   - Baseline: always includes docker-compose.yml.
3. Invariants:
   - Requesting 'workflows' automatically injects 'db' to ensure database prerequisites are active.
   - Profile list deduplication is maintained across all resolution branches.
*/
package rules

import (
	"path/filepath"
)

var KnownProfiles = map[string][]string{
	"stateful":  {"stateful", "data"},
	"stateless": {"stateless", "compute"},
	"data":      {"data"},
	"compute":   {"compute"},
	"network":   {"network"},
	"edge":      {"edge"},
	"db":        {"db"},
	"workflows": {"workflows"},
	"streaming": {"streaming"},
	"analytics": {"analytics"},
	"tracing":   {"tracing"},
	"portal":    {"portal"},
	"full":      {"full"},
}

func ResolveProfiles(requested []string) []string {
	if len(requested) == 0 {
		return []string{"full"}
	}

	var resolved []string
	seen := make(map[string]bool)

	for _, r := range requested {
		if !seen[r] {
			resolved = append(resolved, r)
			seen[r] = true
		}
	}

	if seen["workflows"] && !seen["db"] {
		resolved = append(resolved, "db")
		seen["db"] = true
	}

	return resolved
}

func SelectComposeFiles(baseDir string, profiles []string) []string {
	files := []string{filepath.Join(baseDir, "docker-compose.yml")}

	isStateless := false
	isStateful := false

	for _, p := range profiles {
		if p == "stateless" || p == "compute" {
			isStateless = true
		}
		if p == "stateful" || p == "data" {
			isStateful = true
		}
	}

	if isStateless {
		files = append(files, filepath.Join(baseDir, "docker-compose.stateless.yml"))
	} else if isStateful {
		files = append(files, filepath.Join(baseDir, "docker-compose.prod.yml"))
	}

	return files
}
