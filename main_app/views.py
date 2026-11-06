import json
import math
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Vehicle, City, UserCoeff, Calculation, UserBook, UserNote, UserLibrary


# --- ГОЛОВНА СТОРІНКА ТА АВТОРИЗАЦІЯ ---
def index_view(request):
    error_msg = None
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'register':
            fullname = request.POST.get('fullname', '').strip()
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password', '')

            if not fullname or not email or not password:
                error_msg = "Заповніть усі поля реєстрації!"
            elif len(password) < 6:
                error_msg = "Пароль повинен бути не менше 6 символів!"
            elif User.objects.filter(email=email).exists():
                error_msg = "Користувач з таким Email вже існує!"
            else:
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=fullname
                )
                login(request, user)
                return redirect('index')

        elif action == 'login':
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password', '')

            try:
                user_obj = User.objects.get(email=email)
                user = authenticate(request, username=user_obj.username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('index')
                else:
                    error_msg = "Невірний пароль!"
            except User.DoesNotExist:
                error_msg = "Користувача з таким Email не знайдено!"

        elif action == 'guest':
            guest_user, created = User.objects.get_or_create(
                username='guest',
                defaults={'first_name': 'Гість'}
            )
            login(request, guest_user)
            return redirect('index')

    return render(request, 'main_app/index.html', {'error_msg': error_msg})


def logout_view(request):
    logout(request)
    return redirect('index')


# --- ВІДОБРАЖЕННЯ МОДУЛІВ СИСТЕМИ ---
@login_required
def calc_view(request):
    return render(request, 'main_app/calc.html')

@login_required
def cars_view(request):
    return render(request, 'main_app/cars.html')

@login_required
def cities_view(request):
    return render(request, 'main_app/cities.html')

@login_required
def coeffs_view(request):
    return render(request, 'main_app/coeffs.html')

@login_required
def book_view(request):
    return render(request, 'main_app/book.html')

@login_required
def library_view(request):
    return render(request, 'main_app/library.html')

@login_required
def map_view(request):
    return render(request, 'main_app/map.html')

@login_required
def preview_view(request):
    return render(request, 'main_app/preview.html')



# =====================================================================
# РОЗРАХУНОК ПАЛЬНОГО НА СЕРВЕРІ (єдине місце з формулою)
# =====================================================================
# Чи множити коефіцієнт (1 + 0,01·K) також на транспортну роботу Hw·W.
#   False – як рахував калькулятор у браузері до перенесення на сервер:
#           Q = 0,01·Hs·S·(1 + 0,01·K) + 0,01·Hw·W
#   True  – за формулою з методики та реферату:
#           Q = 0,01·(Hs·S + Hw·W)·(1 + 0,01·K)
# Оберіть варіант, який відповідає чинному наказу (див. реферат, формула 2.1).
K_APPLIES_TO_TRANSPORT_WORK = False

MAX_ROWS = 500


def _num(value, default=0.0):
    """Безпечне перетворення в число (приймає кому, відкидає NaN/inf)."""
    try:
        x = float(str(value).replace(',', '.'))
    except (TypeError, ValueError):
        return default
    return x if math.isfinite(x) else default


def _coeff_code(name):
    """Код коефіцієнта з назви, напр. 'Аеродинамічний опір (K4)' -> 'k4'."""
    m = re.search(r'\(K(\d+)\)', name or '', re.IGNORECASE)
    return 'k' + m.group(1) if m else None


def get_user_coeff_summary(user):
    """Повертає (базовий K, K4, K5, список активних коефіцієнтів) з БД користувача.
    K4 (аеродинаміка) та K5 (позаміська траса) застосовуються лише до ділянок «Траса»."""
    base = k4 = k5 = 0.0
    active = []
    for c in UserCoeff.objects.filter(user=user).order_by('id'):
        val = abs(_num(c.value))
        code = _coeff_code(c.name)
        if code == 'k4':
            k4 = val
        if code == 'k5':
            k5 = val
        if val > 0:
            if c.type == 'minus':
                active.append(f"{c.name}: -{val:g}%")
                if code != 'k5':
                    base -= val
            else:
                active.append(f"{c.name}: +{val:g}%")
                if code != 'k4':
                    base += val
    return base, k4, k5, active


def calculate_fuel(vehicle, rows, base_k, k4, k5, trailer_mass=0.0):
    """Розрахунок нормативної витрати пального й олив по ділянках маршруту."""
    hs = _num(vehicle.hs)
    hw = _num(vehicle.hw)
    trailer = max(_num(trailer_mass), 0.0)

    out_rows = []
    total_q = dist_city = dist_out = max_weight = 0.0

    for row in rows[:MAX_ROWS]:
        dist = max(_num(row.get('dist')), 0.0)
        weight = max(_num(row.get('weight')), 0.0)
        is_hwy = bool(row.get('isHighway'))

        ind_k = 0.0 if is_hwy else _num(row.get('indK'))
        sys_k = base_k + ((k4 - k5) if is_hwy else 0.0)   # без міської надбавки
        row_k = sys_k + ind_k
        work = (weight + trailer) * dist                  # т·км

        if K_APPLIES_TO_TRANSPORT_WORK:
            q = 0.01 * (hs * dist + hw * work) * (1 + 0.01 * row_k)
        else:
            q = 0.01 * hs * dist * (1 + 0.01 * row_k) + 0.01 * hw * work

        total_q += q
        max_weight = max(max_weight, weight)
        if is_hwy:
            dist_out += dist
        else:
            dist_city += dist

        out_rows.append({
            'route': str(row.get('route', ''))[:255],
            'cargo': str(row.get('cargo', '-'))[:255],
            'dist': dist,
            'weight': weight,
            'indK': ind_k,
            'isHighway': is_hwy,
            'row_sys_k': sys_k,
            'row_k': row_k,
            'q': round(q, 6),
        })

    return {
        'rows': out_rows,
        'total_q': round(total_q, 6),
        'dist_city': round(dist_city, 3),
        'dist_out': round(dist_out, 3),
        'max_weight': max_weight,
        'oils': {
            'om': round(total_q * _num(vehicle.om) / 100, 6),
            'ot': round(total_q * _num(vehicle.ot) / 100, 6),
            'os': round(total_q * _num(vehicle.os) / 100, 6),
            'op': round(total_q * _num(vehicle.op) / 100, 6),
        },
    }


def run_calculation(user, car_id, rows, trailer_mass):
    """Спільна логіка для calc_api та збереження розрахунку. Повертає (vehicle, result) або (None, None)."""
    try:
        vehicle = Vehicle.objects.filter(id=int(car_id), user=user).first()
    except (TypeError, ValueError):
        vehicle = None
    if vehicle is None or not isinstance(rows, list):
        return None, None
    base_k, k4, k5, active = get_user_coeff_summary(user)
    result = calculate_fuel(vehicle, rows, base_k, k4, k5, trailer_mass)
    result.update({'sys_k': base_k, 'k4': k4, 'k5': k5, 'active_coeffs': active})
    return vehicle, result


@login_required
@require_POST
def calc_api(request):
    """POST /api/calc/  {car_id, trailer, rows:[{route,dist,cargo,weight,indK,isHighway}]}
    CSRF-токен обов'язковий (заголовок X-CSRFToken)."""
    try:
        data = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'success': False, 'message': 'Невалідний JSON'}, status=400)

    vehicle, result = run_calculation(request.user, data.get('car_id'), data.get('rows'), data.get('trailer', 0))
    if vehicle is None:
        return JsonResponse({'success': False, 'message': 'Автомобіль не знайдено. Оберіть ТЗ зі свого автопарку.'}, status=400)

    result['k_on_work'] = K_APPLIES_TO_TRANSPORT_WORK
    result['car'] = {
        'id': vehicle.id, 'name': vehicle.name, 'plate': vehicle.plate,
        'hs': vehicle.hs, 'hw': vehicle.hw,
        'om': vehicle.om, 'ot': vehicle.ot, 'os': vehicle.os, 'op': vehicle.op,
    }
    result['success'] = True
    return JsonResponse(result)


