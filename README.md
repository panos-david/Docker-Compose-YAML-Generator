# Docker Compose YAML Generator

![Docker Compose](https://img.shields.io/badge/Docker_Compose-2.23.3-blue)
![Python](https://img.shields.io/badge/Python-3.10+-green)
![License](https://img.shields.io/badge/License-MIT-orange)

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
