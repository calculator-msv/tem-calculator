import json

from django.db import migrations


def _loads(text, default):
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return default


def _kind(calc, details):
    """Тип запису; для старих записів (kind порожній) визначається за вмістом."""
    if calc.kind:
        return calc.kind
    if isinstance(details, list):
        return 'trip' if (calc.car_id or (calc.fuel_consumed or 0) > 0) else 'route'
    return 'map'


def copy_calculations(apps, schema_editor):
    """Переносить записи зі старої таблиці Calculation у MapRoute / SavedRoute / Trip.
    Старі записи НЕ видаляються: вони залишаються як резервна копія."""
    Calculation = apps.get_model('main_app', 'Calculation')
    MapRoute = apps.get_model('main_app', 'MapRoute')
    SavedRoute = apps.get_model('main_app', 'SavedRoute')
    Trip = apps.get_model('main_app', 'Trip')

    for calc in Calculation.objects.all().order_by('id').iterator():
        details = _loads(calc.details, {})
        meta = _loads(calc.meta, {})
        if not isinstance(meta, dict):
            meta = {}
        kind = _kind(calc, details)

        if kind == 'map':
            new = MapRoute.objects.create(
                user_id=calc.user_id,
                name=calc.route,
                distance=calc.distance,
                cities_json=calc.details or '{}',
                segments_json=calc.segments_json or '[]',
                image_data=calc.image_data or '',
            )
            model = MapRoute
        elif kind == 'route':
            new = SavedRoute.objects.create(
                user_id=calc.user_id,
                name=calc.route,
                distance=calc.distance,
                max_weight=calc.cargo,
                trailer=meta.get('trailer') or 0,
                rows_json=calc.details or '[]',
            )
            model = SavedRoute
        else:
            trailer = meta.get('trailer') or 0
            meta['trailer'] = trailer
            new = Trip.objects.create(
                user_id=calc.user_id,
                car_id=calc.car_id,
                name=calc.route,
                distance=calc.distance,
                max_weight=calc.cargo,
                trailer=trailer,
                fuel_consumed=calc.fuel_consumed,
                rows_json=calc.details or '[]',
                meta=json.dumps(meta, ensure_ascii=False),
            )
            model = Trip

        # auto_now_add ставить поточний час — повертаємо оригінальну дату створення
        model.objects.filter(pk=new.pk).update(created_at=calc.created_at)


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0005_maproute_savedroute_trip_bookstate'),
    ]

    operations = [
        # зворотна міграція нічого не робить: старі дані в Calculation не змінювались
        migrations.RunPython(copy_calculations, migrations.RunPython.noop),
    ]