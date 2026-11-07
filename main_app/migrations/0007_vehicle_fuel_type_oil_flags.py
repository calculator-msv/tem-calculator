from django.db import migrations, models


class Migration(migrations.Migration):
    """Вид пального авто та галочки: які оливи/мастила рахувати для цього авто."""

    dependencies = [
        ('main_app', '0006_copy_calculations'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicle',
            name='fuel_type',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='Вид пального'),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='use_om',
            field=models.BooleanField(default=True, verbose_name='Рахувати моторну олію'),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='use_ot',
            field=models.BooleanField(default=True, verbose_name='Рахувати трансмісійну олію'),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='use_os',
            field=models.BooleanField(default=True, verbose_name='Рахувати спеціальну олію'),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='use_op',
            field=models.BooleanField(default=True, verbose_name='Рахувати пластичне мастило'),
        ),
    ]