package gpon

import (
	"errors"
	"fmt"
	"net/http"
)

var (
	// ErrDaemonUnreachable is returned when the HTTP REST daemon cannot be contacted.
	ErrDaemonUnreachable = errors.New("gpon: daemon unreachable")

	// ErrRuleNotFound is returned when a port forward rule or entity is not found.
	ErrRuleNotFound = errors.New("gpon: rule not found")

	// ErrRouterAuth is returned when gateway authentication fails (invalid or expired credentials).
	ErrRouterAuth = errors.New("gpon: router authentication failed")

	// ErrInvalidParameter is returned when request arguments violate router or protocol constraints.
	ErrInvalidParameter = errors.New("gpon: invalid parameter")

	// ErrCLIFallbackFailed is returned when daemon fallback execution of the CLI binary fails.
	ErrCLIFallbackFailed = errors.New("gpon: CLI fallback execution failed")
)

// APIError represents a structured error response returned by the GPON REST API daemon.
type APIError struct {
	StatusCode int    `json:"status_code"`
	Detail     string `json:"detail"`
}

// Error implements the standard error interface.
func (e *APIError) Error() string {
	if e.Detail != "" {
		return fmt.Sprintf("gpon: API error (status %d): %s", e.StatusCode, e.Detail)
	}
	return fmt.Sprintf("gpon: API error (status %d)", e.StatusCode)
}

// Is enables errors.Is checks against sentinel errors like ErrRouterAuth, ErrRuleNotFound, and ErrInvalidParameter.
func (e *APIError) Is(target error) bool {
	switch target {
	case ErrRouterAuth:
		return e.StatusCode == http.StatusUnauthorized || e.StatusCode == http.StatusForbidden
	case ErrRuleNotFound:
		return e.StatusCode == http.StatusNotFound
	case ErrInvalidParameter:
		return e.StatusCode == http.StatusBadRequest || e.StatusCode == http.StatusUnprocessableEntity
	default:
		return false
	}
}
