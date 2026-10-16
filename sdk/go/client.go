package gpon

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"
)

// Option is a functional option for configuring a Client.
type Option func(*Client)

// Client is the official Go SDK client for the GPON God-Mode REST API daemon.
type Client struct {
	baseURL     string
	httpClient  *http.Client
	cliFallback bool
	cliPath     string
}

// WithBaseURL overrides the daemon base URL (e.g. "http://127.0.0.1:8254").
func WithBaseURL(rawURL string) Option {
	return func(c *Client) {
		c.baseURL = strings.TrimRight(rawURL, "/")
	}
}

// WithAPIPort overrides the port of the daemon on 127.0.0.1.
func WithAPIPort(port int) Option {
	return func(c *Client) {
		c.baseURL = fmt.Sprintf("http://127.0.0.1:%d", port)
	}
}

// WithHTTPClient provides a custom standard net/http client.
func WithHTTPClient(client *http.Client) Option {
	return func(c *Client) {
		if client != nil {
			c.httpClient = client
		}
	}
}

// WithTimeout sets a custom request timeout on the underlying HTTP client.
func WithTimeout(timeout time.Duration) Option {
	return func(c *Client) {
		c.httpClient.Timeout = timeout
	}
}

// WithCLIFallback enables or disables running the `gpon` CLI via os/exec when
// the HTTP REST daemon is down or unreachable.
func WithCLIFallback(enable bool) Option {
	return func(c *Client) {
		c.cliFallback = enable
	}
}

// WithCLIPath sets the path or command name to the `gpon` CLI executable or script.
func WithCLIPath(path string) Option {
	return func(c *Client) {
		if path != "" {
			c.cliPath = path
		}
	}
}

// NewClient initializes a new GPON SDK Client with optional configurations.
//
// Defaults:
//   - Host: GPON_API_HOST or "127.0.0.1"
//   - Port: GPON_API_PORT or 8254 (URL: http://127.0.0.1:8254)
//   - Fallback: Enabled if GPON_CLI_FALLBACK is set to "1" or "true"
//   - CLI Path: GPON_CLI_PATH or "gpon"
func NewClient(opts ...Option) *Client {
	portStr := os.Getenv("GPON_API_PORT")
	if portStr == "" {
		portStr = "8254"
	}

	host := os.Getenv("GPON_API_HOST")
	if host == "" {
		host = "127.0.0.1"
	}

	baseURL := os.Getenv("GPON_API_URL")
	if baseURL == "" {
		baseURL = os.Getenv("GPON_DAEMON_URL")
	}
	if baseURL == "" {
		baseURL = fmt.Sprintf("http://%s:%s", host, portStr)
	}

	cliPath := os.Getenv("GPON_CLI_PATH")
	if cliPath == "" {
		// Auto-discover gpon in PATH or common project locations
		if p, err := exec.LookPath("gpon"); err == nil {
			cliPath = p
		} else if _, err := os.Stat("./gpon.sh"); err == nil {
			cliPath = "./gpon.sh"
		} else if _, err := os.Stat("../gpon.sh"); err == nil {
			cliPath = "../gpon.sh"
		} else if _, err := os.Stat("../../gpon.sh"); err == nil {
			cliPath = "../../gpon.sh"
		} else {
			cliPath = "gpon"
		}
	}

	cliFallback := false
	if fb := os.Getenv("GPON_CLI_FALLBACK"); fb == "1" || strings.EqualFold(fb, "true") {
		cliFallback = true
	}

	c := &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		httpClient: &http.Client{
			Timeout: 15 * time.Second,
		},
		cliFallback: cliFallback,
		cliPath:     cliPath,
	}

	for _, opt := range opts {
		opt(c)
	}

	return c
}

// BaseURL returns the configured base URL of the REST daemon.
func (c *Client) BaseURL() string {
	return c.baseURL
}

// GetStatus retrieves hardware details, firmware versions, uptime, and WAN link state.
func (c *Client) GetStatus(ctx context.Context) (*GatewayStatus, error) {
	var status GatewayStatus
	err := c.doRequest(ctx, http.MethodGet, "/api/status", nil, &status)
	if err != nil {
		if c.shouldFallback(err) {
			var fbStatus GatewayStatus
			if fbErr := c.execCLI(ctx, []string{"status", "--json"}, &fbStatus); fbErr == nil {
				return &fbStatus, nil
			} else {
				return nil, fmt.Errorf("%w: %v (CLI fallback failed: %w)", ErrDaemonUnreachable, err, fbErr)
			}
		}
		return nil, err
	}
	return &status, nil
}

