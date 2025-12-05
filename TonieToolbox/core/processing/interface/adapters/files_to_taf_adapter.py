#!/usr/bin/env python3
"""
Files to TAF processing adapter.

This module provides interface adapter for combining multiple files
into a single TAF file, coordinating between CLI/GUI interfaces and application services.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import glob

from .base_adapter import BaseInterfaceAdapter, ProgressTrackingMixin
from ...application.services.processing_application_service import ProcessingApplicationService
from ...domain import InputSpecification, OutputSpecification
from ...domain.models.processing_result import ProcessingStatus
from ...domain.services import OutputPathResolver


class FilesToTafAdapter(BaseInterfaceAdapter, ProgressTrackingMixin):
    """
    Adapter for combining multiple files into a single TAF file.
    
    Handles collection of input files from patterns, directories, or lists,
    and coordinates their combination into a single output TAF file.
    """
    
    def __init__(self, processing_service: ProcessingApplicationService,
                 logger: Optional[logging.Logger] = None):
        """Initialize files to TAF processing adapter."""
        BaseInterfaceAdapter.__init__(self, processing_service, logger)
        ProgressTrackingMixin.__init__(self)
        
        # Initialize domain service for output path resolution
        self.path_resolver = OutputPathResolver(logger)
    
    def _validate_request(self, request: Dict[str, Any]) -> bool:
        """
        Validate files to TAF processing request.
        
        Args:
            request: Processing request
            
        Returns:
            True if request is valid
        """
        try:
            # Check for input_pattern (required for this adapter)
            if 'input_pattern' not in request:
                self.logger.error("Missing required field: input_pattern")
                return False
            
            input_path = Path(request['input_pattern'])
            
            # Validate input path exists (unless it's a pattern)
            if not ('*' in str(input_path) or '?' in str(input_path)):
                if not input_path.exists():
                    self.logger.error(f"Input path does not exist: {input_path}")
                    return False
            
            # Validate output path if provided
            if 'output_path' in request:
                output_path = Path(request['output_path'])
                
                # Check if we can write to output directory
                try:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.logger.error(f"Cannot create output directory: {str(e)}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Request validation failed: {str(e)}")
            return False

    def _translate_request_to_options(self, request: Dict[str, Any]):
        """Translate request to ProcessingOptions."""
        try:
            from ...domain.value_objects.processing_options import ProcessingOptions, QualityLevel
            
            # Map quality string to enum
            quality_map = {
                'low': QualityLevel.LOW,
                'medium': QualityLevel.MEDIUM,
                'high': QualityLevel.HIGH,
                'lossless': QualityLevel.LOSSLESS
            }
            quality_level = quality_map.get(request.get('quality', 'medium').lower(), QualityLevel.MEDIUM)
            
            return ProcessingOptions(
                quality_level=quality_level,
                normalize_audio=request.get('normalize_audio', False),
                fade_in_duration=float(request.get('fade_in_duration', 0.0)),
                fade_out_duration=float(request.get('fade_out_duration', 0.0)),
                preserve_metadata=request.get('preserve_metadata', True),
                continue_on_error=request.get('continue_on_error', True),
                timeout_seconds=int(request.get('timeout_seconds', 300)) if request.get('timeout_seconds') else None,
                upload_enabled=request.get('upload_enabled', False),
                upload_after_processing=request.get('upload_enabled', False)
            )
        except Exception as e:
            self.logger.error(f"Failed to translate request to options: {str(e)}")
            # Return default options
            from ...domain.value_objects.processing_options import ProcessingOptions
            return ProcessingOptions()

    def execute(self, request: Dict[str, Any]) -> int:
        """
        Execute files to TAF processing request.
        
        Args:
            request: Processing request containing:
                - input_pattern: File pattern, directory, or list file path
                - output_path: Path for output TAF file
                - recursive: Whether to search directories recursively
                - sort_files: How to sort files (name, date, size, none)
                - file_extensions: List of extensions to include
                - exclude_patterns: Patterns to exclude from processing
                - quality: Quality level for output
                - normalize_audio: Whether to normalize audio levels
                - chapter_marks: Whether to add chapter marks between files
                
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            self.logger.info(f"Starting files to TAF processing: {request.get('input_pattern')}")
            
            # Validate request
            if not self._validate_request(request):
                return 1
            
            self._update_progress("Discovering", 0.0, "Finding input files")
            
            # Discover input files
            input_files = self._discover_input_files(request)
            
            if not input_files:
                self.logger.error(f"No input files found for pattern: {request.get('input_pattern')}")
                return 1
            
            self.logger.info(f"Found {len(input_files)} input files for combination")
            
            self._update_progress("Preparing", 0.1, f"Preparing {len(input_files)} files for combination")
            
            # For multiple files, we need to create a processing operation
            # Use the first file as the primary input and the rest as additional files
            if len(input_files) == 1:
                # Single file - use standard input specification
                input_spec = InputSpecification.from_path(
                    str(input_files[0]),
                    recursive=request.get('recursive', False)
                )
            else:
                # Multiple files - use the directory as input and set options for combining
                input_dir = str(input_files[0].parent)
                input_spec = InputSpecification.from_path(
                    input_dir,
                    recursive=request.get('recursive', True)
                )
            
            output_spec = self._create_output_specification(request)
            self.logger.debug(f"Created output specification with path: {output_spec.output_path}")
            options = self._translate_request_to_options(request)
            
            # Add chapter mark option if requested
            if request.get('chapter_marks', False):
                options = options.with_chapter_marks(True)
            
            # Create processing operation
            from ...domain.models import ProcessingOperation
            from ...domain.value_objects.processing_mode import SINGLE_FILE_MODE
            
            operation = ProcessingOperation(
                input_spec=input_spec,
                output_spec=output_spec,
                processing_mode=SINGLE_FILE_MODE,  # Combine multiple files into one TAF
                options=options
            )
            
            self._update_progress("Combining", 0.2, "Combining files into TAF")
            
            # Execute files to TAF processing through application service
            result = self.processing_service.execute_operation(
                operation,
                progress_callback=self._create_progress_callback()
            )
            
            self._update_progress("Finalizing", 0.9, "Processing complete")
            
            # Log results and return
            self._log_processing_summary(result, request)
            
            if result.is_successful:
                self._update_progress("Complete", 1.0, f"Successfully created: {output_spec.output_path}")
                return 0
            else:
                self._update_progress("Failed", 1.0, f"Processing failed: {result.operation_error if result.operation_error else 'unknown error'}")
                return 1
                
        except Exception as e:
            self.logger.error(f"Files to TAF processing failed: {str(e)}")
            self._update_progress("Failed", 1.0, f"Error: {str(e)}")
            return self._handle_processing_error(e, request)
    
    def _discover_input_files(self, request: Dict[str, Any]) -> List[Path]:
        """Discover input files based on request parameters."""
        input_pattern = request['input_pattern']
        input_path = Path(input_pattern)
        
        files = []
        
        # Handle different input types
        if input_path.exists() and input_path.is_file():
            if input_path.suffix.lower() == '.lst':
                # List file
                files = self._read_list_file(input_path)
            else:
                # Single file
                files = [input_path]
                
        elif input_path.exists() and input_path.is_dir():
            # Directory
            files = self._discover_files_in_directory(input_path, request)
            
        else:
            # Pattern matching
            files = self._discover_files_by_pattern(input_pattern, request)
        
        # Filter by extensions if specified
        if request.get('file_extensions'):
            files = self._filter_by_extensions(files, request['file_extensions'])
        
        # Exclude patterns if specified
        if request.get('exclude_patterns'):
            files = self._exclude_patterns(files, request['exclude_patterns'])
        
        # Sort files if requested
        sort_method = request.get('sort_files', 'name')
        if sort_method != 'none':
            files = self._sort_files(files, sort_method)
        
        return files
    
    def _read_list_file(self, list_file_path: Path) -> List[Path]:
        """Read file paths from a .lst file."""
        try:
            files = []
            base_dir = list_file_path.parent
            
            with open(list_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Convert relative paths to absolute
                        file_path = Path(line)
                        if not file_path.is_absolute():
                            file_path = base_dir / file_path
                        
                        if file_path.exists():
                            files.append(file_path)
                        else:
                            self.logger.warning(f"File not found in list: {file_path}")
            
            return files
            
        except Exception as e:
            self.logger.error(f"Failed to read list file {list_file_path}: {str(e)}")
            return []
    
    def _discover_files_in_directory(self, directory: Path, request: Dict[str, Any]) -> List[Path]:
        """Discover files in directory."""
        files = []
        recursive = request.get('recursive', False)
        
        # Supported audio extensions
        audio_extensions = {'.mp3', '.ogg', '.wav', '.flac', '.m4a', '.aac', '.opus', '.wma'}
        
        if recursive:
            pattern = '**/*'
        else:
            pattern = '*'
        
        for file_path in directory.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                files.append(file_path)
        
        return files
    
    def _discover_files_by_pattern(self, pattern: str, request: Dict[str, Any]) -> List[Path]:
        """Discover files using glob pattern."""
        try:
            files = []
            
            # Use glob to find matching files
            for file_str in glob.glob(pattern, recursive=request.get('recursive', False)):
                file_path = Path(file_str)
                if file_path.is_file():
                    files.append(file_path)
            
            return files
            
        except Exception as e:
            self.logger.error(f"Pattern matching failed for '{pattern}': {str(e)}")
            return []
    
    def _filter_by_extensions(self, files: List[Path], extensions: List[str]) -> List[Path]:
        """Filter files by allowed extensions."""
        # Ensure extensions start with dot
        extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]
        extensions = [ext.lower() for ext in extensions]
        
        return [f for f in files if f.suffix.lower() in extensions]
    
    def _exclude_patterns(self, files: List[Path], exclude_patterns: List[str]) -> List[Path]:
        """Exclude files matching patterns."""
        import fnmatch
        
        filtered_files = []
        
        for file_path in files:
            exclude = False
            file_name = file_path.name
            
            for pattern in exclude_patterns:
                if fnmatch.fnmatch(file_name, pattern):
                    exclude = True
                    break
            
            if not exclude:
                filtered_files.append(file_path)
        
        return filtered_files
    
    def _sort_files(self, files: List[Path], sort_method: str) -> List[Path]:
        """Sort files according to specified method."""
        try:
            if sort_method == 'name':
                return sorted(files, key=lambda f: f.name.lower())
            elif sort_method == 'date':
                return sorted(files, key=lambda f: f.stat().st_mtime)
            elif sort_method == 'size':
                return sorted(files, key=lambda f: f.stat().st_size)
            elif sort_method == 'path':
                return sorted(files, key=lambda f: str(f).lower())
            else:
                return files
                
        except Exception as e:
            self.logger.warning(f"File sorting failed, using original order: {str(e)}")
            return files
    
    def _create_output_specification(self, request: Dict[str, Any]) -> OutputSpecification:
        """
        Create output specification from request.
        
        Delegates to domain service for all business logic.
        """
        self.logger.debug(f"Creating output specification with request keys: {list(request.keys())}")
        self.logger.debug(f"output_to_template: {request.get('output_to_template')}")
        self.logger.debug(f"use_media_tags: {request.get('use_media_tags')}")
        
        # Extract input path
        input_pattern = request['input_pattern']
        input_path = Path(input_pattern)
        
        # Check for explicit output path
        if 'output_path' in request:
            output_path = Path(request['output_path'])
        else:
            # Extract template parameters from request
            use_templates = request.get('use_media_tags', False)
            output_dir_template = request.get('output_to_template')
            filename_template = request.get('name_template')
            
            # Get metadata if templates are requested
            metadata = None
            if use_templates and (output_dir_template or filename_template):
                # Find representative audio file for metadata extraction
                audio_file = None
                if input_path.is_file() and input_path.suffix.lower() in ['.mp3', '.flac', '.wav', '.m4a', '.ogg']:
                    audio_file = input_path
                elif input_path.is_dir():
                    audio_file = self.path_resolver.find_representative_audio_file(input_path)
                
                # Extract metadata from representative file
                if audio_file:
                    from ....media.tags import get_media_tag_service
                    tag_service = get_media_tag_service()
                    metadata = self.path_resolver.resolve_metadata_from_input(audio_file, tag_service)
            
            # Delegate to domain service for path resolution
            output_path = self.path_resolver.resolve_output_path(
                input_path=input_path,
                explicit_output_path=None,
                output_directory_template=output_dir_template,
                filename_template=filename_template,
                metadata=metadata,
                use_templates=use_templates
            )
        
        from ...domain import OutputFormat, OutputMode
        
        return OutputSpecification(
            output_format=OutputFormat.TAF,
            output_mode=OutputMode.SINGLE_FILE,
            output_path=str(output_path),
            overwrite_existing=request.get('overwrite_existing', False),
            create_directories=True
        )
    
    def _create_progress_callback(self):
        """Create progress callback for use case operations."""
        def progress_callback(progress_info):
            operation = progress_info.get('operation', 'Combining')
            progress = progress_info.get('progress', 0.0)
            details = progress_info.get('details', '')
            
            # Scale progress to fit within combining phase (0.2 to 0.9)
            scaled_progress = 0.2 + (progress * 0.7)
            
            self._update_progress(operation, scaled_progress, details)
        
        return progress_callback


