from .auth_router import auth_router
from .user_router import user_router
from .role_router import role_router
from .group_router import group_router
from .permission_router import permission_router
from .entity_router import entity_router
from .membership_router import membership_router
from .activity_router import activity_router
from .communication_router import communication_router
from .comment_router import comment_router
from .magazine_router import magazine_router
from .branding_router import branding_router
from .view_config_router import view_config_router
from .resource_router import resource_router, category_router
from .notification_router import notification_router
from .chat_router import chat_router
from .membership_request_router import membership_request_router
from .download_router import download_router

routers = [
    auth_router,
    user_router,
    role_router,
    permission_router,
    group_router,
    entity_router,
    membership_router,
    membership_request_router,
    activity_router,
    communication_router,
    comment_router,
    magazine_router,
    branding_router,
    view_config_router,
    resource_router,
    category_router,
    notification_router,
    chat_router,
    download_router,
]