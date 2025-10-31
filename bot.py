import logging
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import datetime
import random
import asyncio

# ============================
# 🎯 НАСТРОЙКА ЛОГИРОВАНИЯ
# ============================

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================
# 📁 ФАЙЛЫ ДАННЫХ
# ============================

ADMINS_FILE = 'admins.json'
DUTY_STATE_FILE = 'duty_state.json'
GROUPS_FILE = 'groups.json'

def load_admins():
    """Загрузка списка администраторов"""
    if os.path.exists(ADMINS_FILE):
        try:
            with open(ADMINS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки admins.json: {e}")
    return {
        'Seivel66': {'role': 'headman', 'display_name': 'Староста 👨‍🎓'},
        'krixxsy': {'role': 'creator', 'display_name': 'Создатель Бота | Зам. Старосты 👑'}
    }

def save_admins(admins):
    """Сохранение списка администраторов"""
    with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
        json.dump(admins, f, ensure_ascii=False, indent=2)

def load_duty_state():
    """Загрузка состояния дежурных"""
    if os.path.exists(DUTY_STATE_FILE):
        try:
            with open(DUTY_STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки duty_state.json: {e}")
    return {
        'current_index': 11,  # 31.10.2025 - Иванов и Мещанинов (индекс 11)
        'last_updated': '2025-10-31'
    }

def save_duty_state(state):
    """Сохранение состояния дежурных"""
    with open(DUTY_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def load_groups():
    """Загрузка списка групп"""
    if os.path.exists(GROUPS_FILE):
        try:
            with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки groups.json: {e}")
    return {}

def save_groups(groups):
    """Сохранение списка групп"""
    with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
        json.dump(groups, f, ensure_ascii=False, indent=2)

# ============================
# 📊 ЗАГРУЗКА ДАННЫХ
# ============================

ADMINS = load_admins()
DUTY_STATE = load_duty_state()
GROUPS = load_groups()

# ============================
# 👥 ДАННЫЕ ДЕЖУРНЫХ
# ============================

PAIRS = [
    ("Куряков Дмитрий", "Яковлев Егор"),           # 0 - 03.11.2025
    ("Власенков Кирилл", "Волосенков Владислав"), # 1
    ("Воронцов Алексей", "Головлев Александр"),   # 2
    ("Воробьева Альбина", "Даниленкова Василиса"), # 3
    ("Кришталев Тимур", "Пономарев Андрей"),      # 4
    ("Курошев Александр", "Мингазетдинов Денис"), # 5
    ("Михалев Тимур", "Райник Матвей"),           # 6
    ("Семернев Дмитрий", "Цэруш Миша"),           # 7
    ("Селезнев Кирилл", "Тагави Такиех Сейед"),   # 8
    ("Федоров Егор", "Михайлов Максим"),          # 9
    ("Панкин Максим", "Козлова Диана"),           # 10
    ("Иванов Дмитрий", "Мещанинов Вячеслав"),     # 11 - 31.10.2025
    ("Солдатова Яна", "Лепешко Полина")           # 12 - 01.11.2025
]

EXCLUDED = ["Иванов Дмитрий", "Мещанинов Вячеслав", "Селезнев Кирилл"]

ROLES = {
    'headman': 'Староста 👨‍🎓',
    'creator': 'Создатель Бота | Зам. Старосты 👑',
    'admin': 'Администратор 🔧',
    'moderator': 'Модератор 👀'
}

ADMIN_USER_IDS = {
    'krixxsy': 1805647541,
    'Seivel66': 1950848528
}

# ============================
# 🔧 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================

def get_current_duty_pair():
    """Получить текущую пару дежурных"""
    current_index = DUTY_STATE['current_index']
    return PAIRS[current_index]

def get_next_duty_pair():
    """Получить следующую пару дежурных"""
    current_index = DUTY_STATE['current_index']
    next_index = (current_index + 1) % len(PAIRS)
    return PAIRS[next_index]

def move_to_next_pair():
    """Перейти к следующей паре дежурных"""
    DUTY_STATE['current_index'] = (DUTY_STATE['current_index'] + 1) % len(PAIRS)
    DUTY_STATE['last_updated'] = datetime.datetime.now().strftime('%Y-%m-%d')
    save_duty_state(DUTY_STATE)

def check_and_update_duty_date():
    """Проверить и обновить дату дежурства"""
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    last_updated = DUTY_STATE['last_updated']
    
    if today != last_updated:
        if datetime.datetime.now().weekday() != 6:  # Не воскресенье
            move_to_next_pair()
            logger.info(f"🔄 Автоматически обновлены дежурные с {last_updated} на {today}")
            return True
    return False

def get_week_type_and_schedule(target_date=None):
    """Получить тип недели и расписание"""
    if target_date is None:
        target_date = datetime.datetime.now()
    
    start_date = datetime.datetime(2025, 10, 27)
    delta = target_date - start_date
    weeks_passed = delta.days // 7
    
    if weeks_passed % 2 == 0:
        week_type = "числитель"
        schedule = "1. Физкультура\n2. Информатика\n3. Математика"
    else:
        week_type = "знаменатель"
        schedule = "1. Физика\n2. Информатика\n3. Математика"
    
    return week_type, schedule

# ============================
# 🔔 ПРОСТАЯ СИСТЕМА УВЕДОМЛЕНИЙ
# ============================

async def send_week_notification_to_chat(chat_id, application):
    """Отправка уведомления о неделе в конкретный чат"""
    try:
        logger.info(f"🔔 Отправка уведомления о неделе в чат {chat_id}")
        
        # Определяем следующую неделю
        next_week_date = datetime.datetime.now() + datetime.timedelta(days=7)
        next_week_type, next_schedule = get_week_type_and_schedule(next_week_date)
        
        week_type_text = "числителю" if next_week_type == "числитель" else "знаменателю"
        
        message_text = (
            f"📚 <b>Внимание! ТЕСТОВОЕ УВЕДОМЛЕНИЕ</b>\n\n"
            f"Следующая неделя у нас будет по <b>{week_type_text}</b>\n\n"
            f"<b>Расписание на понедельник:</b>\n"
            f"{next_schedule}"
        )
        
        # Отправляем сообщение
        message = await application.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            parse_mode='HTML'
        )
        
        # Пытаемся закрепить сообщение
        try:
            await application.bot.pin_chat_message(
                chat_id=chat_id,
                message_id=message.message_id,
                disable_notification=True
            )
            logger.info(f"📌 Сообщение закреплено в чате {chat_id}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось закрепить сообщение в {chat_id}: {e}")
        
        # Обновляем данные группы
        if str(chat_id) in GROUPS:
            GROUPS[str(chat_id)]['pinned_message_id'] = message.message_id
            GROUPS[str(chat_id)]['current_week_type'] = next_week_type
            save_groups(GROUPS)
        
        logger.info(f"✅ Уведомление о неделе отправлено в чат {chat_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления в чат {chat_id}: {e}")
        return False

async def send_week_notifications(application):
    """Отправка уведомлений о неделе во все группы"""
    try:
        for chat_id_str in GROUPS.keys():
            chat_id = int(chat_id_str)
            await send_week_notification_to_chat(chat_id, application)
    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомлений о неделе: {e}")

async def send_new_day_notifications(application):
    """Отправка уведомлений о новом дне"""
    try:
        # Обновляем дежурных
        was_updated = check_and_update_duty_date()
        
        duty1, duty2 = get_current_duty_pair()
        today_str = datetime.datetime.now().strftime("%d.%m.%Y")
        
        if was_updated:
            # Уведомления администраторам в ЛС
            for username, user_id in ADMIN_USER_IDS.items():
                try:
                    await application.bot.send_message(
                        chat_id=user_id,
                        text=f"🔄 <b>Я автоматически заменил дежурных на сегодняшний день!</b>\n\n"
                             f"<b>📅 Сегодняшняя дата: {today_str}</b>\n\n"
                             f"<b>🧹 Сегодня дежурные:</b>\n"
                             f"<i>👤 {duty1}</i>\n"
                             f"<i>👤 {duty2}</i>\n\n"
                             f"<i>💡 Используйте команду /start для управления дежурными</i>",
                        parse_mode='HTML'
                    )
                    logger.info(f"📤 Уведомление отправлено администратору {username} (ID: {user_id})")
                except Exception as e:
                    logger.error(f"❌ Не удалось отправить уведомление {username} (ID: {user_id}): {e}")
            
            # Уведомления в группы
            for chat_id_str in GROUPS.keys():
                try:
                    chat_id = int(chat_id_str)
                    await application.bot.send_message(
                        chat_id=chat_id,
                        text=f"🔄 <b>Новый день!</b>\n\n"
                             f"<b>🧹 Сегодня дежурные:</b>\n"
                             f"<i>👤 {duty1}</i>\n"
                             f"<i>👤 {duty2}</i>\n\n"
                             f"<i>Не забудьте выполнить свои обязанности!</i>",
                        parse_mode='HTML'
                    )
                    logger.info(f"📤 Уведомление отправлено в группу {chat_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось отправить уведомление в группу {chat_id}: {e}")
        else:
            # Отправляем уведомление даже если дежурные не обновлены (например, воскресенье)
            for username, user_id in ADMIN_USER_IDS.items():
                try:
                    await application.bot.send_message(
                        chat_id=user_id,
                        text=f"ℹ️ <b>Наступил новый день!</b>\n\n"
                             f"<b>📅 Сегодняшняя дата: {today_str}</b>\n\n"
                             f"<b>🧹 Сегодня дежурные:</b>\n"
                             f"<i>👤 {duty1}</i>\n"
                             f"<i>👤 {duty2}</i>\n\n"
                             f"<i>💡 Воскресенье - дежурных нет, отдыхаем!</i>",
                        parse_mode='HTML'
                    )
                    logger.info(f"📤 Уведомление отправлено администратору {username} (ID: {user_id})")
                except Exception as e:
                    logger.error(f"❌ Не удалось отправить уведомление {username} (ID: {user_id}): {e}")
                    
    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомлений о новом дне: {e}")

# ============================
# 🎮 ОСНОВНЫЕ КОМАНДЫ
# ============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    
    if user.username not in ADMINS:
        await update.message.reply_html(
            "<b>⛔ ОТМЕНА ДЕЙСТВИЙ!</b>\n\n"
            "<i>😢 У вас к сожалению нет доступа к боту, обратитесь за доступом к @krixxsy</i>"
        )
        return

    keyboard = [
        [InlineKeyboardButton("🎯 Выбрать дежурных на сегодня", callback_data="select_duty")],
        [InlineKeyboardButton("👑 Открыть админ панель", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_html(
        "<b>👋 Приветствую, я бот, который выбирает автоматически дежурных.</b>\n\n"
        "<i>💡 Выберите действие:</i>",
        reply_markup=reply_markup
    )

# ============================
# 🏢 КОМАНДЫ ГРУПП
# ============================

async def set_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /set_group - установить группу"""
    user = update.effective_user
    
    if user.username not in ADMINS:
        return
    
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    if chat_type not in ['group', 'supergroup']:
        await update.message.reply_html(
            "❌ <b>Эта команда работает только в группах!</b>\n\n"
            "<i>Добавьте бота в группу и используйте команду там.</i>"
        )
        return
    
    # Добавляем/обновляем группу
    GROUPS[str(chat_id)] = {
        'pinned_message_id': None,
        'current_week_type': 'числитель',
        'last_week_update': datetime.datetime.now().strftime('%Y-%m-%d'),
        'title': update.effective_chat.title
    }
    save_groups(GROUPS)
    
    await update.message.reply_html(
        f"✅ <b>Группа установлена!</b>\n\n"
        f"<i>🏷️ Название: {update.effective_chat.title}</i>\n"
        f"<i>🆔 ID группы: {chat_id}</i>\n\n"
        f"<b>📅 Расписание уведомлений:</b>\n"
        f"• 📚 О неделях - воскресенье в 21:00 МСК\n"
        f"• 🔄 О новом дне - ежедневно в 00:00 МСК\n\n"
        f"<b>✅ Уведомления активированы!</b>"
    )
    
    logger.info(f"✅ Установлена группа: {chat_id}")

async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /remove_group - удалить группу"""
    user = update.effective_user
    
    if user.username not in ADMINS:
        return
    
    chat_id = update.effective_chat.id
    
    if str(chat_id) not in GROUPS:
        await update.message.reply_html(
            "❌ <b>Эта группа не была установлена!</b>\n\n"
            "<i>Сначала используйте команду /set_group</i>"
        )
        return
    
    # Удаляем группу
    group_title = GROUPS[str(chat_id)].get('title', 'Неизвестно')
    del GROUPS[str(chat_id)]
    save_groups(GROUPS)
    
    await update.message.reply_html(
        f"🗑️ <b>Группа удалена!</b>\n\n"
        f"<i>🏷️ Название: {group_title}</i>\n"
        f"<i>🆔 ID группы: {chat_id}</i>\n\n"
        f"<i>Все уведомления остановлены.</i>"
    )
    
    logger.info(f"🗑️ Удалена группа: {chat_id}")

async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /list_groups - список групп"""
    user = update.effective_user
    
    if user.username not in ADMINS:
        return
    
    if not GROUPS:
        await update.message.reply_html(
            "📋 <b>Список групп пуст</b>\n\n"
            "<i>Используйте /set_group в группе чтобы добавить ее</i>"
        )
        return
    
    groups_text = ""
    for chat_id, group_data in GROUPS.items():
        groups_text += f"• <b>{group_data.get('title', 'Неизвестно')}</b>\n"
        groups_text += f"  🆔 ID: {chat_id}\n"
        groups_text += f"  📅 Неделя: {group_data.get('current_week_type', 'Неизвестно')}\n\n"
    
    await update.message.reply_html(
        f"📋 <b>Список активных групп:</b>\n\n{groups_text}"
    )

# ============================
# 🧪 ТЕСТОВЫЕ КОМАНДЫ
# ============================

async def test_week_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /test_week - тест уведомления о неделе"""
    user = update.effective_user
    
    if user.username not in ADMINS:
        return
    
    chat_id = update.effective_chat.id
    
    if str(chat_id) not in GROUPS:
        await update.message.reply_html(
            "❌ <b>Группа не установлена!</b>\n\n"
            "<i>Сначала используйте команду /set_group в группе</i>"
        )
        return
    
    try:
        success = await send_week_notification_to_chat(chat_id, context.application)
        
        if success:
            await update.message.reply_html(
                "✅ <b>Тестовое уведомление отправлено!</b>\n\n"
                "<i>Проверьте группу</i>"
            )
        else:
            await update.message.reply_html(
                "❌ <b>Не удалось отправить тестовое уведомление!</b>\n\n"
                "<i>Проверьте логи бота</i>"
            )
    except Exception as e:
        logger.error(f"❌ Ошибка теста уведомления: {e}")
        await update.message.reply_html(
            "❌ <b>Ошибка отправки тестового уведомления!</b>"
        )

async def test_new_day_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /test_new_day - тест уведомления о новом дне"""
    user = update.effective_user
    
    if user.username not in ADMINS:
        return
    
    try:
        # Принудительно обновляем дежурных для теста
        move_to_next_pair()
        duty1, duty2 = get_current_duty_pair()
        today_str = datetime.datetime.now().strftime("%d.%m.%Y")
        
        # Тестируем отправку администраторам
        for username, user_id in ADMIN_USER_IDS.items():
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🔄 <b>ТЕСТ: Я автоматически заменил дежурных на сегодняшний день!</b>\n\n"
                         f"<b>📅 Сегодняшняя дата: {today_str}</b>\n\n"
                         f"<b>🧹 Сегодня дежурные:</b>\n"
                         f"<i>👤 {duty1}</i>\n"
                         f"<i>👤 {duty2}</i>\n\n"
                         f"<i>💡 Используйте команду /start для управления дежурными</i>",
                    parse_mode='HTML'
                )
                logger.info(f"🧪 Тестовое уведомление отправлено: {username} ({user_id})")
            except Exception as e:
                logger.error(f"❌ Не удалось отправить тестовое уведомление {username} (ID: {user_id}): {e}")
        
        await update.message.reply_html(
            "✅ <b>Тестовое уведомление о новом дне отправлено!</b>\n\n"
            "<i>Проверьте ЛС администраторов</i>"
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании: {e}")
        await update.message.reply_html(
            "❌ <b>Ошибка при отправке тестового уведомления!</b>"
        )

# ============================
# 🎛️ ОБРАБОТЧИКИ CALLBACK
# ============================

# Глобальные переменные для управления сообщениями
user_states = {}

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback запросов"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    
    if user.username not in ADMINS:
        await query.edit_message_text("⛔ У вас нет доступа!")
        return

    if query.data == "select_duty":
        await show_duty_today(query)
    elif query.data == "admin_panel":
        await admin_panel(query)
    elif query.data == "replace_both":
        await replace_both_duty(query)
    elif query.data == "replace_first":
        await replace_single_duty_callback(query, 0)
    elif query.data == "replace_second":
        await replace_single_duty_callback(query, 1)
    elif query.data == "main_menu":
        await main_menu(query)
    elif query.data == "list_groups_callback":
        await list_groups_callback(query)
    elif query.data == "test_week_callback":
        await test_week_callback(query, context)
    elif query.data == "test_day_callback":
        await test_day_callback(query, context)
    elif query.data == "add_admin":
        await start_add_admin(query)
    elif query.data == "remove_admin":
        await start_remove_admin(query)
    elif query.data == "list_admins":
        await show_admins_list(query)
    elif query.data == "cancel_admin":
        await cancel_admin_action(query)
    elif query.data.startswith("set_role_"):
        await set_admin_role(query)

async def show_duty_today(query):
    """Показать дежурных на сегодня"""
    was_updated = check_and_update_duty_date()
    
    today = datetime.datetime.now()
    today_str = today.strftime("%d.%m.%Y")
    
    duty1, duty2 = get_current_duty_pair()
    
    if today.weekday() == 6:
        message = (
            f"<b>📅 Сегодняшняя дата: {today_str}</b>\n\n"
            f"<b>🎉 Воскресенье - выходной день!</b>\n"
            f"<i>Дежурных нет, отдыхаем.</i>"
        )
        keyboard = [
            [InlineKeyboardButton("🔙 На главную", callback_data="main_menu")]
        ]
    else:
        update_info = "🔄 <i>Дежурные автоматически обновлены на сегодня</i>\n\n" if was_updated else ""
        
        message = (
            f"<b>📅 Сегодняшняя дата: {today_str}</b>\n\n"
            f"{update_info}"
            f"<b>🧹 Сегодня дежурные:</b>\n"
            f"<i>👤 {duty1}</i>\n"
            f"<i>👤 {duty2}</i>\n\n"
            f"<i>💡 Для замены дежурных используйте кнопки ниже</i>"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Заменить двух дежурных", callback_data="replace_both")],
            [
                InlineKeyboardButton("👤 Заменить дежурного 1", callback_data="replace_first"),
                InlineKeyboardButton("👤 Заменить дежурного 2", callback_data="replace_second")
            ],
            [InlineKeyboardButton("🔙 На главную", callback_data="main_menu")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def replace_both_duty(query):
    """Заменить обоих дежурных"""
    today = datetime.datetime.now()
    
    if today.weekday() == 6:
        await query.answer("Сегодня воскресенье - дежурных нет!")
        return
    
    move_to_next_pair()
    
    today_str = today.strftime("%d.%m.%Y")
    duty1, duty2 = get_current_duty_pair()
    
    message = (
        f"<b>🔄 Дежурные заменены!</b>\n\n"
        f"<b>📅 Сегодняшняя дата: {today_str}</b>\n\n"
        f"<b>🧹 Сегодня дежурные:</b>\n"
        f"<i>👤 {duty1}</i>\n"
        f"<i>👤 {duty2}</i>\n\n"
        f"<i>💡 Установлена следующая пара по очереди</i>"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 Заменить двух дежурных", callback_data="replace_both")],
        [
            InlineKeyboardButton("👤 Заменить дежурного 1", callback_data="replace_first"),
            InlineKeyboardButton("👤 Заменить дежурного 2", callback_data="replace_second")
        ],
        [InlineKeyboardButton("🔙 На главную", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def replace_single_duty_callback(query, duty_index):
    """Заменить одного дежурного"""
    today = datetime.datetime.now()
    
    if today.weekday() == 6:
        await query.answer("Сегодня воскресенье - дежурных нет!")
        return
    
    current_duty1, current_duty2 = get_current_duty_pair()
    
    # Получаем список всех людей
    all_people = []
    for pair in PAIRS:
        all_people.extend(pair)
    
    # Исключаем текущих дежурных и исключенных
    excluded = EXCLUDED.copy()
    excluded.append(current_duty1)
    excluded.append(current_duty2)
    
    available_people = [person for person in all_people if person not in excluded]
    
    if not available_people:
        await query.answer("Нет доступных людей для замены!")
        return
    
    new_person = random.choice(available_people)
    
    # Создаем новую пару
    new_pair = list(get_current_duty_pair())
    new_pair[duty_index] = new_person
    
    # Обновляем текущую пару
    current_index = DUTY_STATE['current_index']
    PAIRS[current_index] = tuple(new_pair)
    
    today_str = today.strftime("%d.%m.%Y")
    duty_text = "Дежурный 1" if duty_index == 0 else "Дежурный 2"
    old_duty = current_duty1 if duty_index == 0 else current_duty2
    
    message = (
        f"<b>👤 {duty_text} заменен!</b>\n\n"
        f"<b>📅 Сегодняшняя дата: {today_str}</b>\n\n"
        f"<b>🧹 Сегодня дежурные:</b>\n"
        f"<i>👤 {new_pair[0]}</i>\n"
        f"<i>👤 {new_pair[1]}</i>\n\n"
        f"<i>💡 {old_duty} → {new_person}</i>"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 Заменить двух дежурных", callback_data="replace_both")],
        [
            InlineKeyboardButton("👤 Заменить дежурного 1", callback_data="replace_first"),
            InlineKeyboardButton("👤 Заменить дежурного 2", callback_data="replace_second")
        ],
        [InlineKeyboardButton("🔙 На главную", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def admin_panel(query):
    """Панель администратора"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить администратора", callback_data="add_admin")],
        [InlineKeyboardButton("➖ Удалить администратора", callback_data="remove_admin")],
        [InlineKeyboardButton("📋 Список администраторов", callback_data="list_admins")],
        [InlineKeyboardButton("📋 Список групп", callback_data="list_groups_callback")],
        [InlineKeyboardButton("🧪 Тест уведомления о неделе", callback_data="test_week_callback")],
        [InlineKeyboardButton("🧪 Тест уведомления о дне", callback_data="test_day_callback")],
        [InlineKeyboardButton("🔙 На главную", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "<b>👑 Панель администратора</b>\n\n"
        "<i>Выберите действие:</i>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def main_menu(query):
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("🎯 Выбрать дежурных на сегодня", callback_data="select_duty")],
        [InlineKeyboardButton("👑 Открыть админ панель", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "<b>👋 Приветствую, я бот, который выбирает автоматически дежурных.</b>\n\n"
        "<i>💡 Выберите действие:</i>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def list_groups_callback(query):
    """Список групп через callback"""
    if not GROUPS:
        await query.edit_message_text(
            "📋 <b>Список групп пуст</b>\n\n"
            "<i>Используйте /set_group в группе чтобы добавить ее</i>",
            parse_mode='HTML'
        )
        return
    
    groups_text = ""
    for chat_id, group_data in GROUPS.items():
        groups_text += f"• <b>{group_data.get('title', 'Неизвестно')}</b>\n"
        groups_text += f"  🆔 ID: {chat_id}\n"
        groups_text += f"  📅 Неделя: {group_data.get('current_week_type', 'Неизвестно')}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📋 <b>Список активных групп:</b>\n\n{groups_text}",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def test_week_callback(query, context):
    """Тест уведомления о неделе через callback"""
    try:
        if not GROUPS:
            await query.edit_message_text(
                "❌ <b>Нет активных групп!</b>\n\n"
                "<i>Сначала установите группу командой /set_group</i>",
                parse_mode='HTML'
            )
            return
        
        await send_week_notifications(context.application)
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "✅ <b>Тестовое уведомление отправлено!</b>\n\n"
            "<i>Проверьте все активные группы</i>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"❌ Ошибка теста уведомления: {e}")
        await query.edit_message_text(
            "❌ <b>Ошибка отправки тестового уведомления!</b>",
            parse_mode='HTML'
        )

async def test_day_callback(query, context):
    """Тест уведомления о дне через callback"""
    try:
        # Принудительно обновляем дежурных для теста
        move_to_next_pair()
        duty1, duty2 = get_current_duty_pair()
        today_str = datetime.datetime.now().strftime("%d.%m.%Y")
        
        # Тестируем отправку администраторам
        for username, user_id in ADMIN_USER_IDS.items():
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🔄 <b>ТЕСТ: Я автоматически заменил дежурных на сегодняшний день!</b>\n\n"
                         f"<b>📅 Сегодняшняя дата: {today_str}</b>\n\n"
                         f"<b>🧹 Сегодня дежурные:</b>\n"
                         f"<i>👤 {duty1}</i>\n"
                         f"<i>👤 {duty2}</i>\n\n"
                         f"<i>💡 Используйте команду /start для управления дежурными</i>",
                    parse_mode='HTML'
                )
                logger.info(f"🧪 Тестовое уведомление отправлено: {username} ({user_id})")
            except Exception as e:
                logger.error(f"❌ Не удалось отправить тестовое уведомление {username} (ID: {user_id}): {e}")
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "✅ <b>Тестовое уведомление отправлено!</b>\n\n"
            "<i>Проверьте ЛС администраторов</i>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"❌ Ошибка теста уведомления: {e}")
        await query.edit_message_text(
            "❌ <b>Ошибка отправки тестового уведомления!</b>",
            parse_mode='HTML'
        )

# ============================
# 👑 УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ
# ============================

async def start_add_admin(query):
    """Начало добавления администратора"""
    user_id = query.from_user.id
    user_states[user_id] = {
        'state': 'waiting_admin_username_add',
        'message_id': query.message.message_id
    }
    
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_admin")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "👤 <b>Добавление администратора</b>\n\n"
        "Введите username пользователя (без @):\n\n"
        "<i>💡 Сообщение будет автоматически удалено после ввода</i>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def start_remove_admin(query):
    """Начало удаления администратора"""
    user_id = query.from_user.id
    user_states[user_id] = {
        'state': 'waiting_admin_username_remove', 
        'message_id': query.message.message_id
    }
    
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_admin")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "👤 <b>Удаление администратора</b>\n\n"
        "Введите username пользователя (без @):\n\n"
        "<i>💡 Сообщение будет автоматически удалено после ввода</i>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def show_admins_list(query):
    """Показать список администраторов"""
    sorted_admins = []
    
    if 'Seivel66' in ADMINS:
        sorted_admins.append(('Seivel66', ADMINS['Seivel66']))
    
    if 'krixxsy' in ADMINS:
        sorted_admins.append(('krixxsy', ADMINS['krixxsy']))
    
    other_admins = [(username, data) for username, data in ADMINS.items() 
                   if username not in ['Seivel66', 'krixxsy']]
    other_admins.sort(key=lambda x: x[0])
    sorted_admins.extend(other_admins)
    
    admins_text = ""
    for username, data in sorted_admins:
        role_icon = data['display_name']
        admins_text += f"• @{username} - {role_icon}\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="cancel_admin")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"<b>👑 Список администраторов:</b>\n\n{admins_text}",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def set_admin_role(query):
    """Установить роль администратора"""
    user_id = query.from_user.id
    if user_id not in user_states:
        await query.answer("Ошибка состояния!")
        return
    
    state_data = user_states[user_id]
    username = state_data['username']
    role_key = query.data.replace("set_role_", "")
    
    ADMINS[username] = {
        'role': role_key,
        'display_name': ROLES[role_key]
    }
    save_admins(ADMINS)
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить администратора", callback_data="add_admin")],
        [InlineKeyboardButton("➖ Удалить администратора", callback_data="remove_admin")],
        [InlineKeyboardButton("📋 Список администраторов", callback_data="list_admins")],
        [InlineKeyboardButton("🔙 На главную", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ <b>Успех!</b>\n\n"
        f"Пользователь @{username} добавлен в администраторы с ролью {ROLES[role_key]}.",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    del user_states[user_id]

async def cancel_admin_action(query):
    """Отмена действия администратора"""
    user_id = query.from_user.id
    if user_id in user_states:
        del user_states[user_id]
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить администратора", callback_data="add_admin")],
        [InlineKeyboardButton("➖ Удалить администратора", callback_data="remove_admin")],
        [InlineKeyboardButton("📋 Список администраторов", callback_data="list_admins")],
        [InlineKeyboardButton("🔙 На главную", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "<b>👑 Панель администратора</b>\n\n"
        "<i>Выберите действие:</i>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

# Обработчик текстовых сообщений для добавления/удаления администраторов
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    # В группах игнорируем все сообщения от пользователей
    if update.effective_chat.type != 'private':
        return
    
    user = update.effective_user
    text = update.message.text.strip()
    
    if user.id in user_states:
        state_data = user_states[user.id]
        state = state_data['state']
        
        if state == 'waiting_admin_username_add':
            await process_add_admin(update, text, state_data['message_id'])
        elif state == 'waiting_admin_username_remove':
            await process_remove_admin(update, text, state_data['message_id'])

async def process_add_admin(update, username, message_id):
    """Обработка добавления администратора"""
    user_id = update.effective_user.id
    
    if username.startswith('@'):
        username = username[1:]
    
    chat_id = update.effective_chat.id
    
    if username in ADMINS:
        message = (
            "❌ <b>Ошибка!</b>\n\n"
            f"Пользователь @{username} уже является администратором."
        )
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить администратора", callback_data="add_admin")],
            [InlineKeyboardButton("➖ Удалить администратора", callback_data="remove_admin")],
            [InlineKeyboardButton("📋 Список администраторов", callback_data="list_admins")],
            [InlineKeyboardButton("🔙 На главную", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update._bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"{message}\n\n<b>👑 Панель администратора</b>\n\n<i>Выберите действие:</i>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        user_states[user_id] = {
            'state': 'waiting_admin_role',
            'message_id': message_id,
            'username': username
        }
        
        keyboard = [
            [InlineKeyboardButton(role_name, callback_data=f"set_role_{role_key}")]
            for role_key, role_name in ROLES.items() if role_key not in ['headman', 'creator']
        ]
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_admin")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update._bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=(
                f"👤 <b>Добавление администратора:</b> @{username}\n\n"
                f"<i>Выберите роль:</i>"
            ),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    
    if 'waiting_admin_username_add' in user_states.get(user_id, {}).get('state', ''):
        del user_states[user_id]

async def process_remove_admin(update, username, message_id):
    """Обработка удаления администратора"""
    user_id = update.effective_user.id
    
    if username.startswith('@'):
        username = username[1:]
    
    chat_id = update.effective_chat.id
    
    if username not in ADMINS:
        message = (
            "❌ <b>Ошибка!</b>\n\n"
            f"Пользователь @{username} не является администратором."
        )
    elif username in ['Seivel66', 'krixxsy']:
        message = (
            "❌ <b>Ошибка!</b>\n\n"
            "Нельзя удалить основного администратора."
        )
    else:
        removed_user_data = ADMINS[username]
        del ADMINS[username]
        save_admins(ADMINS)
        
        message = (
            f"✅ <b>Успех!</b>\n\n"
            f"Пользователь @{username} удален из администраторов."
        )
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить администратора", callback_data="add_admin")],
        [InlineKeyboardButton("➖ Удалить администратора", callback_data="remove_admin")],
        [InlineKeyboardButton("📋 Список администраторов", callback_data="list_admins")],
        [InlineKeyboardButton("🔙 На главную", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update._bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=f"{message}\n\n<b>👑 Панель администратора</b>\n\n<i>Выберите действие:</i>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    del user_states[user_id]

# ============================
# 🚀 ОСНОВНАЯ ФУНКЦИЯ
# ============================

async def background_notification_checker(application):
    """Фоновая проверка уведомлений"""
    while True:
        try:
            now = datetime.datetime.now()
            current_time = now.strftime("%H:%M")
            today = now.strftime("%Y-%m-%d")
            
            # Уведомление о неделе (воскресенье в 21:00 МСК)
            if (now.weekday() == 6 and  # Воскресенье
                current_time == "21:00"):  # 21:00 МСК
                
                await send_week_notifications(application)
                logger.info("📚 Отправлены уведомления о неделе")
            
            # Уведомление о новом дне (ежедневно в 00:00 МСК)
            if current_time == "00:00":  # 00:00 МСК
                
                await send_new_day_notifications(application)
                logger.info("🔄 Отправлены уведомления о новом дне")
                
        except Exception as e:
            logger.error(f"❌ Ошибка в фоновой проверке: {e}")
        
        # Проверяем каждую минуту
        await asyncio.sleep(60)

async def post_init(application):
    """Инициализация после запуска"""
    await application.bot.set_my_commands([
        BotCommand("start", "Начать работу с ботом"),
        BotCommand("set_group", "Установить группу (только в группах)"),
        BotCommand("test_week", "Тест уведомления о неделе (только в группах)"),
        BotCommand("test_new_day", "Тест уведомления о новом дне"),
    ])
    
    # Запускаем фоновую проверку уведомлений
    asyncio.create_task(background_notification_checker(application))
    
    print("✅ Бот инициализирован, уведомления активированы!")

def main():
    print("🚀 Бот запускается...")
    print("=" * 50)
    
    # НОВЫЙ ТОКЕН
    TOKEN = "8078315381:AAHE1LspvxGJzByVdy6SG3kFLOuMxHCq8yA"
    
    try:
        application = Application.builder().token(TOKEN).build()
        
        # Регистрация обработчиков
        application.add_handler(CommandHandler("start", start, filters.ChatType.PRIVATE))
        application.add_handler(CommandHandler("set_group", set_group, filters.ChatType.GROUP | filters.ChatType.SUPERGROUP))
        application.add_handler(CommandHandler("remove_group", remove_group, filters.ChatType.GROUP | filters.ChatType.SUPERGROUP))
        application.add_handler(CommandHandler("list_groups", list_groups, filters.ChatType.PRIVATE))
        application.add_handler(CommandHandler("test_week", test_week_notification, filters.ChatType.GROUP | filters.ChatType.SUPERGROUP))
        application.add_handler(CommandHandler("test_new_day", test_new_day_notification, filters.ChatType.PRIVATE))
        
        # Обработчик текстовых сообщений для управления администраторами
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, 
            handle_message
        ))
        
        application.add_handler(CallbackQueryHandler(handle_callback))
        
        # Информация при запуске
        print("=" * 50)
        print("✅ Бот успешно запущен!")
        print(f"📊 Групп в системе: {len(GROUPS)}")
        
        duty1, duty2 = get_current_duty_pair()
        print(f"📅 Текущие дежурные: {duty1} и {duty2}")
        
        print("🕐 Временные зоны настроены:")
        print("   • Уведомление о неделе: воскресенье в 21:00 МСК")
        print("   • Уведомление о новом дне: ежедневно в 00:00 МСК")
        print("🔒 Команды работают только в личных чатах с админами")
        print("=" * 50)
        
        # Запускаем пост-инициализацию
        application.post_init = post_init
        
        # Запускаем бота
        application.run_polling()
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        print("🔄 Перезапустите бота")

if __name__ == '__main__':
    main()