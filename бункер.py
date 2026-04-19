import asyncio
import logging
import random
import os
from typing import Dict, List, Optional
from enum import Enum, auto
from threading import Thread

from flask import Flask
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
    BotCommandScopeDefault,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ==================== НАСТРОЙКИ ====================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN", "8787610581:AAEloUd94AScmkVN0G7iLDfLXnzxaFvZDOk")

# ==================== FLASK ДЛЯ RENDER ====================
app = Flask(__name__)


@app.route('/')
def home():
    return "Bot is running!"


def run_web():
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000)))


# ==================== КАРТЫ ====================
PROFESSIONS = [
    "Врач", "Инженер", "Повар", "Психолог", "Химик", "Строитель", "Биолог", "Военный",
    "Пилот", "Учитель", "Фермер", "Электрик", "Механик", "Программист", "Журналист",
    "Пожарный", "Полицейский", "Адвокат", "Бухгалтер", "Архитектор", "Геолог", "Эколог",
    "Ветеринар", "Фармацевт", "Музыкант", "Художник", "Сварщик", "Сантехник", "Священник"
]

BIOLOGY = [
    "Мужчина, 25 лет", "Женщина, 30 лет", "Мужчина, 45 лет", "Женщина, 22 года",
    "Мужчина, 60 лет", "Женщина, 35 лет", "Мужчина, 18 лет", "Женщина, 50 лет",
    "Мужчина, 33 года", "Женщина, 28 лет", "Мужчина, 41 год", "Женщина, 19 лет"
]

HEALTH = [
    "Абсолютно здоров", "Астма", "Близорукость", "Аллергия на пыльцу", "Старый перелом ноги",
    "Диабет (компенсированный)", "Гипертония", "Мигрень", "Плоскостопие", "Хронический гастрит",
    "Аллергия на антибиотики", "Бессонница", "Шрам на лице", "Одно лёгкое", "Кардиостимулятор"
]

HOBBIES = [
    "Охота", "Шахматы", "Садоводство", "Вязание", "Бокс", "Программирование",
    "Рыбалка", "Готовка", "Фотография", "Игра на гитаре", "Чтение", "Скалолазание",
    "Йога", "Коллекционирование марок", "Резьба по дереву", "Астрономия", "Бег"
]

PHOBIAS = [
    "Клаустрофобия", "Арахнофобия", "Агорафобия", "Нет фобий", "Боязнь темноты",
    "Акрофобия (высота)", "Социофобия", "Мизофобия (микробы)", "Танатофобия (смерть)"
]

BAGGAGE = [
    "Аптечка", "Консервы (10 банок)", "Топор", "Спички", "Веревка (20м)", "Семена овощей",
    "Радиоприёмник", "Фонарик", "Нож", "Спальный мешок", "Водяной фильтр", "Карта местности",
    "Набор инструментов", "Книга по выживанию", "Алкоголь", "Золотые украшения"
]

FACTS = [
    "Знает азбуку Морзе", "Выигрывал в лотерею", "Не умеет плавать", "Был скаутом",
    "Играет на гитаре", "Владеет боевыми искусствами", "Имеет права на управление катером",
    "Говорит на 3 языках", "Умеет водить грузовик", "Сдавал нормы ГТО", "Родился в бункере (шутка)",
    "Знает наизусть таблицу Менделеева", "Участвовал в раскопках", "В детстве жил в деревне"
]

SPECIAL_CONDITIONS = [
    "Может переголосовать один раз", "Иммунитет к первому голосованию",
    "Может подсмотреть карту другого игрока", "Может обменяться профессией с другим игроком",
    "Имеет дополнительный голос при голосовании", "Может скрыть одну свою карту до конца игры"
]

CATASTROPHES = [
    "Ядерная война", "Пандемия смертельного вируса", "Падение астероида",
    "Извержение супервулкана", "Восстание ИИ", "Инопланетное вторжение",
    "Глобальное потепление и потоп", "Зомби-апокалипсис", "Солнечная вспышка",
    "Кибератака на все системы"
]

THREATS = [
    "Радиация", "Заражённый воздух", "Дикие животные", "Мародёры",
    "Нехватка еды", "Психологическая нестабильность", "Болезни", "Техногенные аварии",
    "Экстремальный холод", "Отсутствие воды", "Каннибалы"
]

BUNKER_DESCRIPTIONS = [
    "Военный бункер с запасом оружия", "Гражданское убежище с библиотекой",
    "Научная лаборатория", "Подземная ферма", "Бункер-отель с бассейном",
    "Старый шахтный ствол", "Частный бункер миллионера", "Правительственный бункер",
    "Бункер-склад с консервами", "Недостроенное убежище"
]


