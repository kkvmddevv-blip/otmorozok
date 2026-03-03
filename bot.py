import logging
import random
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "ТВОЙ_ТОКЕН_СЮДА"
ADMIN_ID = 1373730608  # твой ID
ADMIN_PASSWORD = "crocodebiller"
CHAT_ID = -1001234567890  # ID чата (заменишь потом)
# ===================================================

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    
    # Таблица пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, role TEXT, 
                  messages INTEGER DEFAULT 0, fav_word TEXT,
                  diss_got INTEGER DEFAULT 0, diss_given INTEGER DEFAULT 0,
                  last_role_change TIMESTAMP)''')
    
    # Таблица нарушений
    c.execute('''CREATE TABLE IF NOT EXISTS violations
                 (user_id INTEGER, date TIMESTAMP, type TEXT, reason TEXT)''')
    
    # Таблица модераторов
    c.execute('''CREATE TABLE IF NOT EXISTS moders
                 (user_id INTEGER PRIMARY KEY)''')
    
    # Таблица жалоб
    c.execute('''CREATE TABLE IF NOT EXISTS reports
                 (from_id INTEGER, on_id INTEGER, message TEXT, time TIMESTAMP, status TEXT)''')
    
    # Таблица фактов
    c.execute('''CREATE TABLE IF NOT EXISTS facts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT)''')
    
    # Таблица строк для !бар
    c.execute('''CREATE TABLE IF NOT EXISTS bars
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT)''')
    
    # Таблица ролей
    c.execute('''CREATE TABLE IF NOT EXISTS roles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)''')
    
    # Таблица эксклюзивных ролей
    c.execute('''CREATE TABLE IF NOT EXISTS exclusive_roles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)''')
    
    conn.commit()
    conn.close()

# Заполняем начальные данные
def init_data():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    
    # Проверяем, есть ли факты
    c.execute("SELECT COUNT(*) FROM facts")
    if c.fetchone()[0] == 0:
        facts = [
            "В 9 лет сжёг школу. Говорит, самовозгорание",
            "Не пьёт, не курит, но торгует битами",
            "Первый трек записал на диктофон в маршрутке",
            "Спит в студии, потому что дома ждут кредиты",
            "Однажды уснул на бите и проснулся звездой"
        ]
        for fact in facts:
            c.execute("INSERT INTO facts (text) VALUES (?)", (fact,))
    
    # Проверяем, есть ли строки для бара
    c.execute("SELECT COUNT(*) FROM bars")
    if c.fetchone()[0] == 0:
        bars = [
            "Из сарая выхожу",
            "Федя на тракторе уже ихний мопед догоняет",
            "И вот я к огороду подхожу",
            "И слышу вопли из толчка: там городской утопает",
            "Рэпчик мужа нахваливать и подносить пиво, пока не спит"
        ]
        for bar in bars:
            c.execute("INSERT INTO bars (text) VALUES (?)", (bar,))
    
    # Проверяем, есть ли роли
    c.execute("SELECT COUNT(*) FROM roles")
    if c.fetchone()[0] == 0:
        roles = [
            "барыга", "плаг", "закладчик", "кладовщик", "курьер",
            "оптовик", "фармацевт", "травник", "дилер", "провизор",
            "битмейкер", "звукореж", "фристайлер", "баттл-рэпер", "MC"
        ]
        for role in roles:
            c.execute("INSERT INTO roles (name) VALUES (?)", (role,))
    
    # Проверяем, есть ли эксклюзивные роли
    c.execute("SELECT COUNT(*) FROM exclusive_roles")
    if c.fetchone()[0] == 0:
        ex_roles = [
            "Легенда чата", "Голос района", "Крокодилов человек",
            "Пацан который всегда тут", "Отморозок с стажем"
        ]
        for role in ex_roles:
            c.execute("INSERT INTO exclusive_roles (name) VALUES (?)", (role,))
    
    # Добавляем админа в модераторы
    c.execute("INSERT OR IGNORE INTO moders (user_id) VALUES (?)", (ADMIN_ID,))
    
    conn.commit()
    conn.close()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def is_moder(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT * FROM moders WHERE user_id = ?", (user_id,))
    result = c.fetchone() is not None
    conn.close()
    return result

def get_random_fact():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT text FROM facts ORDER BY RANDOM() LIMIT 1")
    result = c.fetchone()
    conn.close()
    return result[0] if result else "Фактов пока нет"

def get_random_bar():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT text FROM bars ORDER BY RANDOM() LIMIT 1")
    result = c.fetchone()
    conn.close()
    return result[0] if result else "Строк пока нет"

def get_random_role():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT name FROM roles ORDER BY RANDOM() LIMIT 1")
    result = c.fetchone()
    conn.close()
    return result[0] if result else "рэпер"

def get_user_role(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def update_user_role(user_id, username, role):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''INSERT INTO users (user_id, username, role, last_role_change)
                 VALUES (?, ?, ?, ?)
                 ON CONFLICT(user_id) DO UPDATE SET
                 role = excluded.role, last_role_change = excluded.last_role_change''',
              (user_id, username, role, datetime.now()))
    conn.commit()
    conn.close()

