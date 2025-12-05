#!/usr/bin/env python3
"""
Processing domain module.

This module contains the core domain logic for processing operations.
All business rules, domain models, and domain services are defined here.

The domain layer is independent of external frameworks and infrastructure,
containing only pure business logic.
"""

# Import exceptions first to avoid circular imports
from .exceptions import (
    ProcessingDomainError,
    ValidationError, 
    ValidationErrorCollection,
    ProcessingOperationError,
    InsufficientInputError,
    UnsupportedOperationError,
    InvalidProcessingModeError,
    ProcessingConstraintViolationError
)

# Import value objects
from .value_objects import (
    ProcessingModeType,
    ProcessingMode,
    ProcessingModeRegistry,
    SINGLE_FILE_MODE,
    FILES_TO_TAF_MODE, 
    RECURSIVE_MODE,
    ANALYSIS_MODE,
    InputType,
    ContentType,
    InputSpecification,
    OutputFormat,
    OutputMode,
    OutputSpecification,
    QualityLevel,
    CompressionMode,
    ProcessingOptions
)

# Import domain models
from .models import (
    ProcessingOperation,
    ProcessingResult,
    ProcessedFile,
    ProcessingStatus
)

# Import domain services
from .services import (
    ProcessingRulesService,
    ValidationService,
    ValidationRule,
    InputValidationRule,
    OutputValidationRule,
    BusinessRulesValidationRule,
    SecurityValidationRule
)

__all__ = [
    # Exceptions
    'ProcessingDomainError',
    'ValidationError',
    'ValidationErrorCollection',
    'ProcessingOperationError',
    'InsufficientInputError',
    'UnsupportedOperationError', 
    'InvalidProcessingModeError',
    'ProcessingConstraintViolationError',
    
    # Value objects - Processing modes
    'ProcessingModeType',
    'ProcessingMode',
    'ProcessingModeRegistry',
    'SINGLE_FILE_MODE',
    'FILES_TO_TAF_MODE',
    'RECURSIVE_MODE',
    'ANALYSIS_MODE',
    
    # Value objects - Input/Output
    'InputType',
    'ContentType', 
    'InputSpecification',
    'OutputFormat',
    'OutputMode',
    'OutputSpecification',
    
    # Value objects - Options
    'QualityLevel',
    'CompressionMode',
    'ProcessingOptions',
    
    # Domain models
    'ProcessingOperation',
    'ProcessingResult',
    'ProcessedFile',
    'ProcessingStatus',
    
    # Domain services
    'ProcessingRulesService',
    'ValidationService',
    'ValidationRule',
    'InputValidationRule',
    'OutputValidationRule',
    'BusinessRulesValidationRule',
    'SecurityValidationRule'
]