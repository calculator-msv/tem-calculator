from django.apps import apps as django_apps
from django.contrib.auth.models import User
from django.test import TestCase, Client
from unittest import mock
import os
import importlib
import json

from .models import (Vehicle, City, UserCoeff, Calculation, MapRoute, SavedRoute, Trip,
                     UserBook, BookState)
from .apps import create_admin


class CalcApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='t@t.ua', email='t@t.ua', password='123456')
        self.other = User.objects.create_user(username='o@t.ua', email='o@t.ua', password='123456')
        self.car = Vehicle.objects.create(user=self.user, name='УАЗ', hs=30, hw=1.3, om=2.7, ot=0.3, os=0.1, op=0.2)
        self.client.login(username='t@t.ua', password='123456')

    def post(self, payload):
        return self.client.post('/api/calc/', data=json.dumps(payload), content_type='application/json')

    def test_simple_route_without_coeffs(self):
        # 100 км, без вантажу: Q = 0,01 * 30 * 100 = 30 л
        r = self.post({'car_id': self.car.id, 'rows': [{'dist': 100, 'weight': 0}]}).json()
        self.assertTrue(r['success'])
        self.assertAlmostEqual(r['total_q'], 30.0, places=4)
        self.assertAlmostEqual(r['oils']['om'], 30.0 * 2.7 / 100, places=4)

    def test_city_coeff_applied(self):
        r = self.post({'car_id': self.car.id, 'rows': [{'dist': 100, 'weight': 0, 'indK': 10}]}).json()
        self.assertAlmostEqual(r['total_q'], 33.0, places=4)

    def test_k4_k5_only_on_highway(self):
        UserCoeff.objects.create(user=self.user, name='Аеродинамічний опір (K4)', value=5, type='plus')
        UserCoeff.objects.create(user=self.user, name='Робота за межами населених пунктів (K5)', value=15, type='minus')
        r = self.post({'car_id': self.car.id, 'rows': [
            {'dist': 100, 'weight': 0, 'isHighway': False},
            {'dist': 100, 'weight': 0, 'isHighway': True}]}).json()
        self.assertAlmostEqual(r['rows'][0]['q'], 30.0, places=4)          # місто: K4 і K5 не діють
        self.assertAlmostEqual(r['rows'][1]['q'], 30.0 * (1 - 0.10), places=4)  # траса: +5 – 15 = –10 %

    def test_foreign_car_is_rejected(self):
        self.client.logout()
        self.client.login(username='o@t.ua', password='123456')
        r = self.post({'car_id': self.car.id, 'rows': []})
        self.assertEqual(r.status_code, 400)

    def test_bad_numbers_are_ignored(self):
        r = self.post({'car_id': self.car.id, 'rows': [{'dist': 'abc', 'weight': -5}]}).json()
        self.assertEqual(r['total_q'], 0)

    def test_login_required(self):
        self.client.logout()
        r = self.post({'car_id': self.car.id, 'rows': []})
        self.assertEqual(r.status_code, 302)


