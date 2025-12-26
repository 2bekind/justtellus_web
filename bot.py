import os
import logging
import json
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes, JobQueue

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен бота и ID владельца из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', 0))

# Список получателей сообщений с их username
RECIPIENTS = {
    7654953677: "@jxstkillme",
    8109892353: "@lightalwayswillbeoff"
}

# Словарь для хранения выбора получателя каждым пользователем
# Ключ: user_id отправителя, Значение: recipient_id выбранного получателя
user_recipient_choice = {}

# Статистика для каждого получателя
# Структура: recipient_id -> {
#   'received': количество полученных сообщений,
#   'sent': количество отправленных сообщений,
#   'choosers': множество user_id тех, кто выбирал этого получателя,
#   'last_message_time': datetime последнего сообщения,
#   'current_streak': текущая серия,
#   'max_streak': максимальная серия
# }
recipient_stats = {
    7654953677: {
        'received': 0,
        'sent': 0,
        'choosers': set(),
        'last_message_time': None,
        'current_streak': 0,
        'max_streak': 0
    },
    8109892353: {
        'received': 0,
        'sent': 0,
        'choosers': set(),
        'last_message_time': None,
        'current_streak': 0,
        'max_streak': 0
    }
}

# Словарь для хранения связи между message_id бота и user_id отправителя
# Ключ: message_id сообщения бота, Значение: user_id отправителя исходного сообщения
message_to_user = {}

# Московское время
moscow_tz = pytz.timezone('Europe/Moscow')


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.message.from_user.id
    
    start_text = "анонимно отправить. отправить. напиши что нибудь."
    
    await update.message.reply_text(start_text)
    logger.info(f"Команда /start от пользователя: {user_id}")


async def choose_recipient_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора получателя"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Извлекаем ID получателя из callback_data
    recipient_id = int(query.data.split("_")[-1])
    username = RECIPIENTS[recipient_id]
    
    # Сохраняем выбор
    user_recipient_choice[user_id] = recipient_id
    
    # Обновляем статистику - добавляем пользователя в список выбравших
    if recipient_id in recipient_stats:
        recipient_stats[recipient_id]['choosers'].add(user_id)
        save_data()
    
    await query.answer(f"выбран получатель: {username}")
    await query.edit_message_text(f"✅получатель выбран: {username}\nтеперь отправьте ваше сообщение.\nизменить вроде можно по команде:\n/change")


