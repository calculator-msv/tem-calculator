from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0003_remove_car_vin_code_remove_save_info_cars_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='calculation',
            name='kind',
            field=models.CharField(blank=True, default='', max_length=10, verbose_name='Тип запису'),
        ),
        migrations.AddField(
            model_name='calculation',
            name='image_data',
            field=models.TextField(blank=True, default='', verbose_name='Зображення маршруту (Base64)'),
        ),
        migrations.AddField(
            model_name='calculation',
            name='segments_json',
            field=models.TextField(default='[]', verbose_name='Ділянки маршруту JSON'),
        ),
        migrations.AddField(
            model_name='calculation',
            name='meta',
            field=models.TextField(default='{}', verbose_name='Додаткові дані JSON'),
        ),
    ]