class HistoryApiTests(TestCase):
    """Маршрути карти, маршрути та поїздки калькулятора зберігаються окремо."""

    def setUp(self):
        self.user = User.objects.create_user(username='h@t.ua', email='h@t.ua', password='123456')
        self.car = Vehicle.objects.create(user=self.user, name='УАЗ', hs=30, hw=1.3)
        self.client.login(username='h@t.ua', password='123456')
        self.rows = json.dumps([{'route': 'Хм - Кр', 'dist': 100, 'cargo': '-', 'weight': 0, 'indK': 0, 'isHighway': False}])

    def api(self, **data):
        return self.client.post('/api/map/', data).json()

    def test_lists_are_independent(self):
        self.assertTrue(self.api(action='save_route', name='З карти', total_dist='41.6 км',
                                 cities_json='{"Хмельницький": 10}', segments_json='[]',
                                 image_data='data:image/jpeg;base64,AAAA')['success'])
        self.assertTrue(self.api(action='save_history', kind='route', name='Маршрут', rows=self.rows)['success'])
        self.assertTrue(self.api(action='save_history', kind='trip', name='Поїздка', rows=self.rows, car_id=self.car.id)['success'])

        maps = self.api(action='fetch_routes')['data']
        routes = self.api(action='fetch_history', kind='route')['data']
        trips = self.api(action='fetch_history', kind='trip')['data']
        self.assertEqual([r['route'] for r in maps], ['З карти'])
        self.assertEqual([r['route'] for r in routes], ['Маршрут'])
        self.assertEqual([r['route'] for r in trips], ['Поїздка'])
        self.assertTrue(maps[0]['has_image'])
        self.assertAlmostEqual(trips[0]['fuel_consumed'], 30.0, places=2)

    def test_trip_requires_car(self):
        self.assertFalse(self.api(action='save_history', kind='trip', name='X', rows=self.rows)['success'])

    def test_route_without_car_is_allowed(self):
        self.assertTrue(self.api(action='save_history', kind='route', name='X', rows=self.rows)['success'])

    def test_image_is_returned_separately(self):
        rid = self.api(action='save_route', name='M', total_dist='1', cities_json='{}',
                       image_data='data:image/jpeg;base64,AAAA')['id']
        res = self.api(action='fetch_route_image', route_id=rid)
        self.assertTrue(res['success'])
        self.assertTrue(res['image_data'].startswith('data:image/'))

    def test_delete_requires_kind_and_hits_only_that_table(self):
        self.api(action='save_route', name='M', total_dist='1', cities_json='{}')
        self.api(action='save_history', kind='route', name='R', rows=self.rows)
        self.api(action='save_history', kind='trip', name='T', rows=self.rows, car_id=self.car.id)
        # id у трьох таблицях збігаються (1) — без типу видаляти не можна
        self.assertFalse(self.api(action='delete_route', route_id=1)['success'])
        self.assertEqual((MapRoute.objects.count(), SavedRoute.objects.count(), Trip.objects.count()), (1, 1, 1))
        self.assertTrue(self.api(action='delete_route', kind='route', route_id=SavedRoute.objects.get().id)['success'])
        self.assertEqual((MapRoute.objects.count(), SavedRoute.objects.count(), Trip.objects.count()), (1, 0, 1))

    def test_records_are_private_per_user(self):
        self.api(action='save_history', kind='route', name='R', rows=self.rows)
        other = User.objects.create_user(username='x@t.ua', email='x@t.ua', password='123456')
        rec = SavedRoute.objects.get()
        self.client.logout()
        self.client.login(username='x@t.ua', password='123456')
        self.assertEqual(self.api(action='fetch_history', kind='route')['data'], [])
        self.api(action='delete_route', kind='route', route_id=rec.id)
        self.assertEqual(SavedRoute.objects.count(), 1)

    def test_history_keeps_trailer(self):
        self.api(action='save_history', kind='route', name='R', rows=self.rows, trailer='2.5')
        item = self.api(action='fetch_history', kind='route')['data'][0]
        self.assertEqual(item['meta']['trailer'], 2.5)


class SplitMigrationTests(TestCase):
    """Міграція 0006 переносить записи зі старої таблиці Calculation в нові таблиці."""

    def test_copy_calculations(self):
        user = User.objects.create_user(username='m@t.ua', email='m@t.ua', password='123456')
        car = Vehicle.objects.create(user=user, name='УАЗ', hs=30)
        rows = json.dumps([{'route': 'A', 'dist': 5}])
        Calculation.objects.create(user=user, kind='map', route='Карта', distance=41.6,
                                   details='{"Хм": 10}', segments_json='[{"loc": "Хм", "dist": 10}]',
                                   image_data='data:image/jpeg;base64,AAAA')
        Calculation.objects.create(user=user, kind='trip', route='Поїздка', car=car, distance=5,
                                   fuel_consumed=1.5, details=rows, meta='{"car_name": "УАЗ"}')
        Calculation.objects.create(user=user, kind='route', route='Маршрут', distance=5, cargo=2,
                                   details=rows, meta='{"trailer": 1.5}')
        # старі записи без kind: тип визначається за вмістом
        Calculation.objects.create(user=user, route='Стара карта', details='{"Кр": 3}')
        Calculation.objects.create(user=user, route='Старий маршрут', details=rows)
        Calculation.objects.create(user=user, route='Стара поїздка', details=rows, fuel_consumed=7)
        old_date = Calculation.objects.get(route='Карта').created_at

        module = importlib.import_module('main_app.migrations.0006_copy_calculations')
        module.copy_calculations(django_apps, None)

        self.assertEqual(sorted(MapRoute.objects.values_list('name', flat=True)), ['Карта', 'Стара карта'])
        self.assertEqual(sorted(SavedRoute.objects.values_list('name', flat=True)), ['Маршрут', 'Старий маршрут'])
        self.assertEqual(sorted(Trip.objects.values_list('name', flat=True)), ['Поїздка', 'Стара поїздка'])
        self.assertEqual(Calculation.objects.count(), 6)   # старі записи не видаляються

        m = MapRoute.objects.get(name='Карта')
        self.assertEqual(m.image_data, 'data:image/jpeg;base64,AAAA')
        self.assertEqual(m.created_at, old_date)
        self.assertEqual(SavedRoute.objects.get(name='Маршрут').trailer, 1.5)
        trip = Trip.objects.get(name='Поїздка')
        self.assertEqual((trip.car_id, trip.fuel_consumed), (car.id, 1.5))
        self.assertEqual(json.loads(trip.meta)['car_name'], 'УАЗ')


