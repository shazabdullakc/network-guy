# Network Guy

AI-Powered Network Troubleshooting Assistant for Telecom Test Labs.

## Setup

```bash
poetry install
network-guy init --data-dir ./data
network-guy query "ROUTER-LAB-01 is dropping packets. What's the root cause?"
```

## Commands

| Command | Description |
|---------|-------------|
| `network-guy init` | Load data files, build stores |
| `network-guy query "..."` | Ask a troubleshooting question |
| `network-guy chat` | Interactive multi-turn session |
| `network-guy devices` | List all devices and status |
| `network-guy topology` | Display network topology |
| `network-guy incidents` | List open incidents |
| `network-guy security-scan` | Run security audit |
| `network-guy benchmark` | Run benchmark test queries |
