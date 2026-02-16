# Tab Saver API

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

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install dependencies

```bash
uv sync
```

### Run locally

```bash
uv run flask --app src.app run --debug
```

### Run tests

```bash
uv run pytest
```

Tests are configured to enforce **80% minimum coverage** and generate an HTML coverage report in `htmlcov/`.

## Project Structure

```
TabSaverAPI/
├── src/
│   └── app.py          # Flask application, models, routes, and Lambda handler
├── tests/
│   └── test_tabs.py    # Unit and integration tests
├── Dockerfile           # Multi-stage build for AWS Lambda
├── pyproject.toml       # Project config, dependencies, and tool settings
└── uv.lock
```

## DynamoDB Table Schema

The application uses a single-table design with a composite key:

| Key | Attribute | Type |
|-----|-----------|------|
| Partition key | `entity_type` | String (`tab`, `tag`, `tab_tag`) |
| Sort key | `id` | String |

## Docker

```bash
docker build -t tab-saver-api .
```

## License

MIT
