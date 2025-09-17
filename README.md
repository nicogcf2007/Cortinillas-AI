# Cortinillas AI

An automated system for monitoring TV audio streams and detecting cortinillas (jingles/bumpers) using Deepgram speech-to-text technology. The system runs 24/7 via Windows Task Scheduler, processing audio from multiple TV channels every hour and generating comprehensive reports.

## Features

- **Automated Processing**: Runs every hour via Windows Task Scheduler
- **Multi-Channel Support**: Processes multiple TV channels simultaneously
- **Cortinilla Detection**: Uses Deepgram API for accurate speech recognition
- **Overlap Detection**: Filters duplicate content between consecutive audio segments
- **Comprehensive Reporting**: Generates JSON and Excel reports with historical data
- **Robust Error Handling**: Graceful failure handling with detailed logging
- **Colombian Timezone**: Processes audio based on Colombian local time

## Quick Start

### Option 1: Automated Installation
```cmd
# Run as Administrator
cd C:\Cortinillas_IA
install.bat
```

### Option 2: Manual Installation
```cmd
pip install -r requirements.txt
python setup_tv_monitor.py
```

**Then configure your Deepgram API key in `.env` and set up the scheduled task.**

👉 **See [QUICKSTART.md](QUICKSTART.md) for detailed 5-minute setup instructions.**

## Documentation

### Setup and Installation
- **[Quick Start Guide](QUICKSTART.md)** - Get running in 5 minutes
- **[Installation Guide](docs/installation_guide.md)** - Comprehensive setup instructions
- **[Windows Task Scheduler Setup](docs/windows_task_scheduler_setup.md)** - Automated execution setup

### System Documentation
- **[Main Controller Documentation](README_main_controller.md)** - Core system overview
- **[Cortinilla Detection](README_cortinillas.md)** - Cortinilla detection specifics

### Configuration
- **[Environment Template](config/env.template)** - All available environment variables
- **Channel Configs**: `config/channel1_config.json`, `config/channel2_config.json`

## Project Structure

```
cortinillas-ia/
├── config/                    # Configuration files
│   ├── channel1_config.json   # Channel 1 settings
│   ├── channel2_config.json   # Channel 2 settings
│   └── env.template           # Environment variables template
├── data/                      # Generated reports and cache
│   ├── transcript_cache/      # Previous transcriptions for overlap detection
│   ├── channel1_results.json  # Channel 1 accumulated results
│   ├── channel1_results.xlsx  # Channel 1 Excel report
│   ├── channel2_results.json  # Channel 2 accumulated results
│   └── channel2_results.xlsx  # Channel 2 Excel report
├── docs/                      # Documentation
│   ├── installation_guide.md  # Detailed installation instructions
│   └── windows_task_scheduler_setup.md  # Task Scheduler setup
├── logs/                      # System logs
│   └── tv_monitor_YYYYMMDD.log # Daily log files
├── scripts/                   # Setup and utility scripts
│   ├── create_scheduled_task.ps1  # Automated task creation
│   └── validate_config.py     # Configuration validation
├── src/                       # Source code
│   ├── main.py                # Main controller
│   ├── config_manager.py      # Configuration management
│   ├── audio_extractor.py     # TV API integration
│   ├── cortinilla_detector.py # Deepgram integration
│   ├── overlap_detector.py    # Overlap detection
│   ├── report_generator.py    # Report generation
│   ├── time_manager.py        # Colombian timezone handling
│   └── models.py              # Data models
├── temp/                      # Temporary audio files (auto-cleaned)
├── tests/                     # Test suite
├── .env                       # Environment variables (created during setup)
├── install.bat                # Windows installer script
├── setup_tv_monitor.py        # System setup script
├── requirements.txt           # Python dependencies
├── QUICKSTART.md              # Quick start guide
└── README.md                  # This file
```

## Core Components

### Data Models
- **ChannelConfig**: TV channel configuration and API settings
- **CortinillaResult**: Cortinilla detection results with timestamps
- **TranscriptionResult**: Deepgram speech-to-text results
- **OverlapResult**: Overlap detection between consecutive audio segments
- **Occurrence**: Individual cortinilla occurrences with timing

