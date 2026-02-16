# tab-saver-api

A production REST API for managing browser tabs, built with Flask and backed by AWS DynamoDB. Designed to run on AWS Lambda via API Gateway proxy integration.

## Features

- Save, retrieve, archive, and delete tabs
- Tag tabs with custom labels
- Search tabs by name, URL, or tag
- Statistics and health check endpoints
- Deployable as an AWS Lambda container image

## Tech Stack

- **Runtime:** Python 3.13
- **Framework:** Flask
- **Database:** AWS DynamoDB (single-table design)
- **Deployment:** Docker + AWS Lambda
- **Testing:** pytest + moto (AWS mocking)
- **Code Quality:** ruff (linter) + black (formatter)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API documentation |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/stats` | Tab and tag statistics |
| `POST` | `/api/tabs` | Save a new tab |
| `GET` | `/api/tabs` | List all tabs (`?archived=true` for archived) |
| `GET` | `/api/tabs/<id>` | Get a single tab with its tags |
| `DELETE` | `/api/tabs/<id>` | Delete a tab |
| `PUT` | `/api/tabs/<id>/archive` | Archive or unarchive a tab |
| `GET` | `/api/tags` | List all tags |
| `POST` | `/api/tabs/<id>/tags` | Add a tag to a tab |
| `DELETE` | `/api/tabs/<id>/tags/<tag_name>` | Remove a tag from a tab |
| `GET` | `/api/search` | Search tabs (`?q=query&type=all\|name\|tag`) |

## Getting Started

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install dependencies

```bash
uv sync
```

### Run locally

```bash
uv run flask --app src.app run --debug
```

The API will be available at `http://localhost:5000`

## Code Quality

This project uses modern Python tooling to maintain high code quality standards.

### Black (Code Formatter)

