"""Configuration loader utility."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv


class ConfigLoader:
    """Loads and manages configuration from YAML and environment variables."""

    def __init__(self, config_path: str = None):
        """Initialize config loader.

        Args:
            config_path: Path to config YAML file. Defaults to config/config.yaml
        """
        # Load environment variables
        load_dotenv()

        # Determine config path
        if config_path is None:
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / "config" / "config.yaml"

        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._resolve_env_vars()
        self._resolve_paths()

    def _load_config(self) -> Dict[str, Any]:
        """Load YAML configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _resolve_env_vars(self):
        """Replace ${ENV_VAR} placeholders with environment variable values."""
        def resolve_dict(d: Dict) -> Dict:
            for key, value in d.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    env_var = value[2:-1]
                    d[key] = os.getenv(env_var, value)
                elif isinstance(value, dict):
                    d[key] = resolve_dict(value)
            return d

        self.config = resolve_dict(self.config)

    def _resolve_paths(self):
        """Convert relative paths to absolute paths."""
        base_dir = Path(__file__).parent.parent

        if 'directories' in self.config:
            for key, path in self.config['directories'].items():
                if not Path(path).is_absolute():
                    self.config['directories'][key] = str(base_dir / path)

    def get(self, key: str, default=None) -> Any:
        """Get configuration value using dot notation.

        Args:
            key: Configuration key (e.g., 'gemini.api_key')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration dictionary."""
        return self.config

    def validate(self) -> bool:
        """Validate required configuration values are present.

        Returns:
            True if valid, raises ValueError otherwise
        """
        required_keys = [
            'gemini.api_key',
            'directories.input',
            'directories.chromadb',
        ]

        missing = []
        for key in required_keys:
            value = self.get(key)
            if value is None or (isinstance(value, str) and value.startswith('${')):
                missing.append(key)

        if missing:
            raise ValueError(
                f"Missing required configuration: {', '.join(missing)}\n"
                "Please set environment variables or update config.yaml"
            )

        return True


# Singleton instance
_config_instance = None


def get_config(config_path: str = None) -> ConfigLoader:
    """Get singleton configuration instance.

    Args:
        config_path: Optional path to config file (only used on first call)

    Returns:
        ConfigLoader instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader(config_path)
    return _config_instance