def update_user_stats(user_id, username, text):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    
    # Проверяем, есть ли пользователь
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if c.fetchone():
        c.execute("UPDATE users SET messages = messages + 1 WHERE user_id = ?", (user_id,))
    else:
        c.execute("INSERT INTO users (user_id, username, messages) VALUES (?, ?, 1)", (user_id, username))
    
    conn.commit()
    conn.close()

def get_username_by_id(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else "unknown"

def get_user_id_by_username(username):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_violations_today(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    today = datetime.now().date()
    c.execute("SELECT COUNT(*) FROM violations WHERE user_id = ? AND date(date) = date(?)",
              (user_id, today))
    result = c.fetchone()[0]
    conn.close()
    return result

def parse_duration(duration_str):
    if duration_str.endswith('м'):
        return int(duration_str[:-1]) * 60
    elif duration_str.endswith('ч'):
        return int(duration_str[:-1]) * 3600
    elif duration_str.endswith('д'):
        return int(duration_str[:-1]) * 86400
    return None

# ==================== КОМАНДЫ ДЛЯ ВСЕХ ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎤 Отморозок — районный реп-бот\n\n"
        "Я живу в чате crocodiller и помогаю держать район.\n"
        "Напиши !команды, чтобы узнать, что я умею."
    )

async def commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Доступные команды:\n\n"
        "🎤 !бар — строка из треков\n"
        "🔥 !дисс @ник (или ответом) — задиссить\n"
        "🎭 !кто я — узнать/сменить роль\n"
        "👀 !кто @ник — посмотреть роль другого\n"
        "💀 !факт — факт про crocodiller\n"
        "📊 !стата @ник — статистика\n"
        "⚠️ !репорт (ответом) — жалоба модеру\n"
        "🚨 !sos — вызвать модера\n"
        "📋 !команды — этот список\n\n"
        "В личке у бота: !моя стата, !топ диссеров, !топ ролей, !трек дня"
    )
    await update.message.reply_text(text)

async def bar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🎤 {get_random_bar()}")

async def fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💀 {get_random_fact()}")

async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    current_role = get_user_role(user.id)
    
    # Проверяем, можно ли сменить роль (раз в сутки)
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT last_role_change FROM users WHERE user_id = ?", (user.id,))
    result = c.fetchone()
    conn.close()
    
    can_change = True
    if result and result[0]:
        last_change = datetime.fromisoformat(result[0])
        if datetime.now() - last_change < timedelta(days=1):
            can_change = False
    
    if not current_role or can_change:
        new_role = get_random_role()
        update_user_role(user.id, user.username or "anonymous", new_role)
        await update.message.reply_text(f"🎭 Ты теперь *{new_role}*", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"🎭 Твоя роль: *{current_role}*\nСменить можно раз в сутки", parse_mode='Markdown')