# ==================== СОСТОЯНИЯ ====================
class PlayerState(Enum):
    WAITING = auto()
    CHOOSING_CARD = auto()
    VOTED = auto()


class GameState(Enum):
    LOBBY = auto()
    PLAYING = auto()
    VOTING = auto()
    FINISHED = auto()


# ==================== ХРАНИЛИЩЕ ====================
class GameStorage:
    def __init__(self) -> None:
        self.rooms: Dict[str, 'GameRoom'] = {}

    def create_room(self, chat_id: int) -> 'GameRoom':
        room = GameRoom(chat_id)
        self.rooms[str(chat_id)] = room
        return room

    def get_room(self, chat_id: int) -> Optional['GameRoom']:
        return self.rooms.get(str(chat_id))

    def delete_room(self, chat_id: int) -> None:
        if str(chat_id) in self.rooms:
            del self.rooms[str(chat_id)]


storage = GameStorage()


# ==================== МОДЕЛЬ ИГРОКА ====================
class Player:
    def __init__(self, user_id: int, name: str) -> None:
        self.user_id = user_id
        self.name = name
        self.cards = self._generate_cards()
        self.revealed_cards: List[str] = []
        self.is_alive = True
        self.votes_against = 0
        self.state = PlayerState.WAITING

    @staticmethod
    def _generate_cards() -> Dict[str, str]:
        return {
            "Профессия": random.choice(PROFESSIONS),
            "Биология": random.choice(BIOLOGY),
            "Здоровье": random.choice(HEALTH),
            "Хобби": random.choice(HOBBIES),
            "Фобия": random.choice(PHOBIAS),
            "Багаж": random.choice(BAGGAGE),
            "Факт": random.choice(FACTS),
            "Особое условие": random.choice(SPECIAL_CONDITIONS),
        }

    def get_private_info(self) -> str:
        text = "*Ваш персонаж:*\n"
        for cat, val in self.cards.items():
            text += f"*{cat}*: {val}\n"
        return text

    def get_public_info(self) -> str:
        text = f"*{self.name}*\n"
        for card in self.revealed_cards:
            text += f"  {card}\n"
        return text

    def get_unrevealed_cards(self) -> Dict[str, str]:
        revealed_cats = {c.split(':')[0] for c in self.revealed_cards}
        return {cat: val for cat, val in self.cards.items() if cat not in revealed_cats}


# ==================== МОДЕЛЬ КОМНАТЫ ====================
class GameRoom:
    def __init__(self, chat_id: int) -> None:
        self.chat_id = chat_id
        self.players: Dict[int, Player] = {}
        self.state = GameState.LOBBY
        self.current_round = 0
        self.current_player_index = 0
        self.player_order: List[int] = []
        self.bunker_size = 0
        self.host_id: int = 0
        self.catastrophe: str = random.choice(CATASTROPHES)
        self.threat: str = random.choice(THREATS)
        self.bunker_desc: str = random.choice(BUNKER_DESCRIPTIONS)
        self.timer_job = None

    def add_player(self, user_id: int, name: str) -> bool:
        if user_id in self.players:
            return False
        if not self.players:
            self.host_id = user_id
        self.players[user_id] = Player(user_id, name)
        return True

    def start_game(self) -> bool:
        if len(self.players) < 3:
            return False
        self.state = GameState.PLAYING
        self.player_order = list(self.players.keys())
        random.shuffle(self.player_order)
        self.bunker_size = max(1, len(self.players) // 2)
        self.current_round = 1
        return True

    def next_turn(self) -> Optional[Player]:
        alive_players = [p for p in self.players.values() if p.is_alive]
        if len(alive_players) <= self.bunker_size:
            self.state = GameState.FINISHED
            return None

        while self.current_player_index < len(self.player_order):
            next_id = self.player_order[self.current_player_index]
            player = self.players.get(next_id)
            if player and player.is_alive:
                player.state = PlayerState.CHOOSING_CARD
                return player
            self.current_player_index += 1

        self.state = GameState.VOTING
        return None

    def process_vote(self, voter_id: int, target_id: int) -> bool:
        if target_id not in self.players:
            return False
        voter = self.players.get(voter_id)
        if not voter or voter.state == PlayerState.VOTED:
            return False

        self.players[target_id].votes_against += 1
        voter.state = PlayerState.VOTED
        return True

    def apply_voting_results(self) -> Optional[Player]:
        alive_players = [p for p in self.players.values() if p.is_alive]
        if not alive_players:
            return None

        max_votes = max(p.votes_against for p in alive_players)
        candidates = [p for p in alive_players if p.votes_against == max_votes]
        eliminated = random.choice(candidates) if candidates else None

        for player in self.players.values():
            if player.is_alive:
                player.votes_against = 0
                player.state = PlayerState.WAITING

        if eliminated:
            eliminated.is_alive = False
            self.current_player_index = 0
            self.current_round += 1
            self.state = GameState.PLAYING
        return eliminated

    def all_voted(self) -> bool:
        return all(p.state == PlayerState.VOTED for p in self.players.values() if p.is_alive)

    async def broadcast(self, context: ContextTypes.DEFAULT_TYPE, text: str, **kwargs) -> None:
        for player in self.players.values():
            try:
                await context.bot.send_message(chat_id=player.user_id, text=text, **kwargs)
            except TelegramError:
                pass


# ==================== МЕНЮ И КНОПКИ ====================
def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру с большими кнопками."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🎲 Создать игру")],
            [KeyboardButton("✅ Присоединиться")],
            [KeyboardButton("▶️ Начать игру")],
            [KeyboardButton("📜 Правила")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )


