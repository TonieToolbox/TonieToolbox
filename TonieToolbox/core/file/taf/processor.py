#!/usr/bin/python3
"""
TAF file processing functions for page operations.
"""
from ...utils import get_logger
from ....core.media.formats.ogg import OggPage
from ..opus.headers import check_identification_header, prepare_opus_tags
from ...config import get_config_manager

logger = get_logger(__name__)


def copy_first_and_second_page(
    in_file,
    out_file,
    timestamp: int,
    sha,
    use_custom_tags: bool = True,
    bitrate: int = None,
    vbr: bool = True
) -> None:
    """
    Copy and modify the first two pages of an Opus file for a Tonie file.
    
    Args:
        in_file: Input file handle
        out_file: Output file handle
        timestamp (int): Timestamp to use for the Tonie file
        sha: SHA1 hash object to update with written data
        use_custom_tags (bool): Whether to use custom TonieToolbox tags
        bitrate (int): Actual bitrate used for encoding
        vbr (bool): Whether VBR was used
    """
    # Get default bitrate from config if not provided
    if bitrate is None:
        config_manager = get_config_manager()
        bitrate = config_manager.processing.audio.default_bitrate
        
    logger.debug("Copying first and second pages with timestamp %d", timestamp)
    
    found = OggPage.seek_to_page_header(in_file)
    if not found:
        logger.error("First OGG page not found in input file")
        raise RuntimeError("First ogg page not found")
    
    page = OggPage(in_file)
    page.serial_no = timestamp
    page.checksum = page.calc_checksum()
    check_identification_header(page)
    page.write_page(out_file, sha)
    logger.debug("First page written successfully")
    
    found = OggPage.seek_to_page_header(in_file)
    if not found:
        logger.error("Second OGG page not found in input file")
        raise RuntimeError("Second ogg page not found")
    
    page = OggPage(in_file)
    page.serial_no = timestamp
    page.checksum = page.calc_checksum()
    page = prepare_opus_tags(page, use_custom_tags, bitrate, vbr)
    page.write_page(out_file, sha)
    logger.debug("Second page written successfully")


def skip_first_two_pages(in_file) -> None:
    """
    Skip the first two pages of an Opus file.
    
    Args:
        in_file: Input file handle
        
    Raises:
        RuntimeError: If OGG pages cannot be found or are invalid
    """
    logger.debug("Skipping first two pages")
    
    found = OggPage.seek_to_page_header(in_file)
    if not found:
        logger.error("First OGG page not found in input file")
        raise RuntimeError("First OGG page not found in input file")
    
    try:
        page = OggPage(in_file)
        check_identification_header(page)
    except RuntimeError as e:
        raise RuntimeError(str(e))
    
    found = OggPage.seek_to_page_header(in_file)
    if not found:
        logger.error("Second OGG page not found in input file")
        raise RuntimeError("Second OGG page not found in input file")
    
    OggPage(in_file)
    logger.debug("First two pages skipped successfully")


def read_all_remaining_pages(in_file) -> list:
    """
    Read all remaining OGG pages from an input file.
    
    Args:
        in_file: Input file handle
        
    Returns:
        list: List of OggPage objects
    """
    logger.debug("Reading all remaining OGG pages")
    remaining_pages = []
    found = OggPage.seek_to_page_header(in_file)
    page_count = 0
    
    while found:
        remaining_pages.append(OggPage(in_file))
        page_count += 1
        found = OggPage.seek_to_page_header(in_file)
    
    logger.debug("Read %d remaining OGG pages", page_count)
    return remaining_pages


def resize_pages(
    old_pages: list,
    max_page_size: int,
    first_page_size: int,
    template_page,
    last_granule: int = 0,
    start_no: int = 2,
    set_last_page_flag: bool = False
) -> list:
    """
    Resize OGG pages to fit Tonie requirements.
    
    Args:
        old_pages (list): List of original OggPage objects
        max_page_size (int): Maximum size for pages
        first_page_size (int): Size for the first page
        template_page: Template OggPage to use for creating new pages
        last_granule (int): Last granule position
        start_no (int): Starting page number
        set_last_page_flag (bool): Whether to set the last page flag
        
    Returns:
        list: List of resized OggPage objects
    """
    logger.debug("Resizing %d OGG pages (max_size=%d, first_size=%d, start_no=%d)", 
                len(old_pages), max_page_size, first_page_size, start_no)
    
    new_pages = []
    page = None
    page_no = start_no
    max_size = first_page_size
    new_page = OggPage.from_page(template_page)
    new_page.page_no = page_no
    
    while len(old_pages) or not (page is None):
        if page is None:
            page = old_pages.pop(0)
        
        size = page.get_size_of_first_opus_packet()
        seg_count = page.get_segment_count_of_first_opus_packet()
        
        if (size + seg_count + new_page.get_page_size() <= max_size) and (len(new_page.segments) + seg_count < 256):
            for i in range(seg_count):
                new_page.segments.append(page.segments.pop(0))
            if not len(page.segments):
                page = None
        else:
            new_page.pad(max_size)
            new_page.correct_values(last_granule)
            last_granule = new_page.granule_position
            new_pages.append(new_page)
            logger.trace("Created new page #%d with %d segments", page_no, len(new_page.segments))
            
            new_page = OggPage.from_page(template_page)
            page_no = page_no + 1
            new_page.page_no = page_no
            max_size = max_page_size
    
    if len(new_page.segments):
        if set_last_page_flag:
            new_page.page_type = 4
            logger.debug("Setting last page flag on page #%d", page_no)
        new_page.pad(max_size)
        new_page.correct_values(last_granule)
        new_pages.append(new_page)
        logger.trace("Created final page #%d with %d segments", page_no, len(new_page.segments))
    
    logger.debug("Resized to %d OGG pages", len(new_pages))
    return new_pages


def fix_tonie_header(out_file, chapters: list, timestamp: int, sha) -> None:
    """
    Fix the Tonie header in a file.
    
    Args:
        out_file: Output file handle
        chapters (list): List of chapter page numbers
        timestamp (int): Timestamp for the Tonie file
        sha: SHA1 hash object with file content
    """
    logger.info("Writing Tonie header with %d chapters and timestamp %d", len(chapters), timestamp)
    
    from . import tonie_header_pb2
    import struct
    
    tonie_header = tonie_header_pb2.TonieHeader()
    tonie_header.dataHash = sha.digest()
    data_length = out_file.seek(0, 1) - 0x1000
    tonie_header.dataLength = data_length
    tonie_header.timestamp = timestamp
    
    logger.debug("Data length: %d bytes, SHA1: %s", data_length, sha.hexdigest())
    
    for chapter in chapters:
        tonie_header.chapterPages.append(chapter)
        logger.trace("Added chapter at page %d", chapter)
    
    tonie_header.padding = bytes(0x100)
    header = tonie_header.SerializeToString()
    pad = 0xFFC - len(header) + 0x100
    tonie_header.padding = bytes(pad)
    header = tonie_header.SerializeToString()
    
    out_file.seek(0)
    out_file.write(struct.pack(">L", len(header)))
    out_file.write(header)
    
    logger.debug("Tonie header written successfully (size: %d bytes)", len(header))