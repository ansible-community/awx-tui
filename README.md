# AWX TUI - Starchy Edition 🥔

**Automation at Your Fingertips**

Terminal User Interface for AWX with multi-instance support, built in Python and Textual.

![AWX TUI Logo](./img/AWX-TUI-logo-640px.png)

## AI-Assisted Project

**This project was substantially coded by Large Language Models (LLMs) with human review.**

- **[AI Attribution](https://aiattribution.github.io/):** AIA PAI SeCeNc Hin R Claude Code (Opus, Sonnet & Haiku) v1.0
- **Vibe-Coders:** Andrew Potozniak <potozniak@redhat.com>, John Mitchell <jmitchel@redhat.com>, John Barker <jobarker@redhat.com>, Daniel Brennand <dbrenuk@redhat.com>
- **AWX TUI Logo AI Attribution:** AIA EAI Hin R Gemini v1.0

> [!NOTE]
> This work was mostly AI-generated with human review. We anticipate that it will evolve to incorporate community contributions authored by humans. Our intention is that copyrightable human-authored contributions will be covered by the [MIT license](#license).

## Code of Conduct

We follow the [Ansible Code of Conduct](https://docs.ansible.com/projects/ansible/latest/community/code_of_conduct.html) in all our interactions within this project.

If you encounter abusive behavior, please refer to the [policy violations](https://docs.ansible.com/projects/ansible/latest/community/code_of_conduct.html#policy-violations) section of the Code for information on how to raise a complaint.

## Communication

* Join the Ansible forum:
  * [Posts tagged with 'awx-tui'](https://forum.ansible.com/tag/awx-tui/): subscribe to participate in collection/technology-related conversations.
  * [Social Spaces](https://forum.ansible.com/c/chat/4): gather and interact with fellow enthusiasts.
  * [News & Announcements](https://forum.ansible.com/c/news/5): track project-wide announcements including social events. The [Bullhorn newsletter](https://docs.ansible.com/projects/ansible/latest/community/communication.html#the-bullhorn), which is used to announce releases and important changes, can also be found here.

For more information about communication, see the [Ansible communication guide](https://docs.ansible.com/projects/ansible/latest/community/communication.html).

## Screenshots

|                                                                    |                                                                                  |
| ------------------------------------------------------------------ | -------------------------------------------------------------------------------- |
| ![Multi-Instance Selection](./img/001-awx-tui-multi-instances.png) | ![Classic Dashboard](./img/002-awx-tui-classic-dashboard-v1.png)                 |
| ![Sleek Dashboard](./img/003-awx-tui-sleek-dashboard-v1.png)       | ![Historic Jobs](./img/004-awx-tui-historic-jobs.png)                            |
| ![Active Jobs](./img/005-awx-tui-active-jobs.png)                  | ![Projects](./img/006-awx-tui-projects.png)                                      |
| ![Job Templates](./img/007-awx-tui-job-templates.png)              | ![Inventories](./img/008-awx-tui-inventories.png)                                |
| ![Debug Console](./img/009-awx-tui-debug-console.png)              | ![Advanced API Mode](./img/010-awx-tui-advanced-api-mode.png)                    |
| ![Create Mode](./img/011-awx-tui-create-mode.png)                  | ![Create Job Template](./img/012-awx-tui-create-job-template.png)                |
| ![Create Project](./img/013-awx-tui-create-project.png)            | ![API Payload Preview](./img/014-awx-tui-create-project-api-payload-preview.png) |
| ![Job Logs](./img/015-awx-tui-job-logs.png)                        | ![Job Events](./img/016-awx-tui-job-events.png)                                  |
| ![Launch Job](./img/017-awx-tui-launch-job.png)                    | ![Sync Project](./img/018-awx-tui-sync-project.png)                              |

---

## Requirements

- Python 3.12+
- AWX 21.x+
- Linux, macOS, or WSL2 on Windows
- Terminal size: **188x40** (188 columns × 40 rows) recommended for optimal display
  - Smaller terminals may require scrolling in some screens
  - Create/Update forms are designed for this size

- tmux (Hot Reloading Development Requirement)
---

## Quick Start

### Clone Project Source

```bash
# Clone repository
git clone https://github.com/ansible-community/awx-tui
cd awx-tui
```

### Create a new venv and activate it

```bash
python -m venv ~/.venv-awx-tui
source ~/.venv-awx-tui/bin/activate
```

### Install Python dependencies

```bash
pip install -r requirements.txt
```

### Run awx-tui from Source

```bash
python -m awx_tui.main
```

> [!NOTE]
> If you do not have any awx instances configured the awx-tui will still launch, but will have no awx instances to target.

### Configure an AWX instance connection via Environment Variables and launch awx-tui

```bash
export AWX_HOST=https://awx.example.com
export AWX_TOKEN=your-api-token-here
export AWX_VERIFY_SSL=true
python -m awx_tui.main
```

### Configure an AWX instance connection via command-line arguments and launch awx-tui

```bash
python -m awx_tui.main --host https://awx.example.com --token your-token
```

### Configure multiple AWX instances via the main configuration file

```bash
cp ./config.yaml.example ~/.config/awx-tui/config.yaml
```

Make updates to your configuration file as appropriate.  Below is an example configuration.

**Example configuration**:

```yaml
instances:
  # Example: Token-based authentication (recommended)
  dev2:
    url: https://awx.dev2.example.com      # Required: Full URL including https://
    auth:
      method: token                         # Required: "token" or "password"
      username: admin                       # Required: AWX username
      token: your-token-here                # Required for method: token
    verify_ssl: true                        # Optional: Verify SSL certs (default: true)
    description: "Development AWX 2"        # Optional: Human-readable description

  # Example: Password-based authentication
  dev1:
    url: https://awx.dev1.example.com
    auth:
      method: password
      username: admin
      password: your-password-here          # Required for method: password
    verify_ssl: false                       # Disable for self-signed certs
    description: "Development AWX 1"

preferences:
  # --- Dashboard Refresh Settings ---
  dashboard_auto_refresh: true                    # Enable/disable auto-refresh (default: true)
  dashboard_refresh_interval: 5                   # General dashboard refresh interval in seconds (default: 5)
  dashboard_refresh_timeout: 30                   # Max wait time for refresh before timeout (default: 30)

  # Per-section refresh intervals (seconds)
  dashboard_refresh_interval_running: 1           # Running jobs table (default: 1)
  dashboard_refresh_interval_recent: 1            # Recent jobs table (default: 1)
  dashboard_refresh_interval_capacity: 1          # Capacity metrics (default: 1)
  dashboard_refresh_interval_graphs: 1            # Dashboard graphs (default: 1)
  dashboard_refresh_interval_stats: 1             # Statistics panel (default: 1)

  # --- Job Detail Settings ---
  job_detail_refresh_interval: 1                  # Job detail modal refresh interval (default: 1)
  job_detail_auto_follow: true                    # Auto-scroll to bottom of logs (default: true)

  # --- Instance Management Settings ---
  instance_selection_refresh_interval: 5          # Instance health check interval (default: 5)
  show_instance_in_header: true                   # Show active instance in header (default: true)

  # --- Connection Pool Settings ---
  pool_max_connections: 20                        # Max connections per AWX instance pool (default: 20)
  pool_max_keepalive_connections: 10              # Max keepalive connections per pool (default: 10)

  # --- Development/Testing ---
  mock_mode: false                                # Enable mock mode (default: false)
```

Then, run awx-tui:

```bash
python -m awx_tui.main
```

---

## AWX TUI Configuration

Configuration file locations:
- **Non-Development:** `~/.config/awx-tui/config.yaml`
- **Development:** `./config.yaml` (within the repository root, for use with make targets)

See [config.yaml.example](./config.yaml.example) for complete configuration guide.

---

## Development

### Quick Start

#### Clone Project Source

```bash
# Clone repository
git clone https://github.com/ansible-community/awx-tui
cd awx-tui
```

#### Setup the Development Environment

```bash
# One-command setup (creates venv, installs everything)
make setup
```

#### Run the TUI

```bash
# Option 1: Mock mode (no AWX required - great for testing)
make run-mock

# Option 2: Connect to real AWX instance
cp config.yaml.example config.yaml
# Edit config.yaml with your AWX credentials
make run

# Option 3: Development mode with hot reload and mock data
make dev-mock

# Option 4: Development mode with hot reload connecting to the AWX instance configured in config.yaml (see Development section below)
make dev
```

#### Stopping dev mode

```bash
make stop-dev
```

### Testing

#### Run Tests

```bash
# Run all tests
make test

# Run with coverage report
make coverage

# Run basic smoke tests only
make test-basic
```

### Makefile Targets

```bash
# To see the full list of available make targets run
make help

# A few basic ones are described below:

# Setup & Installation
make setup       # Create venv and install all dependencies
make install     # Install package in development mode (if venv exists)

# Running
make run         # Run with real AWX (requires awx-env.sh)
make run-mock    # Run in mock mode (no AWX required)

# Development with Hot Reload (tmux + textual console)
make dev         # Real AWX + auto-reload on file changes
make dev-mock    # Mock mode + auto-reload on file changes
make stop-dev    # Stop the dev tmux session

# Testing
make test        # Run all tests
make test-basic  # Run basic smoke tests
make coverage    # Run tests with coverage report

# Cleanup
make clean       # Remove venv and build artifacts
```

---

## AWX TUI Key Bindings

### Global
- `Ctrl+Q` - Quit
- `Ctrl+D` - Debug console
- `Ctrl+T` - Advanced API Mode
- `Ctrl+O` - The Loaf (notification history)
- `Ctrl+N` - The Network Queue (connection pool management)
- `H`/`J`/`K`/`L` - Vim-style navigation (left/down/up/right)
- `I` or `?` - AWX-TUI Info

### Dashboard
- `Tab` - Switch between tables
- `↑`/`↓` or `K`/`J` - Navigate
- `Enter` - Job details
- `R` - Refresh

### Create/Update Screens
- `Ctrl+J` - JSON Preview
- `Ctrl+S` - Submit/Save
- `Ctrl+L` - Clear form
- `Ctrl+R` - Reload dropdowns

---

## AWX TUI Known Limitations

### AWX Instance Configuration
- Can only configure AWX Instances from config files, env vars or command line arguments

### Job Templates

**Limited Credential Type Support**
- Create/update job template screens support:
  * Machine (SSH) credentials: Single-select dropdown (one credential only)
  * Vault credentials: Multi-select list (multiple credentials supported)
- Other credential types (Cloud, Kubernetes, Network, etc.) must be added via AWX web UI
- Rationale: Machine and Vault credentials cover the most common use cases; other types are less frequent
- API endpoints used:
  * Machine: `/api/v2/credentials/?credential_type__kind=ssh`
  * Vault: `/api/v2/credentials/?credential_type__kind=vault`

**Prompt-on-Launch Templates**
- Templates with any `ask_*_on_launch` fields enabled cannot be edited via TUI
- Templates with prompt-on-launch fields cannot be launched via TUI (Ctrl+L)
- Affected fields: variables, inventory, credential, limit, tags, job type, execution environment, labels, SCM branch, diff mode, verbosity, forks
- Rationale: TUI forms are pre-populated; prompt-on-launch requires runtime input dialogs
- Workaround: Edit/launch these templates via AWX web UI

### Projects

**Git SCM Only**
- Create/update project screens only support Git SCM type
- Manual, SVN, Insights, and Archive types not supported in TUI
- Rationale: Git is the dominant SCM type; other types require different form fields
- API: Projects can still use other SCM types if created via web UI

**SCM Credentials - All Token Types Shown**
- SCM credential dropdown shows all token-type credentials, not just GitHub/GitLab PATs
- May include unrelated token credentials (e.g., custom credential types)
- Rationale: API doesn't expose specific token type filtering; filtering by name is unreliable
- Impact: Minor UX issue - extra credentials in dropdown that may not work for Git

### Advanced API Mode

**Response Headers Limited**
- Response headers tab only shows pre-populated headers from debug console log
- Fresh API requests via "Send" button don't populate response headers tab
- Headers are displayed for debug console replays only
- Rationale: Deferred feature - full header capture requires client modifications

### User Interface

**DataTable Click Behavior**
- Single click on table row both selects AND opens detail view
- Expected: Click to select, Enter key to open
- Affects: Historic Jobs, Active Jobs, Dashboard tables, Templates screen, Projects screen
- Rationale: Textual framework fires `RowSelected` event for both click and Enter
- Workaround: Use arrow keys for selection without opening details

### Credentials

**Six Credential Types Supported**
- Create credential screen supports: Machine, Source Control, GitHub PAT, GitLab PAT, Vault, Kubernetes
- Other credential types (AWS, Azure, VMware, etc.) must be created via AWX web UI
- Rationale: These six types cover common use cases; TUI forms can't dynamically adapt to all custom types
- All credential types visible in dropdowns (when created via web UI)

### General API Limitations

**Read-Only for Complex Objects**
- Workflow templates: Visible in templates list but cannot be edited (complex node graph)
- System job templates: Visible but cannot be edited (system-defined)
- Inventory sources: Visible but cannot be edited (complex sync configuration)
- Rationale: These objects require specialized UIs beyond TUI form capabilities

**No Bulk Operations**
- Cannot select multiple items for bulk actions
- Cannot delete multiple jobs/templates/projects at once
- Rationale: TUI focused on monitoring and basic CRUD; bulk operations are web UI domain

---

## License

**MIT License** - See [LICENSE](LICENSE)

---

## Contributing

This project is in early development. Contributions welcome after Phase 1 MVP is complete.

For bugs or feature requests: https://github.com/ansible-community/awx-tui/issues

---

## Mascot

**Rage-Tater** 🥔 - The Starchy Angry Automation Potato

Too much personality to render in ASCII art, but lives on in our hearts (and our tagline).

---

**Version:** 0.1.1
**Status:** In Development
