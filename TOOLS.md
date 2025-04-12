# Tools

## GitLab Runner Installation Script

A Python script to automate the installation and configuration of GitLab Runner on Linux systems.

### Key Features

#### Automatic System Detection
- Detects whether to use DEB or RPM packages
- Identifies system architecture (amd64, arm, arm64)

#### Package Installation
- Adds official GitLab Runner repository
- Installs the appropriate package for your system

#### Runner Registration
- Supports interactive registration with all major options
- Configures executor (shell, docker, etc.)
- Sets tags and description

#### Comprehensive Error Handling
- Color-coded output for errors and warnings
- Proper error messages for failed operations

#### Flexible Configuration
- Supports all major GitLab instances (GitLab.com or self-hosted)
- Configurable executor types and Docker images

### Prerequisites

- Linux system
- Python 3
- curl
- grep
- systemd

### Usage

```bash
sudo ./install_gitlab_runner.py --token YOUR_REGISTRATION_TOKEN \
    --description "My Production Runner" \
    --tags "docker,production" \
    --executor docker \
    --docker-image alpine:latest
```

Force reinstall
```bash
sudo ./install_gitlab_runner.py --force
```

Self-hosted GitLab instance
```bash
sudo ./install_gitlab_runner.py --token YOUR_TOKEN --url https://gitlab.example.com
```

Command Line Options:
| Option          | Description                                  | Default Value          |
|-----------------|----------------------------------------------|------------------------|
| --token         | GitLab Runner registration token (optional)  | None                   |
| --url           | GitLab instance URL                          | `"https://gitlab.com"` |
| --description   | Runner description                           | `"My Runner"`          |
| --tags          | Comma-separated tags for the runner          | `""` (empty string)    |
| --executor      | Runner executor type                         | `"shell"`              |
| --docker-image  | Default Docker image                         | `"alpine:latest"`      |
| --force         | Force reinstall                              | `False`                |

## Jenkins Agent Installation Script

### Basic installation
sudo ./install_jenkins_agent.py agent1 https://jenkins.example.com <secret>

### With custom options
sudo ./install_jenkins_agent.py \
    agent1 \
    https://jenkins.example.com \
    <secret> \
    --agent-dir /opt/my-jenkins-agent \
    --user myagent \
    --java-opts "-Xmx2g -Xms512m" \
    --force

