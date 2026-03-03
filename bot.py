import logging
import random
import sqlite3
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "8218602111:AAHESDbEsL0WuP1gbogSNGmnUt4JS5pejyc"          # замени на свой токен
ADMIN_ID = 1373730608                   # замени на свой ID
ADMIN_PASSWORD = "crocodebiller"
CHAT_ID = -1001234567890                # ID чата крокодилдос (заменишь позже)
# ===================================================

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- База данных ----------
def init_db():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, role TEXT, 
                  messages INTEGER DEFAULT 0, fav_word TEXT,
                  diss_got INTEGER DEFAULT 0, diss_given INTEGER DEFAULT 0,
                  last_role_change TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS violations
                 (user_id INTEGER, date TIMESTAMP, type TEXT, reason TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS moders
                 (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS reports
                 (from_id INTEGER, on_id INTEGER, message TEXT, time TIMESTAMP, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS facts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bars
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS roles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS exclusive_roles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)''')
    conn.commit()
    conn.close()

def init_data():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    # Факты
    c.execute("SELECT COUNT(*) FROM facts")
    if c.fetchone()[0] == 0:
        facts = [
            "В 9 лет сжёг школу. Говорит, самовозгорание",
            "Не пьёт, не курит, но торгует битами",
            "Первый трек записал на диктофон в маршрутке",
            "Спит в студии, потому что дома ждут кредиты",
            "Однажды уснул на бите и проснулся звездой"
        ]
        for f in facts:
            c.execute("INSERT INTO facts (text) VALUES (?)", (f,))
    # Строки для !бар
    c.execute("SELECT COUNT(*) FROM bars")
    if c.fetchone()[0] == 0:
        bars = [
            "Из сарая выхожу",
            "Федя на тракторе уже ихний мопед догоняет",
            "И вот я к огороду подхожу",
            "И слышу вопли из толчка: там городской утопает",
            "Рэпчик мужа нахваливать и подносить пиво, пока не спит"
        ]
        for b in bars:
            c.execute("INSERT INTO bars (text) VALUES (?)", (b,))
    # Роли
    c.execute("SELECT COUNT(*) FROM roles")
    if c.fetchone()[0] == 0:
        roles = [
            "барыга", "плаг", "закладчик", "кладовщик", "курьер",
            "оптовик", "фармацевт", "травник", "дилер", "провизор",
            "битмейкер", "звукореж", "фристайлер", "баттл-рэпер", "MC"
        ]
        for r in roles:
            c.execute("INSERT INTO roles (name) VALUES (?)", (r,))
    # Эксклюзивные роли
    c.execute("SELECT COUNT(*) FROM exclusive_roles")
    if c.fetchone()[0] == 0:
        ex_roles = [
            "Легенда чата", "Голос района", "Крокодилов человек",
            "Пацан который всегда тут", "Отморозок с стажем"
        ]
        for er in ex_roles:
            c.execute("INSERT INTO exclusive_roles (name) VALUES (?)", (er,))
    # Добавляем админа в модераторы
    c.execute("INSERT OR IGNORE INTO moders (user_id) VALUES (?)", (ADMIN_ID,))
    conn.commit()
    conn.close()

# ---------- Вспомогательные функции ----------
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

# ---------- Команды ----------
async def bar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🎤 {get_random_bar()}")

async def fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💀 {get_random_fact()}")

async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    current_role = get_user_role(user.id)
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

async def whois(update: Update, context: ContextTypes.DEFAULT_TYPE, target: str):
    target = target.replace('@', '')
    role = get_user_role(target)
    if role:
        await update.message.reply_text(f"👤 @{target} — *{role}*", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ Пользователь @{target} не найден")

async def diss(update: Update, context: ContextTypes.DEFAULT_TYPE, target: str = None):
    user = update.effective_user
    author = user.username or "anonymous"
    if target is None and update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        target = target_user.username or "пользователь"
    if not target:
        await update.message.reply_text("❌ Укажи, кого диссить: !дисс @ник или ответь на сообщение")
        return
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
    # Обновляем статистику
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("UPDATE users SET diss_given = diss_given + 1 WHERE user_id = ?", (user.id,))
    target_id = get_user_id_by_username(target)
    if target_id:
        c.execute("UPDATE users SET diss_got = diss_got + 1 WHERE user_id = ?", (target_id,))
    conn.commit()
    conn.close()

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE, target: str):
    target = target.replace('@', '')
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
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''INSERT INTO reports (from_id, on_id, message, time, status)
                 VALUES (?, ?, ?, ?, ?)''',
              (user.id, offender.id, reported_text, datetime.now(), 'новый'))
    conn.commit()
    conn.close()
    await update.message.reply_text("⚠️ Жалоба отправлена модерам")
    # Уведомление модерам
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

async def commands_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# ---------- Модераторские команды ----------
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not is_moder(update.effective_user.id):
        return
    if len(args) < 2:
        await update.message.reply_text("❌ Формат: мут @ник 10м причина")
        return
    target = args[0].replace('@', '')
    duration_str = args[1]
    reason = ' '.join(args[2:]) if len(args) > 2 else 'без причины'
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
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute('''INSERT INTO violations (user_id, date, type, reason)
                     VALUES (?, ?, ?, ?)''',
                  (target_id, datetime.now(), 'мут', reason))
        conn.commit()
        conn.close()
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not is_moder(update.effective_user.id):
        return
    if len(args) < 2:
        await update.message.reply_text("❌ Формат: пред @ник причина")
        return
    target = args[0].replace('@', '')
    reason = ' '.join(args[1:])
    target_id = get_user_id_by_username(target)
    if not target_id:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''INSERT INTO violations (user_id, date, type, reason)
                 VALUES (?, ?, ?, ?)''',
              (target_id, datetime.now(), 'пред', reason))
    conn.commit()
    violations = get_violations_today(target_id)
    conn.close()
    await update.message.reply_text(
        f"⚠️ @{target}, предупреждение: {reason} ({violations}/3)"
    )
    if violations >= 3:
        await mute(update, context, ['@'+target, '1ч', 'превышен лимит предупреждений'])

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not is_moder(update.effective_user.id):
        return
    if not args:
        await update.message.reply_text("❌ Формат: снять @ник")
        return
    target = args[0].replace('@', '')
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

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not is_moder(update.effective_user.id):
        return
    if not args:
        await update.message.reply_text("❌ Формат: бан @ник причина")
        return
    target = args[0].replace('@', '')
    reason = ' '.join(args[1:]) if len(args) > 1 else 'без причины'
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
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute('''INSERT INTO violations (user_id, date, type, reason)
                     VALUES (?, ?, ?, ?)''',
                  (target_id, datetime.now(), 'бан', reason))
        conn.commit()
        conn.close()
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not is_moder(update.effective_user.id):
        return
    if not args:
        await update.message.reply_text("❌ Формат: разбан @ник")
        return
    target = args[0].replace('@', '')
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

# ---------- Личные сообщения ----------
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
            c.execute('''SELECT user_id, COUNT(*) FROM violations 
                         WHERE date >= ? 
                         GROUP BY user_id
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
            await stats(update, context, '@' + (user.username or 'anonymous'))
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

# ---------- Основной обработчик сообщений в чате ----------
async def chat_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    if not update.message or not update.message.text:
        return
    user = update.effective_user
    text = update.message.text.strip()
    # Обновляем статистику
    update_user_stats(user.id, user.username or "anonymous", text)
    # Проверка нарушений (если не модератор)
    if not is_moder(user.id):
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
    # Обработка команд
    if text.startswith('!'):
        if text == '!бар':
            await bar(update, context)
        elif text == '!факт':
            await fact(update, context)
        elif text == '!кто я':
            await whoami(update, context)
        elif text.startswith('!кто '):
            target = text[5:].strip()
            await whois(update, context, target)
        elif text.startswith('!дисс'):
            parts = text.split()
            if len(parts) > 1:
                target = parts[1].replace('@', '')
                await diss(update, context, target)
            else:
                await diss(update, context)
        elif text.startswith('!стата '):
            target = text[7:].strip()
            await stats(update, context, target)
        elif text == '!репорт':
            await report(update, context)
        elif text == '!sos':
            await sos(update, context)
        elif text == '!команды':
            await commands_list(update, context)
        # Модераторские команды
        elif is_moder(user.id):
            if text.startswith('мут '):
                parts = text.split()
                await mute(update, context, parts[1:])
            elif text.startswith('пред '):
                parts = text.split()
                await warn(update, context, parts[1:])
            elif text.startswith('снять '):
                parts = text.split()
                await unmute(update, context, parts[1:])
            elif text.startswith('бан '):
                parts = text.split()
                await ban(update, context, parts[1:])
            elif text.startswith('разбан '):
                parts = text.split()
                await unban(update, context, parts[1:])

# ---------- Запуск ----------
def main():
    init_db()
    init_data()
    app = Application.builder().token(BOT_TOKEN).build()
    # Обработчик сообщений в чате
    app.add_handler(MessageHandler(filters.TEXT & ~filters.PRIVATE, chat_message_handler))
    # Обработчик личных сообщений
    app.add_handler(MessageHandler(filters.TEXT & filters.PRIVATE, private_message))
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