// GetDevices retrieves all active and known LAN and Wi-Fi client devices.
func (c *Client) GetDevices(ctx context.Context) ([]Device, error) {
	var devices []Device
	err := c.doRequest(ctx, http.MethodGet, "/api/devices", nil, &devices)
	if err != nil {
		if c.shouldFallback(err) {
			var fbDevices []Device
			if fbErr := c.execCLI(ctx, []string{"devices", "--json"}, &fbDevices); fbErr == nil {
				return fbDevices, nil
			} else {
				return nil, fmt.Errorf("%w: %v (CLI fallback failed: %w)", ErrDaemonUnreachable, err, fbErr)
			}
		}
		return nil, err
	}
	return devices, nil
}

// GetOpticalStatus retrieves fiber optic laser telemetry (TX/RX power, temp, bias, signal quality).
func (c *Client) GetOpticalStatus(ctx context.Context) (*OpticalStatus, error) {
	var optical OpticalStatus
	err := c.doRequest(ctx, http.MethodGet, "/api/optical", nil, &optical)
	if err != nil {
		if c.shouldFallback(err) {
			var fbOptical OpticalStatus
			if fbErr := c.execCLI(ctx, []string{"optical", "--json"}, &fbOptical); fbErr == nil {
				return &fbOptical, nil
			} else {
				return nil, fmt.Errorf("%w: %v (CLI fallback failed: %w)", ErrDaemonUnreachable, err, fbErr)
			}
		}
		return nil, err
	}
	return &optical, nil
}

// ListPortForwards retrieves all active NAT port forwarding rules.
func (c *Client) ListPortForwards(ctx context.Context) ([]PortForwardRule, error) {
	var rules []PortForwardRule
	err := c.doRequest(ctx, http.MethodGet, "/api/port-forwards", nil, &rules)
	if err != nil {
		if c.shouldFallback(err) {
			var fbRules []PortForwardRule
			if fbErr := c.execCLI(ctx, []string{"ports", "list", "--json"}, &fbRules); fbErr == nil {
				return fbRules, nil
			} else {
				return nil, fmt.Errorf("%w: %v (CLI fallback failed: %w)", ErrDaemonUnreachable, err, fbErr)
			}
		}
		return nil, err
	}
	return rules, nil
}

// AddPortForward creates a new NAT virtual host port forwarding rule.
func (c *Client) AddPortForward(ctx context.Context, rule PortForwardRequest) error {
	if rule.Protocol == "" {
		rule.Protocol = "TCP"
	}
	rule.Protocol = strings.ToUpper(rule.Protocol)

	if rule.ExternalPort < 1 || rule.ExternalPort > 65535 {
		return fmt.Errorf("%w: external_port must be between 1 and 65535", ErrInvalidParameter)
	}
	if rule.InternalPort < 1 || rule.InternalPort > 65535 {
		return fmt.Errorf("%w: internal_port must be between 1 and 65535", ErrInvalidParameter)
	}
	if rule.ServerIP == "" {
		return fmt.Errorf("%w: server_ip cannot be empty", ErrInvalidParameter)
	}

	payload := map[string]any{
		"external_port": rule.ExternalPort,
		"internal_port": rule.InternalPort,
		"server_ip":     rule.ServerIP,
		"protocol":      rule.Protocol,
	}

	var res map[string]any
	err := c.doRequest(ctx, http.MethodPost, "/api/port-forwards", payload, &res)
	if err != nil {
		if c.shouldFallback(err) {
			args := []string{
				"ports", "add",
				strconv.Itoa(rule.ExternalPort),
				strconv.Itoa(rule.InternalPort),
				rule.ServerIP,
				"--proto", rule.Protocol,
				"--json",
			}
			if fbErr := c.execCLI(ctx, args, nil); fbErr == nil {
				return nil
			} else {
				return fmt.Errorf("%w: %v (CLI fallback failed: %w)", ErrDaemonUnreachable, err, fbErr)
			}
		}
		return err
	}
	return nil
}

