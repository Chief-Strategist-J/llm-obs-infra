/*
Package services implements cryptographic TLS certificate generation and validation.

ALGORITHM BLUEPRINT:
1. Existence Verification: Checks if cert and key already exist. If present and Force is false, returns early.
2. Directory Preparation: Creates destination directories with mode 0755.
3. Key Generation: Generates an RSA 2048-bit cryptographically secure private key.
4. Certificate Template Creation: Constructs x509.Certificate with serial number, Subject, KeyUsage, and SANs (DNSNames & IPAddresses).
5. Self-Signing: Signs template with the generated RSA key using sha256-rsa.
6. PEM Encoding: Writes PEM-encoded certificate and private key blocks to disk with restricted permissions (0600 for key).
7. Invariants:
   - Private key must be stored with 0600 file permissions.
   - SAN list must support both DNS wildcard names and loopback IP addresses.
*/
package services

import (
	"context"
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"fmt"
	"math/big"
	"net"
	"os"
	"path/filepath"
	"time"

	"github.com/llm-observability/platform/packages/platform-orchestrator/src/features/certs/schema"
	"github.com/llm-observability/platform/packages/platform-orchestrator/src/shared/ports"
)

type CertService struct {
	tracer ports.TracerPort
}

func NewCertService(tracer ports.TracerPort) *CertService {
	return &CertService{
		tracer: tracer,
	}
}

func (s *CertService) EnsureCertificates(ctx context.Context, spec schema.CertGenerationSpec) (schema.CertResult, error) {
	_, endSpan := s.tracer.StartSpan(ctx, "llmobs.certs.ensure")
	defer endSpan()

	certPath := filepath.Join(spec.CertDir, spec.CertFile)
	keyPath := filepath.Join(spec.CertDir, spec.KeyFile)

	if !spec.Force {
		_, errCert := os.Stat(certPath)
		_, errKey := os.Stat(keyPath)
		if errCert == nil && errKey == nil {
			return schema.CertResult{
				CertPath:  certPath,
				KeyPath:   keyPath,
				Generated: false,
			}, nil
		}
	}

	if err := os.MkdirAll(spec.CertDir, 0755); err != nil {
		return schema.CertResult{}, fmt.Errorf("failed to create cert directory: %w", err)
	}

	privKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return schema.CertResult{}, fmt.Errorf("failed to generate RSA private key: %w", err)
	}

	serialNumberLimit := new(big.Int).Lsh(big.NewInt(1), 128)
	serialNumber, err := rand.Int(rand.Reader, serialNumberLimit)
	if err != nil {
		return schema.CertResult{}, fmt.Errorf("failed to generate serial number: %w", err)
	}

	notBefore := time.Now().Add(-1 * time.Hour)
	notAfter := notBefore.Add(time.Duration(spec.ValidDays) * 24 * time.Hour)

	template := x509.Certificate{
		SerialNumber: serialNumber,
		Subject: pkix.Name{
			CommonName:   spec.CommonName,
			Organization: []string{spec.Organization},
		},
		NotBefore:             notBefore,
		NotAfter:              notAfter,
		KeyUsage:              x509.KeyUsageKeyEncipherment | x509.KeyUsageDigitalSignature,
		ExtKeyUsage:           []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth, x509.ExtKeyUsageClientAuth},
		BasicConstraintsValid: true,
		IsCA:                  true,
	}

	for _, san := range spec.SANs {
		if ip := net.ParseIP(san); ip != nil {
			template.IPAddresses = append(template.IPAddresses, ip)
		} else {
			template.DNSNames = append(template.DNSNames, san)
		}
	}

	derBytes, err := x509.CreateCertificate(rand.Reader, &template, &template, &privKey.PublicKey, privKey)
	if err != nil {
		return schema.CertResult{}, fmt.Errorf("failed to create certificate: %w", err)
	}

	certOut, err := os.OpenFile(certPath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0644)
	if err != nil {
		return schema.CertResult{}, fmt.Errorf("failed to open %s for writing: %w", certPath, err)
	}
	defer certOut.Close()

	if err := pem.Encode(certOut, &pem.Block{Type: "CERTIFICATE", Bytes: derBytes}); err != nil {
		return schema.CertResult{}, fmt.Errorf("failed to write certificate PEM data: %w", err)
	}

	keyOut, err := os.OpenFile(keyPath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0600)
	if err != nil {
		return schema.CertResult{}, fmt.Errorf("failed to open %s for writing: %w", keyPath, err)
	}
	defer keyOut.Close()

	privBytes, err := x509.MarshalPKCS8PrivateKey(privKey)
	if err != nil {
		return schema.CertResult{}, fmt.Errorf("failed to marshal private key: %w", err)
	}

	if err := pem.Encode(keyOut, &pem.Block{Type: "PRIVATE KEY", Bytes: privBytes}); err != nil {
		return schema.CertResult{}, fmt.Errorf("failed to write key PEM data: %w", err)
	}

	return schema.CertResult{
		CertPath:  certPath,
		KeyPath:   keyPath,
		Generated: true,
	}, nil
}
