"""
Tests for Ansible AWX Collection Mapper

Verifies correct mapping from AWX API data to awx.awx Ansible module YAML tasks.
"""

import pytest
import yaml


@pytest.fixture
def minimal_job_template_data():
    """Minimal job template data with only required fields"""
    return {
        "name": "Test Job Template",
        "job_type": "run",
        "inventory_name": "Test Inventory",
        "project_name": "Test Project",
        "playbook": "site.yml",
    }


@pytest.fixture
def full_job_template_data():
    """Complete job template data with all fields"""
    return {
        "name": "Full Job Template",
        "description": "A comprehensive test template",
        "job_type": "run",
        "inventory": 1,
        "inventory_name": "Production Inventory",
        "project": 2,
        "project_name": "Demo Project",
        "playbook": "playbooks/deploy.yml",
        "execution_environment": 3,
        "execution_environment_name": "Default EE",
        "credentials": [4, 5],
        "credential_names": ["SSH Key", "Vault Password"],
        "forks": 10,
        "job_slice_count": 4,
        "timeout": 300,
        "verbosity": 2,
        "limit": "webservers",
        "extra_vars": {"env": "production", "debug": False},
        "become_enabled": True,
        "allow_simultaneous": True,
        "use_fact_cache": False,
        "ask_inventory_on_launch": True,
        "ask_forks_on_launch": True,
    }


@pytest.fixture
def job_template_with_ids_only():
    """Job template with IDs but no names (testing placeholder generation)"""
    return {
        "name": "ID Only Template",
        "job_type": "run",
        "inventory": 100,
        "project": 200,
        "playbook": "test.yml",
        "execution_environment": 300,
        "credentials": [400, 401],
    }


@pytest.fixture
def minimal_project_data():
    """Minimal project data"""
    return {
        "name": "Test Project",
        "organization_name": "Default",
        "scm_type": "git",
        "scm_url": "https://github.com/example/repo.git",
    }


@pytest.fixture
def full_project_data():
    """Complete project data"""
    return {
        "name": "Full Project",
        "description": "A comprehensive test project",
        "organization": 1,
        "organization_name": "Engineering",
        "scm_type": "git",
        "scm_url": "https://github.com/example/ansible-playbooks.git",
        "scm_branch": "main",
        "credential": 5,
        "credential_name": "GitHub Token",
        "scm_update_on_launch": True,
        "scm_delete_on_update": False,
        "scm_clean": True,
        "default_environment": 2,
        "default_environment_name": "Python 3.9 EE",
    }