// DeletePortForward deletes an active port forwarding rule.
// The name argument can be an external port number (e.g. "8080" or "80") or a rule identifier.
func (c *Client) DeletePortForward(ctx context.Context, name string) error {
	name = strings.TrimSpace(name)
	if name == "" {
		return fmt.Errorf("%w: rule name or port cannot be empty", ErrInvalidParameter)
	}

	port, err := strconv.Atoi(name)
	if err != nil {
		// If name is not a port number, attempt to find a matching rule by external port or IP
		rules, listErr := c.ListPortForwards(ctx)
		if listErr != nil {
			return fmt.Errorf("failed to list rules to locate '%s': %w", name, listErr)
		}
		found := false
		for _, r := range rules {
			if strconv.Itoa(r.ExternalPort) == name || r.ServerIP == name {
				port = r.ExternalPort
				found = true
				break
			}
		}
		if !found {
			return fmt.Errorf("%w: rule '%s' not found", ErrRuleNotFound, name)
		}
	}

	endpoint := fmt.Sprintf("/api/port-forwards/%d", port)
	var res map[string]any
	err = c.doRequest(ctx, http.MethodDelete, endpoint, nil, &res)
	if err != nil {
		if c.shouldFallback(err) {
			args := []string{"ports", "del", strconv.Itoa(port), "--json"}
			if fbErr := c.execCLI(ctx, args, nil); fbErr == nil {
				return nil
			} else {
				return fmt.Errorf("%w: %v (CLI fallback failed: %w)", ErrDaemonUnreachable, err, fbErr)
			}
		}
		return err
	}
	return nil
}

// SetDMZ enables or disables DMZ host forwarding for a given local IP address.
func (c *Client) SetDMZ(ctx context.Context, ip string, enable bool) error {
	if enable && ip == "" {
		return fmt.Errorf("%w: IP address is required when enabling DMZ", ErrInvalidParameter)
	}
	if !enable && ip == "" {
		ip = "0.0.0.0"
	}

	payload := map[string]any{
		"ip_address": ip,
		"enabled":    enable,
	}

	var res map[string]any
	err := c.doRequest(ctx, http.MethodPost, "/api/dmz", payload, &res)
	if err != nil {
		if c.shouldFallback(err) {
			var args []string
			if enable {
				args = []string{"dmz", "set", ip, "--json"}
			} else {
				args = []string{"dmz", "disable", "--json"}
			}
			if fbErr := c.execCLI(ctx, args, nil); fbErr == nil {
				return nil
			} else {
				return fmt.Errorf("%w: %v (CLI fallback failed: %w)", ErrDaemonUnreachable, err, fbErr)
			}
		}
		return err
	}
	return nil
}

// OptimizeGaming executes the one-click gaming latency macro:
// places targetIP into DMZ, disables DoS firewall filter, disables SIP ALG, and enables UPnP.
func (c *Client) OptimizeGaming(ctx context.Context, targetIP string) (*GamingOptimizationResult, error) {
	if targetIP == "" {
		return nil, fmt.Errorf("%w: targetIP cannot be empty", ErrInvalidParameter)
	}

	payload := map[string]any{
		"target_ip":  targetIP,
		"enable_dmz": true,
	}

	var result GamingOptimizationResult
	err := c.doRequest(ctx, http.MethodPost, "/api/optimize-gaming", payload, &result)
	if err != nil {
		if c.shouldFallback(err) {
			var fbResult GamingOptimizationResult
			args := []string{"gaming", targetIP, "--json"}
			if fbErr := c.execCLI(ctx, args, &fbResult); fbErr == nil {
				return &fbResult, nil
			} else {
				return nil, fmt.Errorf("%w: %v (CLI fallback failed: %w)", ErrDaemonUnreachable, err, fbErr)
			}
		}
		return nil, err
	}
	return &result, nil
}

// Reboot safely soft-reboots the GPON Gateway.
func (c *Client) Reboot(ctx context.Context) error {
	payload := map[string]any{
		"confirm": true,
	}

	var res map[string]any
	err := c.doRequest(ctx, http.MethodPost, "/api/reboot", payload, &res)
	if err != nil {
		if c.shouldFallback(err) {
			args := []string{"reboot", "--json"}
			if fbErr := c.execCLI(ctx, args, nil); fbErr == nil {
				return nil
			} else {
				return fmt.Errorf("%w: %v (CLI fallback failed: %w)", ErrDaemonUnreachable, err, fbErr)
			}
		}
		return err
	}
	return nil
}

// GetDMZ retrieves the current DMZ configuration.
func (c *Client) GetDMZ(ctx context.Context) (*DMZConfig, error) {
	var dmz DMZConfig
	err := c.doRequest(ctx, http.MethodGet, "/api/dmz", nil, &dmz)
	if err != nil {
		if c.shouldFallback(err) {
			var fbDMZ DMZConfig
			if fbErr := c.execCLI(ctx, []string{"dmz", "get", "--json"}, &fbDMZ); fbErr == nil {
				return &fbDMZ, nil
			} else {
				return nil, fmt.Errorf("%w: %v (CLI fallback failed: %w)", ErrDaemonUnreachable, err, fbErr)
			}
		}
		return nil, err
	}
	return &dmz, nil
}

