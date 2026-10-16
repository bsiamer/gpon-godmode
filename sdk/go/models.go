package gpon

// GatewayStatus represents Nokia/Alcatel GPON Gateway hardware telemetry,
// firmware version, system uptime, and WAN PPPoE link state.
type GatewayStatus struct {
	ModelName       string   `json:"model_name"`
	HardwareVersion string   `json:"hardware_version"`
	SoftwareVersion string   `json:"software_version"`
	BootVersion     string   `json:"boot_version"`
	UptimeSeconds   int64    `json:"uptime_seconds"`
	UptimeFormatted string   `json:"uptime_formatted"`
	CPUTemperature  *float64 `json:"cpu_temperature,omitempty"`
	WANIP           *string  `json:"wan_ip,omitempty"`
	WANStatus       *string  `json:"wan_status,omitempty"`
}

// Device represents an active or known LAN / Wi-Fi connected host.
type Device struct {
	OID           int    `json:"oid"`
	Hostname      string `json:"hostname"`
	IPAddress     string `json:"ip_address"`
	MACAddress    string `json:"mac_address"`
	Active        bool   `json:"active"`
	InterfaceType string `json:"interface_type"`
}

// OpticalStatus represents fiber optic transceiver signal telemetry,
// laser bias current, and ITU-T G.984 Class B+ signal quality.
type OpticalStatus struct {
	TXPowerDBm             float64 `json:"tx_power_dbm"`
	RXPowerDBm             float64 `json:"rx_power_dbm"`
	TransceiverTemperature float64 `json:"transceiver_temperature"`
	BiasCurrentUA          float64 `json:"bias_current_ua"`
	SignalQuality          string  `json:"signal_quality"`
}

// PortForwardRule represents an active NAT virtual host port forwarding entry.
type PortForwardRule struct {
	OID          *int   `json:"oid,omitempty"`
	Enabled      bool   `json:"enabled"`
	ExternalPort int    `json:"external_port"`
	InternalPort int    `json:"internal_port"`
	ServerIP     string `json:"server_ip"`
	Protocol     string `json:"protocol"`
}

// PortForwardRequest represents parameters to create a new NAT port forward.
type PortForwardRequest struct {
	ExternalPort int    `json:"external_port"`
	InternalPort int    `json:"internal_port"`
	ServerIP     string `json:"server_ip"`
	Protocol     string `json:"protocol,omitempty"` // "TCP", "UDP", or "TCP/UDP" (default: "TCP")
}

// DMZConfig represents current DMZ host state and IP.
type DMZConfig struct {
	Enabled   bool   `json:"enabled"`
	IPAddress string `json:"ip_address"`
}

// GamingOptimizationResult represents the outcome of the one-click gaming latency macro.
type GamingOptimizationResult struct {
	TargetIP              string `json:"target_ip"`
	DMZConfigured         bool   `json:"dmz_configured"`
	DoSProtectionDisabled bool   `json:"dos_protection_disabled"`
	SIPALGDisabled        bool   `json:"sip_alg_disabled"`
	UPnPEnabled           bool   `json:"upnp_enabled"`
	Message               string `json:"message"`
}

// WifiConfig represents the 2.4GHz Wi-Fi radio configuration.
type WifiConfig struct {
	Enabled       bool   `json:"enabled"`
	SSID          string `json:"ssid"`
	Channel       string `json:"channel"`
	PowerPercent  int    `json:"power_percent"`
	WMMEnabled    bool   `json:"wmm_enabled"`
	BroadcastSSID bool   `json:"broadcast_ssid"`
}

// EthernetPortStatus represents physical LAN port state and packet counters.
type EthernetPortStatus struct {
	PortID          int    `json:"port_id"`
	Status          string `json:"status"`
	SpeedMbps       int    `json:"speed_mbps"`
	Duplex          string `json:"duplex"`
	BytesSent       int64  `json:"bytes_sent"`
	BytesReceived   int64  `json:"bytes_received"`
	PacketsSent     int64  `json:"packets_sent"`
	PacketsReceived int64  `json:"packets_received"`
	ErrorsReceived  int64  `json:"errors_received"`
	DropsReceived   int64  `json:"drops_received"`
}
