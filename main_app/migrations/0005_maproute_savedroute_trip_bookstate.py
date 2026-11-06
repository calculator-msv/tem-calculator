import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Схема: окремі таблиці для маршрутів з карти, маршрутів і поїздок калькулятора,
    а також для поточної книги обліку. Дані зі старої таблиці Calculation переносить 0006."""

    dependencies = [
        ('main_app', '0004_calculation_kind_image_meta'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='calculation',
            options={'verbose_name': 'Розрахунок (старий архів)', 'verbose_name_plural': 'Старий архів розрахунків'},
        ),
        migrations.CreateModel(
            name='MapRoute',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Назва маршруту')),
                ('distance', models.FloatField(default=0.0, verbose_name='Відстань (км)')),
                ('cities_json', models.TextField(default='{}', verbose_name='Відстані по населених пунктах JSON')),
                ('segments_json', models.TextField(default='[]', verbose_name='Ділянки маршруту JSON')),
                ('image_data', models.TextField(blank=True, default='', verbose_name='Зображення маршруту (Base64)')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Створено')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Користувач')),
            ],
            options={
                'verbose_name': 'Маршрут з карти',
                'verbose_name_plural': 'Маршрути з карти',
            },
        ),
        migrations.CreateModel(
            name='SavedRoute',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Назва маршруту')),
                ('distance', models.FloatField(default=0.0, verbose_name='Відстань (км)')),
                ('max_weight', models.FloatField(default=0.0, verbose_name='Макс. вага вантажу (т)')),
                ('trailer', models.FloatField(default=0.0, verbose_name='Маса причепа (т)')),
                ('rows_json', models.TextField(default='[]', verbose_name='Ділянки (таблиця) JSON')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Створено')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Користувач')),
            ],
            options={
                'verbose_name': 'Маршрут калькулятора',
                'verbose_name_plural': 'Маршрути калькулятора',
            },
        ),
        migrations.CreateModel(
            name='Trip',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Назва поїздки')),
                ('distance', models.FloatField(default=0.0, verbose_name='Відстань (км)')),
                ('max_weight', models.FloatField(default=0.0, verbose_name='Макс. вага вантажу (т)')),
                ('trailer', models.FloatField(default=0.0, verbose_name='Маса причепа (т)')),
                ('fuel_consumed', models.FloatField(default=0.0, verbose_name='Витрата пального (л)')),
                ('rows_json', models.TextField(default='[]', verbose_name='Ділянки (таблиця) JSON')),
                ('meta', models.TextField(default='{}', verbose_name='Додаткові дані JSON')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Створено')),
                ('car', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='main_app.vehicle', verbose_name='Автомобіль')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Користувач')),
            ],
            options={
                'verbose_name': 'Поїздка',
                'verbose_name_plural': 'Поїздки',
            },
        ),
        migrations.CreateModel(
            name='BookState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('car_title', models.TextField(blank=True, default='', verbose_name='Автомобіль (HTML)')),
                ('car_plate', models.CharField(blank=True, default='', max_length=50, verbose_name='Номерний знак')),
                ('fuel_type', models.CharField(blank=True, default='', max_length=100, verbose_name='Вид пального')),
                ('oil_type', models.CharField(blank=True, default='', max_length=100, verbose_name='Вид оливи')),
                ('entries_data', models.TextField(default='[]', verbose_name='Записи JSON')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Оновлено')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Користувач')),
            ],
            options={
                'verbose_name': 'Поточна книга обліку',
                'verbose_name_plural': 'Поточні книги обліку',
            },
        ),
    ]
