#!/usr/bin/python3
"""
Shell completion utilities for TonieToolbox.
Provides shell completion script generation and installation.

This module enables tab-completion for TonieToolbox commands in various shells
including bash, zsh, fish, and PowerShell. Completions include command options,
file paths, and context-specific suggestions (e.g., bitrate values, URL patterns).

Supported Shells:
    - bash: POSIX-compliant completion with file/directory suggestions
    - zsh: Advanced completion with type-based suggestions and descriptions
    - fish: Intelligent auto-completion with command descriptions
    - PowerShell: ArgumentCompleter for Windows PowerShell and pwsh

Example Usage:
    Install completions for all available shells::
    
        from TonieToolbox.core.integrations.completion import CompletionInstaller
        
        installer = CompletionInstaller()
        
        # Install to all detected shells
        if installer.install_completions():
            print("Shell completions installed successfully")
            print("Restart your shell or source your profile to activate")
        
        # Uninstall from all shells
        if installer.uninstall_completions():
            print("Shell completions removed")
    
    Using completions in bash::
    
        $ tonietoolbox --<TAB><TAB>
        # Shows all available options
        
        $ tonietoolbox --bitrate <TAB><TAB>
        64  96  128  160  192  256  320
        
        $ tonietoolbox --upload http://teddy<TAB>
        # Completes URLs
        
        $ tonietoolbox <TAB><TAB>
        # Shows audio files and directories in current folder
    
    Using completions in zsh::
    
        $ tonietoolbox --up<TAB>
        # Completes to --upload with description
        
        $ tonietoolbox --name-template <TAB>
        # Shows template suggestions like "{artist} - {title}"
    
    Using completions in PowerShell::
    
        PS> tonietoolbox --<TAB>
        # Cycles through options
        
        PS> tonietoolbox --bitrate <TAB>
        # Shows bitrate values
    
    Integration with system installation::
    
        # Completions are automatically installed with system integration
        tonietoolbox --install-integration
        
        # Or install completions only (via Python API)
        from TonieToolbox.core.integrations.completion import CompletionInstaller
        CompletionInstaller().install_completions()

Completion Features:
    - Command option completion (--version, --help, --info, etc.)
    - File path completion for input audio files
    - Bitrate suggestions (64, 96, 128, 160, 192, 256, 320 kbps)
    - URL pattern completion for TeddyCloud uploads
    - Template suggestions for --name-template and --output-to-template
    - Audio file filtering (*.mp3, *.wav, *.flac, *.ogg, *.m4a, *.taf)
"""
from .installer import CompletionInstaller

__all__ = [
    'CompletionInstaller'
]