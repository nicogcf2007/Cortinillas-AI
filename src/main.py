"""
Cortinillas_IA - Main Controller

Main entry point for the Cortinillas_IA system that orchestrates the complete workflow:
1. Load channel configurations
2. Calculate time ranges for audio extraction
3. Extract audio from TV API
4. Detect cortinillas with overlap filtering
5. Generate reports and cleanup files

This script is designed to be executed by Windows Task Scheduler every hour.
"""
import argparse
import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, use system environment variables

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

try:
    from models import ChannelConfig, ProcessingResult
    from config_manager import ConfigManager
    from time_manager import get_previous_hour_range, format_timestamp_for_filename
    from audio_extractor import AudioExtractor
    from overlap_detector import OverlapDetector
    from cortinilla_detector import CortinillaDetector
    from report_generator import ReportGenerator
    from exceptions import (
        TVAudioMonitorError, ConfigurationError, AudioExtractionError,
        TranscriptionError, ReportGenerationError
    )
    from error_handler import ErrorHandler, create_error_context, safe_execute
except ImportError:
    # Handle relative imports when run as module
    from .models import ChannelConfig, ProcessingResult
    from .config_manager import ConfigManager
    from .time_manager import get_previous_hour_range, format_timestamp_for_filename
    from .audio_extractor import AudioExtractor
    from .overlap_detector import OverlapDetector
    from .cortinilla_detector import CortinillaDetector
    from .report_generator import ReportGenerator
    from .exceptions import (
        TVAudioMonitorError, ConfigurationError, AudioExtractionError,
        TranscriptionError, ReportGenerationError
    )
    from .error_handler import ErrorHandler, create_error_context, safe_execute


