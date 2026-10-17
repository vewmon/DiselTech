import json
import hashlib
from pathlib import Path
from datetime import datetime
from time import time

from kivy.config import Config
Config.set("graphics", "multisamples", "0")
Config.set("input", "mouse", "mouse,disable_multitouch")
from kivy.app import App
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.clock import Clock


BG_COLOR = (0.055, 0.067, 0.09, 1)
CARD_COLOR = (0.10, 0.12, 0.16, 1)
BUTTON_COLOR = (0.14, 0.18, 0.24, 1)

TEXT_COLOR = (0.93, 0.95, 0.98, 1)
MUTED_COLOR = (0.62, 0.67, 0.74, 1)

CYAN = (0.10, 0.83, 0.96, 1)
GREEN = (0.20, 0.88, 0.48, 1)
YELLOW = (1.00, 0.72, 0.18, 1)
RED = (1.00, 0.28, 0.34, 1)

BODIES = ["Корпус 1", "Корпус 2", "Корпус 3"]
ELECTROLYSERS = [f"ЭЛ-{i:02d}" for i in range(1, 13)]
WORK_TYPES = [
    "Распределение глинозёма",
    "Пробивка корки",
    "Другая задача",
]
MACHINES = ["МРГ", "МПК"]
DRIVERS = [f"Водитель {i}" for i in range(1, 5)]
ISSUES = [
    "Техника неисправна",
    "Препятствие на пути",
    "Опасная зона",
    "Нет доступа к месту",
    "Нужна помощь",
    "Другая проблема",
]


