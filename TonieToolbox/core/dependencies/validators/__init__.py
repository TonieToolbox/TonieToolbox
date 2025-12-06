#!/usr/bin/python3
"""
Binary Validators for External Dependencies.

This module provides validation functionality for external tool binaries including FFmpeg,
FFplay, and other dependencies. Validators verify binary presence, version compatibility,
and functionality through subprocess execution and output parsing. Implements the Validator
pattern for consistent dependency checking across different tools.
"""
import subprocess
import re
from typing import Optional
from ..base import BaseValidator
from ...utils import get_logger

logger = get_logger(__name__)


class FFmpegValidator(BaseValidator):
    """Validator for FFmpeg binary."""
    
    def validate(self, binary_path: str) -> bool:
        """Validate FFmpeg binary by running -version command."""
        try:
            cmd = [binary_path, '-version']
            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                timeout=5,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.debug("FFmpeg validation successful: %s", binary_path)
                return True
            else:
                self.logger.warning("FFmpeg returned error code %d: %s", 
                                  result.returncode, result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("FFmpeg validation timed out: %s", binary_path)
            return False
        except Exception as e:
            self.logger.error("Error validating FFmpeg %s: %s", binary_path, e)
            return False


class FFplayValidator(BaseValidator):
    """Validator for FFplay binary."""
    
    def validate(self, binary_path: str) -> bool:
        """Validate FFplay binary by running -version command."""
        try:
            cmd = [binary_path, '-version']
            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                timeout=5,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.debug("FFplay validation successful: %s", binary_path)
                return True
            else:
                self.logger.warning("FFplay returned error code %d: %s", 
                                  result.returncode, result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("FFplay validation timed out: %s", binary_path)
            return False
        except Exception as e:
            self.logger.error("Error validating FFplay %s: %s", binary_path, e)
            return False


class FFprobeValidator(BaseValidator):
    """Validator for FFprobe binary."""
    
    def validate(self, binary_path: str) -> bool:
        """Validate FFprobe binary by running -version command."""
        try:
            cmd = [binary_path, '-version']
            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                timeout=5,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.debug("FFprobe validation successful: %s", binary_path)
                return True
            else:
                self.logger.warning("FFprobe returned error code %d: %s", 
                                  result.returncode, result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("FFprobe validation timed out: %s", binary_path)
            return False
        except Exception as e:
            self.logger.error("Error validating FFprobe %s: %s", binary_path, e)
            return False




class ValidatorFactory:
    """Factory for creating appropriate validators."""
    
    _validators = {
        'ffmpeg': FFmpegValidator,
        'ffprobe': FFprobeValidator,
        'ffplay': FFplayValidator,
    }
    
    @classmethod
    def get_validator(cls, tool_name: str) -> Optional[BaseValidator]:
        """
        Get the appropriate validator for a tool.
        
        Args:
            tool_name: Name of the tool to validate
            
        Returns:
            BaseValidator instance or None if no validator available
        """
        validator_class = cls._validators.get(tool_name)
        if validator_class:
            return validator_class()
        
        logger.warning("No validator available for tool: %s", tool_name)
        return None