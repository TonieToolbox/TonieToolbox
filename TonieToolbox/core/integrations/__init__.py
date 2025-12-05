# Integration system exports
from .base.integration import BaseIntegration, UploadConfiguration
from .base.commands import IntegrationCommand, CommandSet, StandardCommandFactory
from .base.templates import get_template_manager
from .manager import IntegrationManager, install_integration, uninstall_integration
from .completion import CompletionInstaller
from .wrapper import handle_integration

# Platform-specific integrations
try:
    from .platforms.windows.registry import WindowsIntegration
except ImportError:
    WindowsIntegration = None

try:
    from .platforms.macos.automator import MacOSIntegration
except ImportError:
    MacOSIntegration = None

try:
    from .platforms.linux.kde import KDEIntegration
except ImportError:
    KDEIntegration = None

try:
    from .platforms.linux.xfce import XFCEIntegration
except ImportError:
    XFCEIntegration = None

try:
    from .platforms.linux.gnome import GNOMEIntegration, UbuntuIntegration
except ImportError:
    GNOMEIntegration = None
    UbuntuIntegration = None

try:
    from .platforms.linux.mate import MATEIntegration
except ImportError:
    MATEIntegration = None

try:
    from .platforms.linux.cinnamon import CinnamonIntegration
except ImportError:
    CinnamonIntegration = None

try:
    from .platforms.linux.lxqt import LXQTIntegration
except ImportError:
    LXQTIntegration = None

__all__ = [
    'BaseIntegration',
    'UploadConfiguration', 
    'IntegrationCommand',
    'CommandSet',
    'StandardCommandFactory',
    'get_template_manager',
    'IntegrationManager',
    'install_integration',
    'uninstall_integration',
    'WindowsIntegration',
    'MacOSIntegration',
    'KDEIntegration',
    'XFCEIntegration',
    'GNOMEIntegration',
    'UbuntuIntegration',
    'MATEIntegration',
    'CinnamonIntegration',
    'LXQTIntegration'
]