def password_hash(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


DEFAULT_USERS = {
    "dispatcher": {
        "password_hash": password_hash("1234"),
        "role": "dispatcher",
        "driver_name": "",
    },
    "driver1": {
        "password_hash": password_hash("1234"),
        "role": "driver",
        "driver_name": "Водитель 1",
    },
    "driver2": {
        "password_hash": password_hash("1234"),
        "role": "driver",
        "driver_name": "Водитель 2",
    },
    "driver3": {
        "password_hash": password_hash("1234"),
        "role": "driver",
        "driver_name": "Водитель 3",
    },
    "driver4": {
        "password_hash": password_hash("1234"),
        "role": "driver",
        "driver_name": "Водитель 4",
    },
}


def current_time():
    return datetime.now().strftime("%d.%m.%Y %H:%M")


def make_label(text, height=dp(40), font_size=dp(16)):
    label = Label(
        text=text,
        size_hint_y=None,
        height=height,
        font_size=font_size,
        color=TEXT_COLOR,
        halign="left",
        valign="middle",
    )
    label.bind(
        size=lambda instance, value:
        setattr(instance, "text_size", value)
    )
    return label


def make_button(text, callback, height=dp(46), color=BUTTON_COLOR):
    button = Button(
        text=text,
        size_hint_y=None,
        height=height,
        font_size=dp(16),
        bold=True,
        color=TEXT_COLOR,
        background_normal="",
        background_down="",
        background_color=color,
    )
    button.bind(on_release=callback)
    return button


class RequestsApp(App):

    def build(self):
        Window.clearcolor = BG_COLOR
        self.title = "ДизельТех"
        self.data_file = (
            Path(self.user_data_dir) / "requests_data.json"
        )
        self.data_file.parent.mkdir(parents=True, exist_ok=True)

        self.data= self.load_data()

        self.users_file = (
            Path(self.user_data_dir) / "users.json"
        )
        self.users_file.parent.mkdir(
            parents=True, exist_ok=True
        )

        self.users = self.load_users()
        self.current_user = None

        self.main_root = BoxLayout(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(12),
        )

        self.last_tick = time()
        Clock.schedule_interval(self.update_equipment_hours, 1)
        Clock.schedule_interval(self.refresh_requests, 10)
        self.show_login()
        return self.main_root

    def update_equipment_hours(self, dt):
        now = time()
        elapsed = max(0, now - self.last_tick)
        self.last_tick = now

        for item in self.data.get("equipment", []):
            if item.get("status") == "В работе":
                item["hours"] = (
                        float(item.get("hours", 0.0))
                        + elapsed / 3600
                )

        self.save_timer_elapsed = getattr(
            self, "save_timer_elapsed", 0
        ) + elapsed

        if self.save_timer_elapsed >= 5:
            self.save_data()
            self.save_timer_elapsed = 0

        if hasattr(self, "equipment_list"):
            self.refresh_equipment()

    def load_data(self):
        if self.data_file.exists():
            try:
                with open(
                        self.data_file, "r", encoding="utf-8"
                ) as file:
                    data = json.load(file)

                if isinstance(data, dict):
                    data.setdefault("requests", [])
                    data.setdefault("next_id", 1)
                    data.setdefault("equipment", [])
                    if not data["equipment"]:
                        data["equipment"] = [
                            {
                                "id": f"ЭЛ-{i:02d}",
                                "name": f"Электролизёр ЭЛ-{i:02d}",
                                "hours": 0.0,
                                "status": "В работе",
                            }
                            for i in range(1, 11)
                        ]
                    return data

            except (json.JSONDecodeError, OSError):
                pass

        return {
            "requests": [],
            "next_id": 1,
            "equipment": [
                {
                    "id": f"ЭЛ-{i:02d}",
                    "name": f"Электролизёр ЭЛ-{i:02d}",
                    "hours": 0.0,
                    "status": "В работе",
                }
                for i in range(1, 11)
            ],
        }

    def save_data(self):
        with open(
                self.data_file, "w", encoding="utf-8"
        ) as file:
            json.dump(
                self.data
                ,
                file,
                ensure_ascii=False,
                indent=4,
            )


    def show_driver(self, *_):
        self.main_root.clear_widgets()

        driver_name = self.current_user["driver_name"]

        self.main_root.add_widget(make_label(
            f"ПАНЕЛЬ ВОДИТЕЛЯ\n{driver_name}",
            dp(65),
            dp(21),
        ))

        self.driver_request_list = GridLayout(
            cols=1,
            spacing=dp(10),
            padding=dp(4),
            size_hint_y=None,
        )

        self.driver_request_list.bind(
            minimum_height=self.driver_request_list.setter("height")
        )

        scroll = ScrollView()
        scroll.add_widget(self.driver_request_list)
        self.main_root.add_widget(scroll)

        self.main_root.add_widget(make_button(
            "Обновить заявки",
            self.refresh_driver_requests,
        ))

        self.main_root.add_widget(make_button(
            "Выйти из аккаунта",
            self.logout,
            dp(44),
            RED,
        ))

        self.refresh_driver_requests()

    def show_login(self, *_):
        self.current_user = None
        self.main_root.clear_widgets()

        self.main_root.add_widget(make_label(
            "[b]ДИЗЕЛЬТЕХ[/b]\nВход в систему",
            dp(100),
            dp(24),
        ))

        self.main_root.add_widget(make_label("Логин"))
        self.login_input = TextInput(
            multiline=False,
            size_hint_y=None,
            height=dp(48),
            hint_text="Введите логин",
            padding=dp(12),
        )
        self.main_root.add_widget(self.login_input)

        self.main_root.add_widget(make_label("Пароль"))
        self.password_input = TextInput(
            multiline=False,
            password=True,
            size_hint_y=None,
            height=dp(48),
            hint_text="Введите пароль",
            padding=dp(12),
        )
        self.main_root.add_widget(self.password_input)

        self.login_message = make_label("", dp(48), dp(14))
        self.login_message.color = RED
        self.main_root.add_widget(self.login_message)

        self.main_root.add_widget(make_button(
            "ВОЙТИ",
            self.login,
            dp(56),
            CYAN,
        ))
        self.main_root.add_widget(make_button(
            "ЗАРЕГИСТРИРОВАТЬСЯ",
            self.show_registration,
            dp(50),
        ))
        self.main_root.add_widget(make_label(
            "Демонстрационные аккаунты:\n"
            "dispatcher / 1234 — диспетчер\n"
            "driver1 / 1234 — водитель 1",
            dp(85),
            dp(13),
        ))

        self.password_input.bind(
            on_text_validate=self.login
        )

    def login(self, *_):
        username = self.login_input.text.strip().lower()
        password = self.password_input.text

        user = self.users.get(username)

        if (
            user is None
            or user["password_hash"] != password_hash(password)
        ):
            self.login_message.text = "Неверный логин или пароль."
            self.password_input.text = ""
            return

        self.current_user = {
            "username": username,
            "role": user["role"],
            "driver_name": user["driver_name"],
        }

        if user["role"] == "dispatcher":
            self.show_dispatcher()
        else:
            self.show_driver()

    def show_registration(self, *_):
        self.main_root.clear_widgets()

        self.main_root.add_widget(make_label(
            "РЕГИСТРАЦИЯ СОТРУДНИКА",
            dp(65),
            dp(21),
        ))

        self.main_root.add_widget(make_label("Логин"))
        self.reg_login = TextInput(
            multiline=False,
            hint_text="Придумайте логин",
            size_hint_y=None,
            height=dp(48),
        )
        self.main_root.add_widget(self.reg_login)

        self.main_root.add_widget(make_label("Пароль"))
        self.reg_password = TextInput(
            multiline=False,
            password=True,
            hint_text="Придумайте пароль",
            size_hint_y=None,
            height=dp(48),
        )
        self.main_root.add_widget(self.reg_password)

        self.main_root.add_widget(make_label(
            "Повторите пароль"
        ))
        self.reg_confirm = TextInput(
            multiline=False,
            password=True,
            hint_text="Повторите пароль",
            size_hint_y=None,
            height=dp(48),
        )
        self.main_root.add_widget(self.reg_confirm)

        self.main_root.add_widget(make_label("Ваша роль"))

        self.reg_role = Spinner(
            text="Водитель",
            values=("Водитель", "Диспетчер"),
            size_hint_y=None,
            height=dp(48),
        )
        self.main_root.add_widget(self.reg_role)

        self.reg_message = make_label("", dp(55), dp(14))
        self.reg_message.color = RED
        self.main_root.add_widget(self.reg_message)

        self.main_root.add_widget(make_button(
            "СОЗДАТЬ АККАУНТ",
            self.register_user,
            dp(54),
            GREEN,
        ))

        self.main_root.add_widget(make_button(
            "← Назад ко входу",
            self.show_login,
        ))

    def register_user(self, *_):
        username = self.reg_login.text.strip().lower()
        password = self.reg_password.text
        confirm = self.reg_confirm.text

        if len(username) < 3:
            self.reg_message.text = (
                "Логин должен содержать минимум 3 символа."
            )
            return

        if not username.replace("_", "").isalnum():
            self.reg_message.text = (
                "Используйте только буквы, цифры и _."
            )
            return

        if len(password) < 6:
            self.reg_message.text = (
                "Пароль должен содержать минимум 6 символов."
            )
            return

        if password != confirm:
            self.reg_message.text = (
                "Пароли не совпадают."
            )
            return

        if username in self.users:
            self.reg_message.text = (
                "Такой логин уже зарегистрирован."
            )
            return

        role = (
            "driver"
            if self.reg_role.text == "Водитель"
            else "dispatcher"
        )

        self.users[username] = {
            "password_hash": password_hash(password),
            "role": role,
            "driver_name": (
                username if role == "driver" else ""
            ),
        }

        try:
            self.save_users()
        except OSError:
            del self.users[username]
            self.reg_message.text = (
                "Не удалось сохранить аккаунт. "
                "Проверь доступ к файлам."
            )
            return

        self.show_login()
        self.login_input.text = username
        self.login_message.color = GREEN
        self.login_message.text = (
            "Аккаунт создан! Теперь войдите."
        )

    def load_users(self):
        if self.users_file.exists():
            try:
                with open(
                    self.users_file, "r", encoding="utf-8"
                ) as file:
                    users = json.load(file)

                if isinstance(users, dict):
                    return users

            except (json.JSONDecodeError, OSError):
                pass

        users = {
            username: user.copy()
            for username, user in DEFAULT_USERS.items()
        }

        self.users = users
        self.save_users()
        return users

    def save_users(self):
        with open(
            self.users_file, "w", encoding="utf-8"
        ) as file:
            json.dump(
                self.users,
                file,
                ensure_ascii=False,
                indent=4,
            )

    def logout(self, *_):
        self.show_login()


    def add_logout_button(self):
        self.main_root.add_widget(make_button(
            "Выйти из аккаунта",
            self.logout,
            dp(44),
            RED,
        ))


    def show_dispatcher(self, *_):
        self.main_root.clear_widgets()

        self.main_root.add_widget(make_label(
            "ПАНЕЛЬ ДИСПЕТЧЕРА",
            dp(55),
            dp(21),
        ))

        self.main_root.add_widget(make_button(
            "＋ Создать заявку",
            self.show_new_request,
            dp(56),
            CYAN,
        ))

        self.main_root.add_widget(make_button(
            "Обновить список",
            self.refresh_requests,
            dp(46),
        ))

        self.main_root.add_widget(make_label(
            "НАРАБОТКА ОБОРУДОВАНИЯ",
            dp(42),
            dp(18),
        ))

        self.equipment_list = GridLayout(
            cols=1,
            spacing=dp(8),
            padding=dp(4),
            size_hint_y=None,
        )
        self.equipment_list.bind(
            minimum_height=self.equipment_list.setter("height")
        )

        equipment_scroll = ScrollView(
            size_hint_y=None,
            height=dp(220),
        )
        equipment_scroll.add_widget(self.equipment_list)
        self.main_root.add_widget(equipment_scroll)

        self.refresh_equipment()

        self.request_list = GridLayout(
            cols=1,
            spacing=dp(10),
            padding=dp(4),
            size_hint_y=None,
        )
        self.request_list.bind(
            minimum_height=self.request_list.setter("height")
        )

        scroll = ScrollView()
        scroll.add_widget(self.request_list)
        self.main_root.add_widget(scroll)

        self.add_logout_button()
        self.refresh_requests()

    def refresh_requests(self, *_):
        if not hasattr(self, "request_list"):
            return

        self.request_list.clear_widgets()
        requests = self.data["requests"]

        if not requests:
            self.request_list.add_widget(make_label(
                "Заявок пока нет.",
                dp(60),
            ))
            return

        for request in reversed(requests):
            self.add_request_card(request)

    def refresh_equipment(self, *_):
        if not hasattr(self, "equipment_list"):
            return

        self.equipment_list.clear_widgets()

        equipment = self.data.setdefault("equipment", [])

        if not equipment:
            self.equipment_list.add_widget(make_label(
                "Оборудование не найдено.",
                dp(50),
            ))
            return

        for item in equipment:
            row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(65),
                spacing=dp(8),
            )

            info = make_label(
                f'{item["name"]}\n'
                f'Наработка: {item.get("hours", 0.0):.3f} ч\n'
                f'Статус: {item.get("status", "Остановлено")}',
                dp(65),
            )
            row.add_widget(info)

            if item.get("status") == "В работе":
                button_text = "Остановить"
                button_color = (0.8, 0.25, 0.25, 1)
            else:
                button_text = "Запустить"
                button_color = CYAN

            button = make_button(
                button_text,
                lambda *_args, equipment=item: self.toggle_equipment(
                    equipment
                ),
                dp(50),
                button_color,
            )
            row.add_widget(button)

            self.equipment_list.add_widget(row)

    def toggle_equipment(self, item):
        if item.get("status") == "В работе":
            item["status"] = "Остановлено"
        else:
            item["status"] = "В работе"

        self.save_data()
        self.refresh_equipment()

    def add_request_card(self, request):
        card = BoxLayout(
            orientation="vertical",
            spacing=dp(5),
            padding=dp(10),
            size_hint_y=None,
        )

        card.add_widget(make_label(
            f"Заявка №{request['id']}",
            dp(35),
            dp(19),
        ))
        accepted_at = request.get("accepted_at")

        if request["status"] == "Новая":
            traffic_text = "ОЖИДАЕТ ПРИНЯТИЯ"
            traffic_color = (0.25, 0.65, 0.35, 1)

        elif request["status"] == "Выполнена":
            traffic_text = "ВЫПОЛНЕНА"
            traffic_color = (0.4, 0.4, 0.4, 1)

        elif accepted_at:
            elapsed = time() - float(accepted_at)

            if elapsed >= 15 * 60:
                traffic_text = "КРАСНЫЙ - КРИТИЧЕСКАЯ ЗАДЕРЖКА"
                traffic_color = (0.9, 0.15, 0.15, 1)

            elif elapsed >= 10 * 60:
                traffic_text = "ЖЕЛТЫЙ - ТРЕБУЕТ ВНИМАНИЯ"
                traffic_color = (0.95, 0.65, 0.1, 1)

            else:
                traffic_text = "ЗЕЛЕНЫЙ - В ПРЕДЕЛАХ ВРЕМЕНИ"
                traffic_color = (0.25, 0.65, 0.35, 1)

        else:
            traffic_text = "ВРЕМЯ ПРИНЯТИЯ НЕ ЗАПИСАНО"
            traffic_color = (0.5, 0.5, 0.5, 1)

        traffic_label = make_label(
            "СВЕТОФОР: " + traffic_text,
            dp(42),
            dp(15),
        )
        traffic_label.color = traffic_color
        card.add_widget(traffic_label)
        details = (
            f"Создана: {request['created']}\n"
            f"Корпус: {request['body']}\n"
            f"Электролизёр: {request['electrolyser']}\n"
            f"Задача: {request['work_type']}\n"
            f"Машина: {request['machine']}\n"
            f"Водитель: {request['driver']}\n"
            f"Статус: {request['status']}"
        )

        card.add_widget(make_label(details, dp(165), dp(15)))

        issues = request.get("issues", [])
        if issues:
            card.add_widget(make_label(
                "Проблемы: " + ", ".join(issues),
                dp(55),
                dp(14),
            ))

        if request.get("finished"):
            card.add_widget(make_label(
                "Завершена: " + request["finished"],
                dp(30),
                dp(14),
            ))

        if request["status"] == "Новая":
            card.add_widget(make_button(
                "Взять в работу",
                lambda _, rid=request["id"]:
                    self.change_status(rid, "В работе"),
            ))
        elif request["status"] == "В работе":
            card.add_widget(make_button(
                "Выполнено",
                lambda _, rid=request["id"]:
                    self.change_status(rid, "Выполнена"),
                color=GREEN,
            ))

        if request["status"] != "Выполнена":
            card.add_widget(make_button(
                "Отметить проблему",
                lambda _, rid=request["id"]:
                    self.show_issue_popup(rid),
            ))

        card.height = (
            sum(child.height for child in card.children)
            + dp(35)
        )
        self.request_list.add_widget(card)


    def show_new_request(self, *_):
        form = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=dp(12),
        )

        scroll = ScrollView()
        fields = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            size_hint_y=None,
        )
        fields.bind(
            minimum_height=fields.setter("height")
        )

        def add_field(caption, options):
            fields.add_widget(make_label(caption, dp(30)))
            spinner = Spinner(
                text=options[0],
                values=options,
                size_hint_y=None,
                height=dp(44),
            )
            fields.add_widget(spinner)
            return spinner

        body = add_field("Корпус:", BODIES)
        electrolyser = add_field("Электролизёр:", ELECTROLYSERS)
        work_type = add_field("Тип задачи:", WORK_TYPES)
        machine = add_field("Машина:", MACHINES)
        driver_options = sorted({
            user["driver_name"]
            for user in self.users.values()
            if user.get("role") == "driver"
               and user.get("driver_name")
        })

        if not driver_options:
            driver_options = DRIVERS

        driver = add_field("Водитель:", driver_options)

        fields.add_widget(make_label(
            "Проверь выбранные данные перед созданием.",
            dp(45),
            dp(13),
        ))

        scroll.add_widget(fields)
        form.add_widget(scroll)

        buttons = BoxLayout(
            size_hint_y=None,
            height=dp(48),
            spacing=dp(8),
        )

        popup = Popup(
            title="Новая заявка",
            content=form,
            size_hint=(0.95, 0.9),
        )

        def create_request(*_):
            request = {
                "id": self.data["next_id"],
                "created": current_time(),
                "body": body.text,
                "electrolyser": electrolyser.text,
                "work_type": work_type.text,
                "machine": machine.text,
                "driver": driver.text,
                "status": "Новая",
                "accepted_at": None,
                "issues": [],
                "finished": "",
            }

            self.data["requests"].append(request)
            self.data["next_id"] += 1

            self.save_data()
            self.refresh_requests()
            popup.dismiss()

        buttons.add_widget(make_button(
            "Создать",
            create_request,
            color=GREEN,
        ))
        buttons.add_widget(make_button(
            "Отмена",
            lambda *_: popup.dismiss(),
        ))

        form.add_widget(buttons)
        popup.open()


    def refresh_driver_requests(self, *_):
        self.driver_request_list.clear_widgets()

        driver_name = self.current_user["driver_name"]
        requests = [r for r in self.data["requests"]
            if r["driver"] == driver_name
        ]

        if not requests:
            self.driver_request_list.add_widget(make_label(
                "Для вас пока нет назначенных заявок.",
                dp(70),
            ))
            return

        for request in reversed(requests):
            card = BoxLayout(
                orientation="vertical",
                spacing=dp(5),
                padding=dp(10),
                size_hint_y=None,
            )

            card.add_widget(make_label(
                f"Заявка №{request['id']}",
                dp(35),
                dp(19),
            ))

            details = (
                f"Корпус: {request['body']}\n"
                f"Электролизёр: {request['electrolyser']}\n"
                f"Задача: {request['work_type']}\n"
                f"Машина: {request['machine']}\n"
                f"Статус: {request['status']}"
            )
            card.add_widget(make_label(details, dp(130), dp(15)))

            if request.get("issues"):
                card.add_widget(make_label(
                    "Проблемы: " + ", ".join(request["issues"]),
                    dp(45),
                    dp(14),
                ))

            if request["status"] == "Новая":
                card.add_widget(make_button(
                    "Принять в работу",
                    lambda _, rid=request["id"]:
                        self.change_driver_status(rid, "В работе"),
                ))
            elif request["status"] == "В работе":
                card.add_widget(make_button(
                    "Завершить заявку",
                    lambda _, rid=request["id"]:
                        self.change_driver_status(rid, "Выполнена"),
                    color=GREEN,
                ))

            if request["status"] != "Выполнена":
                card.add_widget(make_button(
                    "Сообщить о проблеме",
                    lambda _, rid=request["id"]:
                        self.show_issue_popup(rid, driver_mode=True),
                ))

            card.height = (
                sum(child.height for child in card.children)
                + dp(35)
            )
            self.driver_request_list.add_widget(card)

    def change_driver_status(self, request_id, new_status):
        driver_name = self.current_user["driver_name"]

        for request in self.data["requests"]:
            if (
                request["id"] == request_id
                and request["driver"] == driver_name
            ):
                request["status"] = new_status

                if new_status == "Выполнена":
                    request["finished"] = current_time()
                break

        self.save_data()
        self.refresh_driver_requests()

    def change_status(self, request_id, new_status):
        for request in self.data["requests"]:
            if request["id"] == request_id:
                request["status"] = new_status

                if new_status == "В работе":
                    if not request.get("accepted_at"):
                        request["accepted_at"] = time()

                if new_status == "Выполнена":
                    request["finished"] = current_time()
                    request["completed_at"] = time()

                break


            self.save_data()
            self.refresh_requests()

        def show_issue_popup(self, request_id, driver_mode=False):
            content = BoxLayout(
                orientation="vertical",
                spacing=dp(6),
                padding=dp(10),
            )

            popup = Popup(
                title="Выберите проблему",
                content=content,
                size_hint=(0.9, 0.85),
            )

            for issue in ISSUES:
                content.add_widget(
                    make_button(
                        issue,
                        lambda _, value=issue: self.set_issue(
                            request_id, value, popup, driver_mode
                        ),
                    )
                )

            content.add_widget(
                make_button(
                    "Отмена",
                    lambda *_: popup.dismiss(),
                )
            )

            popup.open()


    def set_issue(self, request_id, issue, popup, driver_mode=False):
        for request in self.data["requests"]:
            if request["id"] == request_id:
                if issue not in request["issues"]:
                    request["issues"].append(issue)
            break
            self.save_data()
            popup.dismiss()

        if driver_mode:
            self.refresh_driver_requests()
        else:
            self.refresh_requests()


if __name__ == "__main__":
    RequestsApp().run()