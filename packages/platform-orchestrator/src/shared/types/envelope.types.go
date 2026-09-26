/*
Package types defines transport envelopes and canonical data structures conforming to api-request-response-structure.md.

ALGORITHM BLUEPRINT:
1. MetaEnvelope: Captures distributed tracing context (W3C traceparent compliant), ISO-8601 UTC timestamp, and contract version.
2. APIResponse[T]: Generic JSON payload envelope wrapping payload data, metadata, and optional errors.
3. APIError: Structured error format providing a machine-readable error code, human-readable message, and optional field target.
4. Invariants:
   - Every API and CLI response must populate Meta with a non-empty TraceID and UTC timestamp.
   - Successful operations set Errors to nil or empty slice.
   - Failed operations set Data to nil and populate at least one APIError.
*/
package types

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"time"
)

type MetaEnvelope struct {
	TraceID   string `json:"traceId"`
	Timestamp string `json:"timestamp"`
	Version   string `json:"version"`
}

type APIError struct {
	Code    string `json:"code"`
	Message string `json:"message"`
	Target  string `json:"target,omitempty"`
}

type APIResponse[T any] struct {
	Meta   MetaEnvelope `json:"meta"`
	Data   T            `json:"data"`
	Errors []APIError   `json:"errors,omitempty"`
}

func GenerateTraceID() string {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return fmt.Sprintf("trace-%d", time.Now().UnixNano())
	}
	span := make([]byte, 8)
	rand.Read(span)
	return fmt.Sprintf("00-%s-%s-01", hex.EncodeToString(b), hex.EncodeToString(span))
}

func NewSuccessResponse[T any](data T, version string) APIResponse[T] {
	return APIResponse[T]{
		Meta: MetaEnvelope{
			TraceID:   GenerateTraceID(),
			Timestamp: time.Now().UTC().Format(time.RFC3339),
			Version:   version,
		},
		Data:   data,
		Errors: nil,
	}
}

func NewErrorResponse[T any](code string, message string, target string, version string) APIResponse[T] {
	var zero T
	return APIResponse[T]{
		Meta: MetaEnvelope{
			TraceID:   GenerateTraceID(),
			Timestamp: time.Now().UTC().Format(time.RFC3339),
			Version:   version,
		},
		Data: zero,
		Errors: []APIError{
			{
				Code:    code,
				Message: message,
				Target:  target,
			},
		},
	}
}