# --- API ДЛЯ БАЗИ МІСТ (cities.html) ---
@csrf_exempt
@login_required
def cities_api(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'fetch_cities':
            cities = list(City.objects.all().values('id', 'name', 'percent'))
            formatted = [{'id': c['id'], 'name': c['name'], 'percent': str(c['percent'])} for c in cities]
            return JsonResponse({'success': True, 'data': formatted})

        elif action == 'add_city':
            name = request.POST.get('name', '').strip()
            percent = float(request.POST.get('percent', 0) or 0)
            if name:
                city, created = City.objects.get_or_create(
                    name=name,
                    defaults={'percent': percent, 'user': request.user}
                )
                if not created:
                    city.percent = percent
                    city.save()
                return JsonResponse({'success': True})
            return JsonResponse({'success': False, 'message': 'Заповніть назву міста'})

        elif action == 'delete_city':
            city_id = request.POST.get('city_id')
            City.objects.filter(id=city_id).delete()
            return JsonResponse({'success': True})

    cities = list(City.objects.all().values('id', 'name', 'percent'))
    formatted = [{'id': c['id'], 'name': c['name'], 'percent': str(c['percent'])} for c in cities]
    return JsonResponse({'success': True, 'data': formatted})


# --- API ДЛЯ ПЕРСОНАЛЬНИХ КОЕФІЦІЄНТІВ (coeffs.html) ---
@csrf_exempt
@login_required
def coeffs_api(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'fetch_user_coeffs':
            coeffs = list(UserCoeff.objects.filter(user=request.user).values('id', 'name', 'value', 'type', 'description'))
            formatted_coeffs = []
            for c in coeffs:
                formatted_coeffs.append({
                    'id': str(c['id']),
                    'title': c['name'],
                    'desc': c['description'],
                    'val': abs(float(c['value'])),
                    'type': c['type']
                })
            return JsonResponse({'success': True, 'data': formatted_coeffs})

        elif action == 'save_user_coeffs':
            try:
                coeffs_data = json.loads(request.POST.get('coeffs_data', '[]'))
                UserCoeff.objects.filter(user=request.user).delete()

                for item in coeffs_data:
                    title = item.get('title', '').strip()
                    val = float(item.get('val', 0))
                    coeff_type = item.get('type', 'plus')
                    desc = item.get('desc', '')

                    if title:
                        UserCoeff.objects.create(
                            user=request.user,
                            name=title,
                            value=val,
                            type=coeff_type,
                            description=desc
                        )
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Невалідний запит'})


# --- API ДЛЯ КЕРУВАННЯ АВТОПАРКОМ (cars.html) ---
@csrf_exempt
@login_required
def cars_api(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'fetch_cars':
            cars = list(Vehicle.objects.filter(user=request.user).values())
            return JsonResponse({'success': True, 'data': cars})

        elif action == 'add_car':
            try:
                name_val = request.POST.get('name', '').strip()
                if not name_val:
                    return JsonResponse({'success': False, 'message': 'Назва ТЗ обов\'язкова!'})

                car = Vehicle.objects.create(
                    user=request.user,
                    name=name_val,
                    plate=request.POST.get('plate', 'Б/Н').strip() or 'Б/Н',
                    category=request.POST.get('category', 'Вантажні'),
                    hs=float(request.POST.get('hs', 0) or 0),
                    hw=float(request.POST.get('hw', 0) or 0),
                    has_cargo=str(request.POST.get('has_cargo')) == '1',
                    max_payload=float(request.POST.get('max_payload', 0) or 0),
                    om=float(request.POST.get('om', 2.7) or 0),
                    ot=float(request.POST.get('ot', 0.3) or 0),
                    os=float(request.POST.get('os', 0.1) or 0),
                    op=float(request.POST.get('op', 0.2) or 0),
                    has_adblue=str(request.POST.get('has_adblue')) == '1',
                    adblue=float(request.POST.get('adblue', 0) or 0)
                )
                return JsonResponse({'success': True, 'db_id': car.id})
            except Exception as e:
                return JsonResponse({'success': False, 'message': f'Помилка створення ТЗ: {str(e)}'})

        elif action == 'delete_car':
            car_id = request.POST.get('id')
            Vehicle.objects.filter(id=car_id, user=request.user).delete()
            return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'message': 'Невалідний запит'})


# --- API ДЛЯ МАРШРУТІВ З КАРТИ ТА ЗБЕРЕЖЕННЯ РОЗРАХУНКІВ (map.html) ---
@csrf_exempt
@login_required
def map_api(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'fetch_routes':
            routes = list(Calculation.objects.filter(user=request.user).order_by('-id').values())
            return JsonResponse({'success': True, 'data': routes})

        elif action == 'save_route':
            details = request.POST.get('cities_json', '{}')
            car, fuel, max_weight = None, 0.0, 0.0
            try:
                rows = json.loads(details)
            except ValueError:
                rows = None
            # витрату пального рахує сервер, а не береться з браузера
            if request.POST.get('car_id') and isinstance(rows, list):
                car, result = run_calculation(request.user, request.POST.get('car_id'), rows, request.POST.get('trailer', 0))
                if result:
                    fuel, max_weight = result['total_q'], result['max_weight']
            route = Calculation.objects.create(
                user=request.user,
                car=car,
                route=request.POST.get('name', 'Новий маршрут'),
                distance=_num(str(request.POST.get('total_dist', '0')).replace(' км', '').strip()),
                cargo=max_weight,
                fuel_consumed=round(fuel, 2),
                details=details
            )
            return JsonResponse({'success': True, 'id': route.id})

        elif action == 'delete_route':
            route_id = request.POST.get('route_id')
            Calculation.objects.filter(id=route_id, user=request.user).delete()
            return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'message': 'Помилка запиту'})


