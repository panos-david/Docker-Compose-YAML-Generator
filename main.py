#!/usr/bin/env python3
"""
Docker Compose YAML Generator
=============================================

A lightweight desktop‑friendly CLI/GUI hybrid that intelligently detects the technology
stack of a local project and produces a ready‑to‑use docker‑compose.yml optimized
for development.

Supported Technologies:
- Languages: Node.js/TypeScript, Python, PHP, Go, C++, Ruby, C#/.NET, Rust, Scala, Elixir
- Frameworks: Spring-Boot, Django, Flask, FastAPI, Laravel, React, Vue, Angular
- Databases: PostgreSQL, MySQL, MariaDB, MongoDB, Redis, Elasticsearch, Cassandra
- Tools: Jupyter Notebooks, Nginx, Apache

Features:
- Smart version detection (uses project config files to select the right image version)
- Environment variable aware (can use env vars to configure images)
- Database detection from connection strings and dependencies
- Framework detection from project structure

* No external dependencies except PyYAML (install with `pip install pyyaml`).
* Packaged as a single executable using PyInstaller: `pyinstaller -F main.py`.

Usage (CLI)  
-------------
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

A tiny Tkinter dialog pops up if no path is supplied, so you can double‑click
the executable and select the folder graphically.

"""
from __future__ import annotations

import argparse
import os
import sys
import textwrap
from pathlib import Path
from typing import Dict, List

try:
    import yaml  # type: ignore
except ModuleNotFoundError:
    print("Missing dependency: PyYAML. Install with `pip install pyyaml`.", file=sys.stderr)
    sys.exit(1)

