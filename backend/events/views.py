from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination

from django_filters.rest_framework import DjangoFilterBackend

from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import (Activity,
                     Event,
                     FavoriteEvent,
                     Participation,
                     Like)

from .serializers import (ActivitySerializer,
                          EventSerializer,
                          CommentSerializer)

from .permissions import IsAdminAuthorOrReadOnly
from .pagination import CustomPaginator
from .filters import EventFilter, ActivityFilter
from utils.crud import create_relation, delete_relation


@extend_schema(tags=['Активности'])
@extend_schema_view(
    list=extend_schema(summary='Получение списка активностей'),
    retrieve=extend_schema(summary='Активность'),
)
class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для просмотра видов активности."""
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    pagination_class = None
    permission_classes = (permissions.AllowAny,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = ActivityFilter


@extend_schema(tags=['Мероприятие'])
@extend_schema_view(
    list=extend_schema(summary='Получение списка мероприятий'),
    create=extend_schema(summary='Создание нового мероприятия'),
    retrieve=extend_schema(summary='Получение данных о мероприятии'),
    update=extend_schema(summary='Изменение данные о мероприятии'),
    partial_update=extend_schema(summary='Частичное изменение данных о мероприятии'),
    destroy=extend_schema(summary='Удаление данных о мероприятии'),
)
class EventViewSet(viewsets.ModelViewSet):
    """Вьюсет для работы с постами мероприятий."""
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PageNumberPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = EventFilter

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.AllowAny]
        elif self.request.method in ['PATCH', 'DELETE']:
            self.permission_classes = [IsAdminAuthorOrReadOnly]
        else:
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()
    
    @extend_schema(summary='Избранное')
    @action(methods=['POST', 'DELETE'],
            detail=True,
            permission_classes=[permissions.IsAuthenticated, ])
    def favorite(self, request, pk):
        if request.method == 'POST':
            return create_relation(request,
                                   Event,
                                   FavoriteEvent,
                                   pk,
                                   EventSerializer,
                                   'event')
        return delete_relation(request,
                               Event,
                               FavoriteEvent,
                               pk,
                               'event')

    @extend_schema(summary='Заявка на участие в мероприятии')
    @action(methods=['POST', 'DELETE'],
            detail=True,
            permission_classes=[permissions.IsAuthenticated, ])
    def participate(self, request, pk):
        if request.method == 'POST':
            return create_relation(request,
                                   Event,
                                   Participation,
                                   pk,
                                   EventSerializer,
                                   'event')
        return delete_relation(request,
                               Event,
                               Participation,
                               pk,
                               'event')


@extend_schema(tags=['Комментарий к мероприятию'])
@extend_schema_view(
    list=extend_schema(summary='Получение списока комментариев к мероприятию'),
    create=extend_schema(summary='Создание комментария к мероприятию'),
    retrieve=extend_schema(summary='Получение комментария к мероприятию'),
    update=extend_schema(summary='Изменение комментария к мероприятию'),
    partial_update=extend_schema(summary='Частичное изменение комментария к мероприятию'),
    destroy=extend_schema(summary='Удаление коментария к мероприятию'),
)
class CommentViewSet(viewsets.ModelViewSet):
    """Сериализатор для комментариев к постам."""
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPaginator

    def get_queryset(self):
        post = get_object_or_404(Event, id=self.kwargs['event_id'])
        return post.comments.all()

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.AllowAny]
        elif self.request.method == 'PATCH' or self.request.method == 'DELETE':
            self.permission_classes = [IsAdminAuthorOrReadOnly]
        else:
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

    def perform_create(self, serializer):
        event = get_object_or_404(Event, id=self.kwargs['event_id'])
        serializer.save(author=self.request.user, event=event)

    @extend_schema(summary='Лайк')
    @action(methods=['POST', 'DELETE'],
            detail=True,
            permission_classes=(permissions.IsAuthenticated,))
    def like(self, request, event_id, pk):
        event = get_object_or_404(Event, id=event_id)
        comment = event.comments.get(id=pk)
        like = Like.objects.filter(user=request.user, comment=comment)

        if request.method == 'POST':
            if like.exists():
                return Response('Вы уже оценили этот комментарий.',
                                status=status.HTTP_400_BAD_REQUEST)
            Like.objects.create(user=request.user, comment=comment)
            serializer = CommentSerializer(comment,
                                           context={'request': request})

            return Response(data=serializer.data,
                            status=status.HTTP_201_CREATED)

        if not like.exists():
            return Response('Вы еще не оценили этот комментарий.',
                            status=status.HTTP_400_BAD_REQUEST)
        like.delete()
        return Response(data=self.get_serializer(comment).data,
                        status=status.HTTP_204_NO_CONTENT)

