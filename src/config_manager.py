"""
Configuration management for the Cortinillas_IA system.
Handles loading, validation, and creation of channel configurations.
"""
import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
try:
    from .models import ChannelConfig, DeepgramConfig, APIConfig
    from .exceptions import ConfigurationError, FileOperationError, ValidationError
    from .error_handler import ErrorHandler, create_error_context, safe_execute
except ImportError:
    from models import ChannelConfig, DeepgramConfig, APIConfig
    from exceptions import ConfigurationError, FileOperationError, ValidationError
    from error_handler import ErrorHandler, create_error_context, safe_execute


logger = logging.getLogger(__name__)


# Keep backward compatibility
class ConfigValidationError(ConfigurationError):
    """Raised when configuration validation fails."""
    pass


class ConfigManager:
    """Manages configuration loading, validation, and creation for TV channels."""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.error_handler = ErrorHandler(max_retries=2, base_delay=1.0)
        logger.info(f"ConfigManager initialized with config dir: {config_dir}")
    
    def load_channel_config(self, config_path: str) -> ChannelConfig:
        """
        Load and validate configuration for a single channel.
        
        Args:
            config_path: Path to the JSON configuration file
            
        Returns:
            ChannelConfig: Validated channel configuration
            
        Raises:
            FileNotFoundError: If configuration file doesn't exist
            ConfigurationError: If configuration is invalid
        """
        context = create_error_context(
            "load_channel_config",
            additional_info={"config_path": config_path}
        )
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            # Load JSON with error handling
            config_data = self._load_json_config(config_path)
            
            # Validate and parse configuration
            channel_config = safe_execute(
                self._parse_channel_config,
                config_data,
                config_path,
                error_handler=self.error_handler,
                context=f"{context} | parse_config"
            )
            
            if channel_config is None:
                raise ConfigurationError(f"Failed to parse configuration from {config_path}")
            
            # Validate configuration
            safe_execute(
                self.validate_config,
                channel_config,
                error_handler=self.error_handler,
                context=f"{context} | validate_config"
            )
            
            logger.info(f"Successfully loaded configuration for channel: {channel_config.channel_name}")
            return channel_config
            
        except (FileNotFoundError, ConfigurationError):
            raise
        except Exception as e:
            self.error_handler.handle_error(e, context, critical=True)
            raise ConfigurationError(f"Failed to load configuration from {config_path}: {e}") from e
    
    def create_default_config(self, channel_name: str, idemisora: int = 1, idprograma: int = 5) -> ChannelConfig:
        """
        Create a default configuration for a channel.
        
        Args:
            channel_name: Name of the channel (will be converted to lowercase)
            idemisora: Emisora ID for the channel
            idprograma: Programa ID for the channel
            
        Returns:
            ChannelConfig: Default channel configuration
        """
        default_cortinillas = [
            "buenos días",
            "buenas tardes", 
            "buenas noches",
            "muchas gracias",
            "hasta mañana",
            "volvemos enseguida",
            "no se vayan",
            "continuamos"
        ]
        
        deepgram_config = DeepgramConfig(
            language="multi",
            model="nova-3",
            smart_format=True
        )
        
        api_config = APIConfig(
            base_url="http://172.16.3.20",
            cookie_sid="4ffa5b8066f0d3fbf870e75f3c601d5c",
            format=11,
            video_is_public=0,
            is_masive=1,
            max_retries=3,
            sleep_seconds=30
        )
        
        config = ChannelConfig(
            channel_name=channel_name.lower(),
            idemisora=idemisora,
            idprograma=idprograma,
            cortinillas=default_cortinillas,
            deepgram_config=deepgram_config,
            api_config=api_config
        )
        
        logger.info(f"Created default configuration for channel: {channel_name.lower()}")
        return config
    
    def save_config(self, config: ChannelConfig, config_path: str) -> None:
        """
        Save a channel configuration to a JSON file.
        
        Args:
            config: Channel configuration to save
            config_path: Path where to save the configuration
        """
        config_data = {
            "channel_name": config.channel_name,
            "idemisora": config.idemisora,
            "idprograma": config.idprograma,
            "cortinillas": config.cortinillas,
            "deepgram_config": {
                "language": config.deepgram_config.language,
                "model": config.deepgram_config.model,
                "smart_format": config.deepgram_config.smart_format
            },
            "api_config": {
                "base_url": config.api_config.base_url,
                "cookie_sid": config.api_config.cookie_sid,
                "format": config.api_config.format,
                "video_is_public": config.api_config.video_is_public,
                "is_masive": config.api_config.is_masive,
                "max_retries": config.api_config.max_retries,
                "sleep_seconds": config.api_config.sleep_seconds
            }
        }
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as file:
            json.dump(config_data, file, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved configuration to: {config_path}")
    
    def validate_config(self, config: ChannelConfig) -> bool:
        """
        Validate a channel configuration.
        
        Args:
            config: Channel configuration to validate
            
        Returns:
            bool: True if configuration is valid
            
        Raises:
            ConfigValidationError: If configuration is invalid
        """
        errors = []
        
        # Validate basic fields
        if not config.channel_name or not isinstance(config.channel_name, str):
            errors.append("channel_name must be a non-empty string")
        
        if not isinstance(config.idemisora, int) or config.idemisora <= 0:
            errors.append("idemisora must be a positive integer")
        
        if not isinstance(config.idprograma, int) or config.idprograma <= 0:
            errors.append("idprograma must be a positive integer")
        
        # Validate cortinillas
        if not isinstance(config.cortinillas, list) or len(config.cortinillas) == 0:
            errors.append("cortinillas must be a non-empty list")
        else:
            for i, cortinilla in enumerate(config.cortinillas):
                if not isinstance(cortinilla, str) or not cortinilla.strip():
                    errors.append(f"cortinilla at index {i} must be a non-empty string")
        
        # Validate Deepgram config
        if not config.deepgram_config:
            errors.append("deepgram_config is required")
        else:
            if not config.deepgram_config.language:
                errors.append("deepgram_config.language is required")
            if not config.deepgram_config.model:
                errors.append("deepgram_config.model is required")
            if not isinstance(config.deepgram_config.smart_format, bool):
                errors.append("deepgram_config.smart_format must be a boolean")
        
        # Validate API config
        if not config.api_config:
            errors.append("api_config is required")
        else:
            if not config.api_config.base_url:
                errors.append("api_config.base_url is required")
            if not config.api_config.cookie_sid:
                errors.append("api_config.cookie_sid is required")
            if not isinstance(config.api_config.format, int):
                errors.append("api_config.format must be an integer")
            if not isinstance(config.api_config.max_retries, int) or config.api_config.max_retries < 1:
                errors.append("api_config.max_retries must be a positive integer")
            if not isinstance(config.api_config.sleep_seconds, int) or config.api_config.sleep_seconds < 1:
                errors.append("api_config.sleep_seconds must be a positive integer")
        
        if errors:
            error_msg = f"Configuration validation failed for {config.channel_name}: " + "; ".join(errors)
            raise ConfigValidationError(error_msg)
        
        return True
    
    def load_all_channels(self) -> Dict[str, ChannelConfig]:
        """
        Load all channel configurations from the config directory.
        Creates default configurations if none exist.
        
        Returns:
            Dict[str, ChannelConfig]: Dictionary of channel configurations
        """
        channels = {}
        # Look for both old format (*_config.json) and new format (*.json, excluding env.template)
        old_config_files = list(self.config_dir.glob("*_config.json"))
        new_config_files = [f for f in self.config_dir.glob("*.json") if not f.name.endswith("_config.json") and f.name != "env.template"]
        
        config_files = old_config_files + new_config_files
        
        if not config_files:
            logger.warning("No configuration files found. Creating default configurations.")
            # Create default configurations for two channels
            default_channels = [
                ("caracol", 3, 6),
                ("rcn", 1, 5)
            ]
            
            for channel_name, idemisora, idprograma in default_channels:
                config = self.create_default_config(channel_name, idemisora, idprograma)
                config_path = self.config_dir / f"{channel_name}.json"
                self.save_config(config, str(config_path))
                channels[channel_name] = config
        else:
            # Load existing configurations
            for config_file in config_files:
                try:
                    config = self.load_channel_config(str(config_file))
                    # Use the channel_name from the config, converted to lowercase
                    channel_key = config.channel_name.lower()
                    channels[channel_key] = config
                except (FileNotFoundError, ConfigurationError, ConfigValidationError) as e:
                    logger.error(f"Failed to load configuration from {config_file}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error loading configuration from {config_file}: {e}")
                    continue
        
        return channels
    
    def get_config_path(self, channel_name: str) -> str:
        """
        Get the configuration file path for a channel.
        
        Args:
            channel_name: Name of the channel
            
        Returns:
            str: Path to the configuration file
        """
        return str(self.config_dir / f"{channel_name.lower()}.json")
    
    def _parse_channel_config(self, config_data: Dict[str, Any], config_path: str) -> ChannelConfig:
        """
        Parse channel configuration from dictionary data.
        
        Args:
            config_data: Dictionary containing configuration data
            config_path: Path to the configuration file (for error reporting)
            
        Returns:
            ChannelConfig: Parsed channel configuration
            
        Raises:
            ConfigValidationError: If required fields are missing
        """
        try:
            # Parse Deepgram configuration
            deepgram_data = config_data.get("deepgram_config", {})
            deepgram_config = DeepgramConfig(
                language=deepgram_data.get("language", "multi"),
                model=deepgram_data.get("model", "nova-3"),
                smart_format=deepgram_data.get("smart_format", True)
            )
            
            # Parse API configuration
            api_data = config_data.get("api_config", {})
            api_config = APIConfig(
                base_url=api_data.get("base_url", ""),
                cookie_sid=api_data.get("cookie_sid", ""),
                format=api_data.get("format", 11),
                video_is_public=api_data.get("video_is_public", 0),
                is_masive=api_data.get("is_masive", 1),
                max_retries=api_data.get("max_retries", 3),
                sleep_seconds=api_data.get("sleep_seconds", 30)
            )
            
            # Parse main configuration
            channel_config = ChannelConfig(
                channel_name=config_data.get("channel_name", ""),
                idemisora=config_data.get("idemisora", 0),
                idprograma=config_data.get("idprograma", 0),
                cortinillas=config_data.get("cortinillas", []),
                deepgram_config=deepgram_config,
                api_config=api_config
            )
            
            return channel_config
            
        except KeyError as e:
            raise ConfigValidationError(f"Missing required field in {config_path}: {e}")
        except (TypeError, ValueError) as e:
            raise ConfigValidationError(f"Invalid field type in {config_path}: {e}")
    
    def _load_json_config(self, config_path: str) -> dict:
        """
        Load JSON configuration with error handling.
        
        Args:
            config_path: Path to JSON file
            
        Returns:
            Dictionary with configuration data
            
        Raises:
            ConfigurationError: If JSON loading fails
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in {config_path}: {e}") from e
        except (OSError, IOError) as e:
            raise FileOperationError(f"Failed to read configuration file {config_path}: {e}") from e