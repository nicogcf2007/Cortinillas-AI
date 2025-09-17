#!/usr/bin/env python3
"""
Configuration Validation Script for Cortinillas_IA

This script validates the system configuration and environment setup.
Run this before setting up the scheduled task to ensure everything is configured correctly.
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from config_manager import ConfigManager
    from models import ChannelConfig
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    print("Please ensure you're running this from the project root directory.")
    sys.exit(1)


class ConfigValidator:
    """Validates Cortinillas_IA configuration."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
    
    def validate_environment(self) -> bool:
        """Validate environment variables."""
        print("🔍 Validating environment variables...")
        
        # Check for .env file
        env_file = Path(".env")
        if not env_file.exists():
            self.errors.append(".env file not found. Run setup_tv_monitor.py to create it.")
            return False
        
        # Load environment variables from .env
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        if key not in os.environ:
                            os.environ[key] = value
        except Exception as e:
            self.errors.append(f"Error reading .env file: {e}")
            return False
        
        # Check required environment variables
        required_vars = ['DEEPGRAM_API_KEY']
        for var in required_vars:
            value = os.environ.get(var)
            if not value:
                self.errors.append(f"Required environment variable {var} is not set")
            elif value == "your_deepgram_api_key_here":
                self.errors.append(f"Environment variable {var} has placeholder value")
            else:
                self.info.append(f"✓ {var} is configured")
        
        # Check optional environment variables
        optional_vars = {
            'LOG_LEVEL': 'INFO',
            'CONFIG_DIR': 'config',
            'DATA_DIR': 'data',
            'TEMP_DIR': 'temp',
            'LOG_DIR': 'logs'
        }
        
        for var, default in optional_vars.items():
            value = os.environ.get(var, default)
            self.info.append(f"  {var}: {value}")
        
        return len(self.errors) == 0
    
    def validate_directories(self) -> bool:
        """Validate required directories exist."""
        print("🔍 Validating directory structure...")
        
        required_dirs = [
            'config',
            'data',
            'data/transcript_cache',
            'temp',
            'logs',
            'src'
        ]
        
        for directory in required_dirs:
            path = Path(directory)
            if not path.exists():
                self.errors.append(f"Required directory missing: {directory}")
            elif not path.is_dir():
                self.errors.append(f"Path exists but is not a directory: {directory}")
            else:
                self.info.append(f"✓ Directory exists: {directory}")
        
        return len(self.errors) == 0
    
    def validate_channel_configs(self) -> bool:
        """Validate channel configuration files."""
        print("🔍 Validating channel configurations...")
        
        config_dir = Path("config")
        config_files = list(config_dir.glob("channel*_config.json"))
        
        if not config_files:
            self.errors.append("No channel configuration files found")
            return False
        
        config_manager = ConfigManager("config")
        
        for config_file in config_files:
            try:
                # Load and validate configuration
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # Check required fields
                required_fields = [
                    'channel_name',
                    'idemisora',
                    'idprograma',
                    'cortinillas',
                    'deepgram_config',
                    'api_config'
                ]
                
                for field in required_fields:
                    if field not in config_data:
                        self.errors.append(f"{config_file.name}: Missing required field '{field}'")
                
                # Validate cortinillas
                cortinillas = config_data.get('cortinillas', [])
                if not cortinillas:
                    self.warnings.append(f"{config_file.name}: No cortinillas defined")
                elif not isinstance(cortinillas, list):
                    self.errors.append(f"{config_file.name}: cortinillas must be a list")
                else:
                    self.info.append(f"✓ {config_file.name}: {len(cortinillas)} cortinillas defined")
                
                # Validate deepgram_config
                deepgram_config = config_data.get('deepgram_config', {})
                required_deepgram_fields = ['language', 'model', 'smart_format']
                for field in required_deepgram_fields:
                    if field not in deepgram_config:
                        self.errors.append(f"{config_file.name}: Missing deepgram_config.{field}")
                
                # Validate Deepgram model and language
                if deepgram_config.get('model') != 'nova-3':
                    self.warnings.append(f"{config_file.name}: Recommended to use nova-3 model")
                if deepgram_config.get('language') != 'multi':
                    self.warnings.append(f"{config_file.name}: Recommended to use 'multi' language")
                
                # Validate api_config
                api_config = config_data.get('api_config', {})
                required_api_fields = ['base_url', 'cookie_sid', 'format', 'max_retries']
                for field in required_api_fields:
                    if field not in api_config:
                        self.errors.append(f"{config_file.name}: Missing api_config.{field}")
                
                self.info.append(f"✓ {config_file.name}: Configuration structure is valid")
                
            except json.JSONDecodeError as e:
                self.errors.append(f"{config_file.name}: Invalid JSON format - {e}")
            except Exception as e:
                self.errors.append(f"{config_file.name}: Error validating configuration - {e}")
        
        return len(self.errors) == 0
    
    def validate_dependencies(self) -> bool:
        """Validate Python dependencies."""
        print("🔍 Validating Python dependencies...")
        
        required_packages = [
            ('requests', 'requests'),
            ('deepgram-sdk', 'deepgram'),
            ('pandas', 'pandas'),
            ('openpyxl', 'openpyxl'),
            ('pytz', 'pytz'),
            ('python-dotenv', 'dotenv')
        ]
        
        missing_packages = []
        
        for package_name, import_name in required_packages:
            try:
                __import__(import_name)
                self.info.append(f"✓ {package_name} is installed")
            except ImportError:
                missing_packages.append(package_name)
        
        if missing_packages:
            self.errors.append(f"Missing required packages: {', '.join(missing_packages)}")
            self.errors.append("Run: pip install -r requirements.txt")
        
        return len(missing_packages) == 0
    
    def validate_permissions(self) -> bool:
        """Validate file and directory permissions."""
        print("🔍 Validating file permissions...")
        
        # Check write permissions for data directories
        write_dirs = ['data', 'temp', 'logs']
        
        for directory in write_dirs:
            path = Path(directory)
            if path.exists():
                try:
                    # Try to create a test file
                    test_file = path / '.permission_test'
                    test_file.write_text('test')
                    test_file.unlink()
                    self.info.append(f"✓ Write permission OK: {directory}")
                except Exception as e:
                    self.errors.append(f"No write permission for {directory}: {e}")
            else:
                self.warnings.append(f"Directory does not exist: {directory}")
        
        return len(self.errors) == 0
    
    def validate_network_connectivity(self) -> bool:
        """Validate network connectivity to required services."""
        print("🔍 Validating network connectivity...")
        
        try:
            import requests
            
            # Test Deepgram API connectivity
            deepgram_key = os.environ.get('DEEPGRAM_API_KEY')
            if deepgram_key and deepgram_key != 'your_deepgram_api_key_here':
                try:
                    headers = {'Authorization': f'Token {deepgram_key}'}
                    response = requests.get(
                        'https://api.deepgram.com/v1/projects',
                        headers=headers,
                        timeout=10
                    )
                    if response.status_code == 200:
                        self.info.append("✓ Deepgram API connectivity OK")
                    else:
                        self.warnings.append(f"Deepgram API returned status {response.status_code}")
                except requests.RequestException as e:
                    self.warnings.append(f"Deepgram API connectivity issue: {e}")
            else:
                self.warnings.append("Deepgram API key not configured, skipping connectivity test")
            
            # Test TV API connectivity (if configured)
            config_files = list(Path("config").glob("channel*_config.json"))
            for config_file in config_files:
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    
                    api_config = config_data.get('api_config', {})
                    base_url = api_config.get('base_url')
                    
                    if base_url:
                        response = requests.get(base_url, timeout=10)
                        if response.status_code < 500:
                            self.info.append(f"✓ TV API connectivity OK: {base_url}")
                        else:
                            self.warnings.append(f"TV API returned status {response.status_code}: {base_url}")
                    
                except requests.RequestException as e:
                    self.warnings.append(f"TV API connectivity issue for {config_file.name}: {e}")
                except Exception as e:
                    self.warnings.append(f"Error testing TV API for {config_file.name}: {e}")
        
        except ImportError:
            self.warnings.append("requests package not available, skipping network tests")
        
        return True  # Network issues are warnings, not errors
    
    def run_validation(self) -> bool:
        """Run all validation checks."""
        print("🚀 Starting Cortinillas_IA configuration validation...\n")
        
        validation_steps = [
            self.validate_environment,
            self.validate_directories,
            self.validate_dependencies,
            self.validate_channel_configs,
            self.validate_permissions,
            self.validate_network_connectivity
        ]
        
        all_passed = True
        
        for step in validation_steps:
            try:
                if not step():
                    all_passed = False
            except Exception as e:
                self.errors.append(f"Validation step failed: {e}")
                all_passed = False
            print()  # Add spacing between steps
        
        return all_passed
    
    def print_summary(self):
        """Print validation summary."""
        print("=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        
        if self.info:
            print(f"\n✅ SUCCESS ({len(self.info)} items):")
            for item in self.info:
                print(f"  {item}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)} items):")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)} items):")
            for error in self.errors:
                print(f"  {error}")
        
        print("\n" + "=" * 60)
        
        if not self.errors:
            print("🎉 VALIDATION PASSED - System is ready for deployment!")
            print("\nNext steps:")
            print("1. Set up Windows Task Scheduler using: scripts/create_scheduled_task.ps1")
            print("2. Test the system manually: python main.py --validate-only")
            print("3. Monitor logs after deployment: logs/tv_monitor_YYYYMMDD.log")
        else:
            print("❌ VALIDATION FAILED - Please fix the errors above before deployment.")
            print("\nCommon fixes:")
            print("1. Run setup script: python setup_tv_monitor.py")
            print("2. Install dependencies: pip install -r requirements.txt")
            print("3. Configure .env file with your Deepgram API key")
        
        return len(self.errors) == 0


def main():
    """Main validation function."""
    validator = ConfigValidator()
    
    try:
        success = validator.run_validation()
        validator.print_summary()
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Validation interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n\n❌ Validation failed with unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())