async def set_menu(application: Application):
    """Устанавливает меню команд в интерфейсе бота."""
    commands = [
        BotCommand("start", "🚀 Главное меню"),
        BotCommand("create", "🎲 Создать игру"),
        BotCommand("join", "✅ Присоединиться"),
        BotCommand("begin", "▶️ Начать игру"),
        BotCommand("rules", "📜 Правила"),
    ]
    await application.bot.set_my_commands(commands, scope=BotCommandScopeDefault())


# ==================== ОБРАБОТЧИКИ КОМАНД ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start с большими кнопками."""
    keyboard = get_main_keyboard()
    await update.message.reply_text(
        "🎮 *Добро пожаловать в игру 'Бункер'!*\n\n"
        "Соберите компанию от 3 человек и докажите свою полезность, чтобы попасть в бункер!\n\n"
        "Выберите действие на клавиатуре:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def create_room(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.effective_user or not update.message:
        return
    chat_id = update.effective_chat.id
    user = update.effective_user
    if storage.get_room(chat_id):
        await update.message.reply_text("❌ Здесь уже есть активная игра!")
        return
    room = storage.create_room(chat_id)
    room.add_player(user.id, user.first_name)
    await update.message.reply_text(
        f"🎲 *Комната создана!*\n"
        f"👑 Ведущий: {user.first_name}\n"
        f"Игроки могут присоединиться через кнопку «Присоединиться»",
        parse_mode="Markdown"
    )


async def join_room(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.effective_user or not update.message:
        return
    chat_id = update.effective_chat.id
    user = update.effective_user
    room = storage.get_room(chat_id)
    if not room:
        await update.message.reply_text("❌ Нет активной игры. Создайте новую!")
        return
    if room.state != GameState.LOBBY:
        await update.message.reply_text("❌ Игра уже идёт.")
        return
    if room.add_player(user.id, user.first_name):
        await update.message.reply_text(f"✅ {user.first_name} в игре! Игроков: {len(room.players)}")
    else:
        await update.message.reply_text("❌ Вы уже в игре.")


async def begin_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.effective_user or not update.message:
        return
    chat_id = update.effective_chat.id
    user = update.effective_user
    room = storage.get_room(chat_id)
    if not room:
        await update.message.reply_text("❌ Сначала создайте игру.")
        return
    if room.host_id != user.id:
        await update.message.reply_text("❌ Только создатель может начать.")
        return
    if not room.start_game():
        await update.message.reply_text("❌ Минимум 3 игрока.")
        return

    intro = (
        f"⚠️ *КАТАСТРОФА:* {room.catastrophe}\n"
        f"⚠️ *ОСНОВНАЯ УГРОЗА:* {room.threat}\n"
        f"🏠 *БУНКЕР:* {room.bunker_desc}\n\n"
        f"🪑 Мест в бункере: *{room.bunker_size}*\n"
        "Докажите свою полезность!"
    )
    await update.message.reply_text(intro, parse_mode="Markdown")

    for player in room.players.values():
        try:
            await context.bot.send_message(
                chat_id=player.user_id,
                text=player.get_private_info(),
                parse_mode="Markdown"
            )
        except TelegramError as e:
            logger.warning(f"Не отправили карты {player.name}: {e}")

    await start_next_turn(context, room)


async def start_next_turn(context: ContextTypes.DEFAULT_TYPE, room: GameRoom) -> None:
    if room.timer_job:
        room.timer_job.schedule_removal()
    next_player = room.next_turn()

    if room.state == GameState.FINISHED:
        winners = [p.name for p in room.players.values() if p.is_alive]
        await room.broadcast(
            context,
            f"🏆 *ВЫЖИВШИЕ:* {', '.join(winners)}\nОни попадают в бункер!",
            parse_mode="Markdown"
        )
        storage.delete_room(room.chat_id)
        return

    if room.state == GameState.VOTING:
        await start_voting(context, room)
        return

    if next_player:
        unrevealed = next_player.get_unrevealed_cards()
        if not unrevealed:
            room.current_player_index += 1
            await start_next_turn(context, room)
            return

        text = "🎴 *Ваши нераскрытые карты:*\n"
        for cat, val in unrevealed.items():
            text += f"• {cat}: {val}\n"
        text += "\nВыберите, что раскрыть:"

        keyboard = []
        for cat in unrevealed.keys():
            keyboard.append([InlineKeyboardButton(cat, callback_data=f"reveal_{cat}")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            msg = await context.bot.send_message(
                chat_id=next_player.user_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        except TelegramError:
            await room.broadcast(context, f"⚠️ {next_player.name} не может получить кнопки.")
            room.current_player_index += 1
            await start_next_turn(context, room)
            return

        context.job_queue.run_once(
            lambda ctx: asyncio.create_task(timeout_turn(ctx, room.chat_id, next_player.user_id, msg.message_id)),
            when=30,
            chat_id=room.chat_id,
            user_id=next_player.user_id,
            name=f"turn_timeout_{room.chat_id}"
        )


async def timeout_turn(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int, msg_id: int) -> None:
    room = storage.get_room(chat_id)
    if not room or room.state != GameState.PLAYING:
        return
    player = room.players.get(user_id)
    if player and player.state == PlayerState.CHOOSING_CARD:
        unrevealed = player.get_unrevealed_cards()
        if unrevealed:
            cat = random.choice(list(unrevealed.keys()))
            val = player.cards[cat]
            player.revealed_cards.append(f"{cat}: {val}")
            await context.bot.edit_message_text(
                chat_id=user_id, message_id=msg_id,
                text=f"⏰ Время вышло! Раскрыта карта:\n*{cat}*: {val}",
                parse_mode="Markdown"
            )
            await room.broadcast(
                context,
                f"🃏 {player.name} (по таймауту) раскрывает: *{cat}*: {val}",
                parse_mode="Markdown"
            )
    room.current_player_index += 1
    await start_next_turn(context, room)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.message:
        return
    await query.answer()
    data = query.data
    user = query.from_user

    if data == "show_rules":
        text = (
            "*Правила игры 'Бункер':*\n"
            "• Каждый получает скрытые характеристики.\n"
            "• В каждом раунде игроки раскрывают одну карту.\n"
            "• После круга — голосование за исключение.\n"
            "• Цель: попасть в число выживших."
        )
        await query.edit_message_text(text, parse_mode="Markdown")
        return

    chat = query.message.chat
    if not hasattr(chat, 'id'):
        return
    chat_id = chat.id

    room = storage.get_room(chat_id)
    if not room or room.state != GameState.PLAYING:
        await query.edit_message_text("❌ Игра не активна.")
        return

    if room.current_player_index >= len(room.player_order):
        return
    current_player = room.players.get(room.player_order[room.current_player_index])
    if not current_player or current_player.user_id != user.id:
        await query.answer("Не ваш ход!", show_alert=True)
        return

    if data and data.startswith("reveal_"):
        cat = data.replace("reveal_", "")
        if cat in current_player.cards and cat not in [c.split(':')[0] for c in current_player.revealed_cards]:
            val = current_player.cards[cat]
            current_player.revealed_cards.append(f"{cat}: {val}")
            await query.edit_message_text(
                f"✅ Вы раскрыли: *{cat}*: {val}",
                parse_mode="Markdown"
            )
            await room.broadcast(
                context,
                f"🃏 *{current_player.name}* раскрывает: *{cat}*: {val}",
                parse_mode="Markdown"
            )
            if room.timer_job:
                room.timer_job.schedule_removal()
            room.current_player_index += 1
            await start_next_turn(context, room)


async def start_voting(context: ContextTypes.DEFAULT_TYPE, room: GameRoom) -> None:
    alive = [p for p in room.players.values() if p.is_alive]
    if len(alive) <= room.bunker_size:
        room.state = GameState.FINISHED
        await start_next_turn(context, room)
        return

    summary = "*📊 Итоги раунда:*\n\n"
    for p in alive:
        summary += p.get_public_info() + "\n"
    await room.broadcast(context, summary, parse_mode="Markdown")

    for voter in alive:
        keyboard = []
        for candidate in alive:
            keyboard.append([InlineKeyboardButton(
                f"❌ {candidate.name}",
                callback_data=f"vote_{candidate.user_id}"
            )])
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            msg = await context.bot.send_message(
                chat_id=voter.user_id,
                text="🗳 *ГОЛОСОВАНИЕ* — выберите, кого исключить:",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            context.job_queue.run_once(
                lambda ctx, v_id=voter.user_id, m_id=msg.message_id: asyncio.create_task(
                    timeout_vote(ctx, room.chat_id, v_id, m_id)
                ),
                when=45,
                chat_id=room.chat_id,
                user_id=voter.user_id
            )
        except TelegramError:
            pass


async def timeout_vote(context: ContextTypes.DEFAULT_TYPE, chat_id: int, voter_id: int, msg_id: int) -> None:
    room = storage.get_room(chat_id)
    if not room or room.state != GameState.VOTING:
        return
    voter = room.players.get(voter_id)
    if voter and voter.state != PlayerState.VOTED:
        alive = [p for p in room.players.values() if p.is_alive and p.user_id != voter_id]
        if alive:
            target = random.choice(alive)
            room.process_vote(voter_id, target.user_id)
            try:
                await context.bot.edit_message_text(
                    chat_id=voter_id, message_id=msg_id,
                    text=f"⏰ Время вышло! Случайный голос против {target.name}"
                )
            except TelegramError:
                pass
            await room.broadcast(context, f"ℹ️ {voter.name} не проголосовал вовремя.")
    if room.all_voted():
        await finish_voting(context, room)


async def vote_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.message:
        return
    await query.answer()
    data = query.data
    user = query.from_user

    chat = query.message.chat
    if not hasattr(chat, 'id'):
        return
    chat_id = chat.id

    room = storage.get_room(chat_id)
    if not room or room.state != GameState.VOTING:
        await query.edit_message_text("❌ Голосование окончено.")
        return
    if not data or not data.startswith("vote_"):
        return
    target_id = int(data.replace("vote_", ""))
    if room.process_vote(user.id, target_id):
        target_name = room.players[target_id].name
        await query.edit_message_text(f"✅ Вы проголосовали против {target_name}")
        if room.all_voted():
            await finish_voting(context, room)
    else:
        await query.answer("Вы уже голосовали!", show_alert=True)


async def finish_voting(context: ContextTypes.DEFAULT_TYPE, room: GameRoom) -> None:
    eliminated = room.apply_voting_results()
    if eliminated:
        await room.broadcast(
            context,
            f"💔 *{eliminated.name}* исключён! (голосов: {eliminated.votes_against})",
            parse_mode="Markdown"
        )
    else:
        await room.broadcast(context, "⚖️ Ничья — никто не выбывает.")
    await start_next_turn(context, room)


async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "*Правила игры 'Бункер':*\n"
        "• Каждый получает скрытые характеристики.\n"
        "• В каждом раунде игроки по очереди раскрывают одну карту.\n"
        "• После круга — голосование за исключение.\n"
        "• Цель: попасть в число выживших (мест вдвое меньше игроков)."
    )
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия на большие кнопки."""
    text = update.message.text

    if text == "🎲 Создать игру":
        await create_room(update, context)
    elif text == "✅ Присоединиться":
        await join_room(update, context)
    elif text == "▶️ Начать игру":
        await begin_game(update, context)
    elif text == "📜 Правила":
        await rules_command(update, context)


# ==================== ТОЧКА ВХОДА ====================
def main() -> None:
    """Запуск бота"""
    app_bot = Application.builder().token(TOKEN).build()

    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error(msg="Exception while handling an update:", exc_info=context.error)

    app_bot.add_error_handler(error_handler)

    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("create", create_room))
    app_bot.add_handler(CommandHandler("join", join_room))
    app_bot.add_handler(CommandHandler("begin", begin_game))
    app_bot.add_handler(CommandHandler("rules", rules_command))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app_bot.add_handler(CallbackQueryHandler(button_handler, pattern="^(reveal_|show_rules)"))
    app_bot.add_handler(CallbackQueryHandler(vote_handler, pattern="^vote_"))

    if app_bot.job_queue:
        app_bot.job_queue.run_once(lambda ctx: asyncio.create_task(set_menu(app_bot)), when=0)
    else:
        asyncio.create_task(set_menu(app_bot))

    Thread(target=run_web, daemon=True).start()

    print("🤖 Бот запущен...")
    app_bot.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