class CortinillasAI:
    """Main controller for the Cortinillas AI system."""
    
    def __init__(self, config_dir: str = "config", data_dir: str = "data", 
                 temp_dir: str = "temp", log_dir: str = "logs"):
        """
        Initialize the Cortinillas AI system.
        
        Args:
            config_dir: Directory containing channel configurations
            data_dir: Directory for storing reports and data
            temp_dir: Directory for temporary audio files
            log_dir: Directory for log files
        """
        self.config_dir = config_dir
        self.data_dir = data_dir
        self.temp_dir = temp_dir
        self.log_dir = log_dir
        
        # Ensure directories exist
        for directory in [self.data_dir, self.temp_dir, self.log_dir]:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.config_manager = ConfigManager(config_dir)
        self.overlap_detector = OverlapDetector(os.path.join(data_dir, "transcript_cache"))
        self.cortinilla_detector = CortinillaDetector(self.overlap_detector)
        self.report_generator = ReportGenerator(data_dir)
        
        # Setup logging
        self.logger = self.setup_logging()
        
        # Initialize error handler
        self.error_handler = ErrorHandler(max_retries=3, base_delay=2.0)
        
        # Track processed files for cleanup
        self.temp_files: List[str] = []
    
    def setup_logging(self) -> logging.Logger:
        """
        Setup comprehensive logging system.
        
        Returns:
            Configured logger instance
        """
        # Create logger
        logger = logging.getLogger("cortinillas_ai")
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # File handler for detailed logs
        log_filename = f"tv_monitor_{datetime.now().strftime('%Y%m%d')}.log"
        log_path = os.path.join(self.log_dir, log_filename)
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        
        # Console handler for important messages
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        
        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # Set levels for other loggers to reduce noise
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        
        return logger
    
    def run(self) -> bool:
        """
        Run the complete Cortinillas AI workflow.
        
        Returns:
            bool: True if all channels processed successfully, False otherwise
        """
        self.logger.info("=" * 60)
        self.logger.info("Cortinillas AI - Starting execution")
        self.logger.info("=" * 60)
        
        try:
            # Load channel configurations
            channels = self.load_channel_configurations()
            if not channels:
                self.logger.error("No valid channel configurations found")
                return False
            
            # Calculate time range for audio extraction
            start_time, end_time = get_previous_hour_range()
            self.logger.info(f"Processing time range: {start_time} to {end_time}")
            
            # Process each channel
            results = []
            for channel_name, config in channels.items():
                result = self.process_channel(config, start_time, end_time)
                results.append(result)
            
            # Summary of results
            successful = sum(1 for r in results if r.success)
            total = len(results)
            
            self.logger.info(f"Processing completed: {successful}/{total} channels successful")
            
            if successful == 0:
                self.logger.error("All channels failed to process")
                return False
            elif successful < total:
                self.logger.warning(f"{total - successful} channels failed to process")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Critical error in main workflow: {e}")
            self.logger.error(traceback.format_exc())
            return False
        
        finally:
            # Always cleanup temporary files
            self.cleanup_temp_files()
            
            # Log final summary with error statistics
            self.log_final_summary(successful > 0 if 'successful' in locals() else False)
            
            self.logger.info("Cortinillas AI - Execution completed")
    
    def load_channel_configurations(self) -> Dict[str, ChannelConfig]:
        """
        Load all channel configurations.
        
        Returns:
            Dictionary of channel configurations
        """
        context = create_error_context("load_channel_configurations")
        
        try:
            self.logger.info("Loading channel configurations...")
            
            channels = safe_execute(
                self.config_manager.load_all_channels,
                default_return={},
                error_handler=self.error_handler,
                context=context
            )
            
            if not channels:
                self.logger.error("No channel configurations loaded")
                return {}
            
            self.logger.info(f"Loaded {len(channels)} channel configurations:")
            for channel_name, config in channels.items():
                self.logger.info(f"  - {channel_name}: {config.channel_name} "
                               f"(ID: {config.idemisora}, Program: {config.idprograma})")
            
            return channels
            
        except Exception as e:
            self.error_handler.handle_error(e, context, critical=True)
            return {}
    
    def process_channel(self, config: ChannelConfig, start_time: datetime, 
                       end_time: datetime) -> ProcessingResult:
        """
        Process a single channel through the complete workflow.
        
        Args:
            config: Channel configuration
            start_time: Start time for audio extraction
            end_time: End time for audio extraction
            
        Returns:
            ProcessingResult with processing outcome
        """
        channel_name = config.channel_name
        self.logger.info(f"Processing channel: {channel_name}")
        
        try:
            # Step 1: Extract audio
            audio_path = self.extract_channel_audio(config, start_time, end_time)
            if not audio_path:
                return ProcessingResult(
                    channel_name=channel_name,
                    success=False,
                    execution_time_seconds=0.0,
                    cortinillas_found=0,
                    error_message="Audio extraction failed"
                )
            
            # Step 2: Detect cortinillas with overlap filtering
            cortinilla_result = self.detect_channel_cortinillas(config, audio_path, start_time, start_time, end_time)
            
            # Step 3: Generate reports
            self.generate_channel_reports(cortinilla_result)
            
            # Step 4: Mark audio file for cleanup
            self.temp_files.append(audio_path)
            
            self.logger.info(f"Successfully processed channel {channel_name}: "
                           f"{cortinilla_result.total_cortinillas} cortinillas detected")
            
            return ProcessingResult(
                channel_name=channel_name,
                success=True,
                execution_time_seconds=0.0,
                cortinillas_found=cortinilla_result.total_cortinillas if cortinilla_result else 0,
                cortinilla_results=[cortinilla_result] if cortinilla_result else []
            )
            
        except Exception as e:
            error_msg = f"Error processing channel {channel_name}: {e}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            
            return ProcessingResult(
                channel_name=channel_name,
                success=False,
                execution_time_seconds=0.0,
                cortinillas_found=0,
                error_message=str(e)
            )
    
    def extract_channel_audio(self, config: ChannelConfig, start_time: datetime, 
                             end_time: datetime) -> Optional[str]:
        """
        Extract audio for a channel.
        
        Args:
            config: Channel configuration
            start_time: Start time for extraction
            end_time: End time for extraction
            
        Returns:
            Path to extracted audio file or None if failed
        """
        context = create_error_context(
            "extract_channel_audio",
            channel=config.channel_name,
            timestamp=start_time
        )
        
        try:
            self.logger.info(f"Extracting audio for {config.channel_name}")
            
            # Generate clip name with timestamp
            timestamp_str = format_timestamp_for_filename(start_time)
            clip_name = f"{config.channel_name}_{timestamp_str}"
            
            # Extract audio using AudioExtractor with error handling
            def extract_with_extractor():
                with AudioExtractor(config) as extractor:
                    return extractor.extract_audio(
                        start_time=start_time,
                        end_time=end_time,
                        output_dir=self.temp_dir,
                        clip_name=clip_name
                    )
            
            audio_path = safe_execute(
                extract_with_extractor,
                default_return=None,
                error_handler=self.error_handler,
                context=context
            )
            
            if audio_path:
                self.logger.info(f"Audio extracted successfully: {os.path.basename(audio_path)}")
            else:
                self.logger.error(f"Audio extraction failed for {config.channel_name}")
            
            return audio_path
            
        except Exception as e:
            self.error_handler.handle_error(e, context)
            return None
    
    def detect_channel_cortinillas(self, config: ChannelConfig, audio_path: str, 
                                  timestamp: datetime, start_time: datetime = None, 
                                  end_time: datetime = None):
        """
        Detect cortinillas in channel audio with overlap filtering.
        
        Args:
            config: Channel configuration
            audio_path: Path to audio file
            timestamp: Processing timestamp
            
        Returns:
            CortinillaResult with detection results
        """
        context = create_error_context(
            "detect_channel_cortinillas",
            channel=config.channel_name,
            timestamp=timestamp,
            additional_info={"audio_file": os.path.basename(audio_path)}
        )
        
        try:
            self.logger.info(f"Detecting cortinillas for {config.channel_name}")
            
            # Detect cortinillas (includes overlap filtering) with error handling
            result = safe_execute(
                self.cortinilla_detector.detect_cortinillas,
                audio_path,
                config,
                timestamp,
                start_time,
                end_time,
                error_handler=self.error_handler,
                context=context
            )
            
            if result is None:
                raise TranscriptionError("Cortinilla detection returned no results")
            
            # Log results summary
            if result.overlap_filtered:
                self.logger.info(f"Overlap detected and filtered: "
                               f"{result.overlap_duration:.2f}s removed")
            
            cortinilla_summary = []
            for cortinilla_type, count in result.cortinillas_by_type.items():
                if count > 0:
                    cortinilla_summary.append(f"{cortinilla_type}: {count}")
            
            if cortinilla_summary:
                self.logger.info(f"Cortinillas found: {', '.join(cortinilla_summary)}")
            else:
                self.logger.info("No cortinillas detected")
            
            return result
            
        except Exception as e:
            self.error_handler.handle_error(e, context, critical=True)
            raise
    
    def generate_channel_reports(self, result) -> None:
        """
        Generate JSON and Excel reports for channel results.
        
        Args:
            result: CortinillaResult to include in reports
        """
        context = create_error_context(
            "generate_channel_reports",
            channel=result.channel,
            timestamp=result.timestamp
        )
        
        try:
            self.logger.info(f"Generating reports for {result.channel}")
            
            # Update JSON report with error handling
            safe_execute(
                self.report_generator.update_json_report,
                result,
                error_handler=self.error_handler,
                context=f"{context} | json_report"
            )
            
            # Update Excel report with error handling
            safe_execute(
                self.report_generator.update_excel_report,
                result,
                error_handler=self.error_handler,
                context=f"{context} | excel_report"
            )
            
            self.logger.info(f"Reports updated successfully for {result.channel}")
            
        except Exception as e:
            self.error_handler.handle_error(e, context, critical=True)
            raise
    
    def cleanup_temp_files(self) -> None:
        """
        Clean up temporary audio files after processing.
        """
        if not self.temp_files:
            return
        
        self.logger.info("Cleaning up temporary files...")
        
        cleaned_count = 0
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    cleaned_count += 1
                    self.logger.debug(f"Removed temporary file: {os.path.basename(file_path)}")
            except Exception as e:
                self.logger.warning(f"Failed to remove temporary file {file_path}: {e}")
        
        self.logger.info(f"Cleaned up {cleaned_count}/{len(self.temp_files)} temporary files")
        self.temp_files.clear()
    
    def get_error_summary(self) -> dict:
        """
        Get summary of errors encountered during processing.
        
        Returns:
            Dictionary with error statistics
        """
        return self.error_handler.get_error_summary()
    
    def log_final_summary(self, success: bool) -> None:
        """
        Log final summary including error statistics.
        
        Args:
            success: Whether the overall processing was successful
        """
        error_summary = self.get_error_summary()
        
        self.logger.info("=" * 60)
        self.logger.info("PROCESSING SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Overall Status: {'SUCCESS' if success else 'FAILED'}")
        self.logger.info(f"Total Errors: {error_summary.get('total_errors', 0)}")
        
        if error_summary.get('error_counts'):
            self.logger.info("Error Breakdown:")
            for context, count in error_summary['error_counts'].items():
                self.logger.info(f"  - {context}: {count} errors")
        
        if error_summary.get('last_errors'):
            self.logger.info("Recent Errors:")
            for context, error_info in error_summary['last_errors'].items():
                self.logger.info(f"  - {context}: {error_info.get('error_type', 'Unknown')} - "
                               f"{error_info.get('error_message', 'No message')}")
        
        self.logger.info("=" * 60)
    
    def validate_environment(self) -> bool:
        """
        Validate that the environment is properly configured.
        
        Returns:
            bool: True if environment is valid, False otherwise
        """
        self.logger.info("Validating environment...")
        
        errors = []
        
        # Check for Deepgram API key
        if not os.getenv("DEEPGRAM_API_KEY"):
            errors.append("DEEPGRAM_API_KEY environment variable not set")
        
        # Check required directories
        required_dirs = [self.config_dir, self.data_dir, self.temp_dir, self.log_dir]
        for directory in required_dirs:
            if not os.path.exists(directory):
                try:
                    Path(directory).mkdir(parents=True, exist_ok=True)
                    self.logger.info(f"Created directory: {directory}")
                except Exception as e:
                    errors.append(f"Cannot create directory {directory}: {e}")
        
        # Check if we can load configurations
        try:
            channels = self.config_manager.load_all_channels()
            if not channels:
                errors.append("No valid channel configurations found")
        except Exception as e:
            errors.append(f"Cannot load channel configurations: {e}")
        
        if errors:
            self.logger.error("Environment validation failed:")
            for error in errors:
                self.logger.error(f"  - {error}")
            return False
        
        self.logger.info("Environment validation passed")
        return True


