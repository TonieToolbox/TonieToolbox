#!/usr/bin/env python3
"""
Test trust level integration with plugin manager and GUI.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from TonieToolbox.core.plugins.manager import PluginManager
from TonieToolbox.core.plugins.trust import TrustManager, TrustLevel
from TonieToolbox.core.plugins.base import PluginManifest, PluginMetadata, PluginType


class TestTrustIntegration:
    """Test trust level integration across the plugin system."""
    
    def test_plugin_manager_has_trust_manager(self):
        """Test that PluginManager initializes with TrustManager."""
        manager = PluginManager(config_manager=None, app_version="1.0.0")
        
        assert hasattr(manager, 'trust_manager')
        assert isinstance(manager.trust_manager, TrustManager)
    
    def test_trust_manager_shared_across_components(self):
        """Test that TrustManager is properly shared."""
        from TonieToolbox.core.plugins.trust import get_trust_manager
        
        manager = PluginManager(config_manager=None)
        trust1 = get_trust_manager()
        trust2 = manager.trust_manager
        
        # Should be the same instance
        assert trust1 is trust2
    
    def test_repository_sets_trust_level_on_manifest(self):
        """Test that repository sets trust_level based on author."""
        from TonieToolbox.core.plugins.repository import PluginRepository
        
        repo = PluginRepository()
        
        # Create test manifest data
        official_data = {
            "id": "com.tonietoolbox.test_plugin",
            "name": "Test Plugin",
            "version": "1.0.0",
            "author": "TonieToolbox",
            "description": "Official test plugin",
            "plugin_type": "gui",
            "dependencies": {}
        }
        
        manifest = repo._parse_manifest(official_data)
        
        # Official plugins should have official trust level
        assert manifest.metadata.trust_level == TrustLevel.OFFICIAL
    
    def test_repository_sets_community_trust_for_unknown_author(self):
        """Test that unknown authors get community trust level."""
        from TonieToolbox.core.plugins.repository import PluginRepository
        
        repo = PluginRepository()
        
        community_data = {
            "id": "com.unknown.test_plugin",
            "name": "Test Plugin",
            "version": "1.0.0",
            "author": "UnknownAuthor",
            "description": "Community test plugin",
            "plugin_type": "gui",
            "dependencies": {}
        }
        
        manifest = repo._parse_manifest(community_data)
        
        # Unknown authors should have community trust level
        assert manifest.metadata.trust_level == TrustLevel.COMMUNITY
    
    def test_trust_manager_get_warning_for_official(self):
        """Test that official plugins don't require warnings."""
        manager = PluginManager()
        
        warning = manager.trust_manager.get_warning_message(
            TrustLevel.OFFICIAL,
            "Official Plugin"
        )
        
        # Official plugins should have no warning
        assert warning == ""
    
    def test_trust_manager_get_warning_for_community(self):
        """Test that community plugins get security warnings."""
        manager = PluginManager()
        
        warning = manager.trust_manager.get_warning_message(
            TrustLevel.COMMUNITY,
            "Community Plugin"
        )
        
        # Community plugins should have security warning
        assert warning != ""
        assert "⚠️" in warning or "community plugin" in warning.lower()
    
    def test_trust_manager_requires_confirmation_for_community(self):
        """Test that community plugins require user confirmation."""
        manager = PluginManager()
        
        requires = manager.trust_manager.requires_user_confirmation(TrustLevel.COMMUNITY)
        assert requires is True
    
    def test_trust_manager_no_confirmation_for_official(self):
        """Test that official plugins don't require user confirmation."""
        manager = PluginManager()
        
        requires = manager.trust_manager.requires_user_confirmation(TrustLevel.OFFICIAL)
        assert requires is False
    
    def test_trust_level_persists_in_manifest(self):
        """Test that trust level is properly stored in manifest."""
        metadata = PluginMetadata(
            id="com.test.plugin",
            name="Test",
            version="1.0.0",
            author="TestAuthor",
            description="Test",
            plugin_type=PluginType.GUI,
            trust_level=TrustLevel.VERIFIED
        )
        
        assert metadata.trust_level == TrustLevel.VERIFIED
    
    def test_trust_badge_display_data(self):
        """Test that trust badges have proper display data."""
        manager = PluginManager()
        
        official_badge = manager.trust_manager.get_badge(TrustLevel.OFFICIAL)
        assert official_badge.emoji == "🏆"
        assert "Official" in official_badge.label
        
        verified_badge = manager.trust_manager.get_badge(TrustLevel.VERIFIED)
        assert verified_badge.emoji == "✅"
        assert "Verified" in verified_badge.label
        
        community_badge = manager.trust_manager.get_badge(TrustLevel.COMMUNITY)
        assert community_badge.emoji == "👥"
        assert "Community" in community_badge.label


