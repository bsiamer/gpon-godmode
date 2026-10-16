package gpon

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"
)

func TestNewClientDefaults(t *testing.T) {
	// 1. Default should use port 8254
	c := NewClient()
	expected := "http://127.0.0.1:8254"
	if c.BaseURL() != expected {
		t.Fatalf("expected baseURL %q, got %q", expected, c.BaseURL())
	}

	// 2. Custom env port
	os.Setenv("GPON_API_PORT", "9999")
	defer os.Unsetenv("GPON_API_PORT")
	c2 := NewClient()
	if c2.BaseURL() != "http://127.0.0.1:9999" {
		t.Fatalf("expected port override, got %q", c2.BaseURL())
	}

	// 3. Functional option override
	c3 := NewClient(WithAPIPort(8254), WithBaseURL("http://custom-host:8254"))
	if c3.BaseURL() != "http://custom-host:8254" {
		t.Fatalf("expected custom base URL, got %q", c3.BaseURL())
	}
}

func TestClientEndpoints(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		case r.Method == http.MethodGet && r.URL.Path == "/health":
			_ = json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})

		case r.Method == http.MethodGet && r.URL.Path == "/api/status":
			status := GatewayStatus{
				ModelName:       "G-240W-F",
				HardwareVersion: "3FE46597AAAA",
				SoftwareVersion: "3FE46606BGBB24",
				BootVersion:     "U-Boot 2016",
				UptimeSeconds:   123456,
				UptimeFormatted: "1d 10h 17m",
			}
			_ = json.NewEncoder(w).Encode(status)

		case r.Method == http.MethodGet && r.URL.Path == "/api/devices":
			devices := []Device{
				{
					OID:           1,
					Hostname:      "test-pc",
					IPAddress:     "192.168.1.100",
					MACAddress:    "aa:bb:cc:dd:ee:ff",
					Active:        true,
					InterfaceType: "Ethernet",
				},
			}
			_ = json.NewEncoder(w).Encode(devices)

		case r.Method == http.MethodGet && r.URL.Path == "/api/optical":
			optical := OpticalStatus{
				TXPowerDBm:             2.34,
				RXPowerDBm:             -18.75,
				TransceiverTemperature: 45.1,
				BiasCurrentUA:          12.8,
				SignalQuality:          "Excellent / Healthy",
			}
			_ = json.NewEncoder(w).Encode(optical)

		case r.Method == http.MethodGet && r.URL.Path == "/api/port-forwards":
			rules := []PortForwardRule{
				{
					ExternalPort: 8080,
					InternalPort: 80,
					ServerIP:     "192.168.1.100",
					Protocol:     "TCP",
					Enabled:      true,
				},
			}
			_ = json.NewEncoder(w).Encode(rules)

		case r.Method == http.MethodPost && r.URL.Path == "/api/port-forwards":
			var req PortForwardRequest
			_ = json.NewDecoder(r.Body).Decode(&req)
			if req.ExternalPort != 25565 {
				http.Error(w, `{"detail": "unexpected port"}`, http.StatusBadRequest)
				return
			}
			_ = json.NewEncoder(w).Encode(map[string]any{"success": true})

		case r.Method == http.MethodDelete && r.URL.Path == "/api/port-forwards/8080":
			_ = json.NewEncoder(w).Encode(map[string]any{"success": true, "deleted_port": 8080})

		case r.Method == http.MethodPost && r.URL.Path == "/api/dmz":
			var req map[string]any
			_ = json.NewDecoder(r.Body).Decode(&req)
			_ = json.NewEncoder(w).Encode(map[string]any{"success": true, "ip": req["ip_address"]})

		case r.Method == http.MethodPost && r.URL.Path == "/api/optimize-gaming":
			res := GamingOptimizationResult{
				TargetIP:              "192.168.1.74",
				DMZConfigured:         true,
				DoSProtectionDisabled: true,
				SIPALGDisabled:        true,
				UPnPEnabled:           true,
				Message:               "Optimized",
			}
			_ = json.NewEncoder(w).Encode(res)

		case r.Method == http.MethodPost && r.URL.Path == "/api/reboot":
			_ = json.NewEncoder(w).Encode(map[string]any{"success": true, "message": "Rebooted"})

		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	client := NewClient(WithBaseURL(server.URL), WithTimeout(2*time.Second))
	ctx := context.Background()

	// 1. Health
	if err := client.Health(ctx); err != nil {
		t.Fatalf("health failed: %v", err)
	}

	// 2. Status
	st, err := client.GetStatus(ctx)
	if err != nil {
		t.Fatalf("GetStatus failed: %v", err)
	}
	if st.ModelName != "G-240W-F" {
		t.Errorf("expected model G-240W-F, got %q", st.ModelName)
	}

	// 3. Devices
	devs, err := client.GetDevices(ctx)
	if err != nil {
		t.Fatalf("GetDevices failed: %v", err)
	}
	if len(devs) != 1 || devs[0].IPAddress != "192.168.1.100" {
		t.Errorf("unexpected devices: %+v", devs)
	}

	// 4. Optical
	opt, err := client.GetOpticalStatus(ctx)
	if err != nil {
		t.Fatalf("GetOpticalStatus failed: %v", err)
	}
	if opt.RXPowerDBm != -18.75 {
		t.Errorf("unexpected rx power: %v", opt.RXPowerDBm)
	}

	// 5. Port forwards
	rules, err := client.ListPortForwards(ctx)
	if err != nil {
		t.Fatalf("ListPortForwards failed: %v", err)
	}
	if len(rules) != 1 || rules[0].ExternalPort != 8080 {
		t.Errorf("unexpected rules: %+v", rules)
	}

	// 6. Add Port Forward
	err = client.AddPortForward(ctx, PortForwardRequest{
		ExternalPort: 25565,
		InternalPort: 25565,
		ServerIP:     "192.168.1.100",
		Protocol:     "TCP",
	})
	if err != nil {
		t.Fatalf("AddPortForward failed: %v", err)
	}

	// 7. Delete Port Forward (by port number string)
	if err := client.DeletePortForward(ctx, "8080"); err != nil {
		t.Fatalf("DeletePortForward failed: %v", err)
	}

	// 8. DMZ
	if err := client.SetDMZ(ctx, "192.168.1.100", true); err != nil {
		t.Fatalf("SetDMZ failed: %v", err)
	}

	// 9. Optimize Gaming
	gameRes, err := client.OptimizeGaming(ctx, "192.168.1.74")
	if err != nil {
		t.Fatalf("OptimizeGaming failed: %v", err)
	}
	if !gameRes.UPnPEnabled {
		t.Errorf("expected upnp enabled in result")
	}

	// 10. Reboot
	if err := client.Reboot(ctx); err != nil {
		t.Fatalf("Reboot failed: %v", err)
	}
}

