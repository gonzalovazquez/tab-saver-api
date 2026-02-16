"""
Unit tests for Tab Manager Real API
Comprehensive tests for endpoints, models, and database operations
"""

import os
from datetime import datetime

import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def aws_credentials():
    """Mock AWS credentials - auto-used for all tests"""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def app():
    """Create Flask app for testing"""
    with mock_aws():
        import boto3

        import src.app as app_module
        from src.app import app

        # Create DynamoDB table
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        mock_table = dynamodb.create_table(
            TableName="TabManager",
            KeySchema=[
                {"AttributeName": "entity_type", "KeyType": "HASH"},
                {"AttributeName": "id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "entity_type", "AttributeType": "S"},
                {"AttributeName": "id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Patch the module-level table so routes use the mocked DynamoDB
        app_module.dynamodb = dynamodb
        app_module.table = mock_table

        app.config["TESTING"] = True
        yield app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


class TestTabItemModel:
    """Test TabItem model"""

    def test_tab_item_creation(self):
        """Test creating a TabItem"""
        from src.app import TabItem

        tab = TabItem(
            tab_id="1",
            url="https://github.com",
            title="GitHub",
            notes="Version control",
        )

        assert tab.tab_id == "1"
        assert tab.url == "https://github.com"
        assert tab.title == "GitHub"
        assert tab.notes == "Version control"
        assert tab.is_archived == 0

    def test_tab_item_to_dict(self):
        """Test converting TabItem to dict"""
        from src.app import TabItem

        tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
        result = tab.to_dict()

        assert result["id"] == "1"
        assert result["url"] == "https://github.com"
        assert "created_at" in result

    def test_tab_item_to_dict_with_tags(self):
        """Test converting TabItem to dict with tags"""
        from src.app import TabItem

        tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
        result = tab.to_dict(include_tags=True, tags=["Development"])

        assert result["tags"] == ["Development"]

    def test_tab_item_to_dynamodb_item(self):
        """Test converting TabItem to DynamoDB format"""
        from src.app import TabItem

        tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
        item = tab.to_dynamodb_item()

        assert item["entity_type"] == "tab"
        assert item["id"] == "1"

    def test_tab_item_from_dynamodb_item(self):
        """Test creating TabItem from DynamoDB item"""
        from src.app import TabItem

        dynamodb_item = {
            "entity_type": "tab",
            "id": "1",
            "url": "https://github.com",
            "title": "GitHub",
            "notes": None,
            "is_archived": 0,
            "created_at": "2026-02-15T12:34:56Z",
            "updated_at": "2026-02-15T12:34:56Z",
        }

        tab = TabItem.from_dynamodb_item(dynamodb_item)
        assert tab.tab_id == "1"


class TestTagItemModel:
    """Test TagItem model"""

    def test_tag_item_creation(self):
        """Test creating a TagItem"""
        from src.app import TagItem

        tag = TagItem(tag_id="1", name="Development")
        assert tag.tag_id == "1"
        assert tag.name == "Development"

    def test_tag_item_to_dict(self):
        """Test converting TagItem to dict"""
        from src.app import TagItem

        tag = TagItem(tag_id="1", name="Development")
        result = tag.to_dict()

        assert result["id"] == "1"
        assert result["name"] == "Development"

    def test_tag_item_to_dynamodb_item(self):
        """Test converting TagItem to DynamoDB format"""
        from src.app import TagItem

        tag = TagItem(tag_id="1", name="Development")
        item = tag.to_dynamodb_item()

        assert item["entity_type"] == "tag"
        assert item["id"] == "1"

    def test_tag_item_from_dynamodb_item(self):
        """Test creating TagItem from DynamoDB item"""
        from src.app import TagItem

        dynamodb_item = {
            "entity_type": "tag",
            "id": "1",
            "name": "Development",
            "created_at": "2026-02-15T12:34:56Z",
        }

        tag = TagItem.from_dynamodb_item(dynamodb_item)
        assert tag.tag_id == "1"
        assert tag.name == "Development"


class TestDynamoDBOperations:
    """Test DynamoDB operations"""

    def test_save_and_get_tab(self):
        """Test saving and retrieving a tab"""
        with mock_aws():
            import boto3

            from src.app import TabItem

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.create_table(
                TableName="TabManager",
                KeySchema=[
                    {"AttributeName": "entity_type", "KeyType": "HASH"},
                    {"AttributeName": "id", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "entity_type", "AttributeType": "S"},
                    {"AttributeName": "id", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
            table.put_item(Item=tab.to_dynamodb_item())

            response = table.get_item(
                Key={"entity_type": "tab", "id": "1"}
            )
            assert "Item" in response
            assert response["Item"]["url"] == "https://github.com"

    def test_delete_tab(self):
        """Test deleting a tab"""
        with mock_aws():
            import boto3

            from src.app import TabItem

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.create_table(
                TableName="TabManager",
                KeySchema=[
                    {"AttributeName": "entity_type", "KeyType": "HASH"},
                    {"AttributeName": "id", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "entity_type", "AttributeType": "S"},
                    {"AttributeName": "id", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
            table.put_item(Item=tab.to_dynamodb_item())
            table.delete_item(Key={"entity_type": "tab", "id": "1"})

            response = table.get_item(Key={"entity_type": "tab", "id": "1"})
            assert "Item" not in response

    def test_query_tabs(self):
        """Test querying all tabs"""
        with mock_aws():
            import boto3

            from src.app import TabItem

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.create_table(
                TableName="TabManager",
                KeySchema=[
                    {"AttributeName": "entity_type", "KeyType": "HASH"},
                    {"AttributeName": "id", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "entity_type", "AttributeType": "S"},
                    {"AttributeName": "id", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            tab1 = TabItem(tab_id="1", url="https://github.com", title="GitHub")
            tab2 = TabItem(tab_id="2", url="https://google.com", title="Google")

            table.put_item(Item=tab1.to_dynamodb_item())
            table.put_item(Item=tab2.to_dynamodb_item())

            response = table.query(
                KeyConditionExpression="entity_type = :et",
                ExpressionAttributeValues={":et": "tab"},
            )

            assert len(response["Items"]) == 2

    def test_update_tab_archive_status(self):
        """Test updating tab archive status"""
        with mock_aws():
            import boto3

            from src.app import TabItem

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.create_table(
                TableName="TabManager",
                KeySchema=[
                    {"AttributeName": "entity_type", "KeyType": "HASH"},
                    {"AttributeName": "id", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "entity_type", "AttributeType": "S"},
                    {"AttributeName": "id", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
            table.put_item(Item=tab.to_dynamodb_item())

            table.update_item(
                Key={"entity_type": "tab", "id": "1"},
                UpdateExpression="SET is_archived = :ia, updated_at = :ua",
                ExpressionAttributeValues={
                    ":ia": 1,
                    ":ua": datetime.utcnow().isoformat() + "Z",
                },
            )

            response = table.get_item(Key={"entity_type": "tab", "id": "1"})
            assert response["Item"]["is_archived"] == 1

    def test_save_and_query_tags(self):
        """Test saving and querying tags"""
        with mock_aws():
            import boto3

            from src.app import TagItem

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.create_table(
                TableName="TabManager",
                KeySchema=[
                    {"AttributeName": "entity_type", "KeyType": "HASH"},
                    {"AttributeName": "id", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "entity_type", "AttributeType": "S"},
                    {"AttributeName": "id", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            tag1 = TagItem(tag_id="1", name="Development")
            tag2 = TagItem(tag_id="2", name="News")

            table.put_item(Item=tag1.to_dynamodb_item())
            table.put_item(Item=tag2.to_dynamodb_item())

            response = table.query(
                KeyConditionExpression="entity_type = :et",
                ExpressionAttributeValues={":et": "tag"},
            )

            assert len(response["Items"]) == 2

    def test_tab_tag_association(self):
        """Test associating tags with tabs"""
        with mock_aws():
            import boto3

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.create_table(
                TableName="TabManager",
                KeySchema=[
                    {"AttributeName": "entity_type", "KeyType": "HASH"},
                    {"AttributeName": "id", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "entity_type", "AttributeType": "S"},
                    {"AttributeName": "id", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            item = {
                "entity_type": "tab_tag",
                "id": "1#1",
                "tab_id": "1",
                "tag_id": "1",
                "created_at": datetime.utcnow().isoformat() + "Z",
            }
            table.put_item(Item=item)

            response = table.get_item(
                Key={"entity_type": "tab_tag", "id": "1#1"}
            )
            assert "Item" in response
            assert response["Item"]["tab_id"] == "1"


class TestFlaskEndpoints:
    """Test Flask endpoints with mocked DynamoDB"""

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "tabs_stored" in data

    def test_save_tab_endpoint(self, client):
        """Test saving a tab via HTTP endpoint"""
        response = client.post(
            "/api/tabs",
            json={"url": "https://github.com", "title": "GitHub"},
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.get_json()
        assert "id" in data
        assert data["status"] == "saved"
        assert data["url"] == "https://github.com"
        assert data["title"] == "GitHub"

    def test_save_tab_missing_url(self, client):
        """Test saving a tab without URL fails"""
        response = client.post(
            "/api/tabs",
            json={"title": "GitHub"},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_save_tab_missing_title(self, client):
        """Test saving a tab without title fails"""
        response = client.post(
            "/api/tabs",
            json={"url": "https://github.com"},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_get_tabs_endpoint(self, client):
        """Test getting all tabs"""
        from src.app import TabItem

        import src.app as app_module

        tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
        app_module.table.put_item(Item=tab.to_dynamodb_item())

        response = client.get("/api/tabs")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_get_tabs_archived(self, client):
        """Test getting archived tabs"""
        from src.app import TabItem

        import src.app as app_module

        tab = TabItem(tab_id="1", url="https://github.com", title="GitHub", is_archived=1)
        app_module.table.put_item(Item=tab.to_dynamodb_item())

        response = client.get("/api/tabs?archived=true")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_get_single_tab(self, client):
        """Test getting a single tab"""
        from src.app import TabItem

        import src.app as app_module

        tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
        app_module.table.put_item(Item=tab.to_dynamodb_item())

        response = client.get("/api/tabs/1")
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == "1"
        assert data["url"] == "https://github.com"
        assert "tags" in data

    def test_get_nonexistent_tab(self, client):
        """Test getting a tab that doesn't exist"""
        response = client.get("/api/tabs/nonexistent")
        assert response.status_code == 404

    def test_delete_tab(self, client):
        """Test deleting a tab"""
        from src.app import TabItem

        import src.app as app_module

        tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
        app_module.table.put_item(Item=tab.to_dynamodb_item())

        response = client.delete("/api/tabs/1")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "deleted"

    def test_delete_nonexistent_tab(self, client):
        """Test deleting a tab that doesn't exist"""
        response = client.delete("/api/tabs/nonexistent")
        assert response.status_code == 404

    def test_archive_tab(self, client):
        """Test archiving a tab"""
        from src.app import TabItem

        import src.app as app_module

        tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
        app_module.table.put_item(Item=tab.to_dynamodb_item())

        response = client.put(
            "/api/tabs/1/archive",
            json={"archived": True},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["archived"] is True

    def test_unarchive_tab(self, client):
        """Test unarchiving a tab"""
        from src.app import TabItem

        import src.app as app_module

        tab = TabItem(tab_id="1", url="https://github.com", title="GitHub", is_archived=1)
        app_module.table.put_item(Item=tab.to_dynamodb_item())

        response = client.put(
            "/api/tabs/1/archive",
            json={"archived": False},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["archived"] is False

    def test_archive_nonexistent_tab(self, client):
        """Test archiving a tab that doesn't exist"""
        response = client.put(
            "/api/tabs/nonexistent/archive",
            json={"archived": True},
            content_type="application/json",
        )
        assert response.status_code == 404

    def test_get_stats(self, client):
        """Test getting statistics"""
        from src.app import TabItem

        import src.app as app_module

        tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
        app_module.table.put_item(Item=tab.to_dynamodb_item())

        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.get_json()
        assert data["active_tabs"] == 1
        assert data["archived_tabs"] == 0
        assert "total_tags" in data

    def test_api_documentation(self, client):
        """Test API documentation endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.get_json()
        assert "name" in data
        assert "endpoints" in data


class TestTagEndpoints:
    """Test tag-related endpoints"""

    def test_get_tags_empty(self, client):
        """Test getting tags when none exist"""
        response = client.get("/api/tags")
        assert response.status_code == 200
        data = response.get_json()
        assert data == []

    def test_add_tag_to_tab(self, client):
        """Test adding a tag to a tab"""
        from src.app import TabItem

        import src.app as app_module

        tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
        app_module.table.put_item(Item=tab.to_dynamodb_item())

        response = client.post(
            "/api/tabs/1/tags",
            json={"tag": "Development"},
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["status"] == "tagged"
        assert data["tag"] == "Development"

    def test_add_tag_to_nonexistent_tab(self, client):
        """Test adding a tag to a tab that doesn't exist"""
        response = client.post(
            "/api/tabs/nonexistent/tags",
            json={"tag": "Development"},
            content_type="application/json",
        )
        assert response.status_code == 404

    def test_add_empty_tag(self, client):
        """Test adding an empty tag fails"""
        from src.app import TabItem

        import src.app as app_module

        tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
        app_module.table.put_item(Item=tab.to_dynamodb_item())

        response = client.post(
            "/api/tabs/1/tags",
            json={"tag": ""},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_add_existing_tag_to_tab(self, client):
        """Test adding a tag that already exists reuses it"""
        from src.app import TabItem, TagItem

        import src.app as app_module

        tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
        app_module.table.put_item(Item=tab.to_dynamodb_item())

        tag = TagItem(tag_id="tag-1", name="Development")
        app_module.table.put_item(Item=tag.to_dynamodb_item())

        response = client.post(
            "/api/tabs/1/tags",
            json={"tag": "Development"},
            content_type="application/json",
        )
        assert response.status_code == 201

    def test_remove_tag_from_tab(self, client):
        """Test removing a tag from a tab"""
        from src.app import TabItem, TagItem

        import src.app as app_module

        tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
        app_module.table.put_item(Item=tab.to_dynamodb_item())

        tag = TagItem(tag_id="tag-1", name="Development")
        app_module.table.put_item(Item=tag.to_dynamodb_item())

        app_module.table.put_item(Item={
            "entity_type": "tab_tag",
            "id": "1#tag-1",
            "tab_id": "1",
            "tag_id": "tag-1",
            "created_at": "2026-01-01T00:00:00Z",
        })

        response = client.delete("/api/tabs/1/tags/Development")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "untagged"

    def test_remove_tag_from_nonexistent_tab(self, client):
        """Test removing a tag from a tab that doesn't exist"""
        response = client.delete("/api/tabs/nonexistent/tags/Development")
        assert response.status_code == 404

    def test_get_tags_after_adding(self, client):
        """Test getting tags after adding one"""
        from src.app import TagItem

        import src.app as app_module

        tag = TagItem(tag_id="tag-1", name="Development")
        app_module.table.put_item(Item=tag.to_dynamodb_item())

        response = client.get("/api/tags")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["name"] == "Development"

    def test_get_single_tab_with_tags(self, client):
        """Test getting a single tab includes its tags"""
        from src.app import TabItem, TagItem

        import src.app as app_module

        tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
        app_module.table.put_item(Item=tab.to_dynamodb_item())

        tag = TagItem(tag_id="tag-1", name="Development")
        app_module.table.put_item(Item=tag.to_dynamodb_item())

        app_module.table.put_item(Item={
            "entity_type": "tab_tag",
            "id": "1#tag-1",
            "tab_id": "1",
            "tag_id": "tag-1",
            "created_at": "2026-01-01T00:00:00Z",
        })

        response = client.get("/api/tabs/1")
        assert response.status_code == 200
        data = response.get_json()
        assert "tags" in data
        assert "Development" in data["tags"]


class TestSearchEndpoints:
    """Test search endpoint"""

    def test_search_too_short(self, client):
        """Test search with too short query"""
        response = client.get("/api/search?q=a")
        assert response.status_code == 400

    def test_search_empty(self, client):
        """Test search with empty query"""
        response = client.get("/api/search?q=")
        assert response.status_code == 400

    def test_search_by_name(self, client):
        """Test searching tabs by name"""
        from src.app import TabItem

        import src.app as app_module

        tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
        app_module.table.put_item(Item=tab.to_dynamodb_item())

        response = client.get("/api/search?q=github&type=name")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["id"] == "1"

    def test_search_by_tag(self, client):
        """Test searching tabs by tag"""
        from src.app import TabItem, TagItem

        import src.app as app_module

        tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
        app_module.table.put_item(Item=tab.to_dynamodb_item())

        tag = TagItem(tag_id="tag-1", name="development")
        app_module.table.put_item(Item=tag.to_dynamodb_item())

        app_module.table.put_item(Item={
            "entity_type": "tab_tag",
            "id": "1#tag-1",
            "tab_id": "1",
            "tag_id": "tag-1",
            "created_at": "2026-01-01T00:00:00Z",
        })

        response = client.get("/api/search?q=dev&type=tag")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1

    def test_search_all(self, client):
        """Test searching tabs with type=all"""
        from src.app import TabItem

        import src.app as app_module

        tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
        app_module.table.put_item(Item=tab.to_dynamodb_item())

        response = client.get("/api/search?q=github&type=all")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1

    def test_search_no_results(self, client):
        """Test search with no matching results"""
        response = client.get("/api/search?q=nonexistent&type=name")
        assert response.status_code == 200
        data = response.get_json()
        assert data == []


class TestDatabaseHelpers:
    """Test database helper functions"""

    def test_get_next_id(self):
        """Test that get_next_id returns a UUID string"""
        from src.app import get_next_id

        id1 = get_next_id("tab")
        id2 = get_next_id("tab")
        assert isinstance(id1, str)
        assert id1 != id2

    def test_save_and_get_tab_functions(self, app):
        """Test save_tab and get_tab functions"""
        from src.app import TabItem, get_tab, save_tab

        tab = TabItem(tab_id="test-1", url="https://example.com", title="Example")
        save_tab(tab)

        result = get_tab("test-1")
        assert result is not None
        assert result.url == "https://example.com"

    def test_get_tab_not_found(self, app):
        """Test get_tab returns None for missing tab"""
        from src.app import get_tab

        result = get_tab("nonexistent")
        assert result is None

    def test_delete_tab_function(self, app):
        """Test delete_tab function"""
        from src.app import TabItem, delete_tab, get_tab, save_tab

        tab = TabItem(tab_id="test-1", url="https://example.com", title="Example")
        save_tab(tab)
        delete_tab("test-1")

        result = get_tab("test-1")
        assert result is None

    def test_get_all_tabs_function(self, app):
        """Test get_all_tabs function"""
        from src.app import TabItem, get_all_tabs, save_tab

        tab1 = TabItem(tab_id="1", url="https://github.com", title="GitHub")
        tab2 = TabItem(tab_id="2", url="https://google.com", title="Google", is_archived=1)
        save_tab(tab1)
        save_tab(tab2)

        active = get_all_tabs(archived=False)
        archived = get_all_tabs(archived=True)
        assert len(active) == 1
        assert len(archived) == 1

    def test_update_tab_archive_status_function(self, app):
        """Test update_tab_archive_status function"""
        from src.app import TabItem, get_tab, save_tab, update_tab_archive_status

        tab = TabItem(tab_id="1", url="https://github.com", title="GitHub")
        save_tab(tab)
        update_tab_archive_status("1", 1)

        result = get_tab("1")
        assert result.is_archived == 1

    def test_tag_operations(self, app):
        """Test tag save and retrieval functions"""
        from src.app import TagItem, get_all_tags, get_tag_by_name, save_tag

        tag = TagItem(tag_id="tag-1", name="Development")
        save_tag(tag)

        result = get_tag_by_name("Development")
        assert result is not None
        assert result.name == "Development"

        all_tags = get_all_tags()
        assert len(all_tags) == 1

    def test_get_tag_by_name_not_found(self, app):
        """Test get_tag_by_name returns None for missing tag"""
        from src.app import get_tag_by_name

        result = get_tag_by_name("nonexistent")
        assert result is None

    def test_tab_tag_association_functions(self, app):
        """Test add_tab_tag, get_tab_tags, get_tabs_by_tag, remove_tab_tag"""
        from src.app import (
            add_tab_tag,
            get_tab_tags,
            get_tabs_by_tag,
            remove_tab_tag,
        )

        add_tab_tag("tab-1", "tag-1")

        tab_tags = get_tab_tags("tab-1")
        assert "tag-1" in tab_tags

        tabs = get_tabs_by_tag("tag-1")
        assert "tab-1" in tabs

        remove_tab_tag("tab-1", "tag-1")
        tab_tags = get_tab_tags("tab-1")
        assert "tag-1" not in tab_tags


class TestLambdaHandler:
    """Test Lambda handler"""

    def test_lambda_handler_get(self, app):
        """Test lambda_handler with GET request"""
        from src.app import lambda_handler

        event = {
            "path": "/",
            "httpMethod": "GET",
            "headers": {"Content-Type": "application/json"},
            "body": "",
        }

        result = lambda_handler(event, None)
        assert result["statusCode"] == 200
        assert "Content-Type" in result["headers"]

    def test_lambda_handler_health(self, app):
        """Test lambda_handler with health endpoint"""
        from src.app import lambda_handler

        event = {
            "path": "/api/health",
            "httpMethod": "GET",
            "headers": {},
            "body": "",
        }

        result = lambda_handler(event, None)
        assert result["statusCode"] == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src", "--cov-fail-under=80"])