# --- API ДЛЯ КНИГИ ОБЛІКУ (book.html) ---
@csrf_exempt
@login_required
def book_api(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'fetch_books':
            books = list(UserBook.objects.filter(user=request.user).order_by('-id').values(
                'id', 'title', 'car_title', 'car_plate', 'fuel_type', 'oil_type', 'entries_data', 'created_at'
            ))
            return JsonResponse({'success': True, 'data': books})

        elif action == 'save_book':
            try:
                book = UserBook.objects.create(
                    user=request.user,
                    title=request.POST.get('title', 'Без назви').strip(),
                    car_title=request.POST.get('car_title', '').strip(),
                    car_plate=request.POST.get('car_plate', '').strip(),
                    fuel_type=request.POST.get('fuel_type', '').strip(),
                    oil_type=request.POST.get('oil_type', '').strip(),
                    entries_data=request.POST.get('entries_data', '[]')
                )
                return JsonResponse({'success': True, 'id': book.id})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)})

        elif action == 'delete_book':
            book_id = request.POST.get('book_id')
            UserBook.objects.filter(id=book_id, user=request.user).delete()
            return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'message': 'Невалідний запит'})


# --- API ДЛЯ БІБЛІОТЕКИ ТА НОТАТОК (library.html) ---
@csrf_exempt
@login_required
def library_api(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'fetch_notes':
            note, created = UserNote.objects.get_or_create(user=request.user)
            return JsonResponse({'success': True, 'notes': note.note_text})

        elif action == 'save_notes':
            note, created = UserNote.objects.get_or_create(user=request.user)
            note.note_text = request.POST.get('note_text', '')
            note.save()
            return JsonResponse({'success': True})

        elif action == 'fetch_docs':
            docs = list(UserLibrary.objects.filter(user=request.user).order_by('-id').values('id', 'file_name', 'file_data'))
            return JsonResponse({'success': True, 'data': docs})

        elif action == 'upload_doc':
            file_name = request.POST.get('file_name', 'Документ.pdf').strip()
            file_data = request.POST.get('file_data', '')
            if file_data:
                doc = UserLibrary.objects.create(
                    user=request.user,
                    file_name=file_name,
                    file_data=file_data
                )
                return JsonResponse({'success': True, 'id': doc.id})
            return JsonResponse({'success': False, 'message': 'Файл порожній'})

        elif action == 'delete_doc':
            doc_id = request.POST.get('doc_id')
            UserLibrary.objects.filter(id=doc_id, user=request.user).delete()
            return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'message': 'Невалідний запит'})