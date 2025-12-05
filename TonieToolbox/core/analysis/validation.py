#!/usr/bin/python3
"""
Validation functions for TAF files.
"""
from pathlib import Path
from typing import Dict, Any

from .header import get_header_info
from ..processing.infrastructure.services.taf_analysis_service import TafAnalysisService
from ..utils import get_logger

logger = get_logger(__name__)


def check_tonie_file(filename: str) -> bool:
    """
    Check if a TAF file is valid.
    
    Args:
        filename: Path to the TAF file
        
    Returns:
        True if valid, False otherwise
    """
    try:
        header_info = get_header_info(filename)
        return header_info.get('valid', False)
    except Exception:
        return False


def check_tonie_file_cli(filename: str) -> bool:
    """
    CLI version of check_tonie_file with minimal output.
    
    Args:
        filename: Path to the TAF file
        
    Returns:
        True if valid, False otherwise
    """
    return check_tonie_file(filename)


def compare_taf_files(file1: str, file2: str, detailed: bool = False) -> bool:
    """
    Compare two TAF files for differences.
    
    Args:
        file1: Path to first TAF file
        file2: Path to second TAF file  
        detailed: Whether to show detailed comparison
        
    Returns:
        True if files are identical, False otherwise
    """
    try:
        analysis_service = TafAnalysisService(logger)
        comparison = analysis_service.compare_taf_files(Path(file1), Path(file2))
        
        if 'error' in comparison:
            logger.error(f"Comparison error: {comparison['error']}")
            return False
        
        # Print comparison results
        print(f"\n{'='*60}")
        print(f"Comparing TAF files:")
        print(f"  File 1: {file1}")
        print(f"  File 2: {file2}")
        print(f"{'='*60}")
        
        if comparison['identical']:
            print("\n✓ Files are IDENTICAL")
            return True
        
        print(f"\n✗ Files are DIFFERENT")
        print(f"\nFile size difference: {comparison['file_size_diff']} bytes")
        
        if comparison['differences']:
            print(f"\nDifferences found:")
            for diff in comparison['differences']:
                print(f"  - {diff}")
        
        if detailed and comparison['metadata_diff']:
            print(f"\nMetadata differences:")
            for key, values in comparison['metadata_diff'].items():
                print(f"  {key}:")
                print(f"    File 1: {values['file1']}")
                print(f"    File 2: {values['file2']}")
        
        # Show detailed OGG page comparison if requested
        if detailed and 'ogg_pages_diff' in comparison:
            ogg_diff = comparison['ogg_pages_diff']
            print(f"\nDetailed OGG Page Analysis:")
            print(f"  Total pages in File 1: {ogg_diff['total_pages_file1']}")
            print(f"  Total pages in File 2: {ogg_diff['total_pages_file2']}")
            
            if ogg_diff['page_differences']:
                print(f"\n  OGG Page Differences ({len(ogg_diff['page_differences'])} pages):")
                for diff in ogg_diff['page_differences']:
                    if 'difference' in diff:
                        print(f"    Page {diff['page_index']}: {diff['difference']}")
                    elif 'differences' in diff:
                        print(f"    Page {diff['page_index']} (Page #{diff['page_no']}):")
                        for key, values in diff['differences'].items():
                            print(f"      {key}: {values['file1']} vs {values['file2']}")
            else:
                print(f"    All OGG pages are identical")
        
        print(f"{'='*60}\n")
        return False
        
    except Exception as e:
        logger.error(f"Failed to compare TAF files: {e}")
        return False