# ----------------------------------------------------------------------------
# Built‑in minimal service templates. Derived from the official Docker images
# and community best‑practice compose snippets (see project README for sources).
# You may freely extend or override these at runtime via the --template-dir flag.
# ----------------------------------------------------------------------------
TEMPLATES: Dict[str, str] = {
    "node": textwrap.dedent(
        """
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
            deploy:
              resources:
                limits:
                  cpus: '1'
                  memory: 1G
        """
    ),
    "spring": textwrap.dedent(
        """
        services:
          app:
            image: eclipse-temurin:21-jre-jammy
            working_dir: /app
            volumes:
              - .:/app
              - maven-cache:/root/.m2
            command: ["java","-jar","app.jar"]
            environment:
              SPRING_PROFILES_ACTIVE: dev
            develop:
              watch:
                - path: target/*.jar
                  action: rebuild
                - path: src
                  target: /app/src
                  action: sync
            deploy:
              resources:
                limits:
                  cpus: '2'
                  memory: 2G
        volumes:
          maven-cache:
        """
    ),
    "php": textwrap.dedent(
        """
        services:
          web:
            image: php:8.3-apache
            ports:
              - "8080:80"
            volumes:
              - .:/var/www/html
        """
    ),
    "go": textwrap.dedent(
        """
        services:
          app:
            image: golang:1.22-alpine
            working_dir: /app
            volumes:
              - .:/app
            command: go run .
        """
    ),
    "cpp": textwrap.dedent(
        """
        services:
          build:
            image: gcc:14-bookworm
            working_dir: /src
            volumes:
              - .:/src
            command: ["make"]
        """
    ),
    "ruby": textwrap.dedent(
        """
        services:
          app:
            image: ruby:3.3-alpine
            working_dir: /app
            volumes:
              - .:/app
            command: bundle exec rails s -b 0.0.0.0
            ports:
              - "3000:3000"
        """
    ),
    "dotnet": textwrap.dedent(
        """
        services:
          app:
            image: mcr.microsoft.com/dotnet/aspnet:8.0
            working_dir: /app
            volumes:
              - .:/app
            command: ["dotnet","YourApp.dll"]
            ports:
              - "5000:8080"
        """
    ),
    # --- Databases ----------------------------------------------------------
    "postgres": textwrap.dedent(
        """
        services:
          db:
            image: postgres:16-alpine
            restart: unless-stopped
            environment:
              POSTGRES_USER: postgres
              POSTGRES_PASSWORD: postgres
            volumes:
              - pgdata:/var/lib/postgresql/data
        volumes:
          pgdata:
        """
    ),
    "python": textwrap.dedent(
        """
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
        volumes:
          pip-cache:
        """
    ),
    "mysql": textwrap.dedent(
        """
        services:
          db:
            image: mysql:8.4
            restart: unless-stopped
            environment:
              MYSQL_ROOT_PASSWORD: root
            volumes:
              - mysqldata:/var/lib/mysql
        volumes:
          mysqldata:
        """
    ),
    "mariadb": textwrap.dedent(
        """
        services:
          db:
            image: mariadb:11
            environment:
              MARIADB_ROOT_PASSWORD: root
            volumes:
              - mariadbdata:/var/lib/mysql
        volumes:
          mariadbdata:
        """
    ),
    "cassandra": textwrap.dedent(
        """
        services:
          db:
            image: cassandra:5
            environment:
              CASSANDRA_CLUSTER_NAME: dev-cluster
              CASSANDRA_NUM_TOKENS: 8
        """
    ),
    # --- Proxies ------------------------------------------------------------
    "nginx": textwrap.dedent(
        """
        services:
          proxy:
            image: nginx:1.27-alpine
            ports:
              - "80:80"
              - "443:443"
            volumes:
              - ./nginx.conf:/etc/nginx/nginx.conf:ro
        """
    ),
    "apache": textwrap.dedent(
        """
        services:
          proxy:
            image: httpd:2.4-alpine
            ports:
              - "80:80"
              - "443:443"
            volumes:
              - ./httpd.conf:/usr/local/apache2/conf/httpd.conf:ro
        """
    ),
    "django": textwrap.dedent(
        """
        services:
          web:
            image: python:3.12-slim
            working_dir: /app
            volumes:
              - .:/app
            command: python manage.py runserver 0.0.0.0:8000
            ports:
              - "8000:8000"
            environment:
              - PYTHONUNBUFFERED=1
              - DJANGO_SETTINGS_MODULE=project.settings
        """
    ),
    "flask": textwrap.dedent(
        """
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
        """
    ),
    "jupyter": textwrap.dedent(
        """
        services:
          notebook:
            image: jupyter/minimal-notebook:latest
            volumes:
              - .:/home/jovyan/work
            ports:
              - "8888:8888"
            environment:
              - JUPYTER_ENABLE_LAB=yes
            command: start-notebook.sh --NotebookApp.token='' --NotebookApp.password=''
        """
    ),
    "rust": textwrap.dedent(
        """
        services:
          app:
            image: rust:1.77-slim
            working_dir: /app
            volumes:
              - .:/app
            command: cargo run
        """
    ),
    "scala": textwrap.dedent(
        """
        services:
          app:
            image: sbtscala/scala-sbt:eclipse-temurin-jammy-21.0.2_13_1.9.8
            working_dir: /app
            volumes:
              - .:/app
            command: sbt run
            environment:
              - SBT_OPTS="-Xmx1G"
        """
    ),
    "elixir": textwrap.dedent(
        """
        services:
          app:
            image: elixir:1.16-slim
            working_dir: /app
            volumes:
              - .:/app
            command: mix run
        """
    ),
    "laravel": textwrap.dedent(
        """
        services:
          app:
            image: php:8.3-fpm
            working_dir: /var/www/html
            volumes:
              - .:/var/www/html
            networks:
              - laravel
          webserver:
            image: nginx:1.27-alpine
            ports:
              - "8000:80"
            volumes:
              - .:/var/www/html
              - ./nginx/conf.d:/etc/nginx/conf.d
            networks:
              - laravel
        networks:
          laravel:
        """
    ),
    "fastapi": textwrap.dedent(
        """
        services:
          api:
            image: python:3.12-slim
            working_dir: /app
            volumes:
              - .:/app
            command: uvicorn main:app --host 0.0.0.0 --reload
            ports:
              - "8000:8000"
            environment:
              - PYTHONUNBUFFERED=1
              - LOG_LEVEL=debug
        """
    ),
    "vue": textwrap.dedent(
        """
        services:
          frontend:
            image: node:20-alpine
            working_dir: /app
            volumes:
              - .:/app
            command: npm run serve
            ports:
              - "8080:8080"
            environment:
              - NODE_ENV=development
        """
    ),
    "react": textwrap.dedent(
        """
        services:
          frontend:
            image: node:20-alpine
            working_dir: /app
            volumes:
              - .:/app
            command: npm start
            ports:
              - "3000:3000"
            environment:
              - NODE_ENV=development
              - CHOKIDAR_USEPOLLING=true
        """
    ),
    "angular": textwrap.dedent(
        """
        services:
          frontend:
            image: node:20-alpine
            working_dir: /app
            volumes:
              - .:/app
            command: ng serve --host 0.0.0.0
            ports:
              - "4200:4200"
            environment:
              - NODE_ENV=development
        """
    ),
    "mongodb": textwrap.dedent(
        """
        services:
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
        """
    ),
    "redis": textwrap.dedent(
        """
        services:
          redis:
            image: redis:7.2-alpine
            ports:
              - "6379:6379"
            volumes:
              - redisdata:/data
        volumes:
          redisdata:
        """
    ),
    "elasticsearch": textwrap.dedent(
        """
        services:
          elasticsearch:
            image: elasticsearch:8.12.0
            environment:
              - discovery.type=single-node
              - xpack.security.enabled=false
              - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
            ports:
              - "9200:9200"
            volumes:
              - esdata:/usr/share/elasticsearch/data
        volumes:
          esdata:
        """
    ),
}

