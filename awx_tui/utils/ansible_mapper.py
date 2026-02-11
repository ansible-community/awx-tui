"""
AWX TUI - Ansible AWX Collection Mapper

Maps AWX API data to awx.awx Ansible module parameters.
Converts API JSON to Ansible task YAML format.
"""

from typing import Any, Dict, List, Optional, Tuple

import yaml


def job_template_to_ansible_task(
    api_data: Dict[str, Any],
    task_name: Optional[str] = None,
    include_state: bool = True,
    indent: int = 2,
) -> Tuple[str, List[str]]:
    """
    Convert AWX job template API data to awx.awx.job_template task YAML.

    Args:
        api_data: Job template data from AWX API or form state
        task_name: Optional custom task name (defaults to "Ensure job template {name} exists")
        include_state: Whether to include state: present parameter
        indent: Number of spaces to indent (default 2, for placement under tasks:)

    Returns:
        Tuple of (yaml_string, notes_list)
    """
    notes = []

    # Extract job template name
    template_name = api_data.get("name", "")

    # Build task name (idempotent: "Ensure X exists")
    if not task_name:
        if template_name:
            task_name = f"Ensure job template {template_name} exists"
        else:
            task_name = "Ensure job template exists"

    # Build module parameters
    params = {}

    # Required fields
    params["name"] = template_name

    # Job type
    job_type = api_data.get("job_type", "run")
    params["job_type"] = job_type

    # Inventory (required for most templates)
    inventory_id = api_data.get("inventory")
    inventory_name = api_data.get("inventory_name")  # From form or summary_fields
    if inventory_name:
        params["inventory"] = inventory_name
    elif inventory_id:
        params["inventory"] = f"<inventory_id_{inventory_id}>"
        notes.append(f"Replace <inventory_id_{inventory_id}> with actual inventory name")

    # Project (required)
    project_id = api_data.get("project")
    project_name = api_data.get("project_name")  # From form or summary_fields
    if project_name:
        params["project"] = project_name
    elif project_id:
        params["project"] = f"<project_id_{project_id}>"
        notes.append(f"Replace <project_id_{project_id}> with actual project name")

    # Playbook (required for run jobs)
    playbook = api_data.get("playbook")
    if playbook:
        params["playbook"] = playbook

    # Description (optional)
    description = api_data.get("description")
    if description:
        params["description"] = description

    # Execution Environment (optional)
    ee_id = api_data.get("execution_environment")
    ee_name = api_data.get("execution_environment_name")
    if ee_name:
        params["execution_environment"] = ee_name
    elif ee_id:
        params["execution_environment"] = f"<ee_id_{ee_id}>"
        notes.append(f"Replace <ee_id_{ee_id}> with actual execution environment name")

    # Credentials (optional, can be multiple)
    credentials = api_data.get("credentials", [])
    credential_names = api_data.get("credential_names", [])
    if credential_names:
        params["credentials"] = credential_names
    elif credentials:
        # If we only have IDs, show placeholders
        cred_placeholders = [f"<credential_id_{cid}>" for cid in credentials]
        params["credentials"] = cred_placeholders
        notes.append("Replace credential ID placeholders with actual credential names")

    # Forks (optional)
    forks = api_data.get("forks")
    if forks is not None and forks != "":
        try:
            forks_int = int(forks)
            if forks_int != 0:
                params["forks"] = forks_int
        except (ValueError, TypeError):
            pass

    # Job Slices (optional)
    job_slice_count = api_data.get("job_slice_count")
    if job_slice_count is not None and job_slice_count != "":
        try:
            slices_int = int(job_slice_count)
            if slices_int != 0:
                params["job_slice_count"] = slices_int
        except (ValueError, TypeError):
            pass

    # Timeout (optional)
    timeout = api_data.get("timeout")
    if timeout is not None and timeout != "" and timeout != 0:
        try:
            params["timeout"] = int(timeout)
        except (ValueError, TypeError):
            pass

    # Verbosity (optional)
    verbosity = api_data.get("verbosity")
    if verbosity is not None and verbosity != 0:
        try:
            params["verbosity"] = int(verbosity)
        except (ValueError, TypeError):
            pass

    # Limit (optional)
    limit = api_data.get("limit")
    if limit:
        params["limit"] = limit

    # Extra vars (optional)
    extra_vars = api_data.get("extra_vars")
    if extra_vars:
        # Convert to JSON string format (awx.awx expects JSON, not YAML)
        import json

        if isinstance(extra_vars, (dict, list)):
            params["extra_vars"] = json.dumps(extra_vars)
        elif isinstance(extra_vars, str) and extra_vars.strip():
            # Try to parse as YAML first (AWX API may return YAML strings)
            # If it parses successfully, convert to JSON
            # If it's already JSON or plain text, keep as-is
            try:
                parsed = yaml.safe_load(extra_vars)
                # If parsed result is a dict or list, it was YAML - convert to JSON
                if isinstance(parsed, (dict, list)):
                    params["extra_vars"] = json.dumps(parsed)
                else:
                    # Scalar value or unparseable - keep original
                    params["extra_vars"] = extra_vars
            except (yaml.YAMLError, AttributeError):
                # Not valid YAML, keep as-is
                params["extra_vars"] = extra_vars

    # Boolean flags
    become_enabled = api_data.get("become_enabled", False)
    if become_enabled:
        params["become_enabled"] = True

    allow_simultaneous = api_data.get("allow_simultaneous", False)
    if allow_simultaneous:
        params["allow_simultaneous"] = True

    use_fact_cache = api_data.get("use_fact_cache", False)
    if use_fact_cache:
        params["use_fact_cache"] = True

    # Ask fields on launch (optional)
    ask_fields = [
        "ask_credential_on_launch",
        "ask_diff_mode_on_launch",
        "ask_execution_environment_on_launch",
        "ask_forks_on_launch",
        "ask_instance_groups_on_launch",
        "ask_inventory_on_launch",
        "ask_job_slice_count_on_launch",
        "ask_job_type_on_launch",
        "ask_limit_on_launch",
        "ask_scm_branch_on_launch",
        "ask_skip_tags_on_launch",
        "ask_tags_on_launch",
        "ask_timeout_on_launch",
        "ask_variables_on_launch",
        "ask_verbosity_on_launch",
    ]

    for field in ask_fields:
        if api_data.get(field):
            params[field] = True

    # State parameter
    if include_state:
        params["state"] = "present"

    # Build task structure
    task = {"name": task_name, "awx.awx.job_template": params}

    # Convert to YAML
    yaml_str = yaml.dump([task], default_flow_style=False, sort_keys=False, allow_unicode=True)

    # Indent by specified number of spaces (for placement under tasks:)
    indent_str = " " * indent
    indented_yaml = "\n".join(indent_str + line if line else line for line in yaml_str.splitlines())

    return indented_yaml, notes


