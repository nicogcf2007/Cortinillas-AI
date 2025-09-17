# Cortinillas_IA - Installation Guide

This guide provides step-by-step instructions for installing and configuring the Cortinillas_IA system on Windows.

## Prerequisites

### System Requirements

- **Operating System**: Windows 10 or Windows Server 2016+
- **Python**: Version 3.8 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: At least 2GB free space for temporary files and logs
- **Network**: Internet connectivity for API access

### Required Accounts and Keys

1. **Deepgram Account**: Sign up at [console.deepgram.com](https://console.deepgram.com/)
2. **Deepgram API Key**: Generate from your Deepgram dashboard
3. **TV API Access**: Ensure you have access to the TV backend API

## Installation Steps

### Step 1: Download and Extract

1. Download the Cortinillas_IA project files
2. Extract to a permanent location (e.g., `C:\Cortinillas_IA\`)
3. Open Command Prompt or PowerShell as Administrator
4. Navigate to the project directory:
   ```cmd
   cd C:\Cortinillas_IA
   ```

### Step 2: Install Python Dependencies

1. Ensure Python is installed and accessible:
   ```cmd
   python --version
   ```

2. Install required packages:
   ```cmd
   pip install -r requirements.txt
   ```

3. Verify installation:
   ```cmd
   pip list
   ```

### Step 3: Run Initial Setup

1. Run the setup script:
   ```cmd
   python setup_tv_monitor.py
   ```

2. The setup script will:
   - Create necessary directories
   - Generate default configuration files
   - Create .env template
   - Validate the setup

### Step 4: Configure Environment

1. Edit the `.env` file:
   ```cmd
   notepad .env
   ```

2. Update the Deepgram API key:
   ```env
   DEEPGRAM_API_KEY=your_actual_deepgram_api_key_here
   ```

3. Optionally configure other settings (see `config/env.template` for all options)

### Step 5: Configure Channels

1. Review channel configurations:
   ```cmd
   notepad config\channel1_config.json
   notepad config\channel2_config.json
   ```

2. Update the following fields for each channel:
   - `idemisora`: Channel ID in the TV system
   - `idprograma`: Program ID in the TV system
   - `cortinillas`: List of phrases to detect
   - `api_config.cookie_sid`: Session cookie for TV API

### Step 6: Validate Configuration

1. Run the validation script:
   ```cmd
   python scripts\validate_config.py
   ```

2. Fix any errors reported by the validator

3. Test the system manually:
   ```cmd
   python main.py --validate-only
   ```

### Step 7: Set Up Automated Execution

#### Option A: Automated PowerShell Script (Recommended)

1. Run PowerShell as Administrator
2. Execute the automated setup:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\create_scheduled_task.ps1
   ```

#### Option B: Manual Task Scheduler Setup

1. Follow the detailed instructions in `docs\windows_task_scheduler_setup.md`

### Step 8: Test and Monitor

1. Test the scheduled task:
   ```powershell
   Start-ScheduledTask -TaskName "Cortinillas_IA"
   ```

2. Check the logs:
   ```cmd
   type logs\tv_monitor_20250917.log
   ```

3. Verify reports are generated:
   ```cmd
   dir data\*_results.*
   ```

## Configuration Details

### Environment Variables

The system uses environment variables for configuration. Key variables include:

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `DEEPGRAM_API_KEY` | Yes | Deepgram API key | None |
| `LOG_LEVEL` | No | Logging level | INFO |
| `CONFIG_DIR` | No | Configuration directory | config |
| `DATA_DIR` | No | Data output directory | data |
| `TEMP_DIR` | No | Temporary files directory | temp |
| `LOG_DIR` | No | Log files directory | logs |

### Channel Configuration

Each channel requires a JSON configuration file with the following structure:

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

## Directory Structure

After installation, your directory structure should look like:

```
Cortinillas_IA/
├── config/
│   ├── channel1_config.json
│   ├── channel2_config.json
│   └── env.template
├── data/
│   ├── transcript_cache/
│   ├── channel1_results.json
│   ├── channel1_results.xlsx
│   ├── channel2_results.json
│   └── channel2_results.xlsx
├── docs/
│   ├── installation_guide.md
│   └── windows_task_scheduler_setup.md
├── logs/
│   └── tv_monitor_YYYYMMDD.log
├── scripts/
│   ├── create_scheduled_task.ps1
│   └── validate_config.py
├── main.py
├── src/
│   ├── config_manager.py
│   ├── audio_extractor.py
│   ├── cortinilla_detector.py
│   ├── overlap_detector.py
│   ├── report_generator.py
│   ├── time_manager.py
│   └── models.py
├── temp/
├── tests/
├── .env
├── requirements.txt
├── setup_tv_monitor.py
└── README.md
```

## Troubleshooting

### Common Installation Issues

#### Python Not Found
```
'python' is not recognized as an internal or external command
```
**Solution**: Install Python from [python.org](https://python.org) and ensure it's added to PATH.

#### Permission Denied
```
PermissionError: [Errno 13] Permission denied
```
**Solution**: Run Command Prompt as Administrator.

#### Package Installation Fails
```
ERROR: Could not install packages due to an EnvironmentError
```
**Solution**: 
1. Update pip: `python -m pip install --upgrade pip`
2. Use `--user` flag: `pip install --user -r requirements.txt`

#### Missing Visual C++ Build Tools
```
Microsoft Visual C++ 14.0 is required
```
**Solution**: Install Microsoft C++ Build Tools from [visualstudio.microsoft.com](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

### Configuration Issues

#### Invalid Deepgram API Key
```
ERROR: Deepgram API authentication failed
```
**Solution**: 
1. Verify your API key at [console.deepgram.com](https://console.deepgram.com/)
2. Check the key is correctly set in `.env`
3. Ensure no extra spaces or characters

#### TV API Connection Failed
```
ERROR: Failed to connect to TV API
```
**Solution**:
1. Verify the `base_url` in channel configuration
2. Check network connectivity to the TV API server
3. Verify the `cookie_sid` is valid and current

#### File Permission Errors
```
PermissionError: [Errno 13] Permission denied: 'logs/tv_monitor.log'
```
**Solution**:
1. Ensure the user running the task has write permissions
2. Check Windows folder permissions for the project directory
3. Run the scheduled task with appropriate privileges

### Runtime Issues

#### Task Scheduler Task Fails
**Check**:
1. Task is configured to run with highest privileges
2. Python path is correct in the task action
3. Working directory is set to project root
4. Environment variables are accessible to the SYSTEM account

#### No Audio Files Downloaded
**Check**:
1. TV API credentials are valid
2. Channel IDs (`idemisora`, `idprograma`) are correct
3. Network connectivity to TV API server
4. API rate limits are not exceeded

#### Cortinillas Not Detected
**Check**:
1. Deepgram API key is valid and has sufficient credits
2. Audio quality is adequate for speech recognition
3. Cortinilla phrases match the actual audio content
4. Language settings in Deepgram configuration are correct

## Maintenance

### Regular Tasks

#### Daily
- Check task execution status in Task Scheduler
- Review error logs if any failures occurred

#### Weekly
- Review cortinilla detection accuracy
- Check disk space usage in temp and logs directories
- Verify API key usage and remaining credits

#### Monthly
- Update Python dependencies: `pip install --upgrade -r requirements.txt`
- Archive old log files
- Review and update cortinilla lists if needed

### Updates

When updating the system:

1. **Stop the scheduled task**:
   ```powershell
   Stop-ScheduledTask -TaskName "Cortinillas_IA"
   ```

2. **Backup current configuration**:
   ```cmd
   xcopy config config_backup\ /E /I
   xcopy .env .env.backup
   ```

3. **Update source code**

4. **Test the update**:
   ```cmd
   python scripts\validate_config.py
   python main.py --validate-only
   ```

5. **Restart the scheduled task**:
   ```powershell
   Start-ScheduledTask -TaskName "Cortinillas_IA"
   ```

### Monitoring

#### Log Analysis
```cmd
# View today's log
type logs\tv_monitor_%date:~-4,4%%date:~-10,2%%date:~-7,2%.log

# Search for errors
findstr "ERROR" logs\tv_monitor_*.log

# Count successful runs
findstr "Processing completed successfully" logs\tv_monitor_*.log | find /c /v ""
```

#### Performance Monitoring
```powershell
# Check task status
Get-ScheduledTaskInfo -TaskName "Cortinillas_IA"

# Monitor disk usage
Get-ChildItem -Path temp, logs -Recurse | Measure-Object -Property Length -Sum

# Check memory usage during execution
Get-Process python | Select-Object ProcessName, WorkingSet, CPU
```

## Support

### Getting Help

1. **Check the logs** for specific error messages
2. **Run validation** to identify configuration issues
3. **Test components individually** using the test scripts
4. **Review documentation** for specific components

### Useful Commands

```cmd
# Validate configuration
python scripts\validate_config.py

# Test system without processing
python main.py --validate-only

# Run with verbose logging
python main.py --verbose

# Check Python environment
python -m pip list
python -c "import sys; print(sys.version)"

# Check scheduled task
schtasks /query /tn "Cortinillas_IA" /fo LIST /v
```

### Log Locations

- **Application logs**: `logs\tv_monitor_YYYYMMDD.log`
- **Windows Task Scheduler logs**: Event Viewer → Windows Logs → System
- **Python error logs**: Check console output when running manually

### Contact Information

For technical support:
1. Check the project documentation
2. Review the troubleshooting section
3. Examine log files for specific error messages
4. Test individual components to isolate issues