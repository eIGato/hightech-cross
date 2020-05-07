from django.urls import (
    include,
    path,
)
from rest_framework_nested import routers

from . import views

cross_router = routers.SimpleRouter()
cross_router.register(r'crosses', views.CrossViewSet)
mission_router = routers.NestedSimpleRouter(
    cross_router,
    r'crosses',
    lookup='cross',
)
mission_router.register(r'missions', views.MissionViewSet)
answer_router = routers.NestedSimpleRouter(
    mission_router,
    r'missions',
    lookup='mission',
)
answer_router.register(r'answers', views.AnswerViewSet)
urlpatterns = [
    path('', include(cross_router.urls)),
    path('', include(mission_router.urls)),
    path('', include(answer_router.urls)),
]
