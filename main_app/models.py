from django.db import models
from django.contrib.auth.models import User

# 1. База автомобілів (автопарк)
class Vehicle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Користувач")
    name = models.CharField(max_length=100, verbose_name="Марка та модель")
    plate = models.CharField(max_length=20, default="Б/Н", verbose_name="Номерний знак")
    category = models.CharField(max_length=50, default="Вантажні", verbose_name="Категорія")
    hs = models.FloatField(default=0.0, verbose_name="Hs (базова норма)")
    hw = models.FloatField(default=1.3, verbose_name="Hw (норма на вантаж)")
    has_cargo = models.BooleanField(default=False, verbose_name="Вантажний ТЗ")
    max_payload = models.FloatField(default=0.0, verbose_name="Макс. вантажопідйомність (т)")
    om = models.FloatField(default=2.7, verbose_name="Моторна олива (М)")
    ot = models.FloatField(default=0.3, verbose_name="Трансмісійна олива (Т)")
    os = models.FloatField(default=0.1, verbose_name="Спеціальна олива (S)")
    op = models.FloatField(default=0.2, verbose_name="Пластичне мастило (P)")
    has_adblue = models.BooleanField(default=False, verbose_name="AdBlue")
    adblue = models.FloatField(default=0.0, verbose_name="AdBlue норма %")

    class Meta:
        verbose_name = "Автомобіль"
        verbose_name_plural = "Автопарк"

    def __str__(self):
        return f"{self.name} ({self.plate})"

    @property
    def hsm(self):
        return self.hs

    @property
    def hsz(self):
        return self.hw


# 2. База міст з відсотками надбавок
class City(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Користувач")
    name = models.CharField(max_length=100, verbose_name="Населений пункт")
    percent = models.FloatField(default=0.0, verbose_name="Надбавка %")

    class Meta:
        verbose_name = "Місто"
        verbose_name_plural = "База міст"

    def __str__(self):
        return f"{self.name} (+{self.percent}%)"

    @property
    def coeff(self):
        return self.percent

    @coeff.setter
    def coeff(self, val):
        self.percent = val


# 3. Персональні коефіцієнти користувача
class UserCoeff(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Користувач")
    name = models.CharField(max_length=255, default="Коефіцієнт", verbose_name="Назва коефіцієнта")
    value = models.FloatField(default=0.0, verbose_name="Значення (%)")
    type = models.CharField(max_length=10, default="plus", choices=[('plus', 'Підвищення'), ('minus', 'Зменшення')], verbose_name="Тип")
    description = models.TextField(blank=True, default="", verbose_name="Опис / примітка")
    coeffs_data = models.TextField(default="[]", verbose_name="Коефіцієнти JSON")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Оновлено")

    class Meta:
        verbose_name = "Персональний коефіцієнт"
        verbose_name_plural = "Персональні коефіцієнти"

    def __str__(self):
        return f"{self.name} ({self.value}%) - {self.user.username}"


# 4. Збережені розрахунки калькулятора
class Calculation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Користувач")
    car = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Автомобіль")
    route = models.CharField(max_length=255, verbose_name="Маршрут / Назва")
    distance = models.FloatField(default=0.0, verbose_name="Відстань (км)")
    cargo = models.FloatField(default=0.0, verbose_name="Вага вантажу (т)")
    fuel_consumed = models.FloatField(default=0.0, verbose_name="Витрата пального (л)")
    details = models.TextField(default="{}", verbose_name="Деталі маршруту JSON")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Створено")

    class Meta:
        verbose_name = "Розрахунок"
        verbose_name_plural = "Збережені розрахунки"

    def __str__(self):
        return f"{self.route} - {self.distance} км ({self.user.username})"


# 5. Книга обліку роботи машини
class UserBook(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Користувач")
    title = models.CharField(max_length=255, default="Без назви", verbose_name="Заголовок")
    car_title = models.CharField(max_length=100, blank=True, verbose_name="Автомобіль")
    car_plate = models.CharField(max_length=50, blank=True, verbose_name="Номерний знак")
    fuel_type = models.CharField(max_length=100, blank=True, verbose_name="Вид пального")
    oil_type = models.CharField(max_length=100, blank=True, verbose_name="Вид оливи")
    entries_data = models.TextField(default="[]", verbose_name="Записи JSON")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Створено")

    class Meta:
        verbose_name = "Книга обліку"
        verbose_name_plural = "Книги обліку"

    def __str__(self):
        return f"{self.title} ({self.car_title})"


# 6. Нотатки та Електронна бібліотека (PDF)
class UserNote(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Користувач")
    note_text = models.TextField(default="", blank=True, verbose_name="Текст нотатки")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Оновлено")

    class Meta:
        verbose_name = "Нотатка"
        verbose_name_plural = "Нотатки"


class UserLibrary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Користувач")
    file_name = models.CharField(max_length=255, verbose_name="Назва файла")
    file_data = models.TextField(verbose_name="Base64 вміст")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Завантажено")

    class Meta:
        verbose_name = "Документ бібліотеки"
        verbose_name_plural = "Електронна бібліотека"

    def __str__(self):
        return self.file_name