### System Components
- **Main Controller**: Orchestrates the complete workflow
- **Audio Extractor**: Interfaces with TV API backend for audio retrieval
- **Cortinilla Detector**: Integrates with Deepgram for speech recognition
- **Overlap Detector**: Identifies and filters duplicate content
- **Report Generator**: Creates JSON and Excel reports
- **Time Manager**: Handles Colombian timezone calculations

## Usage

### Automated Execution (Production)
The system runs automatically via Windows Task Scheduler every hour at 5 minutes past the hour (00:05, 01:05, etc.).

### Manual Execution (Testing)
```cmd
# Validate configuration
python scripts\validate_config.py

# Test system without processing
python src\main.py --validate-only

# Run manual processing
python src\main.py

# Run with verbose logging
python src\main.py --verbose
```

### Monitoring
```cmd
# Check today's log
type logs\tv_monitor_20250917.log

# Check task status
Get-ScheduledTaskInfo -TaskName "Cortinillas_IA"

# View generated reports
dir data\*_results.*
```

## Configuration

### Environment Variables (.env)
```env
# Required
DEEPGRAM_API_KEY=your_deepgram_api_key_here

# Optional
LOG_LEVEL=INFO
CONFIG_DIR=config
DATA_DIR=data
TEMP_DIR=temp
LOG_DIR=logs
```

### Channel Configuration (JSON)
```json
{
  "channel_name": "Canal 1",
  "idemisora": 1,
  "idprograma": 5,
  "cortinillas": [
    "buenos días",
    "buenas tardes",
    "buenas noches"
  ],
  "deepgram_config": {
    "language": "multi",
    "model": "nova-3",
    "smart_format": true
  },
  "api_config": {
    "base_url": "http://172.16.3.20",
    "cookie_sid": "your_session_cookie",
    "format": 11,
    "max_retries": 3,
    "sleep_seconds": 30
  }
}
```

## Testing

### Run Test Suite
```cmd
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_cortinillas_ai.py

# Run with coverage
python -m pytest tests/ --cov=src
```

### Validate System
```cmd
# Validate configuration
python scripts\validate_config.py

# Test main controller
python test_main_controller.py

# Test individual components
python -m pytest tests/test_cortinilla_detector.py
```

## Troubleshooting

### Common Issues
- **Python not found**: Install Python and add to PATH
- **Permission denied**: Run as Administrator
- **API key invalid**: Check Deepgram console
- **Task fails**: Verify Python path in Task Scheduler
- **No audio**: Check TV API credentials

### Useful Commands
```cmd
# Check Python installation
python --version
pip list

# Validate environment
python scripts\validate_config.py

# Check scheduled task
schtasks /query /tn "Cortinillas_IA" /fo LIST

# Monitor logs in real-time
Get-Content logs\tv_monitor_20250917.log -Wait -Tail 10
```

## Requirements

### System Requirements
- Windows 10 or Windows Server 2016+
- Python 3.8+
- 4GB RAM minimum (8GB recommended)
- 2GB free disk space
- Internet connectivity

### Python Dependencies
- requests (HTTP client)
- deepgram-sdk (speech recognition)
- pandas (data processing)
- openpyxl (Excel generation)
- pytz (timezone handling)
- python-dotenv (environment variables)

### External Services
- Deepgram API account and key
- TV backend API access
- Network connectivity to both services

## Support

### Getting Help
1. **Check the logs** for specific error messages
2. **Run validation** to identify configuration issues: `python scripts\validate_config.py`
3. **Review documentation** for your specific issue
4. **Test components individually** using the test scripts

### Documentation Index
- [Quick Start](QUICKSTART.md) - 5-minute setup
- [Installation Guide](docs/installation_guide.md) - Comprehensive setup
- [Task Scheduler Setup](docs/windows_task_scheduler_setup.md) - Automation setup
- [Main Controller](README_main_controller.md) - System overview
- [Environment Template](config/env.template) - Configuration options

## License

This project is proprietary software for automated cortinilla detection in TV audio streams.