def main():
    """Main entry point for the Cortinillas AI system."""
    parser = argparse.ArgumentParser(description="Cortinillas AI - Automated cortinilla detection")
    parser.add_argument("--config-dir", default="config", 
                       help="Directory containing channel configurations")
    parser.add_argument("--data-dir", default="data", 
                       help="Directory for storing reports and data")
    parser.add_argument("--temp-dir", default="temp", 
                       help="Directory for temporary audio files")
    parser.add_argument("--log-dir", default="logs", 
                       help="Directory for log files")
    parser.add_argument("--validate-only", action="store_true",
                       help="Only validate environment, don't process audio")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Initialize monitor
    monitor = CortinillasAI(
        config_dir=args.config_dir,
        data_dir=args.data_dir,
        temp_dir=args.temp_dir,
        log_dir=args.log_dir
    )
    
    # Set verbose logging if requested
    if args.verbose:
        monitor.logger.setLevel(logging.DEBUG)
        for handler in monitor.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.setLevel(logging.DEBUG)
    
    # Validate environment
    if not monitor.validate_environment():
        monitor.logger.error("Environment validation failed. Exiting.")
        sys.exit(1)
    
    # If validate-only flag is set, exit after validation
    if args.validate_only:
        monitor.logger.info("Environment validation completed successfully")
        sys.exit(0)
    
    # Run the main workflow
    success = monitor.run()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()