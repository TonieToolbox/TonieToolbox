#!/usr/bin/env python3
"""
Value objects module for processing domain.

This module exports all value objects used in the processing domain.
"""

from .processing_mode import (
    ProcessingModeType,
    ProcessingMode,
    ProcessingModeRegistry,
    SINGLE_FILE_MODE,
    FILES_TO_TAF_MODE,
    RECURSIVE_MODE,
    ANALYSIS_MODE
)

from .input_specification import (
    InputType,
    ContentType,
    InputSpecification
)

from .output_specification import (
    OutputFormat,
    OutputMode,
    OutputSpecification
)

from .processing_options import (
    QualityLevel,
    CompressionMode,
    ProcessingOptions
)

__all__ = [
    # Processing modes
    'ProcessingModeType',
    'ProcessingMode', 
    'ProcessingModeRegistry',
    'SINGLE_FILE_MODE',
    'FILES_TO_TAF_MODE',
    'RECURSIVE_MODE',
    'ANALYSIS_MODE',
    
    # Input specifications
    'InputType',
    'ContentType',
    'InputSpecification',
    
    # Output specifications
    'OutputFormat',
    'OutputMode',
    'OutputSpecification',
    
    # Processing options
    'QualityLevel',
    'CompressionMode',
    'ProcessingOptions'
]