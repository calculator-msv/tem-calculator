import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
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
            route = Calculation.objects.create(
                user=request.user,
                route=request.POST.get('name', 'Новий маршрут'),
                distance=float(str(request.POST.get('total_dist', '0')).replace(' км', '').strip() or 0),
                details=request.POST.get('cities_json', '{}')
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