func TestErrorMappings(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/auth-err":
			http.Error(w, `{"detail": "Authentication failed"}`, http.StatusUnauthorized)
		case "/not-found":
			http.Error(w, `{"detail": "Rule not found"}`, http.StatusNotFound)
		case "/bad-req":
			http.Error(w, `{"detail": "Invalid port range"}`, http.StatusBadRequest)
		}
	}))
	defer server.Close()

	client := NewClient(WithBaseURL(server.URL))
	ctx := context.Background()

	// Unauthorized -> ErrRouterAuth
	err := client.doRequest(ctx, http.MethodGet, "/auth-err", nil, nil)
	if !errors.Is(err, ErrRouterAuth) {
		t.Errorf("expected ErrRouterAuth, got: %v", err)
	}

	// Not Found -> ErrRuleNotFound
	err = client.doRequest(ctx, http.MethodGet, "/not-found", nil, nil)
	if !errors.Is(err, ErrRuleNotFound) {
		t.Errorf("expected ErrRuleNotFound, got: %v", err)
	}

	// Bad Request -> ErrInvalidParameter
	err = client.doRequest(ctx, http.MethodGet, "/bad-req", nil, nil)
	if !errors.Is(err, ErrInvalidParameter) {
		t.Errorf("expected ErrInvalidParameter, got: %v", err)
	}
}

func TestDaemonUnreachable(t *testing.T) {
	// Connect to non-existent server without fallback
	client := NewClient(
		WithBaseURL("http://127.0.0.1:54321"),
		WithCLIFallback(false),
		WithTimeout(200*time.Millisecond),
	)

	_, err := client.GetStatus(context.Background())
	if !errors.Is(err, ErrDaemonUnreachable) {
		t.Errorf("expected ErrDaemonUnreachable, got: %v", err)
	}
}