async def change_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /change - смена получателя"""
    user_id = update.message.from_user.id
    
    # Показываем кнопки выбора получателя
    keyboard = [
        [InlineKeyboardButton(RECIPIENTS[8109892353], callback_data=f"choose_recipient_8109892353")],
        [InlineKeyboardButton(RECIPIENTS[7654953677], callback_data=f"choose_recipient_7654953677")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("выберите кому хотите прислать сообщение. желательно первому. наверное.", reply_markup=reply_markup)


def save_data():
    """Сохраняет все данные в JSON файл"""
    data = {
        'user_recipient_choice': {str(k): v for k, v in user_recipient_choice.items()},
        'recipient_stats': {
            str(k): {
                'received': v['received'],
                'sent': v['sent'],
                'choosers': list(v['choosers']),
                'last_message_time': v['last_message_time'].isoformat() if v['last_message_time'] else None,
                'current_streak': v['current_streak'],
                'max_streak': v['max_streak']
            }
            for k, v in recipient_stats.items()
        }
    }
    with open('bot_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Данные сохранены в bot_data.json")


def load_data():
    """Загружает все данные из JSON файла"""
    global user_recipient_choice, recipient_stats
    
    if not os.path.exists('bot_data.json'):
        logger.info("Файл bot_data.json не найден, используем начальные значения")
        return
    
    try:
        with open('bot_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Загружаем выбор получателей
        user_recipient_choice = {int(k): v for k, v in data.get('user_recipient_choice', {}).items()}
        
        # Загружаем статистику
        for k, v in data.get('recipient_stats', {}).items():
            recipient_id = int(k)
            if recipient_id in recipient_stats:
                recipient_stats[recipient_id]['received'] = v.get('received', 0)
                recipient_stats[recipient_id]['sent'] = v.get('sent', 0)
                recipient_stats[recipient_id]['choosers'] = set(v.get('choosers', []))
                last_time = v.get('last_message_time')
                recipient_stats[recipient_id]['last_message_time'] = datetime.fromisoformat(last_time).replace(tzinfo=moscow_tz) if last_time else None
                recipient_stats[recipient_id]['current_streak'] = v.get('current_streak', 0)
                recipient_stats[recipient_id]['max_streak'] = v.get('max_streak', 0)
        
        logger.info("Данные загружены из bot_data.json")
    except Exception as e:
        logger.error(f"Ошибка при загрузке данных: {e}")


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /profile - статистика"""
    user_id = update.message.from_user.id
    is_owner = user_id in RECIPIENTS
    
    if is_owner:
        # Для владельцев показываем полную статистику
        if user_id not in recipient_stats:
            await update.message.reply_text("статистика недоступна.")
            return
        
        stats = recipient_stats[user_id]
        
        # Формируем текст профиля
        profile_text = f"""только для тех кто владеет ботом.
[- - - - -]
полученные сообщения: [{stats['received']}]✉️
выбирали тебя: [{len(stats['choosers'])}]🙏
для всех
[- - - - -]
отправленные сообщения: [{stats['sent']}]🪶
самая долгая серия сообщений: [{stats['max_streak']}]🔥"""
    else:
        # Для обычных пользователей показываем общую статистику
        total_sent = sum(s['sent'] for s in recipient_stats.values())
        total_max_streak = max(s['max_streak'] for s in recipient_stats.values()) if recipient_stats else 0
        
        profile_text = f"""для всех
[- - - - -]
отправленные сообщения: [{total_sent}]🪶
самая долгая серия сообщений: [{total_max_streak}]🔥"""
    
    await update.message.reply_text(profile_text)


async def check_streak_breaks(context: ContextTypes.DEFAULT_TYPE):
    """Периодическая задача для проверки обрыва серий сообщений"""
    now_moscow = datetime.now(moscow_tz)
    
    for recipient_id, stats in recipient_stats.items():
        if stats['last_message_time'] is None:
            continue
        
        # Проверяем, прошло ли больше суток с последнего сообщения
        time_diff = now_moscow - stats['last_message_time']
        if time_diff > timedelta(days=1):
            # Серия оборвалась, сбрасываем текущую серию
            if stats['current_streak'] > 0:
                stats['current_streak'] = 0
                logger.debug(f"Серия для получателя {recipient_id} оборвалась")