// SetDNS configures primary and secondary IPv4 DNS servers for the LAN DHCP server.
func (c *Client) SetDNS(ctx context.Context, primary, secondary string) error {
	payload := map[string]any{
		"primary_dns":   primary,
		"secondary_dns": secondary,
	}

	var res map[string]any
	err := c.doRequest(ctx, http.MethodPost, "/api/dns", payload, &res)
	if err != nil {
		if c.shouldFallback(err) {
			args := []string{"dns", primary, secondary, "--json"}
			if fbErr := c.execCLI(ctx, args, nil); fbErr == nil {
				return nil
			} else {
				return fmt.Errorf("%w: %v (CLI fallback failed: %w)", ErrDaemonUnreachable, err, fbErr)
			}
		}
		return err
	}
	return nil
}

// GetWifiConfig retrieves 2.4GHz Wi-Fi configuration (SSID, channel, transmit power, WMM).
func (c *Client) GetWifiConfig(ctx context.Context) (*WifiConfig, error) {
	var cfg WifiConfig
	err := c.doRequest(ctx, http.MethodGet, "/api/wifi", nil, &cfg)
	if err != nil {
		if c.shouldFallback(err) {
			var fbCfg WifiConfig
			if fbErr := c.execCLI(ctx, []string{"wifi", "status", "--json"}, &fbCfg); fbErr == nil {
				return &fbCfg, nil
			} else {
				return nil, fmt.Errorf("%w: %v (CLI fallback failed: %w)", ErrDaemonUnreachable, err, fbErr)
			}
		}
		return nil, err
	}
	return &cfg, nil
}

// SetWifiChannel changes the Wi-Fi 2.4GHz operating channel (1-13).
func (c *Client) SetWifiChannel(ctx context.Context, channel int) error {
	if channel < 1 || channel > 13 {
		return fmt.Errorf("%w: Wi-Fi channel must be between 1 and 13", ErrInvalidParameter)
	}

	payload := map[string]any{
		"channel": channel,
	}

	var res map[string]any
	err := c.doRequest(ctx, http.MethodPost, "/api/wifi/channel", payload, &res)
	if err != nil {
		if c.shouldFallback(err) {
			args := []string{"wifi", "channel", strconv.Itoa(channel), "--json"}
			if fbErr := c.execCLI(ctx, args, nil); fbErr == nil {
				return nil
			} else {
				return fmt.Errorf("%w: %v (CLI fallback failed: %w)", ErrDaemonUnreachable, err, fbErr)
			}
		}
		return err
	}
	return nil
}

// GetEthernetPorts retrieves link status and packet counters for physical LAN ports 1-4.
func (c *Client) GetEthernetPorts(ctx context.Context) ([]EthernetPortStatus, error) {
	var ports []EthernetPortStatus
	err := c.doRequest(ctx, http.MethodGet, "/api/ethernet", nil, &ports)
	if err != nil {
		if c.shouldFallback(err) {
			var fbPorts []EthernetPortStatus
			if fbErr := c.execCLI(ctx, []string{"ethernet", "--json"}, &fbPorts); fbErr == nil {
				return fbPorts, nil
			} else {
				return nil, fmt.Errorf("%w: %v (CLI fallback failed: %w)", ErrDaemonUnreachable, err, fbErr)
			}
		}
		return nil, err
	}
	return ports, nil
}

// Health checks liveness of the REST API daemon.
func (c *Client) Health(ctx context.Context) error {
	var res map[string]string
	return c.doRequest(ctx, http.MethodGet, "/health", nil, &res)
}