def project_to_ansible_task(
    api_data: Dict[str, Any],
    task_name: Optional[str] = None,
    include_state: bool = True,
    indent: int = 2,
) -> Tuple[str, List[str]]:
    """
    Convert AWX project API data to awx.awx.project task YAML.

    Args:
        api_data: Project data from AWX API or form state
        task_name: Optional custom task name (defaults to "Ensure project {name} exists")
        include_state: Whether to include state: present parameter
        indent: Number of spaces to indent (default 2, for placement under tasks:)

    Returns:
        Tuple of (yaml_string, notes_list)
    """
    notes = []

    # Extract project name
    project_name = api_data.get("name", "")

    # Build task name (idempotent: "Ensure X exists")
    if not task_name:
        if project_name:
            task_name = f"Ensure project {project_name} exists"
        else:
            task_name = "Ensure project exists"

    # Build module parameters
    params = {}

    # Required fields
    params["name"] = project_name

    # Description (optional)
    description = api_data.get("description")
    if description:
        params["description"] = description

    # Organization (required in AWX)
    org_id = api_data.get("organization")
    org_name = api_data.get("organization_name")
    if org_name:
        params["organization"] = org_name
    elif org_id:
        params["organization"] = f"<org_id_{org_id}>"
        notes.append(f"Replace <org_id_{org_id}> with actual organization name")

    # SCM type
    scm_type = api_data.get("scm_type", "git")
    if scm_type and scm_type != "":
        params["scm_type"] = scm_type

    # SCM URL
    scm_url = api_data.get("scm_url")
    if scm_url:
        params["scm_url"] = scm_url

    # SCM Branch
    scm_branch = api_data.get("scm_branch")
    if scm_branch:
        params["scm_branch"] = scm_branch

    # SCM Credential
    credential_id = api_data.get("credential")
    credential_name = api_data.get("credential_name")
    if credential_name:
        params["scm_credential"] = credential_name
    elif credential_id:
        params["scm_credential"] = f"<credential_id_{credential_id}>"
        notes.append(f"Replace <credential_id_{credential_id}> with actual credential name")

    # Update options
    scm_update_on_launch = api_data.get("scm_update_on_launch", False)
    if scm_update_on_launch:
        params["scm_update_on_launch"] = True

    scm_delete_on_update = api_data.get("scm_delete_on_update", False)
    if scm_delete_on_update:
        params["scm_delete_on_update"] = True

    scm_clean = api_data.get("scm_clean", False)
    if scm_clean:
        params["scm_clean"] = True

    # Default execution environment
    ee_id = api_data.get("default_environment")
    ee_name = api_data.get("default_environment_name")
    if ee_name:
        params["default_environment"] = ee_name
    elif ee_id:
        params["default_environment"] = f"<ee_id_{ee_id}>"
        notes.append(f"Replace <ee_id_{ee_id}> with actual execution environment name")

    # State parameter
    if include_state:
        params["state"] = "present"

    # Build task structure
    task = {"name": task_name, "awx.awx.project": params}

    # Convert to YAML
    yaml_str = yaml.dump([task], default_flow_style=False, sort_keys=False, allow_unicode=True)

    # Indent by specified number of spaces (for placement under tasks:)
    indent_str = " " * indent
    indented_yaml = "\n".join(indent_str + line if line else line for line in yaml_str.splitlines())

    return indented_yaml, notes