class TestTrustGUIIntegration:
    """Test trust level integration with GUI components."""
    
    @pytest.mark.skipif(not pytest.importorskip("PyQt6", reason="PyQt6 not available"), reason="PyQt6 required")
    def test_plugin_card_displays_trust_badge(self, qtbot):
        """Test that PluginCard properly displays trust badges."""
        from TonieToolbox.core.plugins.builtin.plugin_manager.ui.plugin_card import PluginCard
        
        # Mock plugin data with different trust levels
        official_plugin = {
            "id": "com.tonietoolbox.test",
            "name": "Official Plugin",
            "author": "TonieToolbox",
            "description": "Test",
            "plugin_type": "gui",
            "latest_version": "1.0.0",
            "versions": ["1.0.0"],
            "trust_level": TrustLevel.OFFICIAL
        }
        
        mock_manager = Mock()
        mock_manager.get_all_plugins.return_value = {}
        
        card = PluginCard(official_plugin, mock_manager)
        qtbot.addWidget(card)
        
        # Verify trust badge method exists
        badge = card._get_trust_badge(TrustLevel.OFFICIAL)
        assert badge is not None
        assert "Official" in badge['text']
        assert "🏆" in badge['text']
    
    @pytest.mark.skipif(not pytest.importorskip("PyQt6", reason="PyQt6 not available"), reason="PyQt6 required")
    def test_plugin_card_trust_badge_community(self, qtbot):
        """Test community plugin badge display."""
        from TonieToolbox.core.plugins.builtin.plugin_manager.ui.plugin_card import PluginCard
        
        community_plugin = {
            "id": "com.test.plugin",
            "name": "Community Plugin",
            "author": "TestAuthor",
            "description": "Test",
            "plugin_type": "gui",
            "latest_version": "1.0.0",
            "versions": ["1.0.0"],
            "trust_level": TrustLevel.COMMUNITY
        }
        
        mock_manager = Mock()
        mock_manager.get_all_plugins.return_value = {}
        
        card = PluginCard(community_plugin, mock_manager)
        qtbot.addWidget(card)
        badge = card._get_trust_badge(TrustLevel.COMMUNITY)
        
        assert badge is not None
        assert "Community" in badge['text']
        assert "👥" in badge['text']
    
    @pytest.mark.skipif(not pytest.importorskip("PyQt6", reason="PyQt6 not available"), reason="PyQt6 required")
    def test_discover_tab_trust_badge_html(self, qtbot):
        """Test HTML trust badge generation for confirmation dialogs."""
        from TonieToolbox.core.plugins.builtin.plugin_manager.ui.discover_tab import DiscoverTab
        
        mock_manager = Mock()
        mock_manager.search_community_plugins.return_value = []
        mock_manager.get_installed_plugins.return_value = []
        
        tab = DiscoverTab(mock_manager)
        qtbot.addWidget(tab)
        
        official_html = tab._get_trust_badge_html(TrustLevel.OFFICIAL)
        assert "🏆" in official_html
        assert "Official" in official_html
        
        verified_html = tab._get_trust_badge_html(TrustLevel.VERIFIED)
        assert "✅" in verified_html
        assert "Verified" in verified_html
        
        community_html = tab._get_trust_badge_html(TrustLevel.COMMUNITY)
        assert "👥" in community_html
        assert "Community" in community_html


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