async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ответов на сообщения от получателей"""
    if not update.message or not update.message.reply_to_message:
        return
    
    # Проверяем, что ответ пришел от одного из получателей
    sender_id = update.message.from_user.id
    if sender_id not in RECIPIENTS:
        return
    
    # Обновляем статистику отправленных сообщений
    if sender_id in recipient_stats:
        recipient_stats[sender_id]['sent'] += 1
        save_data()
    
    # Получаем ID сообщения, на которое ответили
    replied_message_id = update.message.reply_to_message.message_id
    
    # Проверяем, есть ли связь с исходным отправителем
    if replied_message_id not in message_to_user:
        return
    
    # Получаем информацию об исходном отправителе
    original_sender = message_to_user[replied_message_id]
    original_user_id = original_sender['user_id']
    original_chat_id = original_sender['chat_id']
    
    # Получаем текст ответа
    reply_text = update.message.text or "Нет текста"
    
    # Получаем username отправителя ответа (без @)
    sender_username = RECIPIENTS.get(sender_id, "неизвестно")
    # Убираем @ если есть
    if sender_username.startswith("@"):
        sender_username = sender_username[1:]
    
    # Формируем ответ с username отправителя
    formatted_reply = f"{sender_username}: {reply_text}"
    
    # Отправляем ответ исходному отправителю
    try:
        await context.bot.send_message(
            chat_id=original_chat_id,
            text=formatted_reply
        )
        logger.info(f"Ответ от {sender_username} переслан пользователю {original_user_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке ответа пользователю {original_user_id}: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик входящих сообщений"""
    if not update.message:
        return
    
    # Если это ответ на сообщение от получателя, обрабатываем отдельно
    if update.message.reply_to_message and update.message.from_user.id in RECIPIENTS:
        await handle_reply(update, context)
        return
    
    # Пропускаем сообщения от получателей (кроме ответов)
    if update.message.from_user.id in RECIPIENTS:
        return
    
    user_id = update.message.from_user.id
    
    logger.info(f"Получено сообщение от пользователя: {user_id}")
    
    # Проверяем, выбран ли получатель
    if user_id not in user_recipient_choice:
        # Показываем кнопки выбора получателя
        keyboard = [
            [InlineKeyboardButton(RECIPIENTS[8109892353], callback_data=f"choose_recipient_8109892353")],
            [InlineKeyboardButton(RECIPIENTS[7654953677], callback_data=f"choose_recipient_7654953677")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("выберите кому хотите прислать сообщение. желательно первому. наверное.", reply_markup=reply_markup)
        return
    
    # Получаем выбранного получателя
    recipient_id = user_recipient_choice[user_id]
    
    # Получаем информацию о пользователе
    user = update.message.from_user
    username = f"@{user.username}" if user.username else f"{user.first_name or ''} {user.last_name or ''}".strip() or "Без имени"
    user_id = user.id
    
    # Получаем текст сообщения
    text = update.message.text or "Нет текста"
    
    # Формируем сообщение в нужном формате (без лишних пробелов)
    message_text = f"[{username}]\n[{user_id}]\n- - - - -\n[{text}]"
    
    # Отправляем сообщение только выбранному получателю
    try:
        sent_message = await context.bot.send_message(
            chat_id=recipient_id,
            text=message_text
        )
        # Сохраняем связь между message_id бота и user_id отправителя
        message_to_user[sent_message.message_id] = {
            'user_id': user_id,
            'chat_id': update.message.chat_id
        }
        
        # Обновляем статистику
        if recipient_id in recipient_stats:
            stats = recipient_stats[recipient_id]
            stats['received'] += 1
            stats['choosers'].add(user_id)
            
            # Обновляем серию сообщений
            now_moscow = datetime.now(moscow_tz)
            if stats['last_message_time'] is None:
                # Первое сообщение
                stats['current_streak'] = 1
                stats['max_streak'] = 1
            else:
                # Проверяем, не прошло ли больше суток
                time_diff = now_moscow - stats['last_message_time']
                if time_diff <= timedelta(days=1):
                    # Серия продолжается
                    stats['current_streak'] += 1
                else:
                    # Серия оборвалась, начинаем заново
                    stats['current_streak'] = 1
            
            # Обновляем максимальную серию
            if stats['current_streak'] > stats['max_streak']:
                stats['max_streak'] = stats['current_streak']
            
            stats['last_message_time'] = now_moscow
            save_data()
        
        logger.info(f"Сообщение от {username} переслано получателю {recipient_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения получателю {recipient_id}: {e}")


def main():
    """Основная функция запуска бота"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен! Проверьте файл .env")
        return
    
    if not OWNER_ID:
        logger.error("OWNER_ID не установлен! Проверьте файл .env")
        return
    
    # Загружаем сохраненные данные
    load_data()
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем периодические задачи
    job_queue = application.job_queue
    if job_queue:
        # Проверка обрыва серий сообщений (каждый час)
        job_queue.run_repeating(check_streak_breaks, interval=3600.0, first=3600.0)
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("change", change_command))
    
    # Регистрируем обработчики callback
    application.add_handler(CallbackQueryHandler(choose_recipient_callback, pattern="^choose_recipient_"))
    
    # Регистрируем обработчик текстовых сообщений (исключая команды)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота
    logger.info(f"Бот запущен... Token: {BOT_TOKEN[:10]}..., Owner ID: {OWNER_ID}")
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        logger.exception(e)


if __name__ == '__main__':
    main()