class TestJobTemplateMapper:
    """Tests for job_template_to_ansible_task function"""

    def test_minimal_job_template_generates_valid_yaml(self, minimal_job_template_data):
        """Test that minimal required fields generate valid YAML"""
        from awx_tui.utils.ansible_mapper import job_template_to_ansible_task

        yaml_str, notes = job_template_to_ansible_task(minimal_job_template_data)

        # Should start with 2-space indent
        assert yaml_str.startswith("  - name:")

        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())

        # Should be valid YAML
        task_list = yaml.safe_load(unindented)
        assert isinstance(task_list, list)
        assert len(task_list) == 1

        task = task_list[0]
        assert "name" in task
        assert "awx.awx.job_template" in task

        # Task name should be idempotent: "Ensure job template X exists"
        assert task["name"] == "Ensure job template Test Job Template exists"

        params = task["awx.awx.job_template"]
        assert params["name"] == "Test Job Template"
        assert params["job_type"] == "run"
        assert params["inventory"] == "Test Inventory"
        assert params["project"] == "Test Project"
        assert params["playbook"] == "site.yml"
        assert params["state"] == "present"

    def test_full_job_template_includes_all_fields(self, full_job_template_data):
        """Test that all provided fields are included in output"""
        import json

        from awx_tui.utils.ansible_mapper import job_template_to_ansible_task

        yaml_str, notes = job_template_to_ansible_task(full_job_template_data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)
        params = task_list[0]["awx.awx.job_template"]

        # Check all fields are present
        assert params["name"] == "Full Job Template"
        assert params["description"] == "A comprehensive test template"
        assert params["inventory"] == "Production Inventory"
        assert params["project"] == "Demo Project"
        assert params["playbook"] == "playbooks/deploy.yml"
        assert params["execution_environment"] == "Default EE"
        assert params["credentials"] == ["SSH Key", "Vault Password"]
        assert params["forks"] == 10
        assert params["job_slice_count"] == 4
        assert params["timeout"] == 300
        assert params["verbosity"] == 2
        assert params["limit"] == "webservers"

        # extra_vars should be a JSON string
        assert isinstance(params["extra_vars"], str)
        parsed_vars = json.loads(params["extra_vars"])
        assert parsed_vars == {"env": "production", "debug": False}

        assert params["become_enabled"] is True
        assert params["allow_simultaneous"] is True
        assert params["ask_inventory_on_launch"] is True
        assert params["ask_forks_on_launch"] is True

        # use_fact_cache should not be present (it's False, so omitted)
        assert "use_fact_cache" not in params

    def test_job_template_with_ids_generates_placeholders(self, job_template_with_ids_only):
        """Test that IDs without names generate placeholder strings"""
        from awx_tui.utils.ansible_mapper import job_template_to_ansible_task

        yaml_str, notes = job_template_to_ansible_task(job_template_with_ids_only)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)
        params = task_list[0]["awx.awx.job_template"]

        # Should have placeholders
        assert params["inventory"] == "<inventory_id_100>"
        assert params["project"] == "<project_id_200>"
        assert params["execution_environment"] == "<ee_id_300>"
        assert params["credentials"] == ["<credential_id_400>", "<credential_id_401>"]

        # Should have notes about replacing placeholders
        assert len(notes) > 0
        assert any("inventory_id_100" in note for note in notes)
        assert any("project_id_200" in note for note in notes)
        assert any("credential" in note.lower() for note in notes)

    def test_custom_task_name(self, minimal_job_template_data):
        """Test custom task name parameter"""
        from awx_tui.utils.ansible_mapper import job_template_to_ansible_task

        custom_name = "Deploy Production Application"
        yaml_str, notes = job_template_to_ansible_task(minimal_job_template_data, task_name=custom_name)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        assert task_list[0]["name"] == custom_name

    def test_blank_template_name_gives_generic_task_name(self):
        """Test that blank template name results in generic idempotent task name"""
        from awx_tui.utils.ansible_mapper import job_template_to_ansible_task

        data = {
            "name": "",  # Blank name
            "job_type": "run",
            "inventory_name": "Test Inv",
            "project_name": "Test Proj",
            "playbook": "test.yml",
        }

        yaml_str, notes = job_template_to_ansible_task(data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        # Task name should be generic idempotent form
        assert task_list[0]["name"] == "Ensure job template exists"

    def test_state_parameter_can_be_excluded(self, minimal_job_template_data):
        """Test that state parameter can be excluded"""
        from awx_tui.utils.ansible_mapper import job_template_to_ansible_task

        yaml_str, notes = job_template_to_ansible_task(minimal_job_template_data, include_state=False)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)
        params = task_list[0]["awx.awx.job_template"]

        assert "state" not in params

    def test_empty_optional_fields_are_omitted(self):
        """Test that empty/null optional fields are not included"""
        from awx_tui.utils.ansible_mapper import job_template_to_ansible_task

        data = {
            "name": "Test",
            "job_type": "run",
            "inventory_name": "Test Inv",
            "project_name": "Test Proj",
            "playbook": "test.yml",
            "description": "",  # Empty string
            "forks": None,  # None
            "timeout": 0,  # Zero (should be omitted)
            "limit": "",  # Empty
        }

        yaml_str, notes = job_template_to_ansible_task(data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)
        params = task_list[0]["awx.awx.job_template"]

        # These should not be in output
        assert "description" not in params
        assert "forks" not in params
        assert "timeout" not in params
        assert "limit" not in params

    def test_numeric_strings_are_converted(self):
        """Test that numeric strings are converted to integers"""
        from awx_tui.utils.ansible_mapper import job_template_to_ansible_task

        data = {
            "name": "Test",
            "job_type": "run",
            "inventory_name": "Test Inv",
            "project_name": "Test Proj",
            "playbook": "test.yml",
            "forks": "15",  # String
            "job_slice_count": "3",  # String
            "timeout": "600",  # String
            "verbosity": "1",  # String
        }

        yaml_str, notes = job_template_to_ansible_task(data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)
        params = task_list[0]["awx.awx.job_template"]

        # Should be integers, not strings
        assert params["forks"] == 15
        assert params["job_slice_count"] == 3
        assert params["timeout"] == 600
        assert params["verbosity"] == 1

    def test_extra_vars_yaml_string_converted_to_json(self):
        """Test that extra_vars as YAML string gets converted to JSON"""
        import json

        from awx_tui.utils.ansible_mapper import job_template_to_ansible_task

        # AWX API sometimes returns extra_vars as YAML string
        data = {
            "name": "Test Template",
            "job_type": "run",
            "inventory_name": "Test",
            "project_name": "Test",
            "playbook": "test.yml",
            "extra_vars": "---\nkey1: value1\nkey2: value2\nnested:\n  foo: bar\n",  # YAML string
        }

        yaml_str, notes = job_template_to_ansible_task(data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        params = task_list[0]["awx.awx.job_template"]

        # extra_vars should be converted to JSON string
        assert "extra_vars" in params
        assert isinstance(params["extra_vars"], str)

        # Should be valid JSON
        extra_vars_parsed = json.loads(params["extra_vars"])
        assert extra_vars_parsed["key1"] == "value1"
        assert extra_vars_parsed["key2"] == "value2"
        assert extra_vars_parsed["nested"]["foo"] == "bar"

    def test_extra_vars_dict_converted_to_json(self):
        """Test that extra_vars dict is converted to JSON string"""
        import json

        from awx_tui.utils.ansible_mapper import job_template_to_ansible_task

        data = {
            "name": "Test",
            "job_type": "run",
            "inventory_name": "Test Inv",
            "project_name": "Test Proj",
            "playbook": "test.yml",
            "extra_vars": {
                "var1": "value1",
                "var2": 42,
                "var3": ["list", "items"],
                "var4": {"nested": "dict"},
            },
        }

        yaml_str, notes = job_template_to_ansible_task(data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)
        params = task_list[0]["awx.awx.job_template"]

        # extra_vars should be a JSON string, not a dict
        assert isinstance(params["extra_vars"], str)
        # Parse the JSON to verify it matches original
        parsed_vars = json.loads(params["extra_vars"])
        assert parsed_vars == data["extra_vars"]

    def test_extra_vars_yaml_string_converted(self):
        """Test that extra_vars YAML string is converted to JSON"""
        import json

        from awx_tui.utils.ansible_mapper import job_template_to_ansible_task

        vars_string = "---\nkey: value\nanother: thing"
        data = {
            "name": "Test",
            "job_type": "run",
            "inventory_name": "Test Inv",
            "project_name": "Test Proj",
            "playbook": "test.yml",
            "extra_vars": vars_string,
        }

        yaml_str, notes = job_template_to_ansible_task(data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)
        params = task_list[0]["awx.awx.job_template"]

        # YAML string should be converted to JSON
        assert "extra_vars" in params
        extra_vars_parsed = json.loads(params["extra_vars"])
        assert extra_vars_parsed["key"] == "value"
        assert extra_vars_parsed["another"] == "thing"


class TestProjectMapper:
    """Tests for project_to_ansible_task function"""

    def test_minimal_project_generates_valid_yaml(self, minimal_project_data):
        """Test that minimal project data generates valid YAML"""
        from awx_tui.utils.ansible_mapper import project_to_ansible_task

        yaml_str, notes = project_to_ansible_task(minimal_project_data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        assert isinstance(task_list, list)
        task = task_list[0]

        # Task name should be idempotent
        assert task["name"] == "Ensure project Test Project exists"

        params = task["awx.awx.project"]
        assert params["name"] == "Test Project"
        assert params["organization"] == "Default"
        assert params["scm_type"] == "git"
        assert params["scm_url"] == "https://github.com/example/repo.git"
        assert params["state"] == "present"

    def test_full_project_includes_all_fields(self, full_project_data):
        """Test that all project fields are included"""
        from awx_tui.utils.ansible_mapper import project_to_ansible_task

        yaml_str, notes = project_to_ansible_task(full_project_data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)
        params = task_list[0]["awx.awx.project"]

        assert params["name"] == "Full Project"
        assert params["description"] == "A comprehensive test project"
        assert params["organization"] == "Engineering"
        assert params["scm_url"] == "https://github.com/example/ansible-playbooks.git"
        assert params["scm_branch"] == "main"
        assert params["scm_credential"] == "GitHub Token"
        assert params["scm_update_on_launch"] is True
        assert params["scm_clean"] is True
        assert params["default_environment"] == "Python 3.9 EE"

        # False value should be omitted
        assert "scm_delete_on_update" not in params

    def test_project_with_ids_generates_placeholders(self):
        """Test that project IDs generate placeholders"""
        from awx_tui.utils.ansible_mapper import project_to_ansible_task

        data = {
            "name": "Test Project",
            "organization": 99,
            "scm_type": "git",
            "scm_url": "https://example.com/repo.git",
            "credential": 88,
            "default_environment": 77,
        }

        yaml_str, notes = project_to_ansible_task(data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)
        params = task_list[0]["awx.awx.project"]

        assert params["organization"] == "<org_id_99>"
        assert params["scm_credential"] == "<credential_id_88>"
        assert params["default_environment"] == "<ee_id_77>"

        # Should have notes
        assert len(notes) > 0
        assert any("org_id_99" in note for note in notes)

    def test_project_custom_task_name(self, minimal_project_data):
        """Test custom task name for project"""
        from awx_tui.utils.ansible_mapper import project_to_ansible_task

        yaml_str, notes = project_to_ansible_task(minimal_project_data, task_name="Configure Git Project")
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        assert task_list[0]["name"] == "Configure Git Project"

    def test_blank_project_name_gives_generic_task_name(self):
        """Test that blank project name results in generic idempotent task name"""
        from awx_tui.utils.ansible_mapper import project_to_ansible_task

        data = {
            "name": "",  # Blank name
            "organization_name": "Default",
            "scm_type": "git",
            "scm_url": "https://github.com/example/repo.git",
        }

        yaml_str, notes = project_to_ansible_task(data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        # Task name should be generic idempotent form
        assert task_list[0]["name"] == "Ensure project exists"


class TestYAMLOutput:
    """Tests for YAML output format and quality"""

    def test_yaml_is_properly_formatted(self, minimal_job_template_data):
        """Test that generated YAML is well-formatted"""
        from awx_tui.utils.ansible_mapper import job_template_to_ansible_task

        yaml_str, notes = job_template_to_ansible_task(minimal_job_template_data)

        # Should be indented by 2 spaces
        assert yaml_str.startswith("  - name:")
        assert "  awx.awx.job_template:" in yaml_str
        assert "    state: present" in yaml_str

        # Should not use flow style (no {})
        assert "{" not in yaml_str
        assert "}" not in yaml_str

    def test_yaml_indentation_two_spaces(self, minimal_job_template_data):
        """Test that YAML is indented by 2 spaces for placement under tasks:"""
        from awx_tui.utils.ansible_mapper import job_template_to_ansible_task

        yaml_str, notes = job_template_to_ansible_task(minimal_job_template_data)

        # Every line should start with 2 spaces (or be blank)
        for line in yaml_str.splitlines():
            if line.strip():  # Non-empty lines
                assert line.startswith("  "), f"Line not indented: {line}"

    def test_yaml_custom_indentation(self, minimal_job_template_data):
        """Test that custom indentation works"""
        from awx_tui.utils.ansible_mapper import job_template_to_ansible_task

        # Test 4-space indentation
        yaml_str, notes = job_template_to_ansible_task(minimal_job_template_data, indent=4)

        # Every line should start with 4 spaces (or be blank)
        for line in yaml_str.splitlines():
            if line.strip():  # Non-empty lines
                assert line.startswith("    "), f"Line not indented by 4: {line}"

        # Test no indentation
        yaml_str_no_indent, notes = job_template_to_ansible_task(minimal_job_template_data, indent=0)

        # First line should start with "- name:" (no indent)
        assert yaml_str_no_indent.startswith("- name:")

    def test_yaml_preserves_unicode(self):
        """Test that unicode characters are preserved"""
        from awx_tui.utils.ansible_mapper import job_template_to_ansible_task

        data = {
            "name": "Déployment Jøb Témplate",
            "description": "Unicode test: 你好, мир, 🚀",
            "job_type": "run",
            "inventory_name": "Test",
            "project_name": "Test",
            "playbook": "test.yml",
        }

        yaml_str, notes = job_template_to_ansible_task(data)

        # Unicode should be preserved, not escaped
        assert "Déployment" in yaml_str
        assert "你好" in yaml_str
        assert "🚀" in yaml_str


class TestInventoryMapper:
    """Tests for inventory_to_ansible_task() function"""

    @pytest.fixture
    def minimal_inventory_data(self):
        """Minimal valid inventory data"""
        return {
            "name": "Test Inventory",
            "organization_name": "Default",
        }

    @pytest.fixture
    def full_inventory_data(self):
        """Full inventory data with all optional fields"""
        return {
            "name": "Production Inventory",
            "description": "Production servers inventory",
            "organization_name": "Production Org",
            "variables": {"ansible_connection": "ssh", "env": "prod"},
        }

    def test_minimal_inventory(self, minimal_inventory_data):
        """Test minimal inventory conversion"""
        from awx_tui.utils.ansible_mapper import inventory_to_ansible_task

        yaml_str, notes = inventory_to_ansible_task(minimal_inventory_data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        assert len(task_list) == 1
        task = task_list[0]
        assert task["name"] == "Ensure inventory Test Inventory exists"

        params = task["awx.awx.inventory"]
        assert params["name"] == "Test Inventory"
        assert params["organization"] == "Default"
        assert params["state"] == "present"
        assert len(notes) == 0

    def test_full_inventory(self, full_inventory_data):
        """Test full inventory with all fields"""
        import json

        from awx_tui.utils.ansible_mapper import inventory_to_ansible_task

        yaml_str, notes = inventory_to_ansible_task(full_inventory_data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        params = task_list[0]["awx.awx.inventory"]
        assert params["name"] == "Production Inventory"
        assert params["description"] == "Production servers inventory"
        assert params["organization"] == "Production Org"

        # Variables should be JSON string
        assert isinstance(params["variables"], str)
        vars_dict = json.loads(params["variables"])
        assert vars_dict["ansible_connection"] == "ssh"
        assert vars_dict["env"] == "prod"

    def test_inventory_with_org_id(self):
        """Test inventory with organization ID instead of name"""
        from awx_tui.utils.ansible_mapper import inventory_to_ansible_task

        data = {
            "name": "Test Inventory",
            "organization": 5,  # ID only
        }

        yaml_str, notes = inventory_to_ansible_task(data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        params = task_list[0]["awx.awx.inventory"]
        assert params["organization"] == "<org_id_5>"

        # Should have note about replacing placeholder
        assert len(notes) > 0
        assert any("org_id_5" in note for note in notes)

    def test_inventory_variables_as_string(self):
        """Test inventory with variables as JSON string"""

        from awx_tui.utils.ansible_mapper import inventory_to_ansible_task

        data = {
            "name": "Test Inventory",
            "organization_name": "Default",
            "variables": '{"key": "value"}',  # JSON string
        }

        yaml_str, notes = inventory_to_ansible_task(data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        params = task_list[0]["awx.awx.inventory"]
        # Should keep string as-is
        assert params["variables"] == '{"key": "value"}'

    def test_inventory_custom_task_name(self, minimal_inventory_data):
        """Test custom task name for inventory"""
        from awx_tui.utils.ansible_mapper import inventory_to_ansible_task

        yaml_str, notes = inventory_to_ansible_task(minimal_inventory_data, task_name="Configure Production Inventory")
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        assert task_list[0]["name"] == "Configure Production Inventory"

    def test_blank_inventory_name_gives_generic_task_name(self):
        """Test that blank inventory name results in generic idempotent task name"""
        from awx_tui.utils.ansible_mapper import inventory_to_ansible_task

        data = {
            "name": "",  # Blank name
            "organization_name": "Default",
        }

        yaml_str, notes = inventory_to_ansible_task(data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        # Task name should be generic idempotent form
        assert task_list[0]["name"] == "Ensure inventory exists"


class TestHostMapper:
    """Tests for host_to_ansible_task() function"""

    @pytest.fixture
    def minimal_host_data(self):
        """Minimal valid host data"""
        return {
            "name": "web01.example.com",
            "inventory_name": "Production",
        }

    @pytest.fixture
    def full_host_data(self):
        """Full host data with all optional fields"""
        return {
            "name": "web01.example.com",
            "description": "Production web server 01",
            "inventory_name": "Production",
            "enabled": True,
            "variables": {"ansible_host": "192.168.1.10", "ansible_user": "deploy"},  # NOSONAR
        }

    def test_minimal_host(self, minimal_host_data):
        """Test minimal host conversion"""
        from awx_tui.utils.ansible_mapper import host_to_ansible_task

        yaml_str, notes = host_to_ansible_task(minimal_host_data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        assert len(task_list) == 1
        task = task_list[0]
        assert task["name"] == "Ensure host web01.example.com exists"

        params = task["awx.awx.host"]
        assert params["name"] == "web01.example.com"
        assert params["inventory"] == "Production"
        assert params["state"] == "present"
        assert len(notes) == 0

    def test_full_host(self, full_host_data):
        """Test full host with all fields"""
        import json

        from awx_tui.utils.ansible_mapper import host_to_ansible_task

        yaml_str, notes = host_to_ansible_task(full_host_data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        params = task_list[0]["awx.awx.host"]
        assert params["name"] == "web01.example.com"
        assert params["description"] == "Production web server 01"
        assert params["inventory"] == "Production"

        # Variables should be JSON string
        assert isinstance(params["variables"], str)
        vars_dict = json.loads(params["variables"])
        assert vars_dict["ansible_host"] == "192.168.1.10"  # NOSONAR
        assert vars_dict["ansible_user"] == "deploy"

        # enabled=True should not be in params (it's the default)
        assert "enabled" not in params

    def test_host_with_inventory_id(self):
        """Test host with inventory ID instead of name"""
        from awx_tui.utils.ansible_mapper import host_to_ansible_task

        data = {
            "name": "web01.example.com",
            "inventory": 10,  # ID only
        }

        yaml_str, notes = host_to_ansible_task(data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        params = task_list[0]["awx.awx.host"]
        assert params["inventory"] == "<inventory_id_10>"

        # Should have note about replacing placeholder
        assert len(notes) > 0
        assert any("inventory_id_10" in note for note in notes)

    def test_host_disabled(self):
        """Test host with enabled=False"""
        from awx_tui.utils.ansible_mapper import host_to_ansible_task

        data = {
            "name": "web01.example.com",
            "inventory_name": "Production",
            "enabled": False,
        }

        yaml_str, notes = host_to_ansible_task(data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        params = task_list[0]["awx.awx.host"]
        assert params["enabled"] is False

    def test_host_variables_as_string(self):
        """Test host with variables as JSON string"""
        from awx_tui.utils.ansible_mapper import host_to_ansible_task

        data = {
            "name": "web01.example.com",
            "inventory_name": "Production",
            "variables": '{"key": "value"}',  # JSON string
        }

        yaml_str, notes = host_to_ansible_task(data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        params = task_list[0]["awx.awx.host"]
        # Should keep string as-is
        assert params["variables"] == '{"key": "value"}'

    def test_host_custom_task_name(self, minimal_host_data):
        """Test custom task name for host"""
        from awx_tui.utils.ansible_mapper import host_to_ansible_task

        yaml_str, notes = host_to_ansible_task(minimal_host_data, task_name="Add web server to inventory")
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        assert task_list[0]["name"] == "Add web server to inventory"

    def test_blank_host_name_gives_generic_task_name(self):
        """Test that blank host name results in generic idempotent task name"""
        from awx_tui.utils.ansible_mapper import host_to_ansible_task

        data = {
            "name": "",  # Blank name
            "inventory_name": "Production",
        }

        yaml_str, notes = host_to_ansible_task(data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        # Task name should be generic idempotent form
        assert task_list[0]["name"] == "Ensure host exists"


class TestCredentialMapper:
    """Tests for credential_to_ansible_task() function"""

    @pytest.fixture
    def minimal_credential_data(self):
        """Minimal valid credential data"""
        return {
            "name": "My SSH Key",
            "credential_type_name": "Machine",
        }

    @pytest.fixture
    def full_credential_data(self):
        """Full credential data with all optional fields"""
        return {
            "name": "My SSH Key",
            "description": "SSH key for production servers",
            "credential_type_name": "Machine",
            "organization_name": "Production Org",
            "inputs": {
                "username": "deploy",
                "ssh_key_data": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----",
            },
        }

    def test_minimal_credential(self, minimal_credential_data):
        """Test minimal credential conversion"""
        from awx_tui.utils.ansible_mapper import credential_to_ansible_task

        yaml_str, notes = credential_to_ansible_task(minimal_credential_data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        assert len(task_list) == 1
        task = task_list[0]
        assert task["name"] == "Ensure credential My SSH Key exists"

        params = task["awx.awx.credential"]
        assert params["name"] == "My SSH Key"
        assert params["credential_type"] == "Machine"
        assert params["state"] == "present"

    def test_full_credential(self, full_credential_data):
        """Test full credential with all fields"""
        from awx_tui.utils.ansible_mapper import credential_to_ansible_task

        yaml_str, notes = credential_to_ansible_task(full_credential_data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        params = task_list[0]["awx.awx.credential"]
        assert params["name"] == "My SSH Key"
        assert params["description"] == "SSH key for production servers"
        assert params["credential_type"] == "Machine"
        assert params["organization"] == "Production Org"

        # Inputs should be included
        assert "inputs" in params
        assert params["inputs"]["username"] == "deploy"
        assert "ssh_key_data" in params["inputs"]

        # Should have security warnings in notes
        assert any("sensitive" in note.lower() for note in notes)

    def test_credential_with_type_id(self):
        """Test credential with credential_type ID instead of name"""
        from awx_tui.utils.ansible_mapper import credential_to_ansible_task

        data = {
            "name": "My Credential",
            "credential_type": 1,  # ID only
        }

        yaml_str, notes = credential_to_ansible_task(data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        params = task_list[0]["awx.awx.credential"]
        assert params["credential_type"] == "<credential_type_id_1>"

        # Should have note about replacing placeholder
        assert len(notes) > 0
        assert any("credential_type_id_1" in note for note in notes)

    def test_credential_with_org_id(self):
        """Test credential with organization ID instead of name"""
        from awx_tui.utils.ansible_mapper import credential_to_ansible_task

        data = {
            "name": "My Credential",
            "credential_type_name": "Machine",
            "organization": 5,  # ID only
        }

        yaml_str, notes = credential_to_ansible_task(data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        params = task_list[0]["awx.awx.credential"]
        assert params["organization"] == "<org_id_5>"

        # Should have note about replacing placeholder
        assert any("org_id_5" in note for note in notes)

    def test_credential_custom_task_name(self, minimal_credential_data):
        """Test custom task name for credential"""
        from awx_tui.utils.ansible_mapper import credential_to_ansible_task

        yaml_str, notes = credential_to_ansible_task(minimal_credential_data, task_name="Configure SSH credential")
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        assert task_list[0]["name"] == "Configure SSH credential"

    def test_blank_credential_name_gives_generic_task_name(self):
        """Test that blank credential name results in generic idempotent task name"""
        from awx_tui.utils.ansible_mapper import credential_to_ansible_task

        data = {
            "name": "",  # Blank name
            "credential_type_name": "Machine",
        }

        yaml_str, notes = credential_to_ansible_task(data)
        # Remove indentation for parsing
        unindented = "\n".join(line[2:] if line.startswith("  ") else line for line in yaml_str.splitlines())
        task_list = yaml.safe_load(unindented)

        # Task name should be generic idempotent form
        assert task_list[0]["name"] == "Ensure credential exists"
