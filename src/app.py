"""
Tab Manager Real API
Flask application for AWS Lambda + DynamoDB
"""

from datetime import datetime
from typing import Any

import boto3
from flask import Flask, jsonify, request

app = Flask(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

AWS_REGION = "us-east-1"
DYNAMODB_TABLE = "TabManager"

# Initialize DynamoDB client
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)


# ============================================================
# MODELS & HELPERS
# ============================================================


class TabItem:
    """Represents a tab item in DynamoDB"""

    def __init__(
        self,
        tab_id: str,
        url: str,
        title: str,
        notes: str | None = None,
        is_archived: int = 0,
    ):
        self.tab_id = tab_id
        self.url = url
        self.title = title
        self.notes = notes
        self.is_archived = is_archived
        self.created_at = datetime.utcnow().isoformat() + "Z"
        self.updated_at = self.created_at

    def to_dynamodb_item(self) -> dict[str, Any]:
        """Convert to DynamoDB item format"""
        return {
            "entity_type": "tab",
            "id": self.tab_id,
            "url": self.url,
            "title": self.title,
            "notes": self.notes,
            "is_archived": self.is_archived,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dynamodb_item(item: dict[str, Any]) -> "TabItem":
        """Create from DynamoDB item"""
        tab = TabItem(
            tab_id=item["id"],
            url=item["url"],
            title=item["title"],
            notes=item.get("notes"),
            is_archived=item.get("is_archived", 0),
        )
        tab.created_at = item.get("created_at", tab.created_at)
        tab.updated_at = item.get("updated_at", tab.updated_at)
        return tab

    def to_dict(
        self, include_tags: bool = False, tags: list[str] | None = None
    ) -> dict[str, Any]:
        """Convert to API response format"""
        response = {
            "id": self.tab_id,
            "url": self.url,
            "title": self.title,
            "notes": self.notes,
            "is_archived": self.is_archived,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_tags:
            response["tags"] = tags or []
        return response


class TagItem:
    """Represents a tag item in DynamoDB"""

    def __init__(self, tag_id: str, name: str):
        self.tag_id = tag_id
        self.name = name
        self.created_at = datetime.utcnow().isoformat() + "Z"

    def to_dynamodb_item(self) -> dict[str, Any]:
        """Convert to DynamoDB item format"""
        return {
            "entity_type": "tag",
            "id": self.tag_id,
            "name": self.name,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dynamodb_item(item: dict[str, Any]) -> "TagItem":
        """Create from DynamoDB item"""
        tag = TagItem(tag_id=item["id"], name=item["name"])
        tag.created_at = item.get("created_at", tag.created_at)
        return tag

    def to_dict(self) -> dict[str, Any]:
        """Convert to API response format"""
        return {"id": self.tag_id, "name": self.name}


# ============================================================
# DATABASE OPERATIONS
# ============================================================


def get_next_id(entity_type: str) -> str:
    """Get next ID for entity (simplified counter approach)"""
    # In production, use atomic counters or UUIDs
    import uuid

    return str(uuid.uuid4())


def save_tab(tab: TabItem) -> None:
    """Save tab to DynamoDB"""
    table.put_item(Item=tab.to_dynamodb_item())


def get_tab(tab_id: str) -> TabItem | None:
    """Get tab from DynamoDB"""
    response = table.get_item(Key={"entity_type": "tab", "id": tab_id})
    if "Item" in response:
        return TabItem.from_dynamodb_item(response["Item"])
    return None


def get_all_tabs(archived: bool = False) -> list[TabItem]:
    """Get all tabs from DynamoDB"""
    response = table.query(
        KeyConditionExpression="entity_type = :et",
        ExpressionAttributeValues={":et": "tab"},
    )

    tabs = [TabItem.from_dynamodb_item(item) for item in response.get("Items", [])]

    # Filter by archived status
    filtered = [t for t in tabs if (t.is_archived == 1) == archived]

    # Sort by created_at descending
    return sorted(filtered, key=lambda x: x.created_at, reverse=True)


def delete_tab(tab_id: str) -> None:
    """Delete tab from DynamoDB"""
    table.delete_item(Key={"entity_type": "tab", "id": tab_id})
    # Also delete tab_tag associations
    response = table.query(
        KeyConditionExpression="entity_type = :et AND begins_with(id, :pk)",
        ExpressionAttributeValues={":et": "tab_tag", ":pk": f"{tab_id}#"},
    )
    for item in response.get("Items", []):
        table.delete_item(Key={"entity_type": "tab_tag", "id": item["id"]})


def update_tab_archive_status(tab_id: str, is_archived: int) -> None:
    """Update tab archive status"""
    table.update_item(
        Key={"entity_type": "tab", "id": tab_id},
        UpdateExpression="SET is_archived = :ia, updated_at = :ua",
        ExpressionAttributeValues={
            ":ia": is_archived,
            ":ua": datetime.utcnow().isoformat() + "Z",
        },
    )


def save_tag(tag: TagItem) -> None:
    """Save tag to DynamoDB"""
    table.put_item(Item=tag.to_dynamodb_item())


def get_tag_by_name(tag_name: str) -> TagItem | None:
    """Get tag by name (scan - not ideal for production)"""
    response = table.scan(
        FilterExpression="entity_type = :et AND #name = :name",
        ExpressionAttributeNames={"#name": "name"},
        ExpressionAttributeValues={":et": "tag", ":name": tag_name},
    )
    items = response.get("Items", [])
    if items:
        return TagItem.from_dynamodb_item(items[0])
    return None


def get_all_tags() -> list[TagItem]:
    """Get all tags from DynamoDB"""
    response = table.query(
        KeyConditionExpression="entity_type = :et",
        ExpressionAttributeValues={":et": "tag"},
    )
    tags = [TagItem.from_dynamodb_item(item) for item in response.get("Items", [])]
    return sorted(tags, key=lambda x: x.name)


def add_tab_tag(tab_id: str, tag_id: str) -> None:
    """Associate tag with tab"""
    item = {
        "entity_type": "tab_tag",
        "id": f"{tab_id}#{tag_id}",
        "tab_id": tab_id,
        "tag_id": tag_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    table.put_item(Item=item)


def remove_tab_tag(tab_id: str, tag_id: str) -> None:
    """Remove tag association from tab"""
    table.delete_item(Key={"entity_type": "tab_tag", "id": f"{tab_id}#{tag_id}"})


def get_tabs_by_tag(tag_id: str) -> list[str]:
    """Get all tab IDs associated with a tag"""
    response = table.scan(
        FilterExpression="entity_type = :et AND tag_id = :tid",
        ExpressionAttributeValues={":et": "tab_tag", ":tid": tag_id},
    )
    return [item["tab_id"] for item in response.get("Items", [])]


def get_tab_tags(tab_id: str) -> list[str]:
    """Get all tag IDs associated with a tab"""
    response = table.query(
        KeyConditionExpression="entity_type = :et AND begins_with(id, :pk)",
        ExpressionAttributeValues={":et": "tab_tag", ":pk": f"{tab_id}#"},
    )
    return [item["tag_id"] for item in response.get("Items", [])]


# ============================================================
# FLASK ROUTES - TABS
# ============================================================


@app.route("/api/tabs", methods=["POST"])
def save_tab_route() -> tuple[str, int]:
    """Save a new tab"""
    try:
        data = request.get_json()
        url = data.get("url", "").strip()
        title = data.get("title", "").strip()

        if not url or not title:
            return jsonify({"error": "URL and title required"}), 400

        tab_id = get_next_id("tab")
        tab = TabItem(tab_id=tab_id, url=url, title=title)
        save_tab(tab)

        return (
            jsonify({"id": tab_id, "status": "saved", "url": url, "title": title}),
            201,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tabs", methods=["GET"])
def get_tabs_route() -> tuple[str, int]:
    """Get all tabs"""
    try:
        archived = request.args.get("archived", "false").lower() == "true"
        tabs = get_all_tabs(archived=archived)
        result = [tab.to_dict() for tab in tabs]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tabs/<tab_id>", methods=["GET"])
def get_tab_route(tab_id: str) -> tuple[str, int]:
    """Get a single tab with its tags"""
    try:
        tab = get_tab(tab_id)
        if not tab:
            return jsonify({"error": "Tab not found"}), 404

        # Get tags for this tab
        tag_ids = get_tab_tags(tab_id)
        tag_names = []
        for tag_id in tag_ids:
            response = table.get_item(Key={"entity_type": "tag", "id": tag_id})
            if "Item" in response:
                tag_names.append(response["Item"]["name"])

        return jsonify(tab.to_dict(include_tags=True, tags=tag_names)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tabs/<tab_id>", methods=["DELETE"])
def delete_tab_route(tab_id: str) -> tuple[str, int]:
    """Delete a tab"""
    try:
        if not get_tab(tab_id):
            return jsonify({"error": "Tab not found"}), 404

        delete_tab(tab_id)
        return jsonify({"status": "deleted", "id": tab_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tabs/<tab_id>/archive", methods=["PUT"])
def archive_tab_route(tab_id: str) -> tuple[str, int]:
    """Archive or unarchive a tab"""
    try:
        if not get_tab(tab_id):
            return jsonify({"error": "Tab not found"}), 404

        data = request.get_json()
        is_archived = 1 if data.get("archived", False) else 0

        update_tab_archive_status(tab_id, is_archived)
        return jsonify({"status": "updated", "archived": bool(is_archived)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# FLASK ROUTES - TAGS
# ============================================================


@app.route("/api/tags", methods=["GET"])
def get_tags_route() -> tuple[str, int]:
    """Get all tags"""
    try:
        tags = get_all_tags()
        result = [tag.to_dict() for tag in tags]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tabs/<tab_id>/tags", methods=["POST"])
def add_tag_route(tab_id: str) -> tuple[str, int]:
    """Add a tag to a tab"""
    try:
        if not get_tab(tab_id):
            return jsonify({"error": "Tab not found"}), 404

        data = request.get_json()
        tag_name = data.get("tag", "").strip()

        if not tag_name:
            return jsonify({"error": "Tag name required"}), 400

        # Find or create tag
        tag = get_tag_by_name(tag_name)
        if not tag:
            tag_id = get_next_id("tag")
            tag = TagItem(tag_id=tag_id, name=tag_name)
            save_tag(tag)
        else:
            tag_id = tag.tag_id

        # Associate tag with tab
        add_tab_tag(tab_id, tag_id)

        return jsonify({"status": "tagged", "tag": tag_name}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tabs/<tab_id>/tags/<tag_name>", methods=["DELETE"])
def remove_tag_route(tab_id: str, tag_name: str) -> tuple[str, int]:
    """Remove a tag from a tab"""
    try:
        if not get_tab(tab_id):
            return jsonify({"error": "Tab not found"}), 404

        tag = get_tag_by_name(tag_name)
        if tag:
            remove_tab_tag(tab_id, tag.tag_id)

        return jsonify({"status": "untagged"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# FLASK ROUTES - SEARCH
# ============================================================


@app.route("/api/search", methods=["GET"])
def search_tabs_route() -> tuple[str, int]:
    """Search tabs by name, URL, or tag"""
    try:
        q = request.args.get("q", "").strip().lower()
        search_type = request.args.get("type", "all").lower()

        if not q or len(q) < 2:
            return jsonify({"error": "Query too short (minimum 2 chars)"}), 400

        results = []
        all_tabs = get_all_tabs(archived=False)

        if search_type == "name":
            # Search by URL or title
            for tab in all_tabs:
                if q in tab.url.lower() or q in tab.title.lower():
                    results.append(tab)

        elif search_type == "tag":
            # Search by tag
            tags = get_all_tags()
            matching_tag_ids = [t.tag_id for t in tags if q in t.name.lower()]
            matching_tab_ids = set()
            for tag_id in matching_tag_ids:
                matching_tab_ids.update(get_tabs_by_tag(tag_id))
            results = [t for t in all_tabs if t.tab_id in matching_tab_ids]

        else:  # "all"
            # Search both names and tags
            matching_tabs = set()

            # Search by name
            for tab in all_tabs:
                if q in tab.url.lower() or q in tab.title.lower():
                    matching_tabs.add(tab.tab_id)

            # Search by tag
            tags = get_all_tags()
            matching_tag_ids = [t.tag_id for t in tags if q in t.name.lower()]
            for tag_id in matching_tag_ids:
                matching_tabs.update(get_tabs_by_tag(tag_id))

            results = [t for t in all_tabs if t.tab_id in matching_tabs]

        # Sort by created_at descending
        results.sort(key=lambda x: x.created_at, reverse=True)

        # Add tags to results
        result_dicts = []
        for tab in results[:50]:
            tag_ids = get_tab_tags(tab.tab_id)
            tag_names = []
            for tag_id in tag_ids:
                response = table.get_item(Key={"entity_type": "tag", "id": tag_id})
                if "Item" in response:
                    tag_names.append(response["Item"]["name"])
            result_dicts.append(tab.to_dict(include_tags=True, tags=tag_names))

        return jsonify(result_dicts), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# FLASK ROUTES - STATS
# ============================================================


@app.route("/api/stats", methods=["GET"])
def get_stats_route() -> tuple[str, int]:
    """Get statistics"""
    try:
        active_tabs = get_all_tabs(archived=False)
        archived_tabs = get_all_tabs(archived=True)
        tags = get_all_tags()

        return (
            jsonify(
                {
                    "active_tabs": len(active_tabs),
                    "archived_tabs": len(archived_tabs),
                    "total_tags": len(tags),
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# FLASK ROUTES - HEALTH
# ============================================================


@app.route("/api/health", methods=["GET"])
def health_check() -> tuple[str, int]:
    """Health check endpoint"""
    try:
        active_tabs = get_all_tabs(archived=False)
        return (
            jsonify(
                {
                    "status": "ok",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "tabs_stored": len(active_tabs),
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ============================================================
# FLASK ROUTES - DOCUMENTATION
# ============================================================


@app.route("/", methods=["GET"])
def index() -> tuple[str, int]:
    """API documentation"""
    return (
        jsonify(
            {
                "name": "Tab Manager API (Real)",
                "version": "1.0",
                "description": "Production API using AWS Lambda + DynamoDB",
                "endpoints": {
                    "POST /api/tabs": "Save a new tab",
                    "GET /api/tabs": "Get all tabs (?archived=true)",
                    "GET /api/tabs/<id>": "Get single tab with tags",
                    "DELETE /api/tabs/<id>": "Delete a tab",
                    "PUT /api/tabs/<id>/archive": "Archive/unarchive tab",
                    "GET /api/tags": "List all tags",
                    "POST /api/tabs/<id>/tags": "Add tag to tab",
                    "DELETE /api/tabs/<id>/tags/<tag_name>": "Remove tag",
                    "GET /api/search": "Search tabs (?q=query&type=all|name|tag)",
                    "GET /api/stats": "Get statistics",
                    "GET /api/health": "Health check",
                },
            }
        ),
        200,
    )


# ============================================================
# LAMBDA HANDLER
# ============================================================


def lambda_handler(event, context):
    """AWS Lambda handler for API Gateway proxy integration"""
    with app.test_request_context(
        path=event.get("path", "/"),
        method=event.get("httpMethod", "GET"),
        data=event.get("body", ""),
        headers=event.get("headers", {}),
    ):
        response = app.full_dispatch_request()
        return {
            "statusCode": response.status_code,
            "body": response.get_data(as_text=True),
            "headers": {"Content-Type": "application/json"},
        }


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
