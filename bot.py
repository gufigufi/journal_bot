from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import logging
from database import Database


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RegistrationStates(StatesGroup):
    choosing_role = State()
    choosing_group = State()
    entering_full_name = State()


class WebCredentialsStates(StatesGroup):
    entering_login = State()
    entering_password = State()
    confirming_change = State()


class TelegramBot:
    def __init__(self, token: str, database: Database):
        self.bot = Bot(token=token)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self.db = database
        self._register_handlers()
    
    def _register_handlers(self):
        self.dp.message.register(self.cmd_start, Command("start"))
        self.dp.message.register(self.cmd_change_role, Command("change_role"))
        self.dp.message.register(self.cmd_create_web_login, Command("create_web_login"))
        self.dp.message.register(self.handle_web_access_button, F.text == "🌐 Створити веб-доступ")
        self.dp.message.register(self.handle_change_credentials_button, F.text == "🔑 Змінити дані для входу")
        self.dp.message.register(self.handle_confirm_yes, F.text == "✅ Так")
        self.dp.message.register(self.handle_confirm_no, F.text == "❌ Ні")
        self.dp.message.register(self.process_role_selection, RegistrationStates.choosing_role)
        self.dp.message.register(self.process_group_selection, RegistrationStates.choosing_group)
        self.dp.message.register(self.process_full_name, RegistrationStates.entering_full_name)
        self.dp.message.register(self.process_web_login, WebCredentialsStates.entering_login)
        self.dp.message.register(self.process_web_password, WebCredentialsStates.entering_password)



    
    async def cmd_start(self, message: types.Message, state: FSMContext):
        await self.start_registration(message, state)
    
    async def cmd_change_role(self, message: types.Message, state: FSMContext):
        await self.start_registration(message, state)
    
    async def start_registration(self, message: types.Message, state: FSMContext):
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="студент")],
                [KeyboardButton(text="батько")],
                [KeyboardButton(text="мати")]
            ],
            resize_keyboard=True
        )
        await message.answer(
            "Привіт! Оберіть вашу роль:",
            reply_markup=keyboard
        )
        await state.set_state(RegistrationStates.choosing_role)
    
    async def process_role_selection(self, message: types.Message, state: FSMContext):
        role = message.text.lower().strip()
        
        if role not in ['студент', 'батько', 'мати']:
            await message.answer("Будь ласка, оберіть роль з клавіатури.")
            return
        
        await state.update_data(role=role)
        
        groups = await self.db.get_all_groups()
        
        if not groups:
            await message.answer(
                "На жаль, групи ще не додані до системи. Зверніться до адміністратора.",
                reply_markup=ReplyKeyboardRemove()
            )
            await state.clear()
            return
        
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=group['name'])] for group in groups],
            resize_keyboard=True
        )
        
        await message.answer(
            "Оберіть вашу групу:",
            reply_markup=keyboard
        )
        await state.set_state(RegistrationStates.choosing_group)
    
    async def process_group_selection(self, message: types.Message, state: FSMContext):
        group_name = message.text.strip()
        
        groups = await self.db.get_all_groups()
        selected_group = next((g for g in groups if g['name'] == group_name), None)
        
        if not selected_group:
            await message.answer("Будь ласка, оберіть групу з клавіатури.")
            return
        
        await state.update_data(group_id=selected_group['id'])
        
        await message.answer(
            "Введіть ваше ПІБ рівно як у журналі (строго):",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(RegistrationStates.entering_full_name)
    
    async def process_full_name(self, message: types.Message, state: FSMContext):
        full_name = message.text.strip()
        data = await state.get_data()
        role = data.get('role')
        group_id = data.get('group_id')
        
        student = await self.db.find_student(full_name, group_id)
        
        if not student:
            await message.answer(
                "Студента з таким ПІБ у цій групі не знайдено. "
                "Перевірте написання або зверніться до адміністратора."
            )
            await state.clear()
            return
        
        field_map = {
            'студент': 'student_chat_id',
            'батько': 'father_chat_id',
            'мати': 'mother_chat_id'
        }
        
        chat_id_field = field_map[role]
        existing_chat_id = student.get(chat_id_field)
        
        if existing_chat_id:
            await message.answer(
                "Вже зареєстровано. Якщо це ваш інший акаунт, зв'яжіться з адміністратором."
            )
            await state.clear()
            return
        
        success = await self.db.update_student_chat_id(
            student['id'], 
            role, 
            str(message.from_user.id)
        )
        
        if success:
            if role == 'студент':
                student_data = await self.db.get_student_by_id(student['id'])
                
                if student_data and student_data.get('web_login'):
                    keyboard = ReplyKeyboardMarkup(
                        keyboard=[
                            [KeyboardButton(text="🔑 Змінити дані для входу")]
                        ],
                        resize_keyboard=True
                    )
                    await message.answer(
                        f"Успішно зареєстровано. Ви будете отримувати сповіщення.\n\n"
                        f"Ваш веб-логін: {student_data['web_login']}",
                        reply_markup=keyboard
                    )
                else:
                    keyboard = ReplyKeyboardMarkup(
                        keyboard=[
                            [KeyboardButton(text="🌐 Створити веб-доступ")]
                        ],
                        resize_keyboard=True
                    )
                    await message.answer(
                        "Успішно зареєстровано. Ви будете отримувати сповіщення.\n\n"
                        "Ви можете створити логін та пароль для веб-версії перегляду оцінок.",
                        reply_markup=keyboard
                    )
            else:
                await message.answer(
                    "Успішно зареєстровано. Ви будете отримувати сповіщення."
                )

        else:
            await message.answer(
                "Сталася помилка при реєстрації. Спробуйте пізніше."
            )

    
    async def handle_web_access_button(self, message: types.Message, state: FSMContext):
        await self.cmd_create_web_login(message, state)
    
    async def cmd_create_web_login(self, message: types.Message, state: FSMContext):

        chat_id = str(message.from_user.id)
        student = await self.db.get_student_by_chat_id(chat_id)
        
        if not student:
            await message.answer(
                "Ви не зареєстровані в системі. Спочатку пройдіть реєстрацію командою /start"
            )
            return
        
        if student.get('student_chat_id') != chat_id:
            await message.answer(
                "Створення веб-доступу доступне тільки для студентів. "
                "Батьки та матері не можуть створювати веб-логін."
            )
            return
        
        if student.get('web_login'):
            await message.answer(
                f"У вас вже є веб-логін: {student['web_login']}\n"
                "Якщо ви забули пароль, зверніться до адміністратора."
            )
            return
        
        await message.answer(
            "Створення веб-доступу для перегляду оцінок.\n\n"
            "Введіть логін (мінімум 4 символи, тільки латинські літери та цифри):",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(WebCredentialsStates.entering_login)
    
    async def handle_change_credentials_button(self, message: types.Message, state: FSMContext):
        chat_id = str(message.from_user.id)
        student = await self.db.get_student_by_chat_id(chat_id)
        
        if not student:
            await message.answer(
                "Ви не зареєстровані в системі. Спочатку пройдіть реєстрацію командою /start"
            )
            return
        
        if student.get('student_chat_id') != chat_id:
            await message.answer(
                "Зміна даних доступна тільки для студентів."
            )
            return
        
        if not student.get('web_login'):
            await message.answer(
                "У вас ще немає веб-доступу. Спочатку створіть його."
            )
            return
        
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✅ Так"), KeyboardButton(text="❌ Ні")]
            ],
            resize_keyboard=True
        )
        
        await message.answer(
            f"Ваш поточний логін: {student['web_login']}\n\n"
            "Ви дійсно хочете змінити дані для входу?\n"
            "Старі дані будуть видалені.",
            reply_markup=keyboard
        )
        await state.set_state(WebCredentialsStates.confirming_change)
    
    async def handle_confirm_yes(self, message: types.Message, state: FSMContext):
        current_state = await state.get_state()
        
        if current_state != WebCredentialsStates.confirming_change:
            return
        
        chat_id = str(message.from_user.id)
        student = await self.db.get_student_by_chat_id(chat_id)
        
        if not student:
            await message.answer("Помилка: студента не знайдено.")
            await state.clear()
            return
        
        await self.db.set_web_credentials(student['id'], None, None)
        
        await message.answer(
            "Старі дані видалено.\n\n"
            "Введіть новий логін (мінімум 4 символи, тільки латинські літери та цифри):",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(WebCredentialsStates.entering_login)
    
    async def handle_confirm_no(self, message: types.Message, state: FSMContext):
        current_state = await state.get_state()
        
        if current_state != WebCredentialsStates.confirming_change:
            return
        
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🔑 Змінити дані для входу")]
            ],
            resize_keyboard=True
        )
        
        await message.answer(
            "Зміну даних скасовано.",
            reply_markup=keyboard
        )
        await state.clear()

    async def process_web_login(self, message: types.Message, state: FSMContext):
        login = message.text.strip()
        
        if len(login) < 4:
            await message.answer("Логін повинен містити мінімум 4 символи. Спробуйте ще раз:")
            return
        
        if not login.isalnum():
            await message.answer(
                "Логін може містити тільки латинські літери та цифри. Спробуйте ще раз:"
            )
            return
        
        login_exists = await self.db.check_login_exists(login)
        if login_exists:
            await message.answer("Цей логін вже зайнятий. Оберіть інший:")
            return
        
        await state.update_data(web_login=login)
        await message.answer(
            "Логін прийнято!\n\n"
            "Тепер введіть пароль (мінімум 6 символів):"
        )
        await state.set_state(WebCredentialsStates.entering_password)
    
    async def process_web_password(self, message: types.Message, state: FSMContext):
        import hashlib
        
        password = message.text.strip()
        
        if len(password) < 6:
            await message.answer("Пароль повинен містити мінімум 6 символів. Спробуйте ще раз:")
            return
        
        data = await state.get_data()
        login = data.get('web_login')
        
        chat_id = str(message.from_user.id)
        student = await self.db.get_student_by_chat_id(chat_id)
        
        if not student:
            await message.answer("Помилка: студента не знайдено.")
            await state.clear()
            return
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        success = await self.db.set_web_credentials(
            student['id'],
            login,
            password_hash
        )
        
        if success:
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="🔑 Змінити дані для входу")]
                ],
                resize_keyboard=True
            )
            await message.answer(
                f"✅ Веб-доступ успішно створено!\n\n"
                f"Логін: {login}\n"
                f"Пароль: {password}\n\n"
                f"Збережіть ці дані в безпечному місці!",
                reply_markup=keyboard
            )
        else:
            await message.answer("Сталася помилка при створенні веб-доступу. Спробуйте пізніше.")
        
        await state.clear()



    
    async def send_notification(self, chat_id: str, text: str):
        try:
            await self.bot.send_message(chat_id=int(chat_id), text=text)
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
            return False
    
    async def start(self):
        await self.dp.start_polling(self.bot)
    
    async def stop(self):
        await self.bot.session.close()