[Black](https://black.readthedocs.io/) is an opinionated code formatter that ensures consistent style across the codebase.

**Format all code:**
```bash
uv run black src/ tests/
```

**Check formatting without making changes:**
```bash
uv run black --check src/ tests/
```

**Format a specific file:**
```bash
uv run black src/app.py
```

**Configuration:** Black is configured in `pyproject.toml` with:
- Line length: 100 characters
- Target Python versions: 3.11+

### Ruff (Linter)

[Ruff](https://docs.astral.sh/ruff/) is a fast Python linter that checks for common errors and code issues.

**Check for linting errors:**
```bash
uv run ruff check src/ tests/
```

**Auto-fix errors:**
```bash
uv run ruff check --fix src/ tests/
```

**Check a specific file:**
```bash
uv run ruff check src/app.py
```

**Configuration:** Ruff is configured in `pyproject.toml` with:
- Line length: 100 characters
- Enabled checks: E (errors), W (warnings), F (pyflakes), I (imports), N (naming), UP (upgrades)
- Ignored checks: E501 (line too long - handled by black)

### Running All Code Quality Checks

Run all checks in sequence:

```bash
# Format code
uv run black src/ tests/

# Check for issues
uv run ruff check src/ tests/

# Run tests with coverage
uv run pytest tests/ -v --cov=src --cov-fail-under=80
```

Or create a script `check.sh`:

```bash
#!/bin/bash
set -e

echo "Running black formatter..."
uv run black src/ tests/

echo "Running ruff linter..."
uv run ruff check --fix src/ tests/

echo "Running tests..."
uv run pytest tests/ -v --cov=src --cov-fail-under=80

echo "✅ All checks passed!"
```

Then run:
```bash
chmod +x check.sh
./check.sh
```

## Running Tests

### Run all tests

```bash
uv run pytest tests/ -v
```

### Run tests with coverage report

```bash
uv run pytest tests/ -v --cov=src --cov-report=html
```

This generates an HTML coverage report in `htmlcov/index.html`

### Run specific test file

```bash
uv run pytest tests/test_tabs.py -v
```

### Run specific test class

```bash
uv run pytest tests/test_tabs.py::TestTabItemModel -v
```

### Run specific test function

```bash
uv run pytest tests/test_tabs.py::TestTabItemModel::test_tab_item_creation -v
```

Tests are configured to enforce **80% minimum coverage**.

## Project Structure

```
tab-saver-api/
├── src/
│   └── app.py               # Flask application, models, routes, and Lambda handler
├── tests/
│   └── test_tabs.py         # Unit and integration tests
├── .github/
│   └── workflows/
│       ├── tests.yml        # GitHub Actions: Tests & code quality
│       └── build-and-push.yml  # GitHub Actions: Build Docker & push to ECR
├── Dockerfile                # Multi-stage build for AWS Lambda
├── pyproject.toml            # Project config, dependencies, and tool settings
├── README.md                 # This file
├── .gitignore
└── uv.lock
```

## DynamoDB Table Schema

The application uses a single-table design with a composite key:

| Key | Attribute | Type |
|-----|-----------|------|
| Partition key | `entity_type` | String (`tab`, `tag`, `tab_tag`) |
| Sort key | `id` | String |

**Global Secondary Indexes:**
- `entity_type_created_at_idx` - Query by creation date
- `entity_type_tag_id_idx` - Query tabs by tag

## Docker

### Build image

```bash
docker build -t tab-saver-api .
```

### Run locally

```bash
docker run -p 5000:5000 tab-saver-api
```

### Test image from ECR

First, login to ECR:

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 366579856667.dkr.ecr.us-east-1.amazonaws.com
```

Replace `366579856667` with your AWS Account ID, or use this command to get it automatically:

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com
```

Then pull and run the image:

```bash
docker pull 366579856667.dkr.ecr.us-east-1.amazonaws.com/tab-saver-api:latest
docker run -p 5000:5000 366579856667.dkr.ecr.us-east-1.amazonaws.com/tab-saver-api:latest
```

### Push to AWS ECR

See [GitHub Actions ECR Setup Guide](docs/GitHub_Actions_ECR_Setup_Guide.md) for complete prerequisites and automated builds/pushes.

**Quick summary:**
1. Create ECR repository
2. Create IAM role with OIDC trust
3. Add `AWS_ROLE_ARN` secret to GitHub
4. Push to main branch
5. GitHub Actions automatically builds and pushes to ECR

## GitHub Actions

This project includes two GitHub Actions workflows:

### 1. Tests & Code Quality (`tests.yml`)
Runs on every push and pull request:
- Black formatter check
- Ruff linter
- pytest with 80% coverage requirement
- Codecov upload

### 2. Build & Push to ECR (`build-and-push.yml`)
Runs on push to main (only if tests pass):
- Builds Docker image
- Tags with commit SHA and `latest`
- Pushes to AWS ECR
- (Optional) Updates Lambda function

## Development Workflow

1. **Make changes**
   ```bash
   # Edit src/app.py or tests/
   ```

2. **Format and lint**
   ```bash
   uv run black src/ tests/
   uv run ruff check --fix src/ tests/
   ```

3. **Run tests**
   ```bash
   uv run pytest tests/ -v --cov=src --cov-fail-under=80
   ```

4. **Commit and push**
   ```bash
   git add .
   git commit -m "feat: add new endpoint"
   git push origin main
   ```

5. **GitHub Actions runs automatically:**
   - ✅ Tests pass → Docker builds → ECR push
   - ❌ Tests fail → No build

## Configuration

### pyproject.toml

The project is configured via `pyproject.toml`:

**Black configuration:**
```toml
[tool.black]
line-length = 100
target-version = ["py311", "py312", "py313"]
```

**Ruff configuration:**
```toml
[tool.ruff]
line-length = 100
select = ["E", "W", "F", "I", "N", "UP"]
ignore = ["E501"]
```

**Pytest configuration:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=src --cov-fail-under=80"
```

## Troubleshooting

### "black: command not found"
```bash
# Install dev dependencies
uv sync --all-extras

# Then use uv run
uv run black src/ tests/
```

### "ModuleNotFoundError: No module named 'src'"
```bash
# Make sure you're in the project root
cd tab-saver-api

# And using uv run
uv run pytest tests/
```

### Tests fail with coverage < 80%
```bash
# Run tests with coverage report
uv run pytest tests/ -v --cov=src --cov-report=html

# Open htmlcov/index.html to see which lines need coverage
# Write tests for uncovered lines
```

### Docker build fails
```bash
# Make sure Dockerfile is in project root
ls -la Dockerfile

# And dependencies are in pyproject.toml
cat pyproject.toml | grep dependencies
```

## License

MIT