async def whois(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Укажи ник: !кто @ник")
        return
    
    target = context.args[0].replace('@', '')
    role = get_user_role(target)
    if role:
        await update.message.reply_text(f"👤 @{target} — *{role}*", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ Пользователь @{target} не найден")

async def diss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    author = user.username or "anonymous"
    
    # Определяем цель
    target = None
    if update.message.reply_to_message:
        # Ответ на сообщение
        target_user = update.message.reply_to_message.from_user
        target = target_user.username or "пользователь"
    elif context.args:
        target = context.args[0].replace('@', '')
    else:
        await update.message.reply_text("❌ Укажи, кого диссить: !дисс @ник или ответь на сообщение")
        return
    
    # Шаблоны диссов
    templates = [
        [f'Эй, @{target}, ты как старый бит — уже не в моде',
         'Твой флоу слабее, чем компот в компоте',
         'Я читаю так, что тают даже льды',
         'А ты позоришь микрофон из срамоты'],
        [f'Слыш, @{target}, ты похож на трек без баса',
         'Пустой внутри, как карманы у маса',
         'Твой рэп — вода, но даже не "минералка"',
         'Съеби со сцены, пока не дали тапка']
    ]
    
    t = random.choice(templates)
    diss_text = t[0] + '\n' + t[1] + '\n' + t[2] + '\n' + t[3] + f'\n\nтебя задиссил @{author}'
    await update.message.reply_text(diss_text)
    
    # Обновляем статистику диссов
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("UPDATE users SET diss_given = diss_given + 1 WHERE user_id = ?", (user.id,))
    if target_user := get_user_id_by_username(target):
        c.execute("UPDATE users SET diss_got = diss_got + 1 WHERE user_id = ?", (target_user,))
    conn.commit()
    conn.close()

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Укажи ник: !стата @ник")
        return
    
    target = context.args[0].replace('@', '')
    
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''SELECT messages, role, fav_word, diss_got, diss_given 
                 FROM users WHERE username = ?''', (target,))
    result = c.fetchone()
    conn.close()
    
    if result:
        msg = f"📊 Стата @{target}:\n"
        msg += f"Сообщений: {result[0] or 0}\n"
        msg += f"Роль: {result[1] or 'нет'}\n"
        msg += f"Любимое слово: {result[2] or '—'}\n"
        msg += f"Получил диссов: {result[3] or 0}\n"
        msg += f"Задиссил сам: {result[4] or 0}"
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text(f"❌ Пользователь @{target} не найден")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответь на сообщение командой !репорт")
        return
    
    offender = update.message.reply_to_message.from_user
    reported_text = update.message.reply_to_message.text or "сообщение без текста"
    
    # Сохраняем жалобу
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''INSERT INTO reports (from_id, on_id, message, time, status)
                 VALUES (?, ?, ?, ?, ?)''',
              (user.id, offender.id, reported_text, datetime.now(), 'новый'))
    conn.commit()
    conn.close()
    
    await update.message.reply_text("⚠️ Жалоба отправлена модерам")
    
    # Уведомляем модерам
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM moders")
    moders = c.fetchall()
    conn.close()
    
    for moder in moders:
        try:
            await context.bot.send_message(
                moder[0],
                f"📬 Новая жалоба от @{user.username or 'unknown'} на @{offender.username or 'unknown'}"
            )
        except:
            pass

async def sos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Уведомляем модерам
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM moders")
    moders = c.fetchall()
    conn.close()
    
    for moder in moders:
        try:
            await context.bot.send_message(
                moder[0],
                f"🚨 SOS в чате от @{user.username or 'unknown'}! Срочно нужен модер"
            )
        except:
            pass
    
    await update.message.reply_text("🚨 Модерам отправлен сигнал тревоги")

# ==================== МОДЕРАТОРСКИЕ КОМАНДЫ ====================

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_moder(update.effective_user.id):
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("❌ Формат: мут @ник 10м причина")
        return
    
    target = context.args[0].replace('@', '')
    duration_str = context.args[1]
    reason = ' '.join(context.args[2:]) if len(context.args) > 2 else 'без причины'
    
    target_id = get_user_id_by_username(target)
    if not target_id:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    seconds = parse_duration(duration_str)
    if not seconds:
        await update.message.reply_text("❌ Неверный формат времени. Пример: 10м, 1ч, 1д")
        return
    
    until = int(datetime.now().timestamp()) + seconds
    
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target_id,
            until_date=until,
            permissions={'can_send_messages': False}
        )
        
        await update.message.reply_text(
            f"⏳ @{target} замучен модером @{update.effective_user.username} "
            f"на {duration_str} за {reason}"
        )
        
        # Логируем
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute('''INSERT INTO violations (user_id, date, type, reason)
                     VALUES (?, ?, ?, ?)''',
                  (target_id, datetime.now(), 'мут', reason))
        conn.commit()
        conn.close()
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_moder(update.effective_user.id):
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("❌ Формат: пред @ник причина")
        return
    
    target = context.args[0].replace('@', '')
    reason = ' '.join(context.args[1:])
    
    target_id = get_user_id_by_username(target)
    if not target_id:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    # Добавляем предупреждение
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''INSERT INTO violations (user_id, date, type, reason)
                 VALUES (?, ?, ?, ?)''',
              (target_id, datetime.now(), 'пред', reason))
    conn.commit()
    
    # Считаем предупреждения за сегодня
    violations = get_violations_today(target_id)
    conn.close()
    
    await update.message.reply_text(
        f"⚠️ @{target}, предупреждение: {reason} ({violations}/3)"
    )
    
    # Если 3 предупреждения - автомут
    if violations >= 3:
        await mute(update, context)

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_moder(update.effective_user.id):
        return
    
    if not context.args:
        await update.message.reply_text("❌ Формат: снять @ник")
        return
    
    target = context.args[0].replace('@', '')
    target_id = get_user_id_by_username(target)
    
    if not target_id:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target_id,
            permissions={
                'can_send_messages': True,
                'can_send_media_messages': True,
                'can_send_polls': True,
                'can_send_other_messages': True,
                'can_add_web_page_previews': True,
                'can_change_info': True,
                'can_invite_users': True,
                'can_pin_messages': True
            }
        )
        await update.message.reply_text(f"✅ @{target} размучен")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_moder(update.effective_user.id):
        return
    
    if not context.args:
        await update.message.reply_text("❌ Формат: бан @ник причина")
        return
    
    target = context.args[0].replace('@', '')
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else 'без причины'
    target_id = get_user_id_by_username(target)
    
    if not target_id:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    try:
        await context.bot.ban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target_id
        )
        await update.message.reply_text(f"💔 @{target} забанен. Причина: {reason}")
        
        # Логируем
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute('''INSERT INTO violations (user_id, date, type, reason)
                     VALUES (?, ?, ?, ?)''',
                  (target_id, datetime.now(), 'бан', reason))
        conn.commit()
        conn.close()
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_moder(update.effective_user.id):
        return
    
    if not context.args:
        await update.message.reply_text("❌ Формат: разбан @ник")
        return
    
    target = context.args[0].replace('@', '')
    target_id = get_user_id_by_username(target)
    
    if not target_id:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    try:
        await context.bot.unban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target_id,
            only_if_banned=True
        )
        await update.message.reply_text(f"✅ @{target} разбанен")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

# ==================== ЛИЧНЫЕ СООБЩЕНИЯ ====================

async def private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        return
    
    user = update.effective_user
    text = update.message.text
    
    if is_moder(user.id):
        # Модераторское меню
        if text == 'нарушители':
            conn = sqlite3.connect('bot.db')
            c = conn.cursor()
            today = datetime.now().date()
            c.execute('''SELECT user_id, COUNT(*) FROM violations 
                         WHERE date(date) = date(?) 
                         GROUP BY user_id HAVING COUNT(*) >= 3
                         ORDER BY COUNT(*) DESC''', (today,))
            violators = c.fetchall()
            conn.close()
            
            if not violators:
                await update.message.reply_text("✅ Сегодня нет нарушителей с 3+ нарушениями")
                return
            
            msg = "🚨 СПИСОК НАРУШИТЕЛЕЙ (от большего к меньшему):\n"
            for v in violators:
                username = get_username_by_id(v[0]) or 'unknown'
                msg += f"@{username} — {v[1]} нарушений\n"
            await update.message.reply_text(msg)
            
        elif text == 'жалобы':
            conn = sqlite3.connect('bot.db')
            c = conn.cursor()
            c.execute("SELECT from_id, on_id, message, time FROM reports WHERE status = 'новый'")
            reports = c.fetchall()
            conn.close()
            
            if not reports:
                await update.message.reply_text("📬 Новых жалоб нет")
                return
            
            msg = "📬 НОВЫЕ ЖАЛОБЫ:\n\n"
            for i, r in enumerate(reports, 1):
                from_name = get_username_by_id(r[0]) or 'unknown'
                on_name = get_username_by_id(r[1]) or 'unknown'
                msg += f"{i}. @{from_name} на @{on_name}\n"
                msg += f'   "{r[2]}"\n'
                msg += f'   {r[3]}\n\n'
            await update.message.reply_text(msg)
            
        elif text == 'стата модеров':
            conn = sqlite3.connect('bot.db')
            c = conn.cursor()
            week_ago = datetime.now() - timedelta(days=7)
            c.execute('''SELECT moderator_id, COUNT(*) FROM logs 
                         WHERE date >= ? 
                         GROUP BY moderator_id
                         ORDER BY COUNT(*) DESC''', (week_ago,))
            stats = c.fetchall()
            conn.close()
            
            msg = "📊 Рейтинг модеров за неделю:\n"
            for i, s in enumerate(stats, 1):
                name = get_username_by_id(s[0]) or 'unknown'
                msg += f"{i}. @{name} — {s[1]} действий\n"
            await update.message.reply_text(msg)
            
        elif text == 'броуки':
            await update.message.reply_text("🔑 Введи пароль для доступа к управлению модерами:")
            
        elif text == ADMIN_PASSWORD:
            await update.message.reply_text(
                "👥 УПРАВЛЕНИЕ МОДЕРАМИ\n\n"
                "добавить @ник\n"
                "удалить @ник\n"
                "список"
            )
            
        elif text.startswith('добавить '):
            target = text[9:].replace('@', '')
            target_id = get_user_id_by_username(target)
            if target_id:
                conn = sqlite3.connect('bot.db')
                c = conn.cursor()
                c.execute("INSERT OR IGNORE INTO moders (user_id) VALUES (?)", (target_id,))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"✅ Модератор @{target} добавлен")
            else:
                await update.message.reply_text("❌ Пользователь не найден")
                
        elif text.startswith('удалить '):
            target = text[8:].replace('@', '')
            target_id = get_user_id_by_username(target)
            if target_id:
                conn = sqlite3.connect('bot.db')
                c = conn.cursor()
                c.execute("DELETE FROM moders WHERE user_id = ?", (target_id,))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"✅ Модератор @{target} удален")
            else:
                await update.message.reply_text("❌ Пользователь не найден")
                
        elif text == 'список':
            conn = sqlite3.connect('bot.db')
            c = conn.cursor()
            c.execute("SELECT user_id FROM moders")
            moders = c.fetchall()
            conn.close()
            
            msg = "👥 Список модеров:\n"
            for m in moders:
                name = get_username_by_id(m[0]) or 'unknown'
                msg += f"@{name}\n"
            await update.message.reply_text(msg)
            
        else:
            # Главное меню модера
            menu = (
                "🔐 Панель модератора @otmorozok_bot\n\n"
                "📋 нарушители — список нарушителей (3+)\n"
                "📬 жалобы — новые жалобы\n"
                "📊 стата модеров — рейтинг за неделю\n"
                "👥 броуки — управление модерами (пароль)\n"
                "👮‍♂️ замечание — сделать публичное замечание\n"
                "🎭 роли — управление ролями"
            )
            await update.message.reply_text(menu)
            
    else:
        # Обычный пользователь
        if text == '!моя стата':
            await stats(update, context)
        elif text == '!топ диссеров':
            await update.message.reply_text("🔥 Топ диссеров пока в разработке")
        elif text == '!топ ролей':
            await update.message.reply_text("👑 Топ ролей пока в разработке")
        elif text == '!трек дня':
            await update.message.reply_text(f"🎤 {get_random_bar()}\n\n💀 {get_random_fact()}")
        else:
            await update.message.reply_text(
                "🎤 Отморозок — районный реп-бот\n\n"
                "🔥 !моя стата — твоя статистика\n"
                "🎭 !моя роль — твоя текущая роль\n"
                "📊 !топ диссеров — кто чаще всех шутит\n"
                "👑 !топ ролей — какие роли сейчас в чате\n"
                "🎵 !трек дня — факт + строка из трека"
            )

# ==================== ОБРАБОТКА СООБЩЕНИЙ ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    user = update.effective_user
    text = update.message.text
    
    # Обновляем статистику
    update_user_stats(user.id, user.username or "anonymous", text)
    
    # Проверяем нарушения (если не модератор)
    if not is_moder(user.id) and update.effective_chat.type != 'private':
        stop_words = ['редиска', 'чмо', 'лох', 'петух']
        for word in stop_words:
            if word in text.lower():
                conn = sqlite3.connect('bot.db')
                c = conn.cursor()
                c.execute('''INSERT INTO violations (user_id, date, type, reason)
                             VALUES (?, ?, ?, ?)''',
                          (user.id, datetime.now(), 'мат', word))
                conn.commit()
                conn.close()
                break

# ==================== ЗАПУСК БОТА ====================

def main():
    # Инициализируем базу данных
    init_db()
    init_data()
    
    # Создаем приложение
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Команды для всех
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("бар", bar))
    app.add_handler(CommandHandler("факт", fact))
    app.add_handler(CommandHandler("кто", whoami))
    app.add_handler(CommandHandler("кто", whois))
    app.add_handler(CommandHandler("дисс", diss))
    app.add_handler(CommandHandler("стата", stats))
    app.add_handler(CommandHandler("репорт", report))
    app.add_handler(CommandHandler("sos", sos))
    app.add_handler(CommandHandler("команды", commands))
    
    # Модераторские команды
    app.add_handler(CommandHandler("мут", mute))
    app.add_handler(CommandHandler("пред", warn))
    app.add_handler(CommandHandler("снять", unmute))
    app.add_handler(CommandHandler("бан", ban))
    app.add_handler(CommandHandler("разбан", unban))
    
    # Обработчик личных сообщений
    app.add_handler(MessageHandler(filters.TEXT & filters.PRIVATE, private_message))
    
    # Обработчик обычных сообщений (для статистики и нарушений)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