class BookApiTests(TestCase):
    """Книга обліку: поточна книга та архів зберігаються на сервері."""

    def setUp(self):
        self.user = User.objects.create_user(username='b@t.ua', email='b@t.ua', password='123456')
        self.client.login(username='b@t.ua', password='123456')
        self.entries = json.dumps([{'date': '01.11', 'distTotal': '10.0'}])

    def api(self, **data):
        return self.client.post('/api/book/', data).json()

    def test_state_roundtrip(self):
        empty = self.api(action='fetch_state')['data']
        self.assertEqual((empty['entries_data'], empty['car_title']), ('[]', ''))
        self.assertTrue(self.api(action='save_state', car_title='УАЗ <b>вантажний</b>', car_plate='ВВ0001АА',
                                 fuel_type='ДП', oil_type='М-10', entries_data=self.entries)['success'])
        st = self.api(action='fetch_state')['data']
        self.assertEqual((st['car_title'], st['car_plate'], st['fuel_type']), ('УАЗ <b>вантажний</b>', 'ВВ0001АА', 'ДП'))
        self.assertEqual(json.loads(st['entries_data'])[0]['distTotal'], '10.0')
        self.assertEqual(BookState.objects.count(), 1)

    def test_invalid_entries_rejected(self):
        self.assertFalse(self.api(action='save_state', entries_data='не json')['success'])
        self.assertFalse(self.api(action='save_book', title='X', entries_data='{"a": 1}')['success'])

    def test_archive_save_list_delete(self):
        res = self.api(action='save_book', title='Архів', car_title='УАЗ', car_plate='ВВ', entries_data=self.entries)
        self.assertTrue(res['success'])
        books = self.api(action='fetch_books')['data']
        self.assertEqual([b['title'] for b in books], ['Архів'])
        self.assertEqual(json.loads(books[0]['entries_data'])[0]['date'], '01.11')
        self.assertTrue(self.api(action='delete_book', book_id=res['id'])['success'])
        self.assertEqual(UserBook.objects.count(), 0)

    def test_long_car_title_is_shortened_without_broken_tags(self):
        title = 'Дуже довга назва автомобіля ' * 4 + '<b>вантажний</b>'
        self.assertTrue(self.api(action='save_book', title='X', car_title=title, entries_data='[]')['success'])
        saved = UserBook.objects.get().car_title
        self.assertLessEqual(len(saved), 100)
        self.assertNotIn('<', saved)

    def test_archives_are_private(self):
        book = UserBook.objects.create(user=self.user, title='Моя')
        User.objects.create_user(username='z@t.ua', email='z@t.ua', password='123456')
        self.client.logout()
        self.client.login(username='z@t.ua', password='123456')
        self.assertEqual(self.api(action='fetch_books')['data'], [])
        self.api(action='delete_book', book_id=book.id)
        self.assertEqual(UserBook.objects.count(), 1)


class FormulaTests(TestCase):
    """Методичні рекомендації, п. 4.4, формула (5):
    Q = 0,01 · (Hsan · S + Hw · W) · (1 + 0,01 · K),  Hsan = Hs + Hg · Gпр."""

    def setUp(self):
        self.user = User.objects.create_user(username='f@t.ua', email='f@t.ua', password='123456')
        self.car = Vehicle.objects.create(user=self.user, name='КамАЗ', hs=30, hw=1.3)
        self.client.login(username='f@t.ua', password='123456')

    def calc(self, **extra):
        payload = {'car_id': self.car.id, 'rows': [{'dist': 100, 'weight': 5, 'indK': 10}]}
        payload.update(extra)
        return self.client.post('/api/calc/', data=json.dumps(payload), content_type='application/json').json()

    def test_k_applies_to_transport_work(self):
        # W = 5·100 = 500 т·км:  0,01·(30·100 + 1,3·500)·1,10 = 40,15 л
        self.assertAlmostEqual(self.calc()['total_q'], 40.15, places=4)

    def test_trailer_goes_into_hsan(self):
        # Hsan = 30 + 1,3·2 = 32,6:  0,01·(32,6·100 + 1,3·500)·1,10 = 43,01 л
        self.assertAlmostEqual(self.calc(trailer=2)['total_q'], 43.01, places=4)


class CarEditTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='c@t.ua', email='c@t.ua', password='123456')
        self.car = Vehicle.objects.create(user=self.user, name='УАЗ', plate='AA 1', hs=30, hw=1.3)
        self.client.login(username='c@t.ua', password='123456')

    def api(self, **data):
        return self.client.post('/api/cars/', data).json()

    def test_update_car(self):
        res = self.api(action='update_car', id=self.car.id, name='УАЗ-469', plate='BB 2', category='Спеціальні',
                       hs='28,5', hw='1.5', has_cargo='1', max_payload='0.8', om='3', ot='0.4', os='0.2', op='0.3',
                       has_adblue='0', adblue='5')
        self.assertTrue(res['success'])
        car = Vehicle.objects.get(pk=self.car.pk)
        self.assertEqual((car.name, car.plate, car.category), ('УАЗ-469', 'BB 2', 'Спеціальні'))
        self.assertEqual((car.hs, car.hw, car.max_payload, car.om), (28.5, 1.5, 0.8, 3.0))
        self.assertEqual(car.adblue, 0)           # AdBlue вимкнено — норма скидається
        self.assertEqual(Vehicle.objects.count(), 1)

    def test_update_requires_name(self):
        self.assertFalse(self.api(action='update_car', id=self.car.id, name=' ')['success'])

    def test_cannot_update_foreign_car(self):
        other = User.objects.create_user(username='z@t.ua', email='z@t.ua', password='123456')
        foreign = Vehicle.objects.create(user=other, name='Чужий', hs=10)
        self.assertFalse(self.api(action='update_car', id=foreign.id, name='Мій', hs='1')['success'])
        self.assertEqual(Vehicle.objects.get(pk=foreign.pk).name, 'Чужий')


class CitiesApiTests(TestCase):
    def setUp(self):
        self.a = User.objects.create_user(username='a@t.ua', email='a@t.ua', password='123456')
        self.b = User.objects.create_user(username='b@t.ua', email='b@t.ua', password='123456')

    def api(self, **data):
        return self.client.post('/api/cities/', data).json()

    def login(self, name):
        self.client.logout()
        self.client.login(username=name, password='123456')

    def test_cities_are_per_user(self):
        self.login('a@t.ua')
        self.api(action='add_city', name='Київ', percent='25')
        self.login('b@t.ua')
        self.assertEqual(self.api(action='fetch_cities')['data'], [])
        self.api(action='add_city', name='Київ', percent='10')     # те саме ім'я в іншого користувача — окремий запис
        self.assertEqual(City.objects.count(), 2)
        self.assertEqual(self.api(action='fetch_cities')['data'][0]['percent'], '10.0')

    def test_cannot_delete_foreign_city(self):
        city = City.objects.create(user=self.a, name='Львів', percent=5)
        self.login('b@t.ua')
        self.api(action='delete_city', city_id=city.id)
        self.assertTrue(City.objects.filter(pk=city.pk).exists())

    def test_legacy_city_without_owner_is_visible_but_not_deletable(self):
        city = City.objects.create(user=None, name='Старе', percent=7)
        self.login('a@t.ua')
        self.assertEqual([c['name'] for c in self.api(action='fetch_cities')['data']], ['Старе'])
        self.api(action='delete_city', city_id=city.id)
        self.assertTrue(City.objects.filter(pk=city.pk).exists())


class CsrfAndAdminTests(TestCase):
    def test_api_enforces_csrf(self):
        User.objects.create_user(username='s@t.ua', email='s@t.ua', password='123456')
        strict = Client(enforce_csrf_checks=True)
        strict.login(username='s@t.ua', password='123456')
        self.assertEqual(strict.post('/api/cars/', {'action': 'fetch_cars'}).status_code, 403)

    def test_admin_not_created_without_env_password(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('DJANGO_ADMIN_PASSWORD', None)
            create_admin(sender=None)
        self.assertFalse(User.objects.filter(username='admin').exists())

    def test_admin_created_once_and_password_not_reset(self):
        with mock.patch.dict(os.environ, {'DJANGO_ADMIN_PASSWORD': 'first-pass-1'}):
            create_admin(sender=None)
            admin = User.objects.get(username='admin')
            self.assertTrue(admin.is_superuser and admin.check_password('first-pass-1'))
            admin.set_password('changed-by-owner')
            admin.save()
            create_admin(sender=None)               # повторний запуск не чіпає пароль
        self.assertTrue(User.objects.get(username='admin').check_password('changed-by-owner'))