// doRequest performs an HTTP request against the daemon endpoint.
func (c *Client) doRequest(ctx context.Context, method, path string, bodyData any, result any) error {
	fullURL := c.baseURL + path

	var bodyReader io.Reader
	if bodyData != nil {
		raw, err := json.Marshal(bodyData)
		if err != nil {
			return fmt.Errorf("marshal request payload: %w", err)
		}
		bodyReader = bytes.NewReader(raw)
	}

	req, err := http.NewRequestWithContext(ctx, method, fullURL, bodyReader)
	if err != nil {
		return fmt.Errorf("create HTTP request: %w", err)
	}

	req.Header.Set("User-Agent", "gpon-godmode-go-sdk/2.0.0")
	req.Header.Set("Accept", "application/json")
	if bodyData != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		if isConnectionError(err) {
			return fmt.Errorf("%w: %v", ErrDaemonUnreachable, err)
		}
		return err
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("read response body: %w", err)
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		var errResp struct {
			Detail string `json:"detail"`
		}
		_ = json.Unmarshal(respBody, &errResp)

		detail := errResp.Detail
		if detail == "" {
			detail = strings.TrimSpace(string(respBody))
		}

		apiErr := &APIError{
			StatusCode: resp.StatusCode,
			Detail:     detail,
		}

		switch resp.StatusCode {
		case http.StatusUnauthorized, http.StatusForbidden:
			return fmt.Errorf("%w: %s", ErrRouterAuth, detail)
		case http.StatusNotFound:
			return fmt.Errorf("%w: %s", ErrRuleNotFound, detail)
		case http.StatusBadRequest, http.StatusUnprocessableEntity:
			return fmt.Errorf("%w: %s", ErrInvalidParameter, detail)
		default:
			return apiErr
		}
	}

	if result != nil && len(respBody) > 0 {
		if err := json.Unmarshal(respBody, result); err != nil {
			return fmt.Errorf("unmarshal response JSON: %w (raw: %s)", err, string(respBody))
		}
	}

	return nil
}

// shouldFallback checks if an error indicates the HTTP daemon is unreachable and fallback is enabled.
func (c *Client) shouldFallback(err error) bool {
	if !c.cliFallback {
		return false
	}
	return errors.Is(err, ErrDaemonUnreachable) || isConnectionError(err)
}

// isConnectionError determines whether an error stems from connection refusal, network down, or DNS resolution failure.
func isConnectionError(err error) bool {
	if err == nil {
		return false
	}
	if errors.Is(err, ErrDaemonUnreachable) {
		return true
	}
	var netErr net.Error
	if errors.As(err, &netErr) {
		return true
	}
	var opErr *net.OpError
	if errors.As(err, &opErr) {
		return true
	}
	var urlErr *url.Error
	if errors.As(err, &urlErr) {
		return true
	}
	errStr := strings.ToLower(err.Error())
	return strings.Contains(errStr, "connection refused") ||
		strings.Contains(errStr, "no such host") ||
		strings.Contains(errStr, "dial tcp") ||
		strings.Contains(errStr, "connect: network is unreachable")
}

// execCLI executes the gpon CLI utility directly via os/exec as a fallback when the daemon is offline.
func (c *Client) execCLI(ctx context.Context, args []string, out any) error {
	cmd := exec.CommandContext(ctx, c.cliPath, args...)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()
	output := stdout.Bytes()
	if len(output) == 0 && stderr.Len() > 0 {
		output = stderr.Bytes()
	}

	var env struct {
		Status    string          `json:"status"`
		Data      json.RawMessage `json:"data"`
		ErrorType string          `json:"error_type"`
		Message   string          `json:"message"`
	}

	if jsonErr := json.Unmarshal(output, &env); jsonErr == nil && env.Status != "" {
		if env.Status == "error" {
			switch env.ErrorType {
			case "PermissionError":
				return fmt.Errorf("%w: %s", ErrRouterAuth, env.Message)
			case "ValueError":
				if strings.Contains(strings.ToLower(env.Message), "not found") {
					return fmt.Errorf("%w: %s", ErrRuleNotFound, env.Message)
				}
				return fmt.Errorf("%w: %s", ErrInvalidParameter, env.Message)
			default:
				return fmt.Errorf("%w: %s (%s)", ErrCLIFallbackFailed, env.Message, env.ErrorType)
			}
		}

		if out != nil {
			if len(env.Data) > 0 && string(env.Data) != "null" {
				if err := json.Unmarshal(env.Data, out); err != nil {
					return fmt.Errorf("%w: unmarshal CLI data payload: %v", ErrCLIFallbackFailed, err)
				}
				return nil
			}
			if err := json.Unmarshal(output, out); err != nil {
				return fmt.Errorf("%w: unmarshal CLI response: %v", ErrCLIFallbackFailed, err)
			}
		}
		return nil
	}

	if err != nil {
		errOutput := strings.TrimSpace(stdout.String() + "\n" + stderr.String())
		return fmt.Errorf("%w: %v (output: %s)", ErrCLIFallbackFailed, err, errOutput)
	}

	if out != nil && len(output) > 0 {
		if err := json.Unmarshal(output, out); err != nil {
			return fmt.Errorf("%w: unmarshal raw CLI output: %v", ErrCLIFallbackFailed, err)
		}
	}

	return nil
}
