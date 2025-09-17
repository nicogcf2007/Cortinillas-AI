# Cortinillas_IA - Quick Start Guide

Get the Cortinillas_IA system up and running in 5 minutes.

## Prerequisites

- Windows 10 or Windows Server 2016+
- Python 3.8+ installed
- Administrator access
- Deepgram API key ([get one here](https://console.deepgram.com/))

## Quick Installation

### Option 1: Automated Installation (Recommended)

1. **Download and extract** the project files to `C:\Cortinillas_IA\`

2. **Run the installer** as Administrator:
   ```cmd
   cd C:\Cortinillas_IA
   install.bat
   ```

3. **Configure your API key**:
   ```cmd
   notepad .env
   ```
   Replace `your_deepgram_api_key_here` with your actual Deepgram API key.

4. **Set up the scheduled task**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\create_scheduled_task.ps1
   ```

5. **Test the system**:
   ```cmd
   python main.py --validate-only
   ```

### Option 2: Manual Installation

1. **Install dependencies**:
   ```cmd
   pip install -r requirements.txt
   ```

2. **Run setup**:
   ```cmd
   python setup_tv_monitor.py
   ```

3. **Configure environment**:
   ```cmd
   notepad .env
   ```

4. **Validate configuration**:
   ```cmd
   python scripts\validate_config.py
   ```

5. **Set up Task Scheduler** (see `docs\windows_task_scheduler_setup.md`)

## Configuration

### Required Configuration

1. **Deepgram API Key** in `.env`:
   ```env
   DEEPGRAM_API_KEY=your_actual_api_key_here
   ```

2. **Channel Settings** in `config\channel1_config.json` and `config\channel2_config.json`:
   - Update `idemisora` and `idprograma` with your channel IDs
   - Update `api_config.cookie_sid` with your session cookie
   - Customize `cortinillas` list with phrases to detect

### Optional Configuration

- **Logging level** in `.env`: `LOG_LEVEL=INFO`
- **API settings** in channel configs: retry counts, timeouts
- **Cortinilla lists**: Add or remove phrases to detect

## Testing

### Validate Setup
```cmd
python scripts\validate_config.py
```

### Test System
```cmd
python main.py --validate-only
```

### Test Scheduled Task
```powershell
Start-ScheduledTask -TaskName "Cortinillas_IA"
```

### Check Logs
```cmd
type logs\tv_monitor_20250917.log
```

## Monitoring

### Check Task Status
```powershell
Get-ScheduledTaskInfo -TaskName "Cortinillas_IA"
```

### View Reports
```cmd
dir data\*_results.*
```

### Monitor Logs
```cmd
# View latest log
for /f %i in ('dir /b /o-d logs\tv_monitor_*.log') do type logs\%i & goto :done
:done

# Search for errors
findstr "ERROR" logs\tv_monitor_*.log
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Python not found | Install Python from python.org, ensure it's in PATH |
| Permission denied | Run Command Prompt as Administrator |
| API key invalid | Check your Deepgram API key at console.deepgram.com |
| Task fails to run | Verify Python path in Task Scheduler action |
| No audio downloaded | Check TV API credentials and network connectivity |

### Quick Fixes

1. **Reinstall dependencies**: `pip install --upgrade -r requirements.txt`
2. **Reset configuration**: Delete config files and run `python setup_tv_monitor.py`
3. **Check permissions**: Ensure write access to project directory
4. **Validate environment**: Run `python scripts\validate_config.py`

## File Structure

```
Cortinillas_IA/
├── config/           # Channel configurations
├── data/            # Generated reports
├── logs/            # System logs
├── temp/            # Temporary audio files (auto-cleaned)
├── src/             # Source code
├── scripts/         # Setup and utility scripts
├── docs/            # Documentation
├── .env             # Environment variables
└── install.bat      # Quick installer
```

## What Happens When Running

1. **Every hour at 5 minutes past** (00:05, 01:05, etc.)
2. **Extracts audio** from both TV channels for the previous hour
3. **Detects cortinillas** using Deepgram speech recognition
4. **Filters overlaps** between consecutive audio segments
5. **Generates reports** in JSON and Excel formats
6. **Cleans up** temporary audio files
7. **Logs everything** for monitoring and troubleshooting

## Getting Help

1. **Check logs** first: `logs\tv_monitor_YYYYMMDD.log`
2. **Run validation**: `python scripts\validate_config.py`
3. **Review documentation**:
   - Full installation guide: `docs\installation_guide.md`
   - Task Scheduler setup: `docs\windows_task_scheduler_setup.md`
   - Main documentation: `README_main_controller.md`

## Next Steps

After successful setup:

1. **Monitor the first few runs** to ensure everything works correctly
2. **Review generated reports** in the `data\` directory
3. **Customize cortinilla lists** based on your specific needs
4. **Set up monitoring** for the scheduled task
5. **Plan regular maintenance** (weekly log reviews, monthly updates)

---

**Need more detailed instructions?** See `docs\installation_guide.md`

**Having issues?** Check the troubleshooting section in the full documentation.