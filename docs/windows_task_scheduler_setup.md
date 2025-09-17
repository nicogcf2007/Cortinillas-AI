# Windows Task Scheduler Setup Guide

This guide provides detailed instructions for setting up the Cortinillas_IA to run automatically using Windows Task Scheduler.

## Prerequisites

1. **System Setup Complete**: Run `python setup_tv_monitor.py` first
2. **Environment Configured**: Deepgram API key set in `.env` file
3. **System Tested**: Verify the system works with `python main.py --validate-only`

## Quick Setup

### Option 1: Using PowerShell Script (Recommended)

Run the automated setup script:

```powershell
# Run as Administrator
powershell -ExecutionPolicy Bypass -File scripts/create_scheduled_task.ps1
```

### Option 2: Manual Setup

Follow the detailed manual setup instructions below.

## Manual Setup Instructions

### Step 1: Open Task Scheduler

1. Press `Win + R` to open Run dialog
2. Type `taskschd.msc` and press Enter
3. Task Scheduler will open

### Step 2: Create Basic Task

1. In the right panel, click **"Create Basic Task..."**
2. Enter task details:
   - **Name**: `Cortinillas_IA`
   - **Description**: `Automated cortinilla detection for TV channels - runs every hour`
3. Click **Next**

### Step 3: Configure Trigger

1. Select **"Daily"**
2. Click **Next**
3. Set start date to today
4. Set start time to **00:05** (5 minutes past midnight)
5. Check **"Recur every: 1 days"**
6. Click **Next**

### Step 4: Configure Action

1. Select **"Start a program"**
2. Click **Next**
3. Fill in the action details:
   - **Program/script**: `C:\Path\To\Your\Python\python.exe`
   - **Add arguments**: `"C:\Path\To\Your\Project\main.py"`
   - **Start in**: `C:\Path\To\Your\Project`

> **Note**: Replace the paths above with your actual Python installation and project paths.

4. Click **Next**
5. Review settings and click **Finish**

### Step 5: Advanced Configuration

1. In Task Scheduler Library, find your task
2. Right-click and select **"Properties"**
3. Configure the following tabs:

#### General Tab
- Check **"Run whether user is logged on or not"**
- Check **"Run with highest privileges"**
- Select **"Windows 10"** in "Configure for" dropdown

#### Triggers Tab
1. Double-click the existing trigger
2. Check **"Repeat task every: 1 hour"**
3. Set **"for a duration of: Indefinitely"**
4. Check **"Enabled"**
5. Click **OK**

#### Conditions Tab
- **Uncheck** "Start the task only if the computer is on AC power"
- **Check** "Wake the computer to run this task"
- **Check** "Start the task only if the computer is idle for: 1 minute"

#### Settings Tab
- **Check** "Allow task to be run on demand"
- **Check** "Run task as soon as possible after a scheduled start is missed"
- **Check** "If the running task does not end when requested, force it to stop"
- Set "Stop the task if it runs longer than: 30 minutes"
- Select "Do not start a new instance" in "If the task is already running" dropdown

### Step 6: Test the Task

1. Right-click your task and select **"Run"**
2. Check the **"Last Run Result"** column - should show **"0x0"** (success)
3. Verify log files are created in the `logs/` directory
4. Check that reports are generated in the `data/` directory

## Automated Setup Script

Create this PowerShell script to automate the task creation:

```powershell
# scripts/create_scheduled_task.ps1
# Run as Administrator

param(
    [string]$ProjectPath = (Get-Location).Path,
    [string]$PythonPath = (Get-Command python).Source
)

$TaskName = "Cortinillas_IA"
$TaskDescription = "Automated cortinilla detection for TV channels - runs every hour"
$ScriptPath = Join-Path $ProjectPath "main.py"

# Check if task already exists
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Write-Host "Task '$TaskName' already exists. Removing..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create the action
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$ScriptPath`"" -WorkingDirectory $ProjectPath