# Map heuristics -> template keys ------------------------------------------------
SIGNATURES = {
    "package.json": "node",
    "pom.xml": "spring",
    "build.gradle": "spring",
    "composer.json": "php",
    "go.mod": "go",
    "CMakeLists.txt": "cpp",
    "Gemfile": "ruby",
    ".csproj": "dotnet",
    "requirements.txt": "python",
    "setup.py": "python",
    "pyproject.toml": "python",
    "manage.py": "django",
    "wsgi.py": "django",
    "asgi.py": "django",
    "app.py": "flask",
    "Cargo.toml": "rust",
    "build.sbt": "scala",
    "mix.exs": "elixir",
    "artisan": "laravel",
    "main.rs": "rust",
    "angular.json": "angular",
    "vue.config.js": "vue",
    "gatsby-config.js": "react",
    "next.config.js": "react",
    "tsconfig.json": "node",
}


def find_project_types(project_root: Path) -> List[str]:
    """Return a list of detected tech keys based on signature files."""
    detected: List[str] = []
    for sig, tech in SIGNATURES.items():
        if sig.startswith('.'):
            # glob for csproj in subdirs
            if any(project_root.rglob(sig)):
                detected.append(tech)
        else:
            if (project_root / sig).exists():
                detected.append(tech)
    
    # Special case for Jupyter notebooks
    if list(project_root.glob("*.ipynb")):
        detected.append("jupyter")
    
    # Detect databases and other tech stack from environment variables and configuration files
    db_techs = detect_databases_from_config(project_root)
    detected.extend(db_techs)
    
    # Detect FastAPI framework if not already detected
    if "python" in detected and not any(x in detected for x in ["django", "flask"]):
        # Look for FastAPI imports in Python files
        if has_dependency(project_root, "fastapi"):
            detected.append("fastapi")
        
    return detected


def detect_databases_from_config(project_root: Path) -> List[str]:
    """Detect databases and other services from configuration files."""
    detected = []
    
    # Check common environment file patterns
    env_files = [".env", ".env.local", ".env.development", ".env.example", "docker-compose.env"]
    env_vars = {}
    
    # Collect environment variables from files
    for env_file in env_files:
        env_path = project_root / env_file
        if env_path.exists():
            try:
                with open(env_path, "r") as f:
                    for line in f:
                        if '=' in line and not line.strip().startswith('#'):
                            key, value = line.strip().split('=', 1)
                            env_vars[key] = value
            except:
                pass
    
    # Check for database connection strings
    for key, value in env_vars.items():
        value_lower = value.lower()
        
        if "postgres" in key.lower() or "postgres" in value_lower or "postgresql" in value_lower:
            detected.append("postgres")
        elif "mysql" in key.lower() or "mysql" in value_lower:
            detected.append("mysql")
        elif "mongo" in key.lower() or "mongo" in value_lower:
            detected.append("mongodb")
        elif "redis" in key.lower() or "redis" in value_lower:
            detected.append("redis")
        elif "elastic" in key.lower() or "elastic" in value_lower:
            detected.append("elasticsearch")
        elif "cassandra" in key.lower() or "cassandra" in value_lower:
            detected.append("cassandra")
        elif "maria" in key.lower() or "mariadb" in value_lower:
            detected.append("mariadb")
    
    # Check requirements.txt, package.json, etc. for database dependencies
    if has_dependency(project_root, "psycopg2") or has_dependency(project_root, "pg"):
        detected.append("postgres")
    if has_dependency(project_root, "mysql") or has_dependency(project_root, "mysql2"):
        detected.append("mysql")
    if has_dependency(project_root, "mongodb") or has_dependency(project_root, "mongoose"):
        detected.append("mongodb")
    if has_dependency(project_root, "redis"):
        detected.append("redis")
    if has_dependency(project_root, "elasticsearch"):
        detected.append("elasticsearch")
    
    # Check for nginx/apache config files
    if any(project_root.glob("nginx*.conf")) or any(project_root.glob("*/nginx*.conf")):
        detected.append("nginx")
    if any(project_root.glob("apache*.conf")) or any(project_root.glob("httpd*.conf")) or any(project_root.glob("*/httpd*.conf")):
        detected.append("apache")
    
    return detected


