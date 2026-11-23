#!/usr/bin/env python3
"""
Regression tests for OGG page padding.

Padding a packet that is not the last one on a page (which happens when a page
has so many segments that padding the last packet would exceed the 255 segment
limit) used to insert the new segment at the wrong position, overwriting the
following packet.
"""

import pytest

from TonieToolbox.core.media.formats.ogg.page import OggPage
from TonieToolbox.core.media.formats.opus.packet import OpusPacket

# CELT-only, 20ms, stereo, framepacking 0 (single frame)
TOC_CODE0 = bytes([(31 << 3) | 0b100])


def make_packet(payload_size: int, marker: int) -> OpusPacket:
    packet = OpusPacket(None)
    packet.data = TOC_CODE0 + bytes([marker]) * (payload_size - 1)
    packet.size = len(packet.data)
    packet.first_packet = True
    packet.spanning_packet = False
    packet.config_value = 31
    packet.stereo = 1
    packet.framepacking = 0
    packet.padding = 0
    packet.frame_count = 1
    packet.frame_size = 20
    packet.granule = 960
    return packet


def make_page(packet_count: int, packet_size: int = 3) -> OggPage:
    page = OggPage(None)
    page.page_no = 1
    page.segments = [make_packet(packet_size, marker=i % 256) for i in range(packet_count)]
    return page


@pytest.mark.unit
class TestOggPagePadding:

    def test_padding_packet_in_middle_of_page_keeps_following_packets(self):
        page = make_page(5)
        following = [bytes(s.data) for s in page.segments[3:]]
        target = page.get_page_size() + 392

        page.pad(target, idx_offset=2)

        assert page.get_page_size() == target
        # The padded packet now spans two segments, followed by the untouched packets
        assert [s.size for s in page.segments[2:4]] == [255, 139]
        assert not page.segments[3].first_packet
        assert [bytes(s.data) for s in page.segments[4:]] == following
        assert all(s.first_packet for s in page.segments[4:])

    def test_padding_page_with_too_many_segments(self):
        # 253 tiny packets: padding only the last packet would need more than 255 segments
        page = make_page(253)
        target = 4096

        page.pad(target)

        assert page.get_page_size() == target
        assert len(page.segments) <= 255