def inventory_to_ansible_task(
    api_data: Dict[str, Any],
    task_name: Optional[str] = None,
    include_state: bool = True,
    indent: int = 2,
) -> Tuple[str, List[str]]:
    """
    Convert AWX inventory API data to awx.awx.inventory task YAML.

    Args:
        api_data: Inventory data from AWX API or form state
        task_name: Optional custom task name (defaults to "Ensure inventory {name} exists")
        include_state: Whether to include state: present parameter
        indent: Number of spaces to indent (default 2, for placement under tasks:)

    Returns:
        Tuple of (yaml_string, notes_list)
    """
    notes = []

    # Extract inventory name
    inventory_name = api_data.get("name", "")

    # Build task name (idempotent: "Ensure X exists")
    if not task_name:
        if inventory_name:
            task_name = f"Ensure inventory {inventory_name} exists"
        else:
            task_name = "Ensure inventory exists"

    # Build module parameters
    params = {}

    # Required fields
    params["name"] = inventory_name

    # Description (optional)
    description = api_data.get("description")
    if description:
        params["description"] = description

    # Organization (required in AWX)
    org_id = api_data.get("organization")
    org_name = api_data.get("organization_name")
    if org_name:
        params["organization"] = org_name
    elif org_id:
        params["organization"] = f"<org_id_{org_id}>"
        notes.append(f"Replace <org_id_{org_id}> with actual organization name")

    # Variables (optional)
    variables = api_data.get("variables")
    if variables:
        # Convert to JSON string format (awx.awx expects JSON, not YAML)
        import json

        if isinstance(variables, (dict, list)):
            params["variables"] = json.dumps(variables)
        elif isinstance(variables, str) and variables.strip():
            # Keep as string - awx.awx will handle it
            params["variables"] = variables

    # State parameter
    if include_state:
        params["state"] = "present"

    # Build task structure
    task = {"name": task_name, "awx.awx.inventory": params}

    # Convert to YAML
    yaml_str = yaml.dump([task], default_flow_style=False, sort_keys=False, allow_unicode=True)

    # Indent by specified number of spaces (for placement under tasks:)
    indent_str = " " * indent
    indented_yaml = "\n".join(indent_str + line if line else line for line in yaml_str.splitlines())

    return indented_yaml, notes


