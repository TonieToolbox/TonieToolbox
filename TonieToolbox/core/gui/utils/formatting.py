#!/usr/bin/env python3
"""
Formatting utilities for GUI components and CLI output.
"""

from typing import List, Any


def format_chapter_info(tonie_header: Any, page_count: int, chapter_durations: List[str]) -> str:
    """
    Format chapter information for CLI display.
    
    Creates a formatted, human-readable representation of TAF file chapter
    structure with Unicode icons for visual clarity. Handles single chapters,
    multiple chapters, and missing chapter information gracefully.
    
    Args:
        tonie_header: The Tonie protobuf header object
        page_count: Total number of pages in the file
        chapter_durations: List of chapter duration strings in "MM:SS.CC" format
        
    Returns:
        Formatted chapter information string
    
    Example:
        Display chapter information in CLI::
        
            from TonieToolbox.core.gui.utils.formatting import format_chapter_info
            from TonieToolbox.core.analysis import analyze_taf_file
            
            # Analyze TAF file
            result = analyze_taf_file('audio.taf')
            
            # Format and display chapters
            chapter_info = format_chapter_info(
                result.tonie_header,
                result.page_count,
                result.chapter_durations
            )
            print(chapter_info)
            # Output:
            # 📖 Chapter Information
            # ============================================================
            # 📚 Chapters: 3
            # 📄 Chapter Pages: [0, 150, 300]
            # 📖 Chapter 1: Page 0, Duration 05:23.45
            # 📖 Chapter 2: Page 150, Duration 04:12.30
            # 📖 Chapter 3: Page 300, Duration 03:45.67
        
        Handle single chapter file::
        
            chapter_info = format_chapter_info(
                single_chapter_header,
                100,
                ['10:30.50']
            )
            # Output:
            # 📖 Chapter Information
            # ============================================================
            # 📚 Chapters: 1 (single chapter)
            # 📄 Chapter Pages: [0]
            # 📖 Chapter 1: Page 0, Duration 10:30.50
        
        Display in GUI info dialog::
        
            info_text = format_chapter_info(header, page_count, durations)
            info_dialog = QMessageBox()
            info_dialog.setText(info_text)
            info_dialog.setFont(QFont('Monospace'))
            info_dialog.exec()
    """
    output_lines = []
    
    # Chapter Information header
    output_lines.append("📖 Chapter Information")
    output_lines.append("=" * 60)
    
    # Check if we have chapter information
    if hasattr(tonie_header, 'chapterPages') and len(tonie_header.chapterPages) > 1:
        # Multiple chapters
        output_lines.append(f"📚 Chapters: {len(tonie_header.chapterPages)}")
        output_lines.append(f"📄 Chapter Pages: {list(tonie_header.chapterPages)}")
        
        # Individual chapter details
        for i, (chapter_page, duration) in enumerate(zip(tonie_header.chapterPages, chapter_durations)):
            chapter_num = i + 1
            output_lines.append(f"📖 Chapter {chapter_num}: Page {chapter_page}, Duration {duration}")
            
    elif hasattr(tonie_header, 'chapterPages') and len(tonie_header.chapterPages) == 1:
        # Single chapter
        output_lines.append(f"📚 Chapters: 1 (single chapter)")
        output_lines.append(f"📄 Chapter Pages: {list(tonie_header.chapterPages)}")
        if chapter_durations:
            output_lines.append(f"📖 Chapter 1: Page {tonie_header.chapterPages[0]}, Duration {chapter_durations[0]}")
    else:
        # No chapter information available
        output_lines.append("📚 Chapters: No chapter information available")
        output_lines.append("📄 Chapter Pages: []")
        if chapter_durations:
            output_lines.append(f"📖 Total Duration: {chapter_durations[0] if chapter_durations else 'Unknown'}")
    
    return "\n".join(output_lines)