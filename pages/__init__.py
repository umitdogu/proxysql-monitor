"""Page modules for ProxySQL Monitor"""

from .frontend_page import FrontendPage
from .backend_page import BackendPage
from .runtime_page import RuntimePage
from .performance_page import PerformancePage
from .logs_page import LogsPage

__all__ = [
    'FrontendPage',
    'BackendPage',
    'RuntimePage',
    'PerformancePage',
    'LogsPage'
]