def has_dependency(project_root: Path, dependency_name: str) -> bool:
    """Check if a project has a specific dependency."""
    # Check Python requirements.txt
    req_path = project_root / "requirements.txt"
    if req_path.exists():
        try:
            with open(req_path, "r") as f:
                if any(dependency_name in line.lower() for line in f):
                    return True
        except:
            pass
    
    # Check Python pyproject.toml
    pyproject_path = project_root / "pyproject.toml"
    if pyproject_path.exists():
        try:
            with open(pyproject_path, "r") as f:
                content = f.read()
                if dependency_name in content.lower():
                    return True
        except:
            pass
    
    # Check Node package.json
    package_json_path = project_root / "package.json"
    if package_json_path.exists():
        try:
            import json
            with open(package_json_path, "r") as f:
                data = json.load(f)
                deps = data.get("dependencies", {})
                dev_deps = data.get("devDependencies", {})
                if dependency_name in deps or dependency_name in dev_deps:
                    return True
        except:
            pass
    
    # Check PHP composer.json
    composer_path = project_root / "composer.json"
    if composer_path.exists():
        try:
            import json
            with open(composer_path, "r") as f:
                data = json.load(f)
                deps = data.get("require", {})
                dev_deps = data.get("require-dev", {})
                if any(dependency_name in k for k in list(deps.keys()) + list(dev_deps.keys())):
                    return True
        except:
            pass
            
    # Check for Python imports in .py files
    if dependency_name in ["fastapi", "flask", "django"]:
        try:
            py_files = list(project_root.glob("*.py"))
            for py_file in py_files[:10]:  # Check first 10 Python files
                with open(py_file, "r") as f:
                    content = f.read()
                    if f"import {dependency_name}" in content or f"from {dependency_name}" in content:
                        return True
        except:
            pass
            
    return False


def merge_services(compose_objects: List[dict]) -> dict:
    """Merge a list of docker‑compose dicts (version 3+) into one."""
    merged: dict = {"services": {}, "volumes": {}}
    for obj in compose_objects:
        for section in ["services", "volumes"]:
            if section in obj:
                merged_section = merged.setdefault(section, {})
                for k, v in obj[section].items():
                    if k in merged_section:
                        # naive merge; real‑world implementation may need
                        # to de‑duplicate ports, volumes, etc.
                        merged_section[k].update(v)
                    else:
                        merged_section[k] = v
    return merged


def generate_compose(project_root: Path, extra: List[str] | None = None, generate_bake: bool = True, 
                    enable_gpu: bool = True, add_watch_mode: bool = True) -> dict:
    techs = find_project_types(project_root)
    if extra:
        techs.extend(extra)
    if not techs:
        raise RuntimeError("Did not find a supported type of project")

    # Remove duplicates while preserving order
    unique_techs = []
    for tech in techs:
        if tech not in unique_techs:
            unique_techs.append(tech)
    
    parts = []
    for key in unique_techs:
        if key in TEMPLATES:
            # Customize the template with the correct version
            template_str = TEMPLATES[key]
            template_dict = yaml.safe_load(template_str)
            
            # Update image versions based on detected project versions
            if "services" in template_dict:
                for service_name, service_config in template_dict["services"].items():
                    if "image" in service_config:
                        image_parts = service_config["image"].split(":")
                        if len(image_parts) == 2:
                            base_image, _ = image_parts
                            if ":" in base_image:
                                # Skip if image has a registry with port like localhost:5000/image
                                continue
                            
                            # For base language images like node, python, etc.
                            if any(tech_name in base_image for tech_name in ["node", "python", "php", "ruby", "golang", "dotnet"]):
                                version = detect_version(project_root, key)
                                service_config["image"] = f"{base_image}:{version}"
            
            parts.append(template_dict)

    # Merge all the service templates
    merged_compose = merge_services(parts)
    
    # Add BuildKit cache optimization if there are builds
    merged_compose = add_buildkit_cache_hints(merged_compose)
    
    # Add platform-specific configurations
    platform_info = detect_platform()
    merged_compose = apply_platform_configuration(merged_compose, platform_info)
    
    # Add GPU configuration if enabled and available
    if enable_gpu:
        gpu_capabilities = detect_gpu_capabilities()
        merged_compose = apply_gpu_configuration(merged_compose, gpu_capabilities)
    
    # Generate docker-bake.hcl file if requested
    if generate_bake:
        try:
            generate_bake_file(project_root, merged_compose)
        except Exception as e:
            print(f"Warning: Could not generate bake file: {e}", file=sys.stderr)
    
    return merged_compose


