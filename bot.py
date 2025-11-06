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
        self.dp.message.register(self.process_role_selection, RegistrationStates.choosing_role)
        self.dp.message.register(self.process_group_selection, RegistrationStates.choosing_group)
        self.dp.message.register(self.process_full_name, RegistrationStates.entering_full_name)
    
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
            await message.answer(
                "Успішно зареєстровано. Ви будете отримувати сповіщення."
            )
        else:
            await message.answer(
                "Сталася помилка при реєстрації. Спробуйте пізніше."
            )
        
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
