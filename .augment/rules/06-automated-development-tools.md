# Automated Development Tools Reference

## Purpose
Comprehensive reference for all automated development tools, commands, and workflows implemented in the Multi-Agent Real-Estate Contract Platform.

## Quick Start Commands

### Essential Daily Commands
```bash
# Start development environment
make dev                    # Start all services + health check

# Development workflow
make status                 # Check environment status
make test                   # Run all tests
make quality               # Run all quality checks
make format                # Format all code

# Service management
make start                 # Start services only
make stop                  # Stop all services
make restart               # Restart all services
```

### Python Virtual Environment
```bash
# Activate virtual environment (Windows)
.venv\Scripts\activate

# Activate virtual environment (Unix/Mac)
source .venv/bin/activate

# Install/update dependencies
pip install -r requirements-dev.txt
pip install -r backend/requirements.txt
```

## Automated Code Quality Tools

### Python Tools (Backend)
| Tool | Purpose | Configuration | Auto-Run |
|------|---------|---------------|----------|
| **Black** | Code formatting | `pyproject.toml` | ✅ Pre-commit, Save |
| **isort** | Import sorting | `pyproject.toml` | ✅ Pre-commit, Save |
| **Flake8** | Linting | `pyproject.toml` | ✅ Pre-commit, CI |
| **MyPy** | Type checking | `pyproject.toml` | ✅ Pre-commit, CI |
| **Bandit** | Security scanning | Built-in rules | ✅ Pre-commit, CI |

### TypeScript/JavaScript Tools (Frontend)
| Tool | Purpose | Configuration | Auto-Run |
|------|---------|---------------|----------|
| **Prettier** | Code formatting | `.prettierrc` | ✅ Pre-commit, Save |
| **ESLint** | Linting | `.eslintrc.json` | ✅ Pre-commit, Save |
| **TypeScript** | Type checking | `tsconfig.json` | ✅ Build, CI |

### Additional Tools
| Tool | Purpose | Configuration | Auto-Run |
|------|---------|---------------|----------|
| **detect-secrets** | Secret scanning | `.secrets.baseline` | ✅ Pre-commit, CI |
| **yamllint** | YAML validation | `.yamllint.yaml` | ✅ Pre-commit |
| **markdownlint** | Markdown linting | Built-in rules | ✅ Pre-commit |
| **hadolint** | Dockerfile linting | Built-in rules | ✅ Pre-commit |

## VS Code Integration

### Debug Configurations (F5 Menu)
- **FastAPI Backend**: Debug backend with hot reload
- **Next.js Frontend**: Debug frontend with source maps
- **Python: Current File**: Debug any Python file
- **Pytest Current File**: Debug specific test file
- **Celery Worker**: Debug background tasks
- **Full Stack Development**: Debug both frontend and backend

### Custom Tasks (Ctrl+Shift+P → "Tasks: Run Task")
- Setup Development Environment
- Start/Stop Development Services
- Run Backend/Frontend Tests
- Format Backend/Frontend Code
- Run Pre-commit Hooks
- Check Service Health
- Development Status

### Extensions (Auto-recommended)
- **Python**: ms-python.python
- **TypeScript**: ms-vscode.vscode-typescript-next
- **ESLint**: dbaeumer.vscode-eslint
- **Prettier**: esbenp.prettier-vscode
- **Docker**: ms-azuretools.vscode-docker
- **GitLens**: eamodio.gitlens
- **GitHub Copilot**: github.copilot

## CI/CD Pipeline

### GitHub Actions Workflows
| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **ci.yml** | Push, PR | Full CI pipeline with quality checks |
| **pr-checks.yml** | PR only | PR-specific validation and automation |
| **dependency-update.yml** | Weekly | Automated dependency updates |

### CI Jobs
1. **Task Verification**: Ensures task list is updated
2. **Backend Quality**: Python linting, formatting, type checking
3. **Backend Tests**: Pytest with coverage reporting
4. **Frontend Quality**: TypeScript linting, formatting, building
5. **Frontend Tests**: Jest with coverage reporting
6. **Docker Build**: Validates Docker images build correctly
7. **Security Scan**: Trivy vulnerability scanning
8. **Dependency Check**: Safety (Python) + npm audit (Node.js)

## Development Utilities

### dev_utils.py Commands
```bash
python scripts/dev_utils.py validate    # Validate environment setup
python scripts/dev_utils.py health      # Check service health
python scripts/dev_utils.py start       # Start development services
python scripts/dev_utils.py stop        # Stop development services
python scripts/dev_utils.py reset-db    # Reset development database
python scripts/dev_utils.py test-data   # Generate test data
python scripts/dev_utils.py quality     # Run code quality checks
python scripts/dev_utils.py status      # Show comprehensive status
```

### Environment Setup
```bash
# Initial setup (run once)
python scripts/setup_dev_env.py

# Manual pre-commit installation
.venv\Scripts\pre-commit install

# Manual pre-commit run
.venv\Scripts\pre-commit run --all-files
```

## Quality Gates and Enforcement

### Pre-commit Hooks (Automatic)
- Runs on every `git commit`
- Blocks commits that fail quality checks
- Formats code automatically when possible
- Validates task list compliance for code changes

### CI/CD Quality Gates
- All tests must pass
- Code coverage must meet minimum thresholds
- No linting errors allowed
- Security scans must pass
- Task list must be updated for code changes

### Manual Quality Checks
```bash
# Run all quality checks locally
make quality

# Individual checks
make lint                  # Run all linting
make format               # Format all code
make test                 # Run all tests
make test-coverage        # Run tests with coverage
```

## Troubleshooting

### Common Issues
1. **Pre-commit fails**: Run `make format` then commit again
2. **Tests fail**: Check service health with `make health`
3. **Import errors**: Ensure virtual environment is activated
4. **Docker issues**: Run `make docker-clean` then `make start`
5. **VS Code not configured**: Restart VS Code after setup

### Environment Validation
```bash
# Check everything is working
make status

# Validate specific components
python scripts/dev_utils.py validate
python scripts/dev_utils.py health
```

### Reset Development Environment
```bash
# Nuclear option - reset everything
make clean
make docker-clean
python scripts/setup_dev_env.py
make dev
```

## Best Practices

### Daily Workflow
1. Activate virtual environment
2. Start services: `make dev`
3. Check status: `make status`
4. Develop with automatic quality checks
5. Run tests: `make test`
6. Commit (automatic validation)

### Before Committing
- Code is automatically formatted (pre-commit)
- Tests pass locally: `make test`
- Quality checks pass: `make quality`
- Task list is updated (automatic verification)

### Before Creating PR
- All CI checks pass
- Code coverage meets requirements
- Task list reflects progress
- PR description is comprehensive

This automated foundation ensures consistent quality while maximizing developer productivity.
