#!/usr/bin/env python3
"""
Unit tests for validation service.

Tests ValidationRule classes and ValidationService.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from TonieToolbox.core.processing.domain.services.validation_service import (
    ValidationService,
    ValidationRule,
    InputValidationRule,
    OutputValidationRule,
    BusinessRulesValidationRule,
    SecurityValidationRule
)
from TonieToolbox.core.processing.domain.models.processing_operation import ProcessingOperation
from TonieToolbox.core.processing.domain.exceptions import ValidationError


class TestValidationRule:
    """Test ValidationRule abstract base class."""
    
    def test_custom_validation_rule(self):
        """Test creating a custom validation rule."""
        class CustomRule(ValidationRule):
            def validate(self, operation):
                return []
            
            @property
            def rule_name(self):
                return "custom_rule"
        
        rule = CustomRule()
        assert rule.rule_name == "custom_rule"
        assert rule.severity == "error"  # Default severity


class TestInputValidationRule:
    """Test InputValidationRule."""
    
    def test_rule_name(self):
        """Test rule name property."""
        rule = InputValidationRule()
        assert rule.rule_name == "input_validation"
    
    def test_validate_calls_input_spec(self):
        """Test that validate calls input_spec.validate_requirements."""
        rule = InputValidationRule()
        
        # Create mock operation with input spec
        mock_operation = Mock(spec=ProcessingOperation)
        mock_operation.input_spec.validate_requirements.return_value = []
        
        errors = rule.validate(mock_operation)
        
        mock_operation.input_spec.validate_requirements.assert_called_once()
        assert errors == []
    
    def test_validate_returns_errors(self):
        """Test that validation errors are returned."""
        rule = InputValidationRule()
        
        mock_error = ValidationError("field", "message", "value")
        mock_operation = Mock(spec=ProcessingOperation)
        mock_operation.input_spec.validate_requirements.return_value = [mock_error]
        
        errors = rule.validate(mock_operation)
        
        assert len(errors) == 1
        assert errors[0] == mock_error


class TestOutputValidationRule:
    """Test OutputValidationRule."""
    
    def test_rule_name(self):
        """Test rule name property."""
        rule = OutputValidationRule()
        assert rule.rule_name == "output_validation"
    
    def test_validate_calls_output_spec(self):
        """Test that validate calls output_spec.validate_output_requirements."""
        rule = OutputValidationRule()
        
        mock_operation = Mock(spec=ProcessingOperation)
        mock_operation.output_spec.validate_output_requirements.return_value = []
        
        errors = rule.validate(mock_operation)
        
        mock_operation.output_spec.validate_output_requirements.assert_called_once()
        assert errors == []


class TestSecurityValidationRule:
    """Test SecurityValidationRule."""
    
    def test_rule_name(self):
        """Test rule name property."""
        rule = SecurityValidationRule()
        assert rule.rule_name == "security_validation"
    
    def test_path_traversal_in_input(self):
        """Test detection of path traversal in input path."""
        rule = SecurityValidationRule()
        
        mock_operation = Mock(spec=ProcessingOperation)
        mock_operation.input_spec.input_path = "/test/../etc/passwd"
        mock_operation.output_spec.output_path = "/test/output.taf"
        
        errors = rule.validate(mock_operation)
        
        assert len(errors) > 0
        assert any("path traversal" in str(err).lower() for err in errors)
    
    def test_path_traversal_in_output(self):
        """Test detection of path traversal in output path."""
        rule = SecurityValidationRule()
        
        mock_operation = Mock(spec=ProcessingOperation)
        mock_operation.input_spec.input_path = "/test/input.mp3"
        mock_operation.output_spec.output_path = "/test/../etc/output.taf"
        
        errors = rule.validate(mock_operation)
        
        assert len(errors) > 0
        assert any("path traversal" in str(err).lower() for err in errors)
    
    def test_suspicious_characters_detection(self):
        """Test detection of suspicious characters."""
        rule = SecurityValidationRule()
        
        mock_operation = Mock(spec=ProcessingOperation)
        mock_operation.input_spec.input_path = "/test/file<script>.mp3"
        mock_operation.output_spec.output_path = "/test/output.taf"
        
        errors = rule.validate(mock_operation)
        
        assert len(errors) > 0
        assert any("suspicious" in str(err).lower() for err in errors)
    
    def test_valid_paths_pass(self):
        """Test that valid paths pass validation."""
        rule = SecurityValidationRule()
        
        mock_operation = Mock(spec=ProcessingOperation)
        mock_operation.input_spec.input_path = "/test/input.mp3"
        mock_operation.output_spec.output_path = "/test/output.taf"
        
        errors = rule.validate(mock_operation)
        
        assert len(errors) == 0


class TestValidationService:
    """Test ValidationService."""
    
    def test_service_initialization(self):
        """Test validation service initializes with default rules."""
        service = ValidationService()
        
        assert "input_validation" in service._rules
        assert "output_validation" in service._rules
        assert "business_rules" in service._rules
        assert "security_validation" in service._rules
    
    def test_register_custom_rule(self):
        """Test registering a custom validation rule."""
        service = ValidationService()
        
        class CustomRule(ValidationRule):
            def validate(self, operation):
                return []
            
            @property
            def rule_name(self):
                return "custom_rule"
        
        custom_rule = CustomRule()
        service.register_rule(custom_rule)
        
        assert "custom_rule" in service._rules
        assert "custom_rule" in service._rule_order
    
    def test_unregister_rule(self):
        """Test unregistering a validation rule."""
        service = ValidationService()
        
        assert "input_validation" in service._rules
        
        service.unregister_rule("input_validation")
        
        assert "input_validation" not in service._rules
        assert "input_validation" not in service._rule_order
    
    def test_validate_operation_runs_all_rules(self):
        """Test that validate_operation runs all rules."""
        # Mock business rules service BEFORE creating ValidationService
        with patch('TonieToolbox.core.processing.domain.services.validation_service.ProcessingRulesService') as mock_service:
            mock_service.return_value.validate_operation_business_rules.return_value = []
            
            service = ValidationService()
            
            # Create properly configured mock operation
            mock_operation = Mock(spec=ProcessingOperation)
            mock_operation.input_spec = Mock()
            mock_operation.input_spec.validate_requirements = Mock(return_value=[])
            mock_operation.input_spec.input_path = "/test/input.mp3"
            
            mock_operation.output_spec = Mock()
            mock_operation.output_spec.validate_output_requirements = Mock(return_value=[])
            mock_operation.output_spec.output_path = "/test/output.taf"
            
            error_collection = service.validate_operation(mock_operation)
        
        assert error_collection is not None
        assert len(error_collection.errors) == 0
    
    def test_validate_operation_specific_rules(self):
        """Test running only specific validation rules."""
        service = ValidationService()
        
        mock_operation = Mock(spec=ProcessingOperation)
        mock_operation.input_spec.validate_requirements.return_value = []
        
        error_collection = service.validate_operation(
            mock_operation,
            rules_to_run=["input_validation"]
        )
        
        # Should only call input validation
        mock_operation.input_spec.validate_requirements.assert_called_once()
    
    def test_validate_operation_collects_errors(self):
        """Test that validation errors are collected."""
        service = ValidationService()
        
        mock_error = ValidationError("test_field", "Test error", "value")
        
        mock_operation = Mock(spec=ProcessingOperation)
        mock_operation.input_spec.validate_requirements.return_value = [mock_error]
        mock_operation.output_spec.validate_output_requirements.return_value = []
        mock_operation.input_spec.input_path = "/test/input.mp3"
        mock_operation.output_spec.output_path = "/test/output.taf"
        
        with patch('TonieToolbox.core.processing.domain.services.validation_service.ProcessingRulesService') as mock_service:
            mock_service.return_value.validate_operation_business_rules.return_value = []
            
            error_collection = service.validate_operation(mock_operation)
        
        assert len(error_collection.errors) >= 1
    
    def test_validate_operation_handles_rule_failure(self):
        """Test that service handles rule failures gracefully."""
        service = ValidationService()
        
        mock_operation = Mock(spec=ProcessingOperation)
        mock_operation.input_spec.validate_requirements.side_effect = Exception("Rule failed")
        mock_operation.output_spec.validate_output_requirements.return_value = []
        mock_operation.input_spec.input_path = "/test/input.mp3"
        mock_operation.output_spec.output_path = "/test/output.taf"
        
        with patch('TonieToolbox.core.processing.domain.services.validation_service.ProcessingRulesService') as mock_service:
            mock_service.return_value.validate_operation_business_rules.return_value = []
            
            error_collection = service.validate_operation(mock_operation)
        
        # Should create error for failed rule
        assert len(error_collection.errors) > 0
        assert any("validation_rule" in err.field for err in error_collection.errors)


class TestValidationServiceQuickValidation:
    """Test ValidationService quick validation."""
    
    def test_validate_operation_quick_exists(self):
        """Test that quick validation method exists."""
        service = ValidationService()
        assert hasattr(service, 'validate_operation_quick')
    
    def test_validate_operation_quick_with_valid_operation(self):
        """Test quick validation with valid operation."""
        service = ValidationService()
        
        mock_operation = Mock(spec=ProcessingOperation)
        mock_operation.input_spec.validate_requirements.return_value = []
        mock_operation.output_spec.validate_output_requirements.return_value = []
        mock_operation.input_spec.input_path = "/test/input.mp3"
        mock_operation.output_spec.output_path = "/test/output.taf"
        
        with patch('TonieToolbox.core.processing.domain.services.validation_service.ProcessingRulesService') as mock_service:
            mock_service.return_value.validate_operation_business_rules.return_value = []
            
            result = service.validate_operation_quick(mock_operation)
        
        assert isinstance(result, bool)