class RecursiveProcessingAdapter(BaseInterfaceAdapter, ProgressTrackingMixin):
    """
    Adapter for recursive directory processing.
    
    Handles processing all files in a directory tree with two modes:
    1. Combine mode (default): Combines all files per folder into one TAF per folder
    2. Individual mode (--files-to-taf): Converts each file to individual TAF
    
    Supports template-based naming via --name-template and --output-to-template.
    """
    
    def __init__(self, processing_service: ProcessingApplicationService,
                 logger: Optional[logging.Logger] = None):
        """Initialize recursive processing adapter."""
        BaseInterfaceAdapter.__init__(self, processing_service, logger)
        ProgressTrackingMixin.__init__(self)
        
        # Initialize domain service for output path resolution
        from ...domain.services import OutputPathResolver
        self.path_resolver = OutputPathResolver(logger)
    
    def execute(self, request: Dict[str, Any]) -> int:
        """
        Execute recursive directory processing request.
        
        Behavior depends on files_to_taf flag:
        - files_to_taf=False (default): Combine files per folder → one TAF per folder
        - files_to_taf=True: Each file → individual TAF
        
        Args:
            request: Processing request containing:
                - input_directory: Root directory to process
                - output_directory: Root directory for output files
                - files_to_taf: Whether to process each file individually
                - preserve_structure: Whether to preserve directory structure
                - file_extensions: Extensions to process
                - max_depth: Maximum recursion depth
                - name_template: Template for naming files (optional)
                - output_to_template: Template for output path (optional)
                - use_media_tags: Whether to use media tags for templates
                
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            input_dir = Path(request['input_directory'])
            output_dir = Path(request.get('output_directory', input_dir / 'converted'))
            files_to_taf_mode = request.get('files_to_taf', False)
            
            self.logger.info(f"Starting recursive processing: {input_dir} -> {output_dir}")
            self.logger.debug(f"Mode: {'individual files' if files_to_taf_mode else 'combine per folder'}")
            
            # Validate request
            if not input_dir.exists() or not input_dir.is_dir():
                self.logger.error(f"Input directory does not exist: {input_dir}")
                return 1
            
            # Route to appropriate processing method
            if files_to_taf_mode:
                return self._process_individual_files(input_dir, output_dir, request)
            else:
                return self._process_folders_to_taf(input_dir, output_dir, request)
                
        except Exception as e:
            self.logger.error(f"Recursive processing failed: {str(e)}")
            self._update_progress("Failed", 1.0, f"Recursive processing failed: {str(e)}")
            return self._handle_processing_error(e, request)
    
    def _process_individual_files(self, input_dir: Path, output_dir: Path, request: Dict[str, Any]) -> int:
        """
        Process each file individually to separate TAF files (--files-to-taf mode).
        
        This is the original recursive behavior.
        """
        self._update_progress("Discovering", 0.0, "Finding files to process")
        
        # Discover all files to process
        files_to_process = self._discover_recursive_files(input_dir, request)
        
        if not files_to_process:
            self.logger.warning(f"No files found for processing in {input_dir}")
            return 0
        
        self.logger.info(f"Found {len(files_to_process)} files for recursive processing")
        
        # Process files
        processed = 0
        failed = 0
        
        for i, (input_file, output_file) in enumerate(files_to_process):
            try:
                # Create individual file request
                file_request = {
                    'input_path': str(input_file),
                    'output_path': str(output_file),
                    'quality': request.get('quality', 'MEDIUM'),
                    'normalize_audio': request.get('normalize_audio', False),
                    'preserve_metadata': request.get('preserve_metadata', True),
                    'overwrite_existing': request.get('overwrite_existing', False)
                }
                
                # Process single file
                from .single_file_adapter import SingleFileProcessingAdapter
                adapter = SingleFileProcessingAdapter(self.processing_service, self.logger)
                result = adapter.execute(file_request)
                
                if result == 0:
                    processed += 1
                    status = "Success"
                else:
                    failed += 1
                    status = "Failed"
                    
                    if not request.get('continue_on_error', True):
                        self.logger.error(f"Stopping recursive processing due to failure on {input_file}")
                        break
                
                # Update progress
                progress = (i + 1) / len(files_to_process)
                self._update_progress(
                    "Processing", progress,
                    f"{status}: {input_file.name} ({processed} success, {failed} failed)"
                )
                
            except Exception as e:
                failed += 1
                self.logger.error(f"Error processing {input_file}: {str(e)}")
                
                if not request.get('continue_on_error', True):
                    break
        
        # Final summary
        self._update_progress("Complete", 1.0, f"Recursive processing complete: {processed} success, {failed} failed")
        self.logger.info(f"Recursive processing complete: {processed} successful, {failed} failed")
        
        return 0 if failed == 0 else 1
    
    def _process_folders_to_taf(self, input_dir: Path, output_dir: Path, request: Dict[str, Any]) -> int:
        """
        Combine files per folder into one TAF per folder (default recursive mode).
        
        This mode:
        1. Creates a RECURSIVE ProcessingOperation
        2. Delegates to WorkflowCoordinator which handles parallel/sequential execution
        3. Supports template-based naming
        """
        self._update_progress("Preparing", 0.0, "Preparing recursive processing")
        
        # Create input specification
        from ...domain.value_objects import InputSpecification, OutputSpecification
        input_spec = InputSpecification.from_path(
            str(input_dir),
            recursive=True
        )
        
        # Create output specification for recursive mode
        output_spec = OutputSpecification.for_multiple_taf(
            output_dir=str(output_dir),
            preserve_structure=request.get('preserve_structure', True),
            overwrite=request.get('overwrite_existing', False)
        )
        
        # Translate request to processing options
        options = self._translate_request_to_options(request)
        
        # Add recursive-specific custom options
        custom_options = {}
        
        # Parallel workers (most important!)
        if 'parallel_workers' in request:
            custom_options['parallel_workers'] = request['parallel_workers']
            self.logger.debug(f"Setting parallel workers: {request['parallel_workers']}")
        
        # Max depth
        if 'max_depth' in request:
            custom_options['max_depth'] = request['max_depth']
        
        # File extensions
        if 'file_extensions' in request:
            custom_options['file_extensions'] = request['file_extensions']
        
        # Templates
        if 'name_template' in request:
            custom_options['name_template'] = request['name_template']
        
        if 'output_to_template' in request:
            custom_options['output_to_template'] = request['output_to_template']
        
        # Add custom options to the options object
        for key, value in custom_options.items():
            options = options.with_custom_option(key, value)
        
        # Create RECURSIVE processing operation
        from ...domain.models import ProcessingOperation
        from ...domain.value_objects.processing_mode import RECURSIVE_MODE
        
        operation = ProcessingOperation(
            input_spec=input_spec,
            output_spec=output_spec,
            processing_mode=RECURSIVE_MODE,
            options=options
        )
        
        self._update_progress("Processing", 0.1, "Starting recursive processing")
        
        # Execute through processing service - it will route to WorkflowCoordinator
        result = self.processing_service.execute_operation(
            operation,
            progress_callback=self._create_progress_callback()
        )
        
        # Log results
        self._log_processing_summary(result, request)
        
        # Handle TeddyCloud upload if enabled
        if request.get('upload_enabled', False) and (result.is_successful or result.status == ProcessingStatus.PARTIALLY_COMPLETED):
            upload_exit_code = self._handle_teddycloud_upload(result, request)
            if upload_exit_code != 0:
                self.logger.warning(f"Recursive processing succeeded but upload failed with code {upload_exit_code}")
                # Don't fail entire operation due to upload failure
        
        if result.is_successful or result.status == ProcessingStatus.PARTIALLY_COMPLETED:
            self._update_progress("Complete", 1.0, 
                f"Recursive processing complete: {result.success_count}/{result.total_files} successful")
            return 0 if result.is_successful else 1
        else:
            self._update_progress("Failed", 1.0, 
                f"Recursive processing failed: {result.operation_error if result.operation_error else 'unknown error'}")
            return 1
    
    def _discover_folders_with_audio(self, input_dir: Path, request: Dict[str, Any]) -> Dict[Path, List[Path]]:
        """
        Discover all folders containing audio files and group files by folder.
        
        Args:
            input_dir: Root directory to scan
            request: Processing request with max_depth, file_extensions
            
        Returns:
            Dictionary mapping folder path to list of audio files in that folder
        """
        folders_with_audio = {}
        max_depth = request.get('max_depth', None)
        file_extensions = set(request.get('file_extensions', ['.mp3', '.ogg', '.wav', '.flac', '.m4a']))
        
        # Ensure extensions have dots
        file_extensions = {ext if ext.startswith('.') else f'.{ext}' for ext in file_extensions}
        file_extensions = {ext.lower() for ext in file_extensions}
        
        def scan_directory(current_dir: Path, current_depth: int = 0):
            """Recursively scan directory and collect audio files."""
            if max_depth is not None and current_depth > max_depth:
                return
            
            audio_files_in_dir = []
            subdirs = []
            
            for item in current_dir.iterdir():
                if item.is_file() and item.suffix.lower() in file_extensions:
                    audio_files_in_dir.append(item)
                elif item.is_dir() and not item.name.startswith('.'):
                    subdirs.append(item)
            
            # If this directory has audio files, add it to results
            if audio_files_in_dir:
                folders_with_audio[current_dir] = sorted(audio_files_in_dir)
            
            # Process subdirectories
            for subdir in subdirs:
                scan_directory(subdir, current_depth + 1)
        
        scan_directory(input_dir)
        
        return folders_with_audio
    
    def _extract_folder_metadata(self, audio_files: List[Path], request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from audio files in folder for template resolution.
        
        Uses the first audio file as representative of the folder.
        
        Args:
            audio_files: List of audio files in folder
            request: Processing request with use_media_tags flag
            
        Returns:
            Metadata dictionary for template substitution
        """
        use_templates = request.get('use_media_tags', False)
        
        if not use_templates or not audio_files:
            return {}
        
        # Use first file as representative
        representative_file = audio_files[0]
        
        try:
            from ....media.tags import get_media_tag_service
            tag_service = get_media_tag_service()
            metadata = self.path_resolver.resolve_metadata_from_input(representative_file, tag_service)
            self.logger.debug(f"Extracted metadata from {representative_file.name}: {metadata}")
            return metadata
        except Exception as e:
            self.logger.warning(f"Failed to extract metadata from {representative_file}: {e}")
            return {}
    
    def _resolve_folder_output_path(
        self,
        folder_path: Path,
        input_dir: Path,
        output_dir: Path,
        metadata: Dict[str, Any],
        request: Dict[str, Any]
    ) -> Path:
        """
        Resolve output path for a folder's combined TAF file.
        
        Uses templates if provided, otherwise uses folder name.
        
        Args:
            folder_path: Path to folder being processed
            input_dir: Root input directory
            output_dir: Root output directory
            metadata: Metadata for template substitution
            request: Processing request with templates
            
        Returns:
            Resolved output path for TAF file
        """
        use_templates = request.get('use_media_tags', False)
        output_dir_template = request.get('output_to_template')
        filename_template = request.get('name_template')
        preserve_structure = request.get('preserve_structure', True)
        
        # Determine base output directory
        if preserve_structure:
            # Preserve directory structure
            relative_path = folder_path.relative_to(input_dir)
            base_output_dir = output_dir / relative_path
        else:
            # Flatten to output directory
            base_output_dir = output_dir
        
        # Use OutputPathResolver with templates
        if use_templates and (output_dir_template or filename_template):
            output_path = self.path_resolver.resolve_output_path(
                input_path=folder_path,
                output_directory_template=output_dir_template,
                filename_template=filename_template,
                metadata=metadata,
                use_templates=True
            )
        else:
            # Use folder name as TAF name
            folder_name = folder_path.name
            output_path = base_output_dir / f"{folder_name}.taf"
        
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        return output_path
    
    def _combine_files_to_taf(self, audio_files: List[Path], output_path: Path, request: Dict[str, Any]) -> int:
        """
        Combine multiple audio files into a single TAF file.
        
        Args:
            audio_files: List of audio files to combine
            output_path: Output TAF file path
            request: Processing request with quality, normalize, etc.
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            self.logger.debug(f"Combining {len(audio_files)} files to {output_path}")
            
            # Create a request for FilesToTafAdapter
            combined_request = {
                'input_pattern': str(audio_files[0].parent),  # Directory containing files
                'output_path': str(output_path),
                'quality': request.get('quality', 'MEDIUM'),
                'normalize_audio': request.get('normalize_audio', False),
                'preserve_metadata': request.get('preserve_metadata', True),
                'overwrite_existing': request.get('overwrite_existing', False)
            }
            
            # Use FilesToTafAdapter to combine the files
            adapter = FilesToTafAdapter(self.processing_service, self.logger)
            
            # Temporarily override the file discovery to use our specific files
            original_discover = adapter._discover_input_files
            def custom_discover(req):
                return audio_files
            adapter._discover_input_files = custom_discover
            
            result = adapter.execute(combined_request)
            
            # Restore original method
            adapter._discover_input_files = original_discover
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to combine files to {output_path}: {str(e)}")
            return 1
    
    def _discover_recursive_files(self, input_dir: Path, request: Dict[str, Any]) -> List[tuple]:
        """Discover files for recursive processing and determine output paths."""
        files_to_process = []
        
        output_dir = Path(request.get('output_directory', input_dir / 'converted'))
        preserve_structure = request.get('preserve_structure', True)
        max_depth = request.get('max_depth', None)
        file_extensions = set(request.get('file_extensions', ['.mp3', '.ogg', '.wav', '.flac', '.m4a']))
        
        # Ensure extensions have dots
        file_extensions = {ext if ext.startswith('.') else f'.{ext}' for ext in file_extensions}
        file_extensions = {ext.lower() for ext in file_extensions}
        
        def process_directory(current_dir: Path, current_depth: int = 0):
            if max_depth is not None and current_depth > max_depth:
                return
            
            for item in current_dir.iterdir():
                if item.is_file():
                    if item.suffix.lower() in file_extensions:
                        # Determine output path
                        if preserve_structure:
                            # Preserve directory structure
                            relative_path = item.relative_to(input_dir)
                            output_file = output_dir / relative_path.with_suffix('.taf')
                        else:
                            # Flatten to output directory
                            output_file = output_dir / f"{item.stem}.taf"
                        
                        # Ensure output directory exists
                        output_file.parent.mkdir(parents=True, exist_ok=True)
                        
                        files_to_process.append((item, output_file))
                        
                elif item.is_dir() and not item.name.startswith('.'):
                    # Recursively process subdirectories
                    process_directory(item, current_depth + 1)
        
        process_directory(input_dir)
        
        return files_to_process
    
    def _create_progress_callback(self):
        """Create progress callback for use case operations."""
        def progress_callback(progress_info):
            operation = progress_info.get('operation', 'Processing')
            progress = progress_info.get('progress', 0.0)
            details = progress_info.get('details', '')
            
            # Scale progress to fit within processing phase (0.1 to 1.0)
            scaled_progress = 0.1 + (progress * 0.9)
            
            self._update_progress(operation, scaled_progress, details)
        
        return progress_callback
    
    def _log_processing_summary(self, result, request: Dict[str, Any]) -> None:
        """
        Log a summary table of recursive processing results.
        
        Args:
            result: ProcessingResult with processed files information
            request: Original processing request for context
        """
        from ...domain.models.processing_result import ProcessingStatus
        
        # Print separator for visual clarity
        self.logger.info("")
        self.logger.info("=" * 80)
        self.logger.info("PROCESSING SUMMARY")
        self.logger.info("=" * 80)
        
        # Overall statistics
        self.logger.info("")
        self.logger.info(f"Status: {result.status.name}")
        self.logger.info(f"Total Files: {result.total_files}")
        self.logger.info(f"Successful: {result.success_count}")
        self.logger.info(f"Failed: {result.failure_count}")
        
        if result.duration:
            self.logger.info(f"Duration: {result.duration:.2f} seconds")
        
        if result.success_rate > 0:
            self.logger.info(f"Success Rate: {result.success_rate:.1f}%")
        
        # Detailed file table
        if result.processed_files:
            self.logger.info("")
            self.logger.info("-" * 80)
            self.logger.info(f"{'INPUT':<40} {'OUTPUT':<30} {'STATUS':<10}")
            self.logger.info("-" * 80)
            
            for processed_file in result.processed_files:
                # Shorten paths for readability
                input_name = processed_file.input_path.name
                if processed_file.output_path:
                    output_name = processed_file.output_path.name
                else:
                    output_name = "N/A"
                
                # Status symbol
                if processed_file.is_successful:
                    status = "✓ OK"
                else:
                    status = "✗ FAILED"
                
                self.logger.info(f"{input_name:<40} {output_name:<30} {status:<10}")
            
            self.logger.info("-" * 80)
        
        # Error summary (if any failures)
        if result.failure_count > 0:
            self.logger.info("")
            self.logger.info("ERRORS:")
            failed_files = result.get_failed_files()
            for failed_file in failed_files:
                error_msg = str(failed_file.error) if failed_file.error else "Unknown error"
                self.logger.info(f"  • {failed_file.input_path.name}: {error_msg}")
        
        # Output paths for successful files
        if result.success_count > 0:
            self.logger.info("")
            self.logger.info("OUTPUT FILES:")
            output_paths = result.get_output_paths()
            
            # Group by parent directory for cleaner display
            from collections import defaultdict
            paths_by_dir = defaultdict(list)
            for path in output_paths:
                paths_by_dir[path.parent].append(path.name)
            
            for parent_dir, filenames in paths_by_dir.items():
                self.logger.info(f"  Directory: {parent_dir}")
                for filename in sorted(filenames):
                    self.logger.info(f"    - {filename}")
        
        self.logger.info("")
        self.logger.info("=" * 80)
        self.logger.info("")
    
    def _handle_teddycloud_upload(self, result: 'ProcessingResult', request: Dict[str, Any]) -> int:
        """
        Handle TeddyCloud upload after successful recursive processing.
        
        Args:
            result: Processing result containing output files
            request: Original request with TeddyCloud options
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            # Get successful output files
            output_files = result.get_output_paths()
            if not output_files:
                self.logger.warning("No output files to upload")
                return 0
            
            self.logger.info(f"Uploading {len(output_files)} files to TeddyCloud...")
            
            # Extract source folder metadata for path template resolution
            source_metadata_map = self._build_source_metadata_map(result, request)
            
            # Import TeddyCloud upload processor
            from ....teddycloud.processors.upload_processor import TeddyCloudDirectUploadProcessor
            
            # Create upload processor
            upload_processor = TeddyCloudDirectUploadProcessor(self.logger, {})
            
            # Create args-like namespace with upload options
            import argparse
            upload_args = argparse.Namespace()
            
            # Required fields
            upload_args.upload = request.get('upload', '')  # URL (empty means use config)
            upload_args.files = [str(f) for f in output_files]
            
            # Optional TeddyCloud options
            upload_args.assign_to_tag = request.get('assign_to_tag', None)
            upload_args.create_custom_json = request.get('create_custom_json', False)
            upload_args.path = request.get('path', None)
            upload_args.include_artwork = request.get('include_artwork', False)
            upload_args.special_folder = request.get('special_folder', 'library')
            upload_args.auto_select_tag = request.get('auto_select_tag', False)
            
            # Connection/authentication options (will be loaded from config if not provided)
            upload_args.ignore_ssl_verify = getattr(request, 'ignore_ssl_verify', False)
            upload_args.username = request.get('username', None)
            upload_args.password = request.get('password', None)
            upload_args.client_cert = request.get('client_cert', None)
            upload_args.client_key = request.get('client_key', None)
            upload_args.connection_timeout = request.get('connection_timeout', 10)
            upload_args.read_timeout = request.get('read_timeout', 300)
            upload_args.max_retries = request.get('max_retries', 3)
            upload_args.retry_delay = request.get('retry_delay', 5)
            upload_args.version_2 = request.get('version_2', False)
            
            # Pass source metadata for template resolution
            upload_args.source_metadata_map = source_metadata_map
            
            # Process the upload
            return upload_processor.process(upload_args)
            
        except Exception as e:
            self.logger.error(f"TeddyCloud upload failed: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return 1
    
    def _build_source_metadata_map(self, result: 'ProcessingResult', request: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Build map of output file -> source metadata from source folders.
        
        Extracts media tags from original source audio files for template resolution.
        This reads directly from the source folders to handle cases where files were skipped.
        
        Args:
            result: Processing result containing processed files with output paths
            request: Original request containing source path
            
        Returns:
            Dictionary mapping output file path to extracted metadata
        """
        metadata_map = {}
        
        try:
            self.logger.debug(f"Building source metadata map from {len(result.processed_files)} processed files")
            
            # Get source path from request
            source_path_str = request.get('input_directory', request.get('source', ''))
            self.logger.debug(f"Source path from request: '{source_path_str}'")
            
            source_path = Path(source_path_str) if source_path_str else None
            
            if not source_path or not source_path.exists():
                self.logger.warning(f"Source path not found or invalid: {source_path}")
                return metadata_map
            
            if not source_path.is_dir():
                self.logger.warning(f"Source path is not a directory: {source_path}")
                return metadata_map
            
            self.logger.info(f"Scanning source directory: {source_path}")
            
            # Build map of folder name to output TAF file
            folder_to_taf = {}
            for processed_file in result.processed_files:
                if not processed_file.output_path:
                    continue
                    
                # Get folder name from metadata or from filename
                folder_name = processed_file.metadata.get('folder_name')
                if folder_name:
                    folder_to_taf[folder_name] = str(processed_file.output_path)
                    self.logger.debug(f"Mapped folder '{folder_name}' -> {processed_file.output_path.name}")
            
            self.logger.info(f"Found {len(folder_to_taf)} folder-to-TAF mappings")
            
            # Scan source directory for folders and extract metadata
            for folder_path in source_path.iterdir():
                if not folder_path.is_dir():
                    continue
                
                folder_name = folder_path.name
                
                # Skip if this folder doesn't map to an output TAF
                if folder_name not in folder_to_taf:
                    self.logger.debug(f"Skipping folder without TAF mapping: {folder_name}")
                    continue
                
                # Find first audio file in folder
                audio_extensions = ['.mp3', '.m4a', '.m4b', '.flac', '.ogg', '.wav', '.aac']
                audio_file = None
                
                for ext in audio_extensions:
                    matching_files = list(folder_path.glob(f'*{ext}'))
                    if matching_files:
                        # Sort to get consistent first file
                        audio_file = sorted(matching_files)[0]
                        break
                
                if not audio_file:
                    self.logger.warning(f"No audio files found in folder: {folder_name}")
                    continue
                
                self.logger.debug(f"Extracting metadata from: {audio_file}")
                
                # Import media tag service
                from ....media.tags import get_media_tag_service
                
                tag_service = get_media_tag_service(logger=self.logger)
                tags = tag_service.get_file_tags(str(audio_file))
                
                if tags:
                    # Get all audio files in this folder for source_files list
                    all_audio_files = []
                    for ext in audio_extensions:
                        all_audio_files.extend([str(f) for f in sorted(folder_path.glob(f'*{ext}'))])
                    
                    taf_path = folder_to_taf[folder_name]
                    # Combine tags with source files list
                    metadata_map[taf_path] = {**tags, 'source_files': all_audio_files}
                    self.logger.info(f"Extracted metadata for {Path(taf_path).name}: artist={tags.get('artist')}, album={tags.get('album')}")
                else:
                    self.logger.warning(f"No tags extracted from {audio_file}")
            
            self.logger.info(f"Built source metadata map with {len(metadata_map)} entries")
                
        except Exception as e:
            self.logger.error(f"Failed to build source metadata map: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
        
        return metadata_map
