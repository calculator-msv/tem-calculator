from django.contrib.auth.models import User
from django.test import TestCase
import json

from .models import Vehicle, UserCoeff


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