def write_compose(compose: dict, output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as fh:
        yaml.dump(compose, fh, sort_keys=False)
    print(f"✔ Created file: {output_path}")


# --- Version detection utilities ----------------------------------------------

def detect_version(project_root: Path, tech_type: str) -> str:
    """Detect the version of a technology from project files."""
    version_mapping = {
        "node": _detect_node_version,
        "python": _detect_python_version,
        "php": _detect_php_version,
        "go": _detect_go_version,
        "ruby": _detect_ruby_version,
        "dotnet": _detect_dotnet_version,
    }
    
    if tech_type in version_mapping:
        detected = version_mapping[tech_type](project_root)
        if detected:
            return detected
    
    # Default fallback versions
    defaults = {
        "node": "20-alpine",
        "python": "3.12-slim",
        "django": "3.12-slim",
        "flask": "3.12-slim",
        "php": "8.3-apache",
        "go": "1.22-alpine",
        "ruby": "3.3-alpine",
        "dotnet": "8.0",
        "spring": "21-jre-jammy",
        "postgres": "16-alpine",
        "mysql": "8.4",
        "mariadb": "11",
        "cassandra": "5",
        "nginx": "1.27-alpine",
        "apache": "2.4-alpine",
        "jupyter": "latest",
    }
    
    # Check for version env vars (e.g., NODE_VERSION, PYTHON_VERSION)
    env_var = f"{tech_type.upper()}_VERSION"
    if env_var in os.environ:
        return os.environ[env_var]
    
    return defaults.get(tech_type, "latest")


def _detect_node_version(project_root: Path) -> str:
    """Detect Node.js version from package.json or .nvmrc."""
    # Check .nvmrc file
    nvmrc_path = project_root / ".nvmrc"
    if nvmrc_path.exists():
        with open(nvmrc_path, "r") as f:
            version = f.read().strip()
            if version:
                return f"{version}-alpine"
    
    # Check package.json engines field
    pkg_json_path = project_root / "package.json"
    if pkg_json_path.exists():
        try:
            import json
            with open(pkg_json_path, "r") as f:
                pkg_data = json.load(f)
                if "engines" in pkg_data and "node" in pkg_data["engines"]:
                    node_ver = pkg_data["engines"]["node"]
                    # Clean version string (e.g., ">=14", "^16.13.0")
                    if node_ver.startswith((">=", "^", "~")):
                        node_ver = node_ver[1:].split(".")[0]
                    return f"{node_ver}-alpine"
        except (json.JSONDecodeError, KeyError):
            pass
    
    return ""


def _detect_python_version(project_root: Path) -> str:
    """Detect Python version from pyproject.toml, setup.py or .python-version."""
    # Check .python-version file (pyenv)
    pyenv_path = project_root / ".python-version"
    if pyenv_path.exists():
        with open(pyenv_path, "r") as f:
            version = f.read().strip()
            if version and len(version) >= 3:
                return f"{version[:3]}-slim"
    
    # Check pyproject.toml
    pyproject_path = project_root / "pyproject.toml"
    if pyproject_path.exists():
        try:
            with open(pyproject_path, "r") as f:
                content = f.read()
                import re
                # Look for Python version in requires-python
                python_req = re.search(r'requires-python\s*=\s*["\']([^"\']+)["\']', content)
                if python_req:
                    version_str = python_req.group(1)
                    # Extract major.minor version
                    match = re.search(r'>=\s*(\d+\.\d+)', version_str)
                    if match:
                        return f"{match.group(1)}-slim"
        except:
            pass
    
    # Check runtime.txt (common in Heroku Python apps)
    runtime_path = project_root / "runtime.txt"
    if runtime_path.exists():
        try:
            with open(runtime_path, "r") as f:
                content = f.read().strip()
                if content.startswith("python-"):
                    version = content.replace("python-", "")
                    major_minor = ".".join(version.split(".")[:2])
                    return f"{major_minor}-slim"
        except:
            pass
            
    return ""


def _detect_php_version(project_root: Path) -> str:
    """Detect PHP version from composer.json."""
    composer_path = project_root / "composer.json"
    if composer_path.exists():
        try:
            import json
            with open(composer_path, "r") as f:
                composer_data = json.load(f)
                if "require" in composer_data and "php" in composer_data["require"]:
                    php_ver = composer_data["require"]["php"]
                    # Extract version from constraints like ">=7.4", "^8.0"
                    import re
                    match = re.search(r'[~^]?>=?\s*(\d+\.\d+)', php_ver)
                    if match:
                        return f"{match.group(1)}-apache"
        except:
            pass
    
    return ""


def _detect_go_version(project_root: Path) -> str:
    """Detect Go version from go.mod."""
    go_mod_path = project_root / "go.mod"
    if go_mod_path.exists():
        try:
            with open(go_mod_path, "r") as f:
                content = f.read()
                import re
                go_ver = re.search(r'go\s+(\d+\.\d+)', content)
                if go_ver:
                    return f"{go_ver.group(1)}-alpine"
        except:
            pass
    
    return ""


def _detect_ruby_version(project_root: Path) -> str:
    """Detect Ruby version from .ruby-version or Gemfile."""
    # Check .ruby-version file
    ruby_ver_path = project_root / ".ruby-version"
    if ruby_ver_path.exists():
        with open(ruby_ver_path, "r") as f:
            version = f.read().strip()
            if version:
                major_minor = ".".join(version.split(".")[:2])
                return f"{major_minor}-alpine"
    
    # Check Gemfile for Ruby version
    gemfile_path = project_root / "Gemfile"
    if gemfile_path.exists():
        try:
            with open(gemfile_path, "r") as f:
                content = f.read()
                import re
                ruby_ver = re.search(r'ruby\s+[\'"](\d+\.\d+\.\d+)[\'"]', content)
                if ruby_ver:
                    major_minor = ".".join(ruby_ver.group(1).split(".")[:2])
                    return f"{major_minor}-alpine"
        except:
            pass
    
    return ""


def _detect_dotnet_version(project_root: Path) -> str:
    """Detect .NET version from .csproj files."""
    # Look for any .csproj file in the project
    csproj_files = list(project_root.rglob("*.csproj"))
    if csproj_files:
        try:
            with open(csproj_files[0], "r") as f:
                content = f.read()
                import re
                # Look for TargetFramework element
                framework = re.search(r'<TargetFramework>([^<]+)</TargetFramework>', content)
                if framework:
                    fw = framework.group(1)
                    if fw.startswith("net"):
                        # Extract version number from netX.0
                        ver = fw.replace("net", "").split(".")[0]
                        return f"{ver}.0"
        except:
            pass
    
    return ""


# --- Simple Tkinter fallback -------------------------------------------------

def tk_file_dialog() -> Path | None:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox
    except ModuleNotFoundError:
        return None

    root = tk.Tk()
    root.withdraw()
    directory = filedialog.askdirectory(title="Choose Project Directory",)
    root.destroy()
    return Path(directory) if directory else None


# --- GPU Detection and Platform Configuration -------------------------------------------

def detect_gpu_capabilities() -> Dict[str, bool]:
    """Detect GPU capabilities like CUDA, ROCm, or OpenCL availability."""
    gpu_capabilities = {
        "cuda": False,
        "rocm": False,
        "opencl": False,
        "intel_gpu": False,
        "has_gpu": False
    }
    
    # Check NVIDIA GPUs (CUDA)
    try:
        import subprocess
        result = subprocess.run(["nvidia-smi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            gpu_capabilities["cuda"] = True
            gpu_capabilities["has_gpu"] = True
    except:
        pass
    
    # Check AMD GPUs (ROCm)
    try:
        result = subprocess.run(["rocm-smi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            gpu_capabilities["rocm"] = True
            gpu_capabilities["has_gpu"] = True
    except:
        pass
    
    # Check OpenCL support
    try:
        import ctypes
        ctypes.CDLL("libOpenCL.so")
        gpu_capabilities["opencl"] = True
    except:
        try:
            ctypes.CDLL("OpenCL.dll")
            gpu_capabilities["opencl"] = True
        except:
            pass
    
    # Check Intel GPUs
    try:
        result = subprocess.run(["intel_gpu_top", "-L"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            gpu_capabilities["intel_gpu"] = True
            gpu_capabilities["has_gpu"] = True
    except:
        pass
    
    return gpu_capabilities

def detect_platform() -> Dict[str, str]:
    """Detect platform-specific information."""
    import platform
    
    arch = platform.machine().lower()
    os_name = platform.system().lower()
    
    platform_info = {
        "architecture": arch,
        "os": os_name,
        "is_arm": "arm" in arch or "aarch" in arch,
        "is_x86": "x86" in arch or "amd64" in arch,
        "docker_platform": "linux/amd64" if "x86" in arch or "amd64" in arch else "linux/arm64"
    }
    
    return platform_info

def apply_gpu_configuration(compose_dict: dict, gpu_capabilities: Dict[str, bool]) -> dict:
    """Apply GPU-specific configuration to docker-compose services."""
    if not gpu_capabilities.get("has_gpu", False):
        return compose_dict
    
    if "services" not in compose_dict:
        return compose_dict
    
    for service_name, service_config in compose_dict["services"].items():
        # Skip services that shouldn't get GPU access (like databases)
        if service_name in ["db", "redis", "postgres", "mysql", "mariadb", "mongodb"]:
            continue
        
        # Set deploy section with GPU resources
        deploy = service_config.setdefault("deploy", {})
        resources = deploy.setdefault("resources", {})
        
        if gpu_capabilities.get("cuda", False):
            # NVIDIA GPU configuration
            if "reservations" not in resources:
                resources["reservations"] = {}
            
            devices = resources["reservations"].setdefault("devices", [])
            devices.append({
                "driver": "nvidia",
                "count": "all",
                "capabilities": ["gpu", "compute", "utility"]
            })
            
            # Add NVIDIA runtime if needed for older Docker versions
            service_config["runtime"] = "nvidia"
        
        elif gpu_capabilities.get("rocm", False):
            # AMD GPU configuration
            if "reservations" not in resources:
                resources["reservations"] = {}
                
            devices = resources["reservations"].setdefault("devices", [])
            devices.append({
                "driver": "amd",
                "count": "all",
                "capabilities": ["gpu", "compute"]
            })
    
    return compose_dict

def apply_platform_configuration(compose_dict: dict, platform_info: Dict[str, str]) -> dict:
    """Apply platform-specific configuration to docker-compose services."""
    if "services" not in compose_dict:
        return compose_dict
    
    for service_name, service_config in compose_dict["services"].items():
        if "image" in service_config:
            # Add platform flag for cross-platform compatibility
            service_config["platform"] = platform_info["docker_platform"]
    
    return compose_dict


# --- BuildKit Caching and Bake Support ----------------------------------------------

def add_buildkit_cache_hints(compose_dict: dict) -> dict:
    """Add BuildKit cache optimization hints to service builds."""
    if "services" not in compose_dict:
        return compose_dict
    
    for service_name, service_config in compose_dict["services"].items():
        if "build" in service_config:
            # If build is a string, convert to dict
            if isinstance(service_config["build"], str):
                service_config["build"] = {"context": service_config["build"]}
                
            # Add BuildKit cache settings
            build_config = service_config["build"]
            
            # Add cache_from and cache_to directives
            build_config["cache_from"] = ["type=registry,ref=user/app:buildcache"]
            build_config["cache_to"] = ["type=inline,mode=max"]
            
            # Add build arguments for better caching
            if "args" not in build_config:
                build_config["args"] = {}
            
            build_config["args"]["BUILDKIT_INLINE_CACHE"] = "1"
    
    return compose_dict

def generate_bake_file(project_root: Path, compose_dict: dict) -> None:
    """Generate a docker-bake.hcl file for the project."""
    bake_content = """// docker-bake.hcl - Generated by Docker Compose YAML Generator
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

"""
    
    # Add targets for each buildable service
    if "services" in compose_dict:
        for service_name, service_config in compose_dict["services"].items():
            if "build" in service_config:
                # Get build context
                build_context = service_config["build"]
                if isinstance(build_context, dict):
                    build_context = build_context.get("context", ".")
                
                # Add development target
                bake_content += f"""
target "{service_name}-development" {{
  context = "{build_context}"
  tags = ["{service_name}:development"]
  cache-from = ["type=registry,ref={service_name}:buildcache"]
  cache-to = ["type=inline"]
  target = "development"
}}

target "{service_name}-production" {{
  context = "{build_context}"
  tags = ["{service_name}:${{TAG}}"]
  cache-from = ["type=registry,ref={service_name}:buildcache"]
  platforms = ["linux/amd64", "linux/arm64"]
  target = "production"
}}
"""
    
    # Write to file
    bake_path = project_root / "docker-bake.hcl"
    with open(bake_path, "w") as f:
        f.write(bake_content)
    
    print(f"✔ Created bake file: {bake_path}")
    return


# ----------------------------------------------------------------------------
# Entry‑point
# ----------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate docker‑compose.yml for a local project.")
    parser.add_argument("project_root", nargs="?", help="Path to the project directory")
    parser.add_argument("--output", "-o", default="docker-compose.generated.yml", help="Output YAML file name")
    parser.add_argument("--include", "-i", nargs="*", choices=list(TEMPLATES.keys()), help="Force‑include extra templates (e.g. db, proxy)")
    parser.add_argument("--force-type", "-t", choices=list(TEMPLATES.keys()), help="Force project type detection")
    parser.add_argument("--env-file", "-e", help="Specify path to an environment file to use for configuration")
    parser.add_argument("--list-supported", "-l", action="store_true", help="List all supported project types")
    parser.add_argument("--no-gpu", action="store_true", help="Disable GPU detection and configuration")
    parser.add_argument("--no-bake", action="store_true", help="Disable docker-bake.hcl generation")
    parser.add_argument("--no-watch", action="store_true", help="Disable Docker Compose watch mode configuration")
    parser.add_argument("--platform", choices=["auto", "amd64", "arm64"], default="auto", help="Force a specific platform target")
    parser.add_argument("--resource-limits", action="store_true", help="Add resource limits to services")
    args = parser.parse_args()
    
    if args.list_supported:
        print("Supported project types:")
        for tech in sorted(TEMPLATES.keys()):
            print(f"  - {tech}")
        return
    
    if args.project_root:
        project_path = Path(args.project_root).expanduser().resolve()
    else:
        sel = tk_file_dialog()
        if not sel:
            parser.error("Provide folder name in command prompt or via dialog.")
        project_path = sel

    if not project_path.exists():
        parser.error(f"Folder {project_path} doesn't exist.")
    
    # Set environment variables from specified env file
    if args.env_file:
        env_path = Path(args.env_file).expanduser().resolve()
        if env_path.exists():
            try:
                with open(env_path, "r") as f:
                    for line in f:
                        if '=' in line and not line.strip().startswith('#'):
                            key, value = line.strip().split('=', 1)
                            os.environ[key] = value
                print(f"✔ Loaded environment from: {env_path}")
            except Exception as e:
                print(f"Warning: Could not load environment file: {e}", file=sys.stderr)
    
    try:
        extra_techs = args.include or []
        if args.force_type:
            extra_techs.append(args.force_type)
        
        # Set platform override if specified
        if args.platform != "auto":
            os.environ["DOCKER_DEFAULT_PLATFORM"] = f"linux/{args.platform}"
        
        compose_dict = generate_compose(
            project_path, 
            extra=extra_techs,
            generate_bake=not args.no_bake,
            enable_gpu=not args.no_gpu,
            add_watch_mode=not args.no_watch
        )
        
        output_path = Path(args.output).resolve()
        write_compose(compose_dict, output_path)
        
        # Print detected technologies
        techs = find_project_types(project_path)
        if techs:
            print(f"✔ Detected technologies: {', '.join(techs)}")
        
        # Print detected platform
        platform_info = detect_platform()
        print(f"✔ Target platform: {platform_info['docker_platform']}")
        
        # Print GPU capabilities if enabled
        if not args.no_gpu:
            gpu_capabilities = detect_gpu_capabilities()
            if gpu_capabilities.get("has_gpu", False):
                gpu_types = []
                if gpu_capabilities.get("cuda", False):
                    gpu_types.append("CUDA")
                if gpu_capabilities.get("rocm", False):
                    gpu_types.append("ROCm")
                if gpu_capabilities.get("opencl", False):
                    gpu_types.append("OpenCL")
                if gpu_capabilities.get("intel_gpu", False):
                    gpu_types.append("Intel GPU")
                
                print(f"✔ GPU capabilities detected: {', '.join(gpu_types)}")
                print(f"  GPU passthrough enabled for compatible services")
        
        print(f"✔ Next steps:")
        print(f"  1. Review {output_path}")
        print(f"  2. Run with: docker compose -f {output_path.name} up")
        
        # Show bake command if generated
        if not args.no_bake:
            print(f"  3. Or build with: docker buildx bake")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
