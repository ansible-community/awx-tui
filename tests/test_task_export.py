"""
Tests for TaskExportModal

Tests the modal that displays exported Ansible tasks (awx.awx collection).
"""

import pytest

from awx_tui.modals.task_export import TaskExportModal


class TestTaskExportModalInitialization:
    """Tests for TaskExportModal initialization and parameter handling"""

    def test_minimal_initialization(self):
        """Test TaskExportModal with minimal required parameters"""
        yaml_content = "  - name: Test task\n    awx.awx.job_template:\n      name: test"

        modal = TaskExportModal(
            task_yaml=yaml_content,
        )

        assert modal.task_yaml == yaml_content
        assert modal.title_text == "Export AP Task - Ansible awx.awx Collection"
        assert modal.module_name is None
        assert modal.notes == []

    def test_full_initialization(self):
        """Test TaskExportModal with all parameters"""
        yaml_content = "  - name: Test task\n    awx.awx.project:\n      name: test"
        notes = ["Note 1", "Note 2"]

        modal = TaskExportModal(
            task_yaml=yaml_content,
            title="Custom Title",
            module_name="project",
            notes=notes,
        )

        assert modal.task_yaml == yaml_content
        assert modal.title_text == "Custom Title"
        assert modal.module_name == "project"
        assert modal.notes == notes

    def test_rejects_wrong_parameter_yaml_content(self):
        """Test that using wrong parameter name 'yaml_content' raises TypeError"""
        with pytest.raises(TypeError, match="missing 1 required positional argument: 'task_yaml'"):
            TaskExportModal(
                yaml_content="- name: test",  # Wrong parameter name!
                title="Test",
            )

    def test_rejects_wrong_parameter_resource_type(self):
        """Test that using wrong parameter name 'resource_type' raises TypeError"""
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            TaskExportModal(
                task_yaml="- name: test",
                resource_type="Project",  # Wrong parameter name!
            )

    def test_accepts_empty_notes(self):
        """Test that notes can be empty list"""
        modal = TaskExportModal(
            task_yaml="- name: test",
            notes=[],
        )

        assert modal.notes == []

    def test_notes_default_to_empty_list(self):
        """Test that notes default to empty list when not provided"""
        modal = TaskExportModal(
            task_yaml="- name: test",
        )

        assert modal.notes == []


class TestTaskExportModalCompose:
    """Tests for TaskExportModal composition and layout"""

    def test_modal_has_compose_method(self):
        """Test that modal has compose method"""
        modal = TaskExportModal(task_yaml="- name: test\n  awx.awx.job_template: {}")

        # Should have compose method
        assert hasattr(modal, "compose")
        assert callable(modal.compose)

    def test_modal_stores_notes_for_display(self):
        """Test that notes are stored for later display"""
        notes = ["Note 1", "Note 2"]
        modal = TaskExportModal(
            task_yaml="- name: test",
            notes=notes,
        )

        assert modal.notes == notes

    def test_modal_stores_module_name_for_display(self):
        """Test that module name is stored for display in title"""
        modal = TaskExportModal(
            task_yaml="- name: test",
            title="Export Task",
            module_name="inventory",
        )

        # Module name should be stored
        assert modal.module_name == "inventory"


class TestTaskExportModalContent:
    """Tests for TaskExportModal content display"""

    def test_displays_yaml_content(self):
        """Test that YAML content is stored correctly"""
        yaml_content = """  - name: Ensure project Test exists
    awx.awx.project:
      name: Test
      organization: Default
      state: present"""

        modal = TaskExportModal(task_yaml=yaml_content)

        assert modal.task_yaml == yaml_content

    def test_handles_multiline_yaml(self):
        """Test that multiline YAML is handled correctly"""
        yaml_content = """  - name: Task 1
    awx.awx.inventory:
      name: Inv1
  - name: Task 2
    awx.awx.host:
      name: host1
      inventory: Inv1"""

        modal = TaskExportModal(task_yaml=yaml_content)

        assert modal.task_yaml == yaml_content
        assert "Task 1" in yaml_content
        assert "Task 2" in yaml_content

    def test_handles_unicode_in_yaml(self):
        """Test that Unicode characters in YAML are preserved"""
        yaml_content = """  - name: Ensure project Déployment exists
    awx.awx.project:
      name: Déployment
      description: 你好 мир 🚀"""

        modal = TaskExportModal(task_yaml=yaml_content)

        assert "Déployment" in modal.task_yaml
        assert "你好" in modal.task_yaml
        assert "🚀" in modal.task_yaml


class TestTaskExportModalNotes:
    """Tests for TaskExportModal notes functionality"""

    def test_single_note(self):
        """Test displaying a single note"""
        modal = TaskExportModal(
            task_yaml="- name: test",
            notes=["Replace <org_id_5> with actual organization name"],
        )

        assert len(modal.notes) == 1
        assert "org_id_5" in modal.notes[0]

    def test_multiple_notes(self):
        """Test displaying multiple notes"""
        notes = [
            "Replace <project_id_10> with actual project name",
            "Replace <inventory_id_5> with actual inventory name",
            "WARNING: inputs may contain sensitive data",
        ]

        modal = TaskExportModal(
            task_yaml="- name: test",
            notes=notes,
        )

        assert len(modal.notes) == 3
        assert modal.notes == notes

    def test_notes_with_special_characters(self):
        """Test notes with special characters"""
        notes = [
            "Note with 'quotes'",
            'Note with "double quotes"',
            "Note with <angle brackets>",
            "Note with émojis 🎉",
        ]

        modal = TaskExportModal(
            task_yaml="- name: test",
            notes=notes,
        )

        assert modal.notes == notes