# Create the trigger (every hour)
$Trigger = New-ScheduledTaskTrigger -Daily -At "00:05"
$Trigger.Repetition = New-ScheduledTaskTrigger -Once -At "00:05" -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 365)

# Create the principal (run with highest privileges)
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

# Create the settings
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun -StartWhenAvailable -DontStopOnIdleEnd

# Register the task
Register-ScheduledTask -TaskName $TaskName -Description $TaskDescription -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings

Write-Host "Task '$TaskName' created successfully!" -ForegroundColor Green
Write-Host "You can test it by running: Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Cyan
```

## Troubleshooting

### Common Issues

#### Task Fails to Start
- **Check**: Python path is correct
- **Check**: Script path is correct and accessible
- **Check**: Working directory is set correctly
- **Solution**: Use full absolute paths

#### Task Runs but No Output
- **Check**: Environment variables are accessible to SYSTEM account
- **Check**: Log files for error messages
- **Solution**: Set environment variables at system level

#### Permission Denied Errors
- **Check**: Task is running with highest privileges
- **Check**: SYSTEM account has access to project directory
- **Solution**: Move project to a location accessible by SYSTEM

#### Network/API Errors
- **Check**: System has internet connectivity when task runs
- **Check**: Firewall settings allow outbound connections
- **Check**: API keys are valid and not expired

### Verification Steps

1. **Manual Test**: Run the script manually first
   ```cmd
   cd C:\Path\To\Your\Project
   python main.py --validate-only
   ```

2. **Task Test**: Run the scheduled task manually
   ```powershell
   Start-ScheduledTask -TaskName "Cortinillas_IA"
   ```

3. **Log Check**: Verify logs are being created
   ```cmd
   dir logs\tv_monitor_*.log
   ```

4. **Output Check**: Verify reports are being generated
   ```cmd
   dir data\*_results.*
   ```

### Environment Variables for SYSTEM Account

If the task runs as SYSTEM and can't access user environment variables:

1. Open **System Properties** → **Advanced** → **Environment Variables**
2. Add variables to **System variables** (not User variables):
   - `DEEPGRAM_API_KEY=your_key_here`
   - `LOG_LEVEL=INFO`

### Monitoring Task Execution

#### View Task History
1. Open Task Scheduler
2. Select your task
3. Click **"History"** tab to see execution history

#### Monitor Logs
```powershell
# Monitor today's log file
Get-Content "logs\tv_monitor_$(Get-Date -Format 'yyyyMMdd').log" -Wait -Tail 10
```

#### Check Task Status
```powershell
Get-ScheduledTask -TaskName "Cortinillas_IA" | Get-ScheduledTaskInfo
```

## Best Practices

1. **Test First**: Always test manually before scheduling
2. **Monitor Initially**: Check logs frequently after setup
3. **Regular Maintenance**: Review logs weekly for issues
4. **Backup Configs**: Keep backup copies of configuration files
5. **Update Carefully**: Test updates in development environment first

## Security Considerations

- **Principle of Least Privilege**: Only grant necessary permissions
- **Secure API Keys**: Store API keys securely, never in code
- **Network Security**: Ensure secure connections to APIs
- **File Permissions**: Restrict access to configuration and log files
- **Regular Updates**: Keep Python and dependencies updated

## Performance Optimization

- **Resource Limits**: Set appropriate CPU and memory limits
- **Cleanup**: Ensure temporary files are cleaned up
- **Monitoring**: Monitor system resources during execution
- **Scheduling**: Avoid peak system usage times if possible

## Maintenance Schedule

### Daily
- Check task execution status
- Review error logs if any

### Weekly  
- Review performance metrics
- Check disk space usage
- Verify API key validity

### Monthly
- Update dependencies if needed
- Review and optimize configurations
- Archive old log files

## Support

For additional help:

1. Check the main project documentation
2. Review log files for specific error messages
3. Test individual components using the test scripts
4. Verify all prerequisites are met