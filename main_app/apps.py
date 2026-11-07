import os

from django.apps import AppConfig
from django.db.models.signals import post_migrate


def create_admin(sender, **kwargs):
    """Створює суперкористувача після міграцій, але ТІЛЬКИ якщо в змінних середовища
    задано DJANGO_ADMIN_PASSWORD (на Render: Environment -> Add variable).
    Логін береться з DJANGO_ADMIN_USERNAME (за замовчуванням «admin»), пошта – з DJANGO_ADMIN_EMAIL.
    Пароль існуючого користувача НІКОЛИ не змінюється й у коді не зберігається."""
    password = os.environ.get('DJANGO_ADMIN_PASSWORD')
    if not password:
        return
    from django.contrib.auth import get_user_model
    User = get_user_model()
    username = os.environ.get('DJANGO_ADMIN_USERNAME', 'admin')
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(
            username=username,
            email=os.environ.get('DJANGO_ADMIN_EMAIL', ''),
            password=password,
        )


class MainAppConfig(AppConfig):
    name = 'main_app'

    def ready(self):
        post_migrate.connect(create_admin, sender=self)