class TestTaskExportModalModuleNames:
    """Tests for different awx.awx module types"""

    @pytest.mark.parametrize(
        "module_name",
        [
            "job_template",
            "project",
            "inventory",
            "host",
            "credential",
            "organization",
            "team",
            "user",
        ],
    )
    def test_various_module_names(self, module_name):
        """Test that various awx.awx module names are accepted"""
        modal = TaskExportModal(
            task_yaml=f"- name: test\n  awx.awx.{module_name}: {{}}",
            module_name=module_name,
        )

        assert modal.module_name == module_name

    def test_none_module_name(self):
        """Test that module_name can be None"""
        modal = TaskExportModal(
            task_yaml="- name: test",
            module_name=None,
        )

        assert modal.module_name is None


class TestTaskExportModalEdgeCases:
    """Tests for edge cases and error handling"""

    def test_empty_yaml_string(self):
        """Test with empty YAML string"""
        modal = TaskExportModal(task_yaml="")

        assert modal.task_yaml == ""

    def test_whitespace_only_yaml(self):
        """Test with whitespace-only YAML"""
        modal = TaskExportModal(task_yaml="   \n\n   ")

        assert modal.task_yaml == "   \n\n   "

    def test_very_long_yaml(self):
        """Test with very long YAML content"""
        # Generate a long YAML with many tasks
        tasks = []
        for i in range(100):
            tasks.append(f"""  - name: Task {i}
    awx.awx.host:
      name: host{i}
      inventory: Production""")

        yaml_content = "\n".join(tasks)
        modal = TaskExportModal(task_yaml=yaml_content)

        assert len(modal.task_yaml) > 1000
        assert "Task 0" in modal.task_yaml
        assert "Task 99" in modal.task_yaml

    def test_yaml_with_sensitive_placeholders(self):
        """Test YAML content with sensitive data placeholders"""
        yaml_content = """  - name: Ensure credential SSH Key exists
    awx.awx.credential:
      name: SSH Key
      credential_type: Machine
      inputs:
        username: deploy
        ssh_key_data: '***REMOVED***'"""

        modal = TaskExportModal(
            task_yaml=yaml_content,
            notes=["WARNING: inputs may contain sensitive data"],
        )

        assert "***REMOVED***" in modal.task_yaml
        assert any("sensitive" in note.lower() for note in modal.notes)

    def test_invalid_yaml_syntax_still_accepted(self):
        """Test that invalid YAML syntax is still accepted (modal just displays it)"""
        # Modal doesn't validate YAML, just displays it
        invalid_yaml = "  - name: test\n    invalid yaml {{{ syntax"

        modal = TaskExportModal(task_yaml=invalid_yaml)

        assert modal.task_yaml == invalid_yaml


class TestTaskExportModalIntegration:
    """Integration tests for complete workflows"""

    def test_job_template_export_workflow(self):
        """Test complete job template export workflow"""
        from awx_tui.utils.ansible_mapper import job_template_to_ansible_task

        # Simulate job template data
        template_data = {
            "name": "Deploy Application",
            "description": "Deploys the application to production",
            "job_type": "run",
            "inventory_name": "Production",
            "project_name": "MyProject",
            "playbook": "deploy.yml",
            "verbosity": 1,
        }

        # Generate YAML
        yaml_str, notes = job_template_to_ansible_task(template_data)

        # Create modal
        modal = TaskExportModal(
            task_yaml=yaml_str,
            title="Export AP Task - Job Template",
            module_name="job_template",
            notes=notes,
        )

        assert "Deploy Application" in modal.task_yaml
        assert "awx.awx.job_template" in modal.task_yaml
        assert modal.module_name == "job_template"

    def test_inventory_with_hosts_export_workflow(self):
        """Test inventory + hosts export workflow"""
        from awx_tui.utils.ansible_mapper import host_to_ansible_task, inventory_to_ansible_task

        # Inventory data
        inventory_data = {
            "name": "Production",
            "organization_name": "Default",
        }

        # Generate inventory YAML
        inv_yaml, inv_notes = inventory_to_ansible_task(inventory_data)

        # Host data
        host_data = {
            "name": "web01.example.com",
            "inventory_name": "Production",
            "enabled": True,
        }

        # Generate host YAML
        host_yaml, host_notes = host_to_ansible_task(host_data)

        # Combine
        combined_yaml = inv_yaml + "\n" + host_yaml
        combined_notes = inv_notes + host_notes

        # Create modal
        modal = TaskExportModal(
            task_yaml=combined_yaml,
            title="Export AP Task - Inventory + Hosts",
            module_name="inventory",
            notes=combined_notes,
        )

        assert "awx.awx.inventory" in modal.task_yaml
        assert "awx.awx.host" in modal.task_yaml
        assert "Production" in modal.task_yaml
        assert "web01.example.com" in modal.task_yaml

    def test_credential_export_with_security_notes(self):
        """Test credential export includes security warnings"""
        from awx_tui.utils.ansible_mapper import credential_to_ansible_task

        # Credential with sensitive inputs
        cred_data = {
            "name": "SSH Key",
            "credential_type_name": "Machine",
            "organization_name": "Default",
            "inputs": {
                "username": "deploy",
                "ssh_key_data": "FAKE_SSH_KEY_CONTENT",
            },
        }

        # Generate YAML
        yaml_str, notes = credential_to_ansible_task(cred_data)

        # Create modal
        modal = TaskExportModal(
            task_yaml=yaml_str,
            title="Export AP Task - Credential",
            module_name="credential",
            notes=notes,
        )

        assert "awx.awx.credential" in modal.task_yaml
        assert len(modal.notes) > 0
        assert any("sensitive" in note.lower() for note in modal.notes)
