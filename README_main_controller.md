# Cortinillas_IA - Main Controller

## Overview

The main controller (`main.py`) is the central orchestration component of the Cortinillas AI system. It coordinates the complete workflow for automated cortinilla detection in TV audio streams.

## Features

- **Automated Workflow**: Orchestrates the complete process from audio extraction to report generation
- **Multi-Channel Processing**: Handles multiple TV channels in a single execution
- **Error Handling**: Robust error handling with graceful degradation
- **Comprehensive Logging**: Detailed logging with multiple levels and file/console output
- **File Cleanup**: Automatic cleanup of temporary audio files after processing
- **Environment Validation**: Validates system configuration before processing

## Architecture

The main controller coordinates these components:

1. **ConfigManager**: Loads and validates channel configurations
2. **TimeManager**: Calculates Colombian timezone time ranges
3. **AudioExtractor**: Extracts audio from TV API backend
4. **OverlapDetector**: Detects and filters overlapping content
5. **CortinillaDetector**: Detects predefined cortinillas using Deepgram
6. **ReportGenerator**: Generates JSON and Excel reports

## Usage

### Command Line Options

```bash
# Basic execution (processes previous hour)
python main.py

# Validate environment only
python main.py --validate-only

# Custom directories
python main.py --config-dir custom_config --data-dir custom_data

# Verbose logging
python main.py --verbose
```

### Environment Variables

Required:
- `DEEPGRAM_API_KEY`: Your Deepgram API key

Optional:
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

### Directory Structure

```
project/
├── config/                 # Channel configurations
│   ├── channel1_config.json
│   └── channel2_config.json
├── data/                   # Reports and cached data
│   ├── transcript_cache/   # Previous transcriptions for overlap detection
│   ├── channel1_results.json
│   ├── channel1_results.xlsx
│   ├── channel2_results.json
│   └── channel2_results.xlsx
├── temp/                   # Temporary audio files (auto-cleaned)
├── logs/                   # Log files
└── src/                    # Source code
    └── tv_audio_monitor.py # Main controller
```

## Workflow

1. **Initialization**
   - Setup logging system
   - Initialize all components
   - Validate environment

2. **Configuration Loading**
   - Load all channel configurations
   - Validate configuration files
   - Create defaults if missing

3. **Time Calculation**
   - Calculate previous hour range in Colombian timezone
   - Format timestamps for API calls

4. **Channel Processing** (for each channel)
   - Extract audio from TV API
   - Detect overlaps with previous audio
   - Detect cortinillas with Deepgram
   - Filter overlapping content
   - Generate reports
   - Mark files for cleanup

5. **Cleanup**
   - Remove temporary audio files
   - Log processing summary

## Error Handling

The system implements multiple levels of error handling:

- **Channel-level**: If one channel fails, others continue processing
- **Retry Logic**: Network operations retry up to 3 times with exponential backoff
- **Graceful Degradation**: System continues with partial failures
- **Comprehensive Logging**: All errors logged with full context

## Logging

The logging system provides:

- **File Logging**: Detailed logs saved to `logs/tv_monitor_YYYYMMDD.log`
- **Console Logging**: Important messages displayed on console
- **Log Rotation**: Daily log files with timestamps
- **Multiple Levels**: DEBUG, INFO, WARNING, ERROR levels

## Windows Task Scheduler Integration

The system is designed to run via Windows Task Scheduler:

1. **Frequency**: Every hour
2. **Timing**: 5 minutes past each hour (e.g., 00:05, 01:05, etc.)
3. **Privileges**: Run with highest privileges
4. **Reliability**: Wake computer if needed, retry missed runs

### Task Scheduler Setup

Use the setup script to get detailed instructions:

```bash
python setup_tv_monitor.py
```

## Testing

Run the test suite to verify functionality:

```bash
python test_main_controller.py
```

The test suite covers:
- Monitor initialization
- Environment validation
- Channel processing workflow
- Error handling scenarios
- File cleanup functionality

## Performance Considerations

- **Memory Management**: Audio files processed and cleaned up immediately
- **Concurrent Processing**: Channels processed sequentially to avoid API rate limits
- **File I/O**: Efficient file handling with proper cleanup
- **Network Resilience**: Retry logic for network operations

## Troubleshooting

### Common Issues

1. **Environment Validation Failed**
   - Check `DEEPGRAM_API_KEY` is set
   - Verify configuration files exist
   - Ensure directories are writable

2. **Audio Extraction Failed**
   - Check TV API connectivity
   - Verify channel configuration parameters
   - Check network connectivity

3. **Cortinilla Detection Failed**
   - Verify Deepgram API key is valid
   - Check audio file format compatibility
   - Review cortinilla configuration

4. **Report Generation Failed**
   - Check data directory permissions
   - Verify Excel dependencies installed
   - Check disk space availability

### Log Analysis

Check the daily log files in the `logs/` directory:

```bash
# View today's log
type logs\tv_monitor_20250917.log

# Search for errors
findstr "ERROR" logs\tv_monitor_20250917.log

# Monitor real-time (if running)
Get-Content logs\tv_monitor_20250917.log -Wait -Tail 10
```

## Configuration

### Channel Configuration

Each channel requires a JSON configuration file in the `config/` directory:

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
    "video_is_public": 0,
    "is_masive": 1,
    "max_retries": 3,
    "sleep_seconds": 30
  }
}
```

### Environment Configuration

Create a `.env` file in the project root:

```env
DEEPGRAM_API_KEY=your_deepgram_api_key_here
LOG_LEVEL=INFO
```

## Requirements

The main controller requires all dependencies listed in `requirements.txt`:

- Python 3.8+
- requests (HTTP client)
- deepgram-sdk (speech recognition)
- pandas (data processing)
- openpyxl (Excel generation)
- pytz (timezone handling)

## Security Considerations

- **API Keys**: Store sensitive keys in environment variables
- **File Permissions**: Restrict access to configuration files
- **Network Security**: Validate all API responses
- **Data Privacy**: Audio files are automatically deleted after processing

## Maintenance

### Regular Tasks

1. **Monitor Logs**: Check daily logs for errors or warnings
2. **Disk Space**: Ensure adequate space for temporary files
3. **API Limits**: Monitor Deepgram usage and limits
4. **Configuration Updates**: Update cortinilla lists as needed

### Updates

When updating the system:

1. Stop the scheduled task
2. Update source code
3. Test with `--validate-only`
4. Restart the scheduled task
5. Monitor logs for issues

## Support

For issues or questions:

1. Check the logs for error details
2. Run validation: `python main.py --validate-only`
3. Test individual components using the test scripts
4. Review configuration files for accuracy