#!/usr/bin/env python3
"""
Validation service for processing operations.

This module provides centralized validation logic for all aspects
of processing operations, coordinating between different validators.
"""

from typing import List, Dict, Any, Optional, Callable
from abc import ABC, abstractmethod

from ..models.processing_operation import ProcessingOperation
from ..models.processing_result import ProcessingResult
from ..exceptions import ValidationError, ValidationErrorCollection
from .processing_rules_service import ProcessingRulesService


class ValidationRule(ABC):
    """Abstract base class for validation rules."""
    
    @abstractmethod
    def validate(self, operation: ProcessingOperation) -> List[ValidationError]:
        """Validate operation and return any errors."""
        pass
    
    @property
    @abstractmethod
    def rule_name(self) -> str:
        """Name of the validation rule."""
        pass
    
    @property
    def severity(self) -> str:
        """Severity level: 'error', 'warning', 'info'."""
        return 'error'


class InputValidationRule(ValidationRule):
    """Validates input specifications."""
    
    def validate(self, operation: ProcessingOperation) -> List[ValidationError]:
        """Validate input specification."""
        return operation.input_spec.validate_requirements()
    
    @property
    def rule_name(self) -> str:
        return "input_validation"


class OutputValidationRule(ValidationRule):
    """Validates output specifications."""
    
    def validate(self, operation: ProcessingOperation) -> List[ValidationError]:
        """Validate output specification."""
        return operation.output_spec.validate_output_requirements()
    
    @property
    def rule_name(self) -> str:
        return "output_validation"


class BusinessRulesValidationRule(ValidationRule):
    """Validates business rules using ProcessingRulesService."""
    
    def __init__(self):
        self.rules_service = ProcessingRulesService()
    
    def validate(self, operation: ProcessingOperation) -> List[ValidationError]:
        """Validate business rules."""
        return self.rules_service.validate_operation_business_rules(operation)
    
    @property
    def rule_name(self) -> str:
        return "business_rules"


class SecurityValidationRule(ValidationRule):
    """Validates security constraints."""
    
    def validate(self, operation: ProcessingOperation) -> List[ValidationError]:
        """Validate security constraints."""
        errors = []
        
        # Check for path traversal in input
        if '../' in operation.input_spec.input_path or '..\\' in operation.input_spec.input_path:
            errors.append(ValidationError(
                "input_path",
                "Path traversal detected in input path",
                operation.input_spec.input_path
            ))
        
        # Check for path traversal in output
        if (operation.output_spec.output_path and 
            ('../' in operation.output_spec.output_path or '..\\' in operation.output_spec.output_path)):
            errors.append(ValidationError(
                "output_path", 
                "Path traversal detected in output path",
                operation.output_spec.output_path
            ))
        
        # Check for suspicious filenames
        suspicious_patterns = ['..', '<', '>', '|', ':', '*', '?', '"']
        for pattern in suspicious_patterns:
            if pattern in operation.input_spec.input_path:
                errors.append(ValidationError(
                    "input_path",
                    f"Suspicious character '{pattern}' in input path",
                    pattern
                ))
        
        return errors
    
    @property
    def rule_name(self) -> str:
        return "security_validation"


