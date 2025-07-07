# Docker Compose YAML Generator

![Docker Compose](https://img.shields.io/badge/Docker_Compose-2.23.3-blue)
![Python](https://img.shields.io/badge/Python-3.10+-green)
![License](https://img.shields.io/badge/License-MIT-purple)

A lightweight desktop-friendly CLI/GUI hybrid tool that intelligently detects the technology stack of a local project and produces a ready-to-use `docker-compose.yml` optimized for development.

## Features

- **Smart Technology Detection**: Automatically identifies your project's stack based on configuration files
- **Multiple Language Support**: Works with Node.js/TypeScript, Python, PHP, Go, C++, Ruby, C#/.NET, Rust, Scala, Elixir
- **Framework Detection**: Supports Spring-Boot, Django, Flask, FastAPI, Laravel, React, Vue, Angular
- **Database Integration**: PostgreSQL, MySQL, MariaDB, MongoDB, Redis, Elasticsearch, Cassandra
- **Tool Support**: Jupyter Notebooks, Nginx, Apache
- **Smart Version Detection**: Uses project config files to select the right image version
- **Environment Variable Awareness**: Uses env vars to configure images
- **Database Detection**: Identifies databases from connection strings and dependencies
- **Docker Compose Watch**: Auto-configures file watching for live reloading
- **BuildKit Cache Optimization**: Adds cache hints for faster builds
- **Docker Buildx Bake**: Generates docker-bake.hcl for multi-platform builds
- **GPU Detection**: Supports CUDA, ROCm, and OpenCL-enabled services
- **Platform-specific Settings**: ARM64/x86_64 architecture detection
- **Resource Management**: CPU/Memory limits and reservations

## Installation

### Prerequisites

- Python 3.10 or higher
- PyYAML library (`pip install pyyaml`)

### Simple Installation

```bash
# Clone this repository
git clone https://github.com/YourUsername/Docker-Compose-YAML-Generator.git

# Install the requirements
pip install -r requirements.txt
```

### Executable Build (Optional)

You can create a standalone executable for easier distribution:

```bash
# Install PyInstaller
pip install pyinstaller

# Build the executable
pyinstaller -F main.py
```

## Usage

### Command Line Interface

```bash
# Basic usage (generates docker-compose.generated.yml)
python main.py /path/to/project

# Add additional services
python main.py /path/to/project --include postgres redis

# Force a specific project type
python main.py /path/to/project --force-type python

# Use a specific env file for configuration
python main.py /path/to/project --env-file .env.docker

# List all supported project types
python main.py --list-supported

# Disable GPU detection
python main.py /path/to/project --no-gpu

# Disable docker-bake.hcl generation
python main.py /path/to/project --no-bake

# Target specific platform
python main.py /path/to/project --platform arm64
```

### Graphical Interface

Simply double-click the executable (or run the script without arguments), and a file dialog will appear to select your project folder.

## How It Works

1. **Detection**: The tool scans your project directory for signature files like `package.json`, `requirements.txt`, etc.
2. **Analysis**: It determines your project's main language, frameworks, and dependencies
3. **Environment Check**: Examines environment variables and configuration files for database connections
4. **Template Selection**: Chooses the appropriate Docker templates for each detected technology
5. **Version Selection**: Selects the most compatible Docker image versions
6. **Generation**: Creates a `docker-compose.generated.yml` file optimized for development

## Supported Technologies

### Languages
- Node.js/TypeScript
- Python
- PHP
- Go
- C++
- Ruby
- C#/.NET
- Rust
- Scala
- Elixir

### Frameworks
- Spring-Boot
- Django
- Flask
- FastAPI
- Laravel
- React
- Vue
- Angular

### Databases
- PostgreSQL
- MySQL
- MariaDB
- MongoDB
- Redis
- Elasticsearch
- Cassandra

### Tools
- Jupyter Notebooks
- Nginx
- Apache

## Examples

### Python Flask Application

For a Flask application with a `requirements.txt` containing Flask and Redis:

```yaml
services:
  web:
    image: python:3.12-slim
    working_dir: /app
    volumes:
      - .:/app
    command: flask run --host=0.0.0.0
    ports:
      - "5000:5000"
    environment:
      - FLASK_APP=app.py
      - FLASK_ENV=development
      - PYTHONUNBUFFERED=1
  
  redis:
    image: redis:7.2-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data

volumes:
  redisdata:
```

### Node.js Application with MongoDB

For a Node.js application with MongoDB dependency in `package.json`:

```yaml
services:
  app:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - .:/app
    command: npm start
    environment:
      - NODE_ENV=development

  mongodb:
    image: mongo:7.0
    environment:
      - MONGO_INITDB_ROOT_USERNAME=root
      - MONGO_INITDB_ROOT_PASSWORD=example
    ports:
      - "27017:27017"
    volumes:
      - mongodata:/data/db

volumes:
  mongodata:
```

### Python Application with GPU Support

For a Python application with GPU dependencies:

```yaml
services:
  app:
    image: python:3.12-slim
    working_dir: /app
    volumes:
      - .:/app
      - pip-cache:/root/.cache/pip
    command: python main.py
    environment:
      - PYTHONUNBUFFERED=1
    develop:
      watch:
        - path: requirements.txt
          action: rebuild
        - path: .
          target: /app
          action: sync
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu, compute, utility]

volumes:
  pip-cache:
```

### Node.js with Docker Compose Watch

For a Node.js application configured with watch mode for auto-reloading:

```yaml
services:
  app:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - .:/app
    command: npm start
    environment:
      - NODE_ENV=development
    develop:
      watch:
        - path: package.json
          action: rebuild
        - path: .
          target: /app
          action: sync
    ports:
      - "3000:3000"

volumes:
  node_modules:
```

### Docker Bake Configuration

The generated `docker-bake.hcl` file allows multi-platform builds:

```hcl
// docker-bake.hcl - Generated by Docker Compose YAML Generator
// Run with: docker buildx bake

group "default" {
  targets = ["development"]
}

group "production" {
  targets = ["app-production"]
}

group "development" {
  targets = ["app-development"]
}

// Default variables
variable "TAG" {
  default = "latest"
}

target "app-development" {
  context = "."
  tags = ["app:development"]
  cache-from = ["type=registry,ref=app:buildcache"]
  cache-to = ["type=inline"]
  target = "development"
}

target "app-production" {
  context = "."
  tags = ["app:${TAG}"]
  cache-from = ["type=registry,ref=app:buildcache"]
  platforms = ["linux/amd64", "linux/arm64"]
  target = "production"
}
```

## Advanced Features

### GPU Support

The tool automatically detects NVIDIA CUDA, AMD ROCm, and OpenCL-capable GPUs and configures Docker Compose services appropriately:

- **NVIDIA GPUs**: Adds NVIDIA runtime and device configuration
- **AMD GPUs**: Configures ROCm device access
- **Intel GPUs**: Sets up Intel GPU access when available

To disable GPU detection, use the `--no-gpu` flag.

### Docker Compose Watch

Automatically configures Docker Compose's watch feature for supported project types, enabling:

- **File Change Detection**: Rebuilds services when critical files change
- **Live File Syncing**: Updates files in containers without full rebuilds
- **Selective Rebuilding**: Only rebuilds when package managers detect changes

### Docker BuildX Bake Support

Generates a `docker-bake.hcl` file for multi-platform builds with:

- **Multi-architecture Support**: Builds for both ARM64 and AMD64
- **Development/Production Targets**: Separate targets for different environments
- **BuildKit Cache**: Optimized caching configuration

To disable bake file generation, use the `--no-bake` flag.

### Platform-Specific Configuration

Automatically detects the current architecture and configures:

- **Compatible Images**: Selects images that work on your architecture
- **Cross-Platform Support**: Adds platform flags when needed
- **Architecture-Specific Optimizations**: Tailors configuration to ARM or x86

To target a specific platform, use the `--platform` flag with either `arm64` or `amd64`.

### Resource Management

Adds sensible defaults for container resource limits:

- **Memory Limits**: Prevents container memory leaks from affecting the host
- **CPU Limits**: Ensures fair CPU distribution
- **Resource Reservations**: Guarantees minimum resources for critical services

## Contributing

Contributions are welcome! Feel free to:

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add some amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by the need for quick Docker environment setup for development
- Thanks to the Docker community for best practices in container configuration
