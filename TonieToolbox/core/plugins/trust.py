#!/usr/bin/env python3
"""
Trust model for plugin verification and security.

Implements a tiered trust system for plugins:
- Official: Core team plugins (auto-approved, no warnings)
- Verified: Community contributors with proven track record
- Community: All other plugins (require user confirmation)
"""
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
from ..utils import get_logger

logger = get_logger(__name__)


@dataclass
class TrustBadge:
    """Trust badge information for display."""
    emoji: str
    label: str
    description: str
    color: str  # Hex color for UI


class TrustLevel:
    """Trust level constants."""
    OFFICIAL = "official"
    VERIFIED = "verified"
    COMMUNITY = "community"


# Trust level configuration
TRUST_CONFIG = {
    TrustLevel.OFFICIAL: {
        "authors": ["TonieToolbox"],
        "auto_verify": True,
        "auto_merge": True,
        "requires_user_confirmation": False,
        "badge": TrustBadge(
            emoji="🏆",
            label="Official",
            description="Developed by the TonieToolbox core team",
            color="#FFD700"
        )
    },
    TrustLevel.VERIFIED: {
        "authors": [],  # Populated from config/database
        "auto_verify": False,
        "requires_review": True,
        "requires_user_confirmation": False,  # Only first time
        "review_priority": "medium",
        "badge": TrustBadge(
            emoji="✅",
            label="Verified",
            description="Reviewed and approved by TonieToolbox maintainers",
            color="#4CAF50"
        )
    },
    TrustLevel.COMMUNITY: {
        "auto_verify": False,
        "requires_review": True,
        "requires_user_confirmation": True,
        "review_priority": "high",
        "badge": TrustBadge(
            emoji="👥",
            label="Community",
            description="Community-contributed plugin - install at your own risk",
            color="#757575"
        )
    }
}


class TrustManager:
    """Manages plugin trust levels and verification."""
    
    def __init__(self, config_manager=None):
        """
        Initialize trust manager.
        
        Args:
            config_manager: Optional config manager for loading verified authors
        """
        self.config_manager = config_manager
        self._verified_authors: Set[str] = set()
        self._load_verified_authors()
    
    def _load_verified_authors(self) -> None:
        """Load verified authors from configuration."""
        if self.config_manager:
            try:
                verified = getattr(self.config_manager.plugins, 'verified_authors', [])
                self._verified_authors = set(verified)
                logger.info(f"Loaded {len(self._verified_authors)} verified authors")
            except Exception as e:
                logger.warning(f"Failed to load verified authors: {e}")
        
        # Add verified authors from config
        self._verified_authors.update(TRUST_CONFIG[TrustLevel.VERIFIED]["authors"])
    
    def get_trust_level(self, author: str, plugin_id: Optional[str] = None) -> str:
        """
        Determine trust level for a plugin.
        
        Args:
            author: Plugin author
            plugin_id: Optional plugin ID for additional checks
            
        Returns:
            Trust level string ("official", "verified", or "community")
        """
        # Check if official author
        if author in TRUST_CONFIG[TrustLevel.OFFICIAL]["authors"]:
            return TrustLevel.OFFICIAL
        
        # Check if verified author
        if author in self._verified_authors:
            return TrustLevel.VERIFIED
        
        # Default to community
        return TrustLevel.COMMUNITY
    
    def get_badge(self, trust_level: str) -> TrustBadge:
        """
        Get trust badge for display.
        
        Args:
            trust_level: Trust level string
            
        Returns:
            TrustBadge for the trust level
        """
        return TRUST_CONFIG.get(trust_level, TRUST_CONFIG[TrustLevel.COMMUNITY])["badge"]
    
    def requires_user_confirmation(self, trust_level: str) -> bool:
        """
        Check if plugin requires user confirmation before installation.
        
        Args:
            trust_level: Trust level string
            
        Returns:
            True if user confirmation required
        """
        return TRUST_CONFIG.get(trust_level, {}).get("requires_user_confirmation", True)
    
    def requires_review(self, trust_level: str) -> bool:
        """
        Check if plugin requires manual review.
        
        Args:
            trust_level: Trust level string
            
        Returns:
            True if manual review required
        """
        return TRUST_CONFIG.get(trust_level, {}).get("requires_review", True)
    
    def can_auto_merge(self, trust_level: str) -> bool:
        """
        Check if plugin can be auto-merged to repository.
        
        Args:
            trust_level: Trust level string
            
        Returns:
            True if auto-merge allowed
        """
        return TRUST_CONFIG.get(trust_level, {}).get("auto_merge", False)
    
    def add_verified_author(self, author: str) -> bool:
        """
        Add an author to the verified list.
        
        Args:
            author: Author name to verify
            
        Returns:
            True if added successfully
        """
        if author in self._verified_authors:
            logger.info(f"Author '{author}' is already verified")
            return False
        
        self._verified_authors.add(author)
        
        # Save to config if available
        if self.config_manager:
            try:
                self.config_manager.plugins.verified_authors = list(self._verified_authors)
                self.config_manager.save_config()
                logger.info(f"Added '{author}' to verified authors")
                return True
            except Exception as e:
                logger.error(f"Failed to save verified author: {e}")
                return False
        
        return True
    
    def remove_verified_author(self, author: str) -> bool:
        """
        Remove an author from the verified list.
        
        Args:
            author: Author name to remove
            
        Returns:
            True if removed successfully
        """
        if author not in self._verified_authors:
            logger.warning(f"Author '{author}' is not in verified list")
            return False
        
        self._verified_authors.remove(author)
        
        # Save to config if available
        if self.config_manager:
            try:
                self.config_manager.plugins.verified_authors = list(self._verified_authors)
                self.config_manager.save_config()
                logger.info(f"Removed '{author}' from verified authors")
                return True
            except Exception as e:
                logger.error(f"Failed to save verified authors: {e}")
                return False
        
        return True
    
    def get_verified_authors(self) -> List[str]:
        """
        Get list of all verified authors.
        
        Returns:
            List of verified author names
        """
        return sorted(self._verified_authors)
    
    def get_warning_message(self, trust_level: str, plugin_name: str) -> str:
        """
        Get user warning message for plugin installation.
        
        Args:
            trust_level: Trust level string
            plugin_name: Plugin name
            
        Returns:
            Warning message string (empty if no warning needed)
        """
        if trust_level == TrustLevel.OFFICIAL:
            return ""
        
        if trust_level == TrustLevel.VERIFIED:
            return f"'{plugin_name}' is a verified community plugin. It has been reviewed by maintainers."
        
        # Community plugins
        return (
            f"⚠️ '{plugin_name}' is a community plugin that has not been verified.\n\n"
            "Community plugins may:\n"
            "- Access your files and network\n"
            "- Execute arbitrary code\n"
            "- Contain security vulnerabilities\n\n"
            "Only install plugins from sources you trust.\n"
            "Do you want to continue?"
        )


# Global trust manager instance
_trust_manager = None


def get_trust_manager(config_manager=None) -> TrustManager:
    """
    Get the global trust manager instance.
    
    Args:
        config_manager: Optional config manager
        
    Returns:
        TrustManager instance
    """
    global _trust_manager
    if _trust_manager is None:
        _trust_manager = TrustManager(config_manager=config_manager)
    return _trust_manager