class ValidationService:
    """
    Central validation service that coordinates all validation rules.
    
    This service provides a unified interface for validating processing operations
    using pluggable validation rules.
    """
    
    def __init__(self):
        """Initialize validation service with default rules."""
        self._rules: Dict[str, ValidationRule] = {}
        self._rule_order: List[str] = []
        
        # Register default validation rules
        self.register_rule(InputValidationRule())
        self.register_rule(OutputValidationRule())
        self.register_rule(BusinessRulesValidationRule())
        self.register_rule(SecurityValidationRule())
    
    def register_rule(self, rule: ValidationRule):
        """Register a validation rule."""
        self._rules[rule.rule_name] = rule
        if rule.rule_name not in self._rule_order:
            self._rule_order.append(rule.rule_name)
    
    def unregister_rule(self, rule_name: str):
        """Unregister a validation rule."""
        if rule_name in self._rules:
            del self._rules[rule_name]
            self._rule_order.remove(rule_name)
    
    def validate_operation(self, operation: ProcessingOperation, 
                         rules_to_run: Optional[List[str]] = None) -> ValidationErrorCollection:
        """
        Validate processing operation using specified rules.
        
        Args:
            operation: Processing operation to validate
            rules_to_run: List of rule names to run, or None for all rules
            
        Returns:
            ValidationErrorCollection containing all validation errors
        """
        all_errors = []
        
        # Determine which rules to run
        if rules_to_run is None:
            rules_to_run = self._rule_order
        
        # Run validation rules in order
        for rule_name in rules_to_run:
            if rule_name not in self._rules:
                continue
            
            try:
                rule = self._rules[rule_name]
                errors = rule.validate(operation)
                
                # Add rule context to errors
                for error in errors:
                    error.details = error.details or {}
                    error.details['validation_rule'] = rule_name
                
                all_errors.extend(errors)
                
            except Exception as e:
                # If validation rule itself fails, create error
                rule_error = ValidationError(
                    f"validation_rule_{rule_name}",
                    f"Validation rule '{rule_name}' failed: {str(e)}",
                    str(e)
                )
                all_errors.append(rule_error)
        
        return ValidationErrorCollection(all_errors) if all_errors else ValidationErrorCollection([])
    
    def validate_operation_quick(self, operation: ProcessingOperation) -> bool:
        """
        Quick validation that only checks critical rules.
        
        Args:
            operation: Processing operation to validate
            
        Returns:
            True if operation passes critical validation
        """
        critical_rules = ['input_validation', 'security_validation']
        errors = self.validate_operation(operation, critical_rules)
        return len(errors) == 0
    
    def validate_operation_full(self, operation: ProcessingOperation) -> ValidationErrorCollection:
        """
        Full validation using all registered rules.
        
        Args:
            operation: Processing operation to validate
            
        Returns:
            ValidationErrorCollection with all validation results
        """
        return self.validate_operation(operation)
    
    def validate_and_prepare_operation(self, operation: ProcessingOperation) -> ValidationErrorCollection:
        """
        Validate operation and prepare it for execution if valid.
        
        Args:
            operation: Processing operation to validate and prepare
            
        Returns:
            ValidationErrorCollection with validation results
        """
        errors = self.validate_operation_full(operation)
        
        if len(errors) == 0:
            # Prepare operation for execution
            try:
                # Prepare output directories if needed
                operation.output_spec.prepare_output_location()
                
                # Mark operation as validated
                operation.is_validated = True
                operation.validation_errors = []
                
            except Exception as e:
                preparation_error = ValidationError(
                    "preparation",
                    f"Failed to prepare operation for execution: {str(e)}",
                    str(e)
                )
                errors = ValidationErrorCollection([preparation_error])
        
        # Store validation results in operation
        operation.validation_errors = list(errors)
        operation.is_validated = len(errors) == 0
        
        return errors
    
    def get_validation_summary(self, errors: ValidationErrorCollection) -> Dict[str, Any]:
        """
        Get summary of validation results.
        
        Args:
            errors: Collection of validation errors
            
        Returns:
            Dictionary containing validation summary
        """
        if len(errors) == 0:
            return {
                'status': 'valid',
                'error_count': 0,
                'errors_by_rule': {},
                'critical_errors': []
            }
        
        # Group errors by validation rule
        errors_by_rule = {}
        critical_errors = []
        
        for error in errors:
            rule_name = error.details.get('validation_rule', 'unknown') if error.details else 'unknown'
            
            if rule_name not in errors_by_rule:
                errors_by_rule[rule_name] = []
            errors_by_rule[rule_name].append({
                'field': error.field,
                'message': str(error),
                'value': error.value
            })
            
            # Identify critical errors
            if rule_name in ['security_validation', 'input_validation']:
                critical_errors.append({
                    'field': error.field,
                    'message': str(error),
                    'rule': rule_name
                })
        
        return {
            'status': 'invalid',
            'error_count': len(errors),
            'errors_by_rule': errors_by_rule,
            'critical_errors': critical_errors,
            'has_critical_errors': len(critical_errors) > 0
        }
    
    def create_custom_rule(self, rule_name: str, validation_func: Callable[[ProcessingOperation], List[ValidationError]]) -> ValidationRule:
        """
        Create a custom validation rule from a function.
        
        Args:
            rule_name: Name of the custom rule
            validation_func: Function that takes operation and returns validation errors
            
        Returns:
            Custom validation rule instance
        """
        class CustomValidationRule(ValidationRule):
            def validate(self, operation: ProcessingOperation) -> List[ValidationError]:
                return validation_func(operation)
            
            @property
            def rule_name(self) -> str:
                return rule_name
        
        return CustomValidationRule()
    
    def get_available_rules(self) -> List[str]:
        """Get list of all available validation rule names."""
        return list(self._rules.keys())
    
    def get_rule_info(self, rule_name: str) -> Optional[Dict[str, str]]:
        """Get information about a specific validation rule."""
        if rule_name not in self._rules:
            return None
        
        rule = self._rules[rule_name]
        return {
            'name': rule.rule_name,
            'severity': rule.severity,
            'class': rule.__class__.__name__
        }