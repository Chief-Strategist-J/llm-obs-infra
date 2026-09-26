/*
Package schema defines entity structures and validation rules for TLS certificates.

ALGORITHM BLUEPRINT:
1. CertGenerationSpec: Entity defining SANs, validity duration, output paths, and force regeneration flag.
2. CertResult: Represents generated certificate and private key paths with validity status.
3. Invariants:
   - Output paths must resolve to valid directory structures.
   - At least one CommonName or SAN must be specified.
*/
package schema

type CertGenerationSpec struct {
	CertDir      string   `json:"certDir"`
	CertFile     string   `json:"certFile"`
	KeyFile      string   `json:"keyFile"`
	CommonName   string   `json:"commonName"`
	Organization string   `json:"organization"`
	ValidDays    int      `json:"validDays"`
	SANs         []string `json:"sans"`
	Force        bool     `json:"force"`
}

type CertResult struct {
	CertPath  string `json:"certPath"`
	KeyPath   string `json:"keyPath"`
	Generated bool   `json:"generated"`
}

func DefaultCertSpec(baseDir string) CertGenerationSpec {
	return CertGenerationSpec{
		CertDir:      baseDir + "/config/certs",
		CertFile:     "traefik.crt",
		KeyFile:      "traefik.key",
		CommonName:   "localhost",
		Organization: "LLMObs Infrastructure",
		ValidDays:    365,
		SANs: []string{
			"localhost",
			"127.0.0.1",
			"*.llmobs.local",
			"llmobs-traefik",
			"llmobs-traefik-gateway",
			"host.docker.internal",
		},
		Force: false,
	}
}
