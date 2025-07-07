# Changelog

All notable changes to the Docker Compose YAML Generator project will be documented in this file.

## [1.1.0] - 2025-07-07

### Added
- Docker Compose Watch mode support for live reloading
- Docker BuildX Bake file generation (docker-bake.hcl)
- BuildKit cache optimization hints for faster builds
- GPU detection and configuration (CUDA, ROCm, OpenCL)
- Resource reservations and limits (CPU, memory)
- Platform-specific settings for ARM64/x86_64
- Cross-platform build configuration
- Device passthrough configuration

### Changed
- Updated templates to include resource limits and watch configuration
- Enhanced CLI with options for GPU, Bake, and platform settings
- Expanded documentation with examples for new features

## [1.0.0] - 2025-07-06

### Added
- Initial release
- Support for multiple programming languages: Node.js/TypeScript, Python, PHP, Go, C++, Ruby, C#/.NET, Rust, Scala, Elixir
- Framework detection: Spring-Boot, Django, Flask, FastAPI, Laravel, React, Vue, Angular
- Database integration: PostgreSQL, MySQL, MariaDB, MongoDB, Redis, Elasticsearch, Cassandra
- Smart version detection based on project configuration files
- Environment variable awareness
- Database detection from connection strings and project dependencies
