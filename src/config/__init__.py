import os
import re
from typing import Any, Union


def expand_config_vars(config: Any) -> Any:
    """
    Recursively expand environment variables in configuration.

    Replaces ${VAR_NAME} patterns in strings with environment variable values.
    If an environment variable is not set, replaces with empty string.

    Args:
        config: Configuration data (dict, list, str, or other primitive)

    Returns:
        Configuration with all environment variables expanded
    """
    if isinstance(config, str):
        # Pattern to match ${VAR_NAME}
        pattern = r'\$\{([^}]+)\}'

        def replace_match(match: re.Match) -> str:
            var_name = match.group(1)
            return os.getenv(var_name, "")

        return re.sub(pattern, replace_match, config)

    elif isinstance(config, dict):
        return {key: expand_config_vars(value) for key, value in config.items()}

    elif isinstance(config, list):
        return [expand_config_vars(item) for item in config]

    else:
        # Return primitives (int, float, bool, None) unchanged
        return config
