from django.apps import AppConfig


class MainAppConfig(AppConfig):
    name = 'main_app'

    def ready(self):
        # Автоматичне створення адміна при запуску на новій БД PostgreSQL
        try:
            from django.contrib.auth.models import User
            
            # Якщо користувача з ім'ям 'admin' ще немає — створюємо його
            if not User.objects.filter(username='admin').exists():
                User.objects.create_superuser(
                    username='admin',
                    email='sergijmarcinisen1@gmail.com',
                    password='admin12345'
                )
                print("Суперкористувача 'admin' успішно створено!")
            else:
                # Якщо він вже існує — переконуємося, що в нього є всі права
                user = User.objects.get(username='admin')
                user.is_staff = True
                user.is_superuser = True
                user.set_password('admin12345')
                user.save()
        except Exception:
            pass
