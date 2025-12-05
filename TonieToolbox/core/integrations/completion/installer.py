#!/usr/bin/python3
"""
Shell completion support for TonieToolbox.
Generates and installs completion scripts for various shells.
"""
import os
import shutil
import subprocess
from ...utils import get_logger
logger = get_logger(__name__)

class CompletionInstaller:
    """Handles installation of shell completion scripts for TonieToolbox.
    
    This class detects available shells (bash, zsh, fish, PowerShell) on the system
    and installs appropriate completion scripts to enable tab-completion of
    TonieToolbox commands and arguments.
    
    Example:
        Basic installation of completions for all detected shells::
        
            installer = CompletionInstaller()
            if installer.install_completions():
                print("Completion scripts installed successfully")
                print("Restart your shell or source the completion files")
        
        Uninstalling all completion scripts::
        
            installer = CompletionInstaller()
            if installer.uninstall_completions():
                print("Completion scripts removed")
        
        Checking which shells have completion support::
        
            installer = CompletionInstaller()
            for shell in ['bash', 'zsh', 'fish', 'pwsh']:
                available = installer._is_shell_available(shell)
                print(f"{shell}: {'Available' if available else 'Not found'}")
            # Output:
            # bash: Available
            # zsh: Available
            # fish: Not found
            # pwsh: Available
    """
    def __init__(self):
        self.supported_shells = {
            'bash': self._generate_bash_completion,
            'zsh': self._generate_zsh_completion,
            'fish': self._generate_fish_completion,
            'pwsh': self._generate_powershell_completion
        }
    def install_completions(self):
        """Install completion scripts for all detected shells.
        
        Detects available shells on the system (bash, zsh, fish, PowerShell) and
        installs appropriate completion scripts. The installer automatically chooses
        the correct installation location based on the operating system and shell.
        
        Returns:
            True if at least one completion was installed, False otherwise
        
        Shell-Specific Installation:
            bash: ~/.local/share/bash-completion/completions/tonietoolbox
            zsh: ~/.local/share/zsh/site-functions/_tonietoolbox
            fish: ~/.config/fish/completions/tonietoolbox.fish
            PowerShell: Appends to $PROFILE file
        
        Post-Installation:
            For shells to recognize new completions, you may need to:
            - bash: Restart terminal or run `source ~/.bashrc`
            - zsh: Restart terminal or run `source ~/.zshrc`
            - fish: Completions available immediately (no restart needed)
            - PowerShell: Restart PowerShell or reload profile with `. $PROFILE`
        
        Example:
            Install completions during integration setup::
            
                from TonieToolbox.core.integrations.completion import CompletionInstaller
                
                installer = CompletionInstaller()
                if installer.install_completions():
                    print("✓ Shell completions installed")
                    print("Restart your terminal or reload your shell profile")
                else:
                    print("No shells found or installation failed")
            
            Manual installation via CLI::
            
                # Using tonietoolbox command
                tonietoolbox --install-integration
                # This installs both context menus and shell completions
            
            Test completions after installation::
            
                # In bash/zsh:
                $ tonietoolbox --<TAB>
                # Shows available options:
                # --version --help --info --play --gui --upload ...
                
                $ tonietoolbox --bitrate <TAB>
                # Shows common bitrates: 64 96 128 160 192 256 320
                
                $ tonietoolbox --upload http://teddy<TAB>
                # Completes URLs
            
            PowerShell example::
            
                PS> tonietoolbox --<TAB>
                # Cycles through available options
                
                PS> tonietoolbox --bitrate <TAB>
                # Shows bitrate suggestions
        """
        installed_count = 0
        for shell_name, generator in self.supported_shells.items():
            if self._is_shell_available(shell_name):
                try:
                    if self._install_shell_completion(shell_name, generator):
                        logger.info(f"Installed {shell_name} completion script")
                        installed_count += 1
                    else:
                        logger.debug(f"Failed to install {shell_name} completion")
                except Exception as e:
                    logger.debug(f"Error installing {shell_name} completion: {e}")
            else:
                logger.debug(f"Shell {shell_name} not available, skipping completion")
        if installed_count > 0:
            logger.info(f"Installed completion scripts for {installed_count} shell(s)")
            logger.info("You may need to restart your shell or source the completion files")
            return True
        else:
            logger.debug("No completion scripts were installed")
            return False
    def uninstall_completions(self):
        """Remove all installed completion scripts.
        
        Removes completion files from all standard installation locations for
        bash, zsh, fish, and PowerShell. For PowerShell, removes the completion
        section from the profile file without deleting the entire profile.
        
        Returns:
            True if at least one completion was removed, False if none found
        
        Cleanup Locations:
            bash: ~/.bash_completion.d/, ~/.local/share/bash-completion/completions/
            zsh: ~/.zsh/completions/, ~/.local/share/zsh/site-functions/
            fish: ~/.config/fish/completions/
            PowerShell: Removes completion section from $PROFILE
        
        Example:
            Uninstall all completions::
            
                from TonieToolbox.core.integrations.completion import CompletionInstaller
                
                installer = CompletionInstaller()
                if installer.uninstall_completions():
                    print("✓ Shell completions removed")
                    print("Restart your terminal for changes to take effect")
                else:
                    print("No completion files found to remove")
            
            Uninstall via CLI::
            
                tonietoolbox --uninstall-integration
                # Removes both context menus and shell completions
            
            Manual removal::
            
                # bash
                rm ~/.local/share/bash-completion/completions/tonietoolbox
                
                # zsh
                rm ~/.local/share/zsh/site-functions/_tonietoolbox
                
                # fish
                rm ~/.config/fish/completions/tonietoolbox.fish
                
                # PowerShell - edit profile and remove TonieToolbox section
                notepad $PROFILE  # Windows
                nano ~/.config/powershell/Microsoft.PowerShell_profile.ps1  # Linux
        """
        removed_count = 0
        completion_files = [
            os.path.expanduser('~/.bash_completion.d/tonietoolbox'),
            os.path.expanduser('~/.local/share/bash-completion/completions/tonietoolbox'),
            '/etc/bash_completion.d/tonietoolbox',
            os.path.expanduser('~/.zsh/completions/_tonietoolbox'),
            os.path.expanduser('~/.local/share/zsh/site-functions/_tonietoolbox'),
            os.path.expanduser('~/.config/fish/completions/tonietoolbox.fish')
        ]
        for file_path in completion_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.debug(f"Removed completion file: {file_path}")
                    removed_count += 1
                except Exception as e:
                    logger.debug(f"Error removing {file_path}: {e}")
        
        # Determine PowerShell profile locations
        if os.name == 'nt':
            # Windows: Use standard profile locations
            # Note: Documents folder location can vary by locale/configuration
            powershell_profiles = [
                os.path.expanduser('~/Documents/PowerShell/Microsoft.PowerShell_profile.ps1'),
                os.path.expanduser('~/OneDrive/Documents/PowerShell/Microsoft.PowerShell_profile.ps1')  # OneDrive sync
            ]
        else:
            powershell_profiles = [
                os.path.expanduser('~/.config/powershell/Microsoft.PowerShell_profile.ps1')
            ]
        for profile_path in powershell_profiles:
            if os.path.exists(profile_path):
                try:
                    with open(profile_path, 'r') as f:
                        content = f.read()
                    if '# TonieToolbox completion' in content or 'Register-ArgumentCompleter -Native -CommandName tonietoolbox' in content:
                        import re
                        pattern = r'# TonieToolbox completion.*?Register-ArgumentCompleter -Native -CommandName tonietoolbox -ScriptBlock \{.*?\n\}'
                        new_content = re.sub(pattern, '', content, flags=re.DOTALL)
                        new_content = re.sub(r'\n\s*\n\s*\n', '\n\n', new_content)
                        with open(profile_path, 'w') as f:
                            f.write(new_content)
                        logger.debug(f"Removed TonieToolbox completion from PowerShell profile: {profile_path}")
                        removed_count += 1
                except Exception as e:
                    logger.debug(f"Error processing PowerShell profile {profile_path}: {e}")
        if removed_count > 0:
            logger.info(f"Removed {removed_count} completion file(s)")
            return True
        else:
            logger.debug("No completion files found to remove")
            return False
    def _is_shell_available(self, shell_name):
        """Check if a shell is available on the system."""
        try:
            import platform
            
            # Use appropriate command based on platform
            if platform.system() == 'Windows':
                # On Windows, use 'where' command
                cmd = ['where', shell_name]
                if shell_name == 'pwsh':
                    # Try both 'pwsh' and 'pwsh.exe'
                    try:
                        result = subprocess.run(['where', 'pwsh'], 
                                              capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)
                        if result.returncode == 0:
                            return True
                        result = subprocess.run(['where', 'pwsh.exe'], 
                                              capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)
                        return result.returncode == 0
                    except Exception:
                        return False
                else:
                    # For other shells on Windows, try with .exe extension too
                    try:
                        result = subprocess.run(['where', shell_name], 
                                              capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)
                        if result.returncode == 0:
                            return True
                        result = subprocess.run(['where', f'{shell_name}.exe'], 
                                              capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)
                        return result.returncode == 0
                    except Exception:
                        return False
            else:
                # On Unix-like systems, use 'which' command
                result = subprocess.run(['which', shell_name], 
                                      capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)
                return result.returncode == 0
        except Exception:
            return False
    def _install_shell_completion(self, shell_name, generator):
        """Install completion script for a specific shell."""
        completion_script = generator()
        if not completion_script:
            return False
        install_paths = self._get_completion_paths(shell_name)
        if shell_name == 'pwsh':
            return self._install_powershell_completion(completion_script, install_paths)
        for path in install_paths:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w') as f:
                    f.write(completion_script)
                if shell_name != 'fish':
                    os.chmod(path, 0o755)
                logger.debug(f"Installed {shell_name} completion to: {path}")
                return True
            except PermissionError:
                logger.debug(f"Permission denied writing to {path}, trying next location")
                continue
            except Exception as e:
                logger.debug(f"Error writing to {path}: {e}")
                continue
        logger.warning(f"Could not install {shell_name} completion to any location")
        return False
    def _get_completion_paths(self, shell_name):
        """Get possible installation paths for shell completion scripts."""
        if shell_name == 'bash':
            return [
                os.path.expanduser('~/.local/share/bash-completion/completions/tonietoolbox'),
                os.path.expanduser('~/.bash_completion.d/tonietoolbox'),
                '/etc/bash_completion.d/tonietoolbox'
            ]
        elif shell_name == 'zsh':
            return [
                os.path.expanduser('~/.local/share/zsh/site-functions/_tonietoolbox'),
                os.path.expanduser('~/.zsh/completions/_tonietoolbox')
            ]
        elif shell_name == 'fish':
            return [
                os.path.expanduser('~/.config/fish/completions/tonietoolbox.fish')
            ]
        elif shell_name == 'pwsh':
            if os.name == 'nt':
                return [
                    os.path.expanduser('~/Documents/PowerShell/Microsoft.PowerShell_profile.ps1')
                ]
            else:
                return [
                    os.path.expanduser('~/.config/powershell/Microsoft.PowerShell_profile.ps1')
                ]
        else:
            return []
    def _install_powershell_completion(self, completion_script, profile_paths):
        """Install PowerShell completion by appending to profile."""
        for profile_path in profile_paths:
            try:
                os.makedirs(os.path.dirname(profile_path), exist_ok=True)
                if os.path.exists(profile_path):
                    with open(profile_path, 'r') as f:
                        existing_content = f.read()
                    if '# TonieToolbox completion' in existing_content:
                        logger.debug(f"PowerShell completion already installed in {profile_path}")
                        return True
                    with open(profile_path, 'a') as f:
                        f.write('\n\n# TonieToolbox completion\n')
                        f.write(completion_script)
                else:
                    with open(profile_path, 'w') as f:
                        f.write('# PowerShell profile\n\n')
                        f.write('# TonieToolbox completion\n')
                        f.write(completion_script)
                logger.debug(f"Installed PowerShell completion to profile: {profile_path}")
                return True
            except PermissionError:
                logger.debug(f"Permission denied writing to {profile_path}")
                continue
            except Exception as e:
                logger.debug(f"Error writing to {profile_path}: {e}")
                continue
        logger.warning("Could not install PowerShell completion to any profile location")
        return False
    def _generate_bash_completion(self):
        """Generate bash completion script."""
        return '''#!/bin/bash
# Bash completion for TonieToolbox
_tonietoolbox_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    # All available options organized by category
    local core_opts="--version -v"
    local processing_opts="--ffmpeg -f --bitrate -b --cbr -c --auto-download --no-mono-conversion"
    local file_ops_opts="--info -i --play -p --gui --split -s --recursive -r --files-to-taf --convert-to-separate-mp3 --convert-to-single-mp3"
    local output_opts="--output-to-source -O --force-creation -fc"
    local tonie_opts="--timestamp -t --append-tonie-tag -a --no-tonie-header -n --keep-temp -k --use-legacy-tags -u"
    local analysis_opts="--compare -C --detailed-compare -D"
    local integration_opts="--config-integration --install-integration --uninstall-integration"
    local teddycloud_opts="--upload --include-artwork --assign-to-tag --get-tags --ignore-ssl-verify --special-folder --path --connection-timeout --read-timeout --max-retries --retry-delay --create-custom-json --version-2 --username --password --client-cert --client-key"
    local media_opts="--use-media-tags -m --name-template --output-to-template --show-tags"
    local version_opts="--skip-update-check -S --force-update-check -F --clear-version-cache --check-updates-only --disable-notifications --include-pre-releases"
    local logging_opts="--debug -d --trace -T --quiet -q --silent -Q --log-file"
    
    opts="$core_opts $processing_opts $file_ops_opts $output_opts $tonie_opts $analysis_opts $integration_opts $teddycloud_opts $media_opts $version_opts $logging_opts"
    case "${prev}" in
        --upload|--get-tags)
            # Complete with common URL patterns
            COMPREPLY=($(compgen -W "http:// https://" -- ${cur}))
            return 0
            ;;
        --name-template)
            # Complete with template suggestions
            local templates='"{artist} - {album}" "{albumartist} - {title}" "{title}" "{album}"'
            COMPREPLY=($(compgen -W "${templates}" -- ${cur}))
            return 0
            ;;
        --output-to-template)
            # Complete with path templates
            local path_templates='"./output/{albumartist}/{album}" "./Music/{artist}" "./{album}"'
            COMPREPLY=($(compgen -W "${path_templates}" -- ${cur}))
            return 0
            ;;
        --special-folder)
            COMPREPLY=($(compgen -W "library" -- ${cur}))
            return 0
            ;;
        --bitrate)
            COMPREPLY=($(compgen -W "64 96 128 160 192 256 320" -- ${cur}))
            return 0
            ;;
        --ffmpeg|--client-cert|--client-key)
            # Complete with file paths
            COMPREPLY=($(compgen -f -- ${cur}))
            return 0
            ;;
        --append-tonie-tag)
            # Suggest hex pattern
            COMPREPLY=($(compgen -W "AABBCCDD 12345678" -- ${cur}))
            return 0
            ;;
    esac
    # File completion for input files
    if [[ ${cur} != -* ]]; then
        # Complete audio files and directories
        local audio_files=$(find . -maxdepth 1 -name "*.mp3" -o -name "*.wav" -o -name "*.flac" -o -name "*.ogg" -o -name "*.m4a" -o -name "*.aac" -o -name "*.taf" 2>/dev/null | sed 's|^\\./||')
        local dirs=$(find . -maxdepth 1 -type d ! -name "." 2>/dev/null | sed 's|^\\./||')
        COMPREPLY=($(compgen -W "${audio_files} ${dirs}" -- ${cur}))
        return 0
    fi
    COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
    return 0
}
complete -F _tonietoolbox_completion tonietoolbox
'''
    def _generate_zsh_completion(self):
        """Generate zsh completion script."""
        return '''#compdef tonietoolbox
# Zsh completion for TonieToolbox
_tonietoolbox() {
    local context state line
    typeset -A opt_args
    _arguments \\
        '(-h --help)'{-h,--help}'[Show help message]' \\
        + '(core)' \\
        '(-v --version)'{-v,--version}'[Show program version and exit]' \\
        + '(processing)' \\
        '(-f --ffmpeg)'{-f,--ffmpeg}'[Specify FFmpeg location]:file:_files' \\
        '(-b --bitrate)'{-b,--bitrate}'[Set encoding bitrate in kbps]:bitrate:(64 96 128 160 192 256 320)' \\
        '(-c --cbr)'{-c,--cbr}'[Encode in CBR mode]' \\
        '--auto-download[Automatically download ffmpeg if not found]' \\
        '--no-mono-conversion[Do not convert mono audio to stereo]' \\
        + '(file-ops)' \\
        '(-i --info)'{-i,--info}'[Check and display info about Tonie file]' \\
        '(-p --play)'{-p,--play}'[Play TAF using TonieToolbox GUI Player with auto-play]' \\
        '--gui[Launch comprehensive TonieToolbox GUI]' \\
        '(-s --split)'{-s,--split}'[Split Tonie file into opus tracks]' \\
        '(-r --recursive)'{-r,--recursive}'[Process folders recursively]' \\
        '--files-to-taf[Convert each audio file to individual TAF files]' \\
        '--convert-to-separate-mp3[Convert to individual MP3 tracks]' \\
        '--convert-to-single-mp3[Convert to single MP3 file]' \\
        + '(output)' \\
        '(-O --output-to-source)'{-O,--output-to-source}'[Save output in source directory]' \\
        '(-fc --force-creation)'{-fc,--force-creation}'[Force creation even if file exists]' \\
        + '(tonie)' \\
        '(-t --timestamp)'{-t,--timestamp}'[Set custom timestamp]:timestamp:' \\
        '(-a --append-tonie-tag)'{-a,--append-tonie-tag}'[Append TAG to filename]:tag:' \\
        '(-n --no-tonie-header)'{-n,--no-tonie-header}'[Do not write Tonie header]' \\
        '(-k --keep-temp)'{-k,--keep-temp}'[Keep temporary opus files for testing]' \\
        '(-u --use-legacy-tags)'{-u,--use-legacy-tags}'[Use legacy hardcoded tags]' \\
        + '(analysis)' \\
        '(-C --compare)'{-C,--compare}'[Compare with another TAF file]:file:_files -g "*.taf"' \\
        '(-D --detailed-compare)'{-D,--detailed-compare}'[Show detailed OGG page differences]' \\
        + '(integration)' \\
        '--config-integration[Configure context menu integration]' \\
        '--install-integration[Install system integration]' \\
        '--uninstall-integration[Uninstall context menu integration]' \\
        + '(teddycloud)' \\
        '--upload[Upload to TeddyCloud instance]:URL:_urls' \\
        '--include-artwork[Upload cover artwork alongside Tonie file]' \\
        '--assign-to-tag[Assign uploaded file to specific tag ID]' \\
        '--get-tags[Get available tags from TeddyCloud]:URL:_urls' \\
        '--ignore-ssl-verify[Ignore SSL certificate verification]' \\
        '--special-folder[Special folder to upload to]:folder:(library)' \\
        '--path[Path on TeddyCloud server]:path:_directories' \\
        '--connection-timeout[Connection timeout in seconds]:seconds:(10 30 60)' \\
        '--read-timeout[Read timeout in seconds]:timeout:(300 600 900)' \\
        '--max-retries[Maximum retry attempts]:retries:(1 3 5)' \\
        '--retry-delay[Delay between retries]:delay:(1 5 10)' \\
        '--create-custom-json[Create custom Tonies JSON]' \\
        '--version-2[Use version 2 of Tonies JSON format]' \\
        '--username[Username for authentication]:username:' \\
        '--password[Password for authentication]:password:' \\
        '--client-cert[Client certificate file]:file:_files' \\
        '--client-key[Client private key file]:file:_files' \\
        + '(media)' \\
        '(-m --use-media-tags)'{-m,--use-media-tags}'[Use media tags for naming]' \\
        '--name-template[Template for naming files]:template:_tonietoolbox_templates' \\
        '--output-to-template[Template for output path]:path template:_tonietoolbox_path_templates' \\
        '--show-tags[Show available media tags]' \\
        + '(version)' \\
        '(-S --skip-update-check)'{-S,--skip-update-check}'[Skip checking for updates]' \\
        '(-F --force-update-check)'{-F,--force-update-check}'[Force refresh update information]' \\
        '--clear-version-cache[Clear version check cache and exit]' \\
        '--check-updates-only[Only check for updates and exit]' \\
        '--disable-notifications[Disable update notification messages]' \\
        '--include-pre-releases[Include pre-release versions when checking]' \\
        + '(logging)' \\
        '(-d --debug)'{-d,--debug}'[Enable debug logging]' \\
        '(-T --trace)'{-T,--trace}'[Enable trace logging (very verbose)]' \\
        '(-q --quiet)'{-q,--quiet}'[Show only warnings and errors]' \\
        '(-Q --silent)'{-Q,--silent}'[Show only errors]' \\
        '--log-file[Save logs to timestamped file]' \\
        '*:audio files:_tonietoolbox_files'
}
_tonietoolbox_files() {
    _alternative \\
        'audio-files:audio files:_files -g "*.(mp3|wav|flac|ogg|opus|aac|m4a|taf)"' \\
        'directories:directories:_directories'
}
_tonietoolbox_templates() {
    local templates=(
        '"{artist} - {album}"'
        '"{albumartist} - {title}"'
        '"{title}"'
        '"{album}"'
        '"{artist} - {title}"'
    )
    _describe 'templates' templates
}
_tonietoolbox_path_templates() {
    local path_templates=(
        '"./output/{albumartist}/{album}"'
        '"./Music/{artist}"'
        '"./{album}"'
        '"~/Music/{albumartist}/{album}"'
    )
    _describe 'path templates' path_templates
}
_tonietoolbox "$@"
'''
    def _generate_fish_completion(self):
        """Generate fish completion script."""
        return '''# Fish completion for TonieToolbox
# Core arguments
complete -c tonietoolbox -s h -l help -d 'Show help message'
complete -c tonietoolbox -s v -l version -d 'Show program version and exit'

# Processing options
complete -c tonietoolbox -s f -l ffmpeg -d 'Specify location of ffmpeg' -r
complete -c tonietoolbox -s b -l bitrate -d 'Set encoding bitrate in kbps' -x -a '64 96 128 160 192 256 320'
complete -c tonietoolbox -s c -l cbr -d 'Encode in CBR mode'
complete -c tonietoolbox -l auto-download -d 'Automatically download ffmpeg if not found'
complete -c tonietoolbox -l no-mono-conversion -d 'Do not convert mono audio to stereo'

# File operations
complete -c tonietoolbox -s i -l info -d 'Check and display info about Tonie file'
complete -c tonietoolbox -s p -l play -d 'Play TAF using TonieToolbox GUI Player with auto-play'
complete -c tonietoolbox -l gui -d 'Launch comprehensive TonieToolbox GUI'
complete -c tonietoolbox -s s -l split -d 'Split Tonie file into opus tracks'
complete -c tonietoolbox -s r -l recursive -d 'Process folders recursively'
complete -c tonietoolbox -l files-to-taf -d 'Convert each audio file to individual TAF files'
complete -c tonietoolbox -l convert-to-separate-mp3 -d 'Convert Tonie file to individual MP3 tracks'
complete -c tonietoolbox -l convert-to-single-mp3 -d 'Convert Tonie file to single MP3 file'

# Output control
complete -c tonietoolbox -s O -l output-to-source -d 'Save output files in source directory'
complete -c tonietoolbox -l force-creation -d 'Force creation even if file already exists'

# Tonie-specific options
complete -c tonietoolbox -s t -l timestamp -d 'Set custom timestamp / bitstream serial' -x
complete -c tonietoolbox -s a -l append-tonie-tag -d 'Append TAG to filename (8-char hex)' -x
complete -c tonietoolbox -s n -l no-tonie-header -d 'Do not write Tonie header'
complete -c tonietoolbox -s k -l keep-temp -d 'Keep temporary opus files for testing'
complete -c tonietoolbox -s u -l use-legacy-tags -d 'Use legacy hardcoded tags'

# Analysis & debugging
complete -c tonietoolbox -s C -l compare -d 'Compare input file with another TAF file' -r -a '(__fish_complete_suffix .taf)'
complete -c tonietoolbox -s D -l detailed-compare -d 'Show detailed OGG page differences'

# System integration
complete -c tonietoolbox -l config-integration -d 'Configure context menu integration'
complete -c tonietoolbox -l install-integration -d 'Install system integration'
complete -c tonietoolbox -l uninstall-integration -d 'Uninstall context menu integration'

# TeddyCloud options
complete -c tonietoolbox -l upload -d 'Upload to TeddyCloud instance' -r
complete -c tonietoolbox -l include-artwork -d 'Upload cover artwork alongside Tonie file'
complete -c tonietoolbox -l assign-to-tag -d 'Assign uploaded file to specific tag ID'
complete -c tonietoolbox -l get-tags -d 'Get available tags from TeddyCloud' -r
complete -c tonietoolbox -l ignore-ssl-verify -d 'Ignore SSL certificate verification'
complete -c tonietoolbox -l special-folder -d 'Special folder to upload to' -x -a 'library'
complete -c tonietoolbox -l path -d 'Path on TeddyCloud server' -r
complete -c tonietoolbox -l connection-timeout -d 'Connection timeout in seconds' -x -a '10 30 60'
complete -c tonietoolbox -l read-timeout -d 'Read timeout in seconds' -x -a '300 600 900'
complete -c tonietoolbox -l max-retries -d 'Maximum retry attempts' -x -a '1 3 5'
complete -c tonietoolbox -l retry-delay -d 'Delay between retries in seconds' -x -a '1 5 10'
complete -c tonietoolbox -l create-custom-json -d 'Create custom Tonies JSON'
complete -c tonietoolbox -l version-2 -d 'Use version 2 of Tonies JSON format'
complete -c tonietoolbox -l username -d 'Username for authentication' -x
complete -c tonietoolbox -l password -d 'Password for authentication' -x
complete -c tonietoolbox -l client-cert -d 'Client certificate file' -r
complete -c tonietoolbox -l client-key -d 'Client private key file' -r

# Media tag options
complete -c tonietoolbox -s m -l use-media-tags -d 'Use media tags from audio files for naming'
complete -c tonietoolbox -l name-template -d 'Template for naming files using media tags' -x -a '"{artist} - {album}" "{albumartist} - {title}" "{title}" "{album}"'
complete -c tonietoolbox -l output-to-template -d 'Template for output path using media tags' -r -a '"./output/{albumartist}/{album}" "./Music/{artist}" "./{album}"'
complete -c tonietoolbox -l show-tags -d 'Show available media tags from input files'

# Version check options
complete -c tonietoolbox -s S -l skip-update-check -d 'Skip checking for updates'
complete -c tonietoolbox -s F -l force-update-check -d 'Force refresh of update information from PyPI'
complete -c tonietoolbox -l clear-version-cache -d 'Clear version check cache and exit'
complete -c tonietoolbox -l check-updates-only -d 'Only check for updates and exit'
complete -c tonietoolbox -l disable-notifications -d 'Disable update notification messages'
complete -c tonietoolbox -l include-pre-releases -d 'Include pre-release versions when checking'

# Logging options
complete -c tonietoolbox -s d -l debug -d 'Enable debug logging'
complete -c tonietoolbox -s T -l trace -d 'Enable trace logging (very verbose)'
complete -c tonietoolbox -s q -l quiet -d 'Show only warnings and errors'
complete -c tonietoolbox -s Q -l silent -d 'Show only errors'
complete -c tonietoolbox -l log-file -d 'Save logs to timestamped file'

# File completion for audio files and TAF files
complete -c tonietoolbox -f -a '(__fish_complete_suffix .mp3 .wav .flac .ogg .opus .aac .m4a .taf)'
# Complete directories for recursive processing
complete -c tonietoolbox -x -a '(__fish_complete_directories)'
'''
    def _generate_powershell_completion(self):
        """Generate PowerShell completion script."""
        return '''# PowerShell completion for TonieToolbox
Register-ArgumentCompleter -Native -CommandName tonietoolbox -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    
    # Organize options by category for better maintainability
    $core_options = @('-v', '--version')
    $processing_options = @('-f', '--ffmpeg', '-b', '--bitrate', '-c', '--cbr', '--auto-download', '--no-mono-conversion')
    $file_ops_options = @('-i', '--info', '-p', '--play', '--gui', '-s', '--split', '-r', '--recursive', '--files-to-taf', '--convert-to-separate-mp3', '--convert-to-single-mp3')
    $output_options = @('-O', '--output-to-source', '-fc', '--force-creation')
    $tonie_options = @('-t', '--timestamp', '-a', '--append-tonie-tag', '-n', '--no-tonie-header', '-k', '--keep-temp', '-u', '--use-legacy-tags')
    $analysis_options = @('-C', '--compare', '-D', '--detailed-compare')
    $integration_options = @('--config-integration', '--install-integration', '--uninstall-integration')
    $teddycloud_options = @('--upload', '--include-artwork', '--assign-to-tag', '--get-tags', '--ignore-ssl-verify', '--special-folder', '--path', '--connection-timeout', '--read-timeout', '--max-retries', '--retry-delay', '--create-custom-json', '--version-2', '--username', '--password', '--client-cert', '--client-key')
    $media_options = @('-m', '--use-media-tags', '--name-template', '--output-to-template', '--show-tags')
    $version_options = @('-S', '--skip-update-check', '-F', '--force-update-check', '--clear-version-cache', '--check-updates-only', '--disable-notifications', '--include-pre-releases')
    $logging_options = @('-d', '--debug', '-T', '--trace', '-q', '--quiet', '-Q', '--silent', '--log-file')
    $help_options = @('-h', '--help')
    
    $all_options = $core_options + $processing_options + $file_ops_options + $output_options + $tonie_options + $analysis_options + $integration_options + $teddycloud_options + $media_options + $version_options + $logging_options + $help_options
    
    # Complete options that start with what the user typed
    if ($wordToComplete -match '^-') {
        $all_options | Where-Object { $_ -like "$wordToComplete*" } | Sort-Object
    } else {
        # Complete audio files and directories if not completing an option
        $results = @()
        
        # Add audio files
        Get-ChildItem -Path "." -File -ErrorAction SilentlyContinue | Where-Object { 
            $_.Extension -in @('.mp3', '.wav', '.flac', '.ogg', '.opus', '.aac', '.m4a', '.taf', '.lst') -and
            $_.Name -like "$wordToComplete*"
        } | ForEach-Object { $results += $_.Name }
        
        # Add directories
        Get-ChildItem -Path "." -Directory -ErrorAction SilentlyContinue | Where-Object {
            $_.Name -like "$wordToComplete*"
        } | ForEach-Object { $results += $_.Name + "/" }
        
        $results | Sort-Object
    }
}
'''