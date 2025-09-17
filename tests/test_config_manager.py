"""
Tests for configuration management.
"""
import json
import os
import tempfile
import pytest
from pathlib import Path
from src.config_manager import ConfigManager, ConfigValidationError
from src.models import ChannelConfig, DeepgramConfig, APIConfig


class TestConfigManager:
    """Test cases for ConfigManager class."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = ConfigManager(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment after each test."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_valid_config_file(self, filename: str, channel_name: str = "Test Channel") -> str:
        """Create a valid configuration file for testing."""
        config_data = {
            "channel_name": channel_name,
            "idemisora": 1,
            "idprograma": 5,
            "cortinillas": ["buenos días", "buenas tardes"],
            "deepgram_config": {
                "language": "multi",
                "model": "nova-3",
                "smart_format": True
            },
            "api_config": {
                "base_url": "http://test.com",
                "cookie_sid": "test_sid",
                "format": 11,
                "video_is_public": 0,
                "is_masive": 1,
                "max_retries": 3,
                "sleep_seconds": 30
            }
        }
        
        config_path = os.path.join(self.temp_dir, filename)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)
        
        return config_path
    
    def test_config_manager_initialization(self):
        """Test ConfigManager initialization."""
        assert self.config_manager is not None
        assert Path(self.temp_dir).exists()
    
    def test_load_channel_config_success(self):
        """Test successful loading of a valid configuration."""
        config_path = self.create_valid_config_file("test_config.json")
        
        config = self.config_manager.load_channel_config(config_path)
        
        assert isinstance(config, ChannelConfig)
        assert config.channel_name == "Test Channel"
        assert config.idemisora == 1
        assert config.idprograma == 5
        assert len(config.cortinillas) == 2
        assert "buenos días" in config.cortinillas
        assert config.deepgram_config.language == "es"
        assert config.api_config.base_url == "http://test.com"
    
    def test_load_channel_config_file_not_found(self):
        """Test loading configuration when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            self.config_manager.load_channel_config("nonexistent.json")
    
    def test_load_channel_config_invalid_json(self):
        """Test loading configuration with invalid JSON."""
        config_path = os.path.join(self.temp_dir, "invalid.json")
        with open(config_path, 'w') as f:
            f.write("{ invalid json }")
        
        with pytest.raises(ConfigValidationError):
            self.config_manager.load_channel_config(config_path)
    
    def test_create_default_config(self):
        """Test creation of default configuration."""
        config = self.config_manager.create_default_config("Test Channel", 1)
        
        assert isinstance(config, ChannelConfig)
        assert config.channel_name == "Test Channel"
        assert config.idemisora == 1
        assert config.idprograma == 5
        assert len(config.cortinillas) > 0
        assert "buenos días" in config.cortinillas
        assert config.deepgram_config.language == "es"
        assert config.api_config.max_retries == 3
    
    def test_create_default_config_different_ids(self):
        """Test creation of default configuration with different IDs."""
        config = self.config_manager.create_default_config("Channel 2", 2)
        
        assert config.idemisora == 2
        assert config.idprograma == 6  # 5 + 2 - 1
    
    def test_save_config(self):
        """Test saving configuration to file."""
        config = self.config_manager.create_default_config("Save Test", 1)
        config_path = os.path.join(self.temp_dir, "save_test.json")
        
        self.config_manager.save_config(config, config_path)
        
        assert os.path.exists(config_path)
        
        # Verify saved content
        with open(config_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert saved_data["channel_name"] == "Save Test"
        assert saved_data["idemisora"] == 1
        assert "cortinillas" in saved_data
        assert "deepgram_config" in saved_data
        assert "api_config" in saved_data
    
    def test_validate_config_valid(self):
        """Test validation of a valid configuration."""
        config = self.config_manager.create_default_config("Valid Config", 1)
        
        # Should not raise any exception
        result = self.config_manager.validate_config(config)
        assert result is True
    
    def test_validate_config_empty_channel_name(self):
        """Test validation with empty channel name."""
        config = self.config_manager.create_default_config("Test", 1)
        config.channel_name = ""
        
        with pytest.raises(ConfigValidationError) as exc_info:
            self.config_manager.validate_config(config)
        
        assert "channel_name must be a non-empty string" in str(exc_info.value)
    
    def test_validate_config_invalid_idemisora(self):
        """Test validation with invalid idemisora."""
        config = self.config_manager.create_default_config("Test", 1)
        config.idemisora = -1
        
        with pytest.raises(ConfigValidationError) as exc_info:
            self.config_manager.validate_config(config)
        
        assert "idemisora must be a positive integer" in str(exc_info.value)
    
    def test_validate_config_empty_cortinillas(self):
        """Test validation with empty cortinillas list."""
        config = self.config_manager.create_default_config("Test", 1)
        config.cortinillas = []
        
        with pytest.raises(ConfigValidationError) as exc_info:
            self.config_manager.validate_config(config)
        
        assert "cortinillas must be a non-empty list" in str(exc_info.value)
    
    def test_validate_config_invalid_cortinilla(self):
        """Test validation with invalid cortinilla in list."""
        config = self.config_manager.create_default_config("Test", 1)
        config.cortinillas = ["valid", "", "also valid"]
        
        with pytest.raises(ConfigValidationError) as exc_info:
            self.config_manager.validate_config(config)
        
        assert "cortinilla at index 1 must be a non-empty string" in str(exc_info.value)
    
    def test_validate_config_missing_deepgram_config(self):
        """Test validation with missing deepgram config."""
        config = self.config_manager.create_default_config("Test", 1)
        config.deepgram_config = None
        
        with pytest.raises(ConfigValidationError) as exc_info:
            self.config_manager.validate_config(config)
        
        assert "deepgram_config is required" in str(exc_info.value)
    
    def test_validate_config_invalid_api_retries(self):
        """Test validation with invalid API retries."""
        config = self.config_manager.create_default_config("Test", 1)
        config.api_config.max_retries = 0
        
        with pytest.raises(ConfigValidationError) as exc_info:
            self.config_manager.validate_config(config)
        
        assert "api_config.max_retries must be a positive integer" in str(exc_info.value)
    
    def test_load_all_channels_no_configs(self):
        """Test loading all channels when no config files exist."""
        channels = self.config_manager.load_all_channels()
        
        # Should create default configurations
        assert len(channels) == 2
        assert "channel1" in channels
        assert "channel2" in channels
        
        # Verify config files were created
        assert os.path.exists(os.path.join(self.temp_dir, "channel1_config.json"))
        assert os.path.exists(os.path.join(self.temp_dir, "channel2_config.json"))
    
    def test_load_all_channels_existing_configs(self):
        """Test loading all channels when config files exist."""
        # Create test config files
        self.create_valid_config_file("test1_config.json", "Test Channel 1")
        self.create_valid_config_file("test2_config.json", "Test Channel 2")
        
        channels = self.config_manager.load_all_channels()
        
        assert len(channels) == 2
        assert "test1" in channels
        assert "test2" in channels
        assert channels["test1"].channel_name == "Test Channel 1"
        assert channels["test2"].channel_name == "Test Channel 2"
    
    def test_get_config_path(self):
        """Test getting configuration file path."""
        path = self.config_manager.get_config_path("test_channel")
        expected_path = os.path.join(self.temp_dir, "test_channel_config.json")
        
        assert path == expected_path
    
    def test_parse_channel_config_missing_fields(self):
        """Test parsing configuration with missing required fields fails validation."""
        config_data = {
            "channel_name": "Test",
            # Missing other required fields
        }
        
        config_path = os.path.join(self.temp_dir, "incomplete.json")
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        # Should fail validation due to missing required fields
        with pytest.raises(ConfigValidationError) as exc_info:
            self.config_manager.load_channel_config(config_path)
        
        error_msg = str(exc_info.value)
        assert "idemisora must be a positive integer" in error_msg
        assert "cortinillas must be a non-empty list" in error_msg
        assert "api_config.base_url is required" in error_msg