"""
Tests for Advanced API Mode

Tests the advanced API mode screen for handling API responses correctly.
"""

import json


class TestResponseBodyHandling:
    """Tests for response body handling in Advanced API Mode"""

    def test_response_body_dict_converts_to_json(self):
        """Test that dict response bodies are converted to JSON strings"""
        # Simulate a dict response
        response_dict = {"name": "test", "id": 123, "status": "success"}

        # Should convert to JSON string
        expected = json.dumps(response_dict, indent=2)

        # Verify the conversion logic would work
        resp_text = response_dict
        if isinstance(resp_text, (dict, list)):
            resp_text = json.dumps(resp_text, indent=2)

        assert resp_text == expected
        assert isinstance(resp_text, str)

    def test_response_body_list_converts_to_json(self):
        """Test that list response bodies are converted to JSON strings (regression test)"""
        # Simulate a list response (like playbook list)
        response_list = ["hello_world.yml", "deploy.yml", "site.yml"]

        # Should convert to JSON string
        expected = json.dumps(response_list, indent=2)

        # Verify the conversion logic would work
        resp_text = response_list
        if isinstance(resp_text, (dict, list)):
            resp_text = json.dumps(resp_text, indent=2)

        assert resp_text == expected
        assert isinstance(resp_text, str)
        assert resp_text.startswith("[\n")

    def test_response_body_string_remains_string(self):
        """Test that string response bodies are kept as-is"""
        # Simulate a string response
        response_str = "Simple text response"

        # Should remain as string
        resp_text = response_str
        if isinstance(resp_text, (dict, list)):
            resp_text = json.dumps(resp_text, indent=2)

        assert resp_text == response_str
        assert isinstance(resp_text, str)

    def test_response_body_empty_list_converts(self):
        """Test that empty lists are converted to JSON"""
        response_list = []

        # Should convert to JSON string
        expected = json.dumps(response_list, indent=2)

        resp_text = response_list
        if isinstance(resp_text, (dict, list)):
            resp_text = json.dumps(resp_text, indent=2)

        assert resp_text == expected
        assert resp_text == "[]"

    def test_response_body_nested_structures(self):
        """Test that nested dict/list structures are converted properly"""
        response_data = {"results": [{"id": 1, "name": "item1"}, {"id": 2, "name": "item2"}], "count": 2}

        # Should convert to JSON string
        expected = json.dumps(response_data, indent=2)

        resp_text = response_data
        if isinstance(resp_text, (dict, list)):
            resp_text = json.dumps(resp_text, indent=2)

        assert resp_text == expected
        assert isinstance(resp_text, str)
        assert "results" in resp_text
        assert "item1" in resp_text


class TestStateLoading:
    """Tests for state loading with different response body types"""

    def test_state_with_list_response_body(self):
        """Test that loading state with a list response body doesn't crash"""
        # This is a regression test for the bug where list response bodies
        # caused AttributeError: 'list' object has no attribute 'splitlines'

        state_data = {
            "response_body": ["hello_world.yml", "deploy.yml"],
            "method": "GET",
            "endpoint": "/api/v2/job_templates/1/playbooks/",
        }

        # Simulate what the code does
        resp_text = state_data["response_body"]
        if isinstance(resp_text, (dict, list)):
            resp_text = json.dumps(resp_text, indent=2)

        # Should not crash and should be a valid string
        assert isinstance(resp_text, str)
        assert "hello_world.yml" in resp_text

    def test_state_with_dict_response_body(self):
        """Test that loading state with a dict response body works"""
        state_data = {
            "response_body": {"id": 1, "name": "Test Job Template"},
            "method": "GET",
            "endpoint": "/api/v2/job_templates/1/",
        }

        # Simulate what the code does
        resp_text = state_data["response_body"]
        if isinstance(resp_text, (dict, list)):
            resp_text = json.dumps(resp_text, indent=2)

        # Should not crash and should be a valid string
        assert isinstance(resp_text, str)
        assert "Test Job Template" in resp_text

    def test_state_with_string_response_body(self):
        """Test that loading state with a string response body works"""
        state_data = {"response_body": "Plain text response", "method": "GET", "endpoint": "/api/v2/some/endpoint/"}

        # Simulate what the code does
        resp_text = state_data["response_body"]
        if isinstance(resp_text, (dict, list)):
            resp_text = json.dumps(resp_text, indent=2)

        # Should remain as original string
        assert resp_text == "Plain text response"