def host_to_ansible_task(
    api_data: Dict[str, Any],
    task_name: Optional[str] = None,
    include_state: bool = True,
    indent: int = 2,
) -> Tuple[str, List[str]]:
    """
    Convert AWX host API data to awx.awx.host task YAML.

    Args:
        api_data: Host data from AWX API or form state
        task_name: Optional custom task name (defaults to "Ensure host {name} exists")
        include_state: Whether to include state: present parameter
        indent: Number of spaces to indent (default 2, for placement under tasks:)

    Returns:
        Tuple of (yaml_string, notes_list)
    """
    notes = []

    # Extract host name
    host_name = api_data.get("name", "")

    # Build task name (idempotent: "Ensure X exists")
    if not task_name:
        if host_name:
            task_name = f"Ensure host {host_name} exists"
        else:
            task_name = "Ensure host exists"

    # Build module parameters
    params = {}

    # Required fields
    params["name"] = host_name

    # Inventory (required)
    inventory_id = api_data.get("inventory")
    inventory_name = api_data.get("inventory_name")
    if inventory_name:
        params["inventory"] = inventory_name
    elif inventory_id:
        params["inventory"] = f"<inventory_id_{inventory_id}>"
        notes.append(f"Replace <inventory_id_{inventory_id}> with actual inventory name")

    # Description (optional)
    description = api_data.get("description")
    if description:
        params["description"] = description

    # Enabled (optional boolean)
    enabled = api_data.get("enabled")
    if enabled is not None and enabled is False:
        # Only include if explicitly disabled (default is True in AWX)
        params["enabled"] = False

    # Variables (optional)
    variables = api_data.get("variables")
    if variables:
        # Convert to JSON string format (awx.awx expects JSON, not YAML)
        import json

        if isinstance(variables, (dict, list)):
            params["variables"] = json.dumps(variables)
        elif isinstance(variables, str) and variables.strip():
            # Keep as string - awx.awx will handle it
            params["variables"] = variables

    # State parameter
    if include_state:
        params["state"] = "present"

    # Build task structure
    task = {"name": task_name, "awx.awx.host": params}

    # Convert to YAML
    yaml_str = yaml.dump([task], default_flow_style=False, sort_keys=False, allow_unicode=True)

    # Indent by specified number of spaces (for placement under tasks:)
    indent_str = " " * indent
    indented_yaml = "\n".join(indent_str + line if line else line for line in yaml_str.splitlines())

    return indented_yaml, notes


def credential_to_ansible_task(
    api_data: Dict[str, Any],
    task_name: Optional[str] = None,
    include_state: bool = True,
    indent: int = 2,
) -> Tuple[str, List[str]]:
    """
    Convert AWX credential API data to awx.awx.credential task YAML.

    Args:
        api_data: Credential data from AWX API or form state
        task_name: Optional custom task name (defaults to "Ensure credential {name} exists")
        include_state: Whether to include state: present parameter
        indent: Number of spaces to indent (default 2, for placement under tasks:)

    Returns:
        Tuple of (yaml_string, notes_list)
    """
    notes = []

    # Extract credential name
    credential_name = api_data.get("name", "")

    # Build task name (idempotent: "Ensure X exists")
    if not task_name:
        if credential_name:
            task_name = f"Ensure credential {credential_name} exists"
        else:
            task_name = "Ensure credential exists"

    # Build module parameters
    params = {}

    # Required fields
    params["name"] = credential_name

    # Credential type (required)
    credential_type_id = api_data.get("credential_type")
    credential_type_name = api_data.get("credential_type_name")
    if credential_type_name:
        params["credential_type"] = credential_type_name
    elif credential_type_id:
        params["credential_type"] = f"<credential_type_id_{credential_type_id}>"
        notes.append(f"Replace <credential_type_id_{credential_type_id}> with actual credential type name")

    # Description (optional)
    description = api_data.get("description")
    if description:
        params["description"] = description

    # Organization (optional but recommended)
    org_id = api_data.get("organization")
    org_name = api_data.get("organization_name")
    if org_name:
        params["organization"] = org_name
    elif org_id:
        params["organization"] = f"<org_id_{org_id}>"
        notes.append(f"Replace <org_id_{org_id}> with actual organization name")

    # Inputs (optional, contains sensitive data)
    inputs = api_data.get("inputs")
    if inputs:
        # Inputs is a dict that may contain sensitive fields
        if isinstance(inputs, dict) and inputs:
            params["inputs"] = inputs
            notes.append("WARNING: inputs may contain sensitive data (passwords, keys, tokens)")
            notes.append("Review and secure the inputs field before using in production")

    # State parameter
    if include_state:
        params["state"] = "present"

    # Build task structure
    task = {"name": task_name, "awx.awx.credential": params}

    # Convert to YAML
    yaml_str = yaml.dump([task], default_flow_style=False, sort_keys=False, allow_unicode=True)

    # Indent by specified number of spaces (for placement under tasks:)
    indent_str = " " * indent
    indented_yaml = "\n".join(indent_str + line if line else line for line in yaml_str.splitlines())

    return indented_yaml, notes
