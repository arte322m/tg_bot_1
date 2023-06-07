import logging

import requests

from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, \
    ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

URL_KINOKINO = 'http://192.168.0.150:9200/'
URL_USER = 'v1/user/'
URL_START = 'v1/start/'
URL_SEARCH_FILM = 'v1/search_film/'
URL_ADD_MOVIE = 'v1/add_movie_api/'
URL_PROFILE_STAT = 'v1/profile_statistics/'
URL_MOVIES = 'v1/user_movies/'
URL_INFO_MOVIES = 'v1/movie_info/'
URL_FAVORITE = 'v1/add_favorite/'
URL_CHANGE_STATUS = 'v1/change_status/'
URL_SEASONS_EPISODES = 'v1/seasons_episodes/'
URL_ADD_EPISODE = 'v1/add_episode/'

SEARCHING = range(1)
MOVIES = range(1)

PLANNED_TO_WATCH: str = 'Запланировано'
WATCHING: str = 'Смотрю'
COMPLETED: str = 'Просмотрено'

STATUSES: list = [PLANNED_TO_WATCH, WATCHING, COMPLETED]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    try:
        requests.get(URL_KINOKINO)
    except requests.ConnectionError:
        await update.message.reply_text('Включи сервер, лошара')
    json = {
        'username': f'{user.id}',
        'password': f'{user.id}',
    }
    response = requests.post(f'{URL_KINOKINO}{URL_START}',
                             json=json)

    reply_keyboard = [
        ['Поиск фильма'],
        ['Мои фильмы', 'Моя статистика']
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard)
    if response.status_code == 200:
        await update.message.reply_text('🫖', reply_markup=markup)
    if response.status_code == 201:
        await update.message.reply_text('Можно начинать (^˵◕ω◕˵^)', reply_markup=markup)


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [
        ['/skip']
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    await update.message.reply_text("Введите название... или если передумали /skip", reply_markup=markup)
    return SEARCHING


async def searching(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    search_text = update.message.text
    reply_keyboard = [
        ['Поиск фильма'],
        ['Мои фильмы', 'Моя статистика']
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard)
    await update.message.reply_text('Идёт поиск...', reply_markup=markup)
    params = {'name': search_text}
    searching_result = requests.get(f'{URL_KINOKINO}{URL_SEARCH_FILM}', params).json()
    if not searching_result:
        await update.message.reply_text('Нет фильмов с таким названием')
        return ConversationHandler.END
    result_message = 'Выберит фильм, который хотите добавить\n'

    reply_keyboard = []

    for i, movie in enumerate(searching_result):
        try:
            movie_years = movie['releaseYears']
            if movie_years:
                movie_years = movie_years[0]
                reply_keyboard.append(
                    [
                        InlineKeyboardButton(
                            f"{movie['name']} ({movie_years['start']}-{movie_years['end']})",
                            callback_data=f'search__{search_text}__{i}'
                        )
                    ]
                )
        except KeyError:
            reply_keyboard.append(
                [
                    InlineKeyboardButton(
                        f"{movie['name']} ({movie['year']})",
                        callback_data=f'search__{search_text}__{i}'
                    )
                ]
            )
    markup = InlineKeyboardMarkup(reply_keyboard)
    await update.message.reply_text(result_message, reply_markup=markup)

    return ConversationHandler.END


async def searching_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    searching_text = query.data
    if searching_text.startswith('search__'):
        searching_text_split = searching_text.split('__')
        found_name = searching_text_split[1]
        found_id = searching_text_split[2]
        params = {
            'number': found_id,
            'name': found_name,
            'username': query.from_user.id,
        }
        response = requests.post(
            url=f"{URL_KINOKINO}{URL_ADD_MOVIE}",
            params=params
        )
        await query.answer()
        if response.status_code == 200:
            await query.message.reply_text(f"Есть в списках")
        if response.status_code == 201:
            await query.message.reply_text(f"Добавлено")


async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [
        ['Поиск фильма'],
        ['Мои фильмы', 'Моя статистика']
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard)
    await update.message.reply_text('//', reply_markup=markup)

    return ConversationHandler.END


async def statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    response = requests.post(
        url=f"{URL_KINOKINO}{URL_PROFILE_STAT}",
        params={'username': user.id}
    )
    if response.status_code == 200:
        response_json = response.json()
        result_message = f"Статистика.\n" \
                         f"Всего: {response_json['all_count']}\n" \
                         f"Запланировано: {response_json['planned_count']}\n" \
                         f"Смотрю: {response_json['watching_count']}\n" \
                         f"Просмотрено: {response_json['completed_count']}\n"
        await update.message.reply_text(result_message)
    else:
        await update.message.reply_text('error')


async def my_movies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    keyboard = [
            ['Все', 'Запланировано'],
            ['Смотрю', 'Просмотрено'],
            ['Избранное', 'Закрыть'],
        ]

    markup = ReplyKeyboardMarkup(keyboard)
    await update.message.reply_text('Выберите:',
                                    reply_markup=markup)

    return MOVIES


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return MOVIES


async def planned_movies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user = update.effective_user
    keyboard = []
    buttons = []
    response = requests.post(
        url=f"{URL_KINOKINO}{URL_MOVIES}",
        params={
            'username': user.id,
            'field_name': PLANNED_TO_WATCH,
        },
    ).json()
    for i, movie in enumerate(response['films']):
        callback_data = f"info__{movie['id']}"
        keyboard.append([InlineKeyboardButton(f"{i + 1}) {movie['name']}", callback_data=callback_data)])
    keyboard.append(buttons)
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f'В планах:\n', reply_markup=markup)
    return MOVIES


async def watching_movies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user = update.effective_user
    keyboard = []
    buttons = []
    response = requests.post(
        url=f"{URL_KINOKINO}{URL_MOVIES}",
        params={
            'username': user.id,
            'field_name': WATCHING,
        },
    ).json()
    for i, movie in enumerate(response['films']):
        callback_data = f"info__{movie['id']}"
        keyboard.append([InlineKeyboardButton(f"{i + 1}) {movie['name']}", callback_data=callback_data)])
    keyboard.append(buttons)
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f'Смотрю:\n', reply_markup=markup)
    return MOVIES


async def completed_movies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user = update.effective_user
    keyboard = []
    buttons = []
    response = requests.post(
        url=f"{URL_KINOKINO}{URL_MOVIES}",
        params={
            'username': user.id,
            'field_name': COMPLETED,
        },
    ).json()
    for i, movie in enumerate(response['films']):
        callback_data = f"info__{movie['id']}"
        keyboard.append([InlineKeyboardButton(f"{i + 1}) {movie['name']}", callback_data=callback_data)])
    keyboard.append(buttons)
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f'Просмотренные:\n', reply_markup=markup)
    return MOVIES


async def all_movies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user = update.effective_user
    keyboard = []
    buttons = []
    response = requests.post(
        url=f"{URL_KINOKINO}{URL_MOVIES}",
        params={
            'username': user.id,
            'field_name': 'None',
        },
    ).json()
    for i, movie in enumerate(response['films']):
        callback_data = f"info__{movie['id']}"
        keyboard.append([InlineKeyboardButton(f"{i + 1}) {movie['name']}", callback_data=callback_data)])
    keyboard.append(buttons)
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f'Все:\n', reply_markup=markup)
    return MOVIES


async def favorite_movies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user = update.effective_user
    keyboard = []
    buttons = []
    response = requests.post(
        url=f"{URL_KINOKINO}{URL_MOVIES}",
        params={
            'username': user.id,
            'field_name': 'favorite',
        },
    ).json()
    for i, movie in enumerate(response['films']):
        callback_data = f"info__{movie['id']}"
        keyboard.append([InlineKeyboardButton(f"{i + 1}) {movie['name']}", callback_data=callback_data)])
    keyboard.append(buttons)
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f'Избранное:\n', reply_markup=markup)
    return MOVIES


async def movie_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    query = update.callback_query
    data_split = query.data.split('__')
    movie_id = data_split[1]
    if data_split[0] == 'add':
        fav = data_split[2]
        response_fav = requests.post(
            url=f"{URL_KINOKINO}{URL_FAVORITE}",
            params={
                'username': f'{query.from_user.id}',
                'movie_id': f'{movie_id}',
                'fav': f'{fav}',
            },
        ).text[1:-1]
        await query.message.reply_text(response_fav)
    elif data_split[0] == 'change':
        status = data_split[2]
        response_status = requests.post(
            url=f"{URL_KINOKINO}{URL_CHANGE_STATUS}",
            params={
                'username': f'{query.from_user.id}',
                'movie_id': f'{movie_id}',
                'status': f'{status}',
            }
        ).text[1:-1]
        await query.message.reply_text(response_status)
    response = requests.post(
        url=f"{URL_KINOKINO}{URL_INFO_MOVIES}",
        params={
            'username': f'{query.from_user.id}',
            'movie_id': f'{movie_id}',
        },
    ).json()
    buttons = []
    keyboard = [buttons]
    if response['favorite']:
        keyboard.append([InlineKeyboardButton('Удалить из избранного', callback_data=f"add__{movie_id}__rem")])
    else:
        keyboard.append([InlineKeyboardButton('Добавить в избранное', callback_data=f"add__{movie_id}__add")])
    movie_status: str = response['status']
    statuses = [i for i in STATUSES if i != movie_status]
    status_buttons = []
    for status in statuses:
        status_buttons.append(InlineKeyboardButton(f"{status}", callback_data=f"change__{movie_id}__{status}"))
    keyboard.append(status_buttons)
    result_message = f"Название: {response['name']}\n" \
                     f"Статус: {movie_status}\n" \
                     f"Год: {response['year']}\n"
    if response['episodes_count'] and response['seasons_count'] != 'None':
        result_message += f"Сезонов: {response['seasons_count']}\n" \
                          f"Серий: {response['episodes_count']}\n"
        movie_details_buttons = [
            InlineKeyboardButton(f"Сезоны", callback_data=f"seasons__{movie_id}"),
        ]
        keyboard.append(movie_details_buttons)
    markup = InlineKeyboardMarkup(keyboard)
    result_message += f"Превью: {response['preview_url']}\n"
    await query.answer()
    await query.edit_message_text(result_message, reply_markup=markup)
    return MOVIES


async def movie_seasons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    query = update.callback_query
    data_split = query.data.split('__')
    movie_id = data_split[1]
    response = requests.post(
        url=f"{URL_KINOKINO}{URL_SEASONS_EPISODES}",
        params={
            'username': f'{query.from_user.id}',
            'movie_id': f'{movie_id}',
            'season_number': 'None',
        }
    ).json()
    buttons = []
    keyboard = [buttons]
    for i in response['seasons']:
        callback_data = f"season_details__{movie_id}__{i}"
        keyboard.append([InlineKeyboardButton(f"{i} Сезон", callback_data=callback_data)])
    keyboard.append([InlineKeyboardButton("К фильму", callback_data=f"info__{movie_id}")]),
    markup = InlineKeyboardMarkup(keyboard)
    await query.answer()
    await query.edit_message_text('Сезоны:', reply_markup=markup)
    return MOVIES


async def season_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    query = update.callback_query
    data_split = query.data.split('__')
    movie_id = data_split[1]
    season_number = data_split[2]
    if data_split[0] == 'episode':
        episode_number = data_split[3]
        complete = data_split[4]
        response_episode = requests.post(
            url=f"{URL_KINOKINO}{URL_ADD_EPISODE}",
            params={
                'username': f'{query.from_user.id}',
                'movie_id': f'{movie_id}',
                'episode_number': f'{episode_number}',
                'season_number': season_number,
                'complete': complete,
            }
        ).status_code
    response = requests.post(
        url=f"{URL_KINOKINO}{URL_SEASONS_EPISODES}",
        params={
            'username': f'{query.from_user.id}',
            'movie_id': f'{movie_id}',
            'season_number': season_number,
        }
    ).json()
    buttons = []
    completed_episodes = response['complete_episodes']
    keyboard = [buttons]
    episodes_buttons = []
    for i in response['episodes']:
        callback_data = f"episode__{movie_id}__{season_number}__{i}__"
        if i in completed_episodes:
            callback_data += 'rem'
            episodes_buttons.append(InlineKeyboardButton(f"{i} Серия ✅", callback_data=callback_data))
        else:
            callback_data += 'add'
            episodes_buttons.append(InlineKeyboardButton(f"{i} Серия", callback_data=callback_data))
        if len(episodes_buttons) == 3:
            keyboard.append(episodes_buttons)
            episodes_buttons = []
    if len(episodes_buttons):
        keyboard.append(episodes_buttons)
    keyboard.append([InlineKeyboardButton("К сезонам", callback_data=f"seasons__{movie_id}")]),
    markup = InlineKeyboardMarkup(keyboard)
    await query.answer()
    await query.edit_message_text('Серии:', reply_markup=markup)
    return MOVIES


async def close_movies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [
        ['Поиск фильма'],
        ['Мои фильмы', 'Моя статистика']
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard)
    await update.message.reply_text('//', reply_markup=markup)

    return ConversationHandler.END


def main() -> None:
    application = Application.builder().token("5454514886:AAFL06SwdfSCkv_afMBIvT576G-sEE5_cvY").build()

    search_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("search", search),
                      MessageHandler(filters.Regex("^Поиск фильма$"), search)
                      ],
        states={

            SEARCHING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, searching),
                CommandHandler('skip', skip),
            ],

        },
        fallbacks=[CommandHandler("skip", skip)],
    )

    movies_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("my_movies", my_movies),
                      MessageHandler(filters.Regex("^Мои фильмы$"), my_movies)],
        states={

            MOVIES: [
                MessageHandler(filters.Regex("^Все$"), all_movies),
                MessageHandler(filters.Regex("^Запланировано"), planned_movies),
                MessageHandler(filters.Regex("^Смотрю$"), watching_movies),
                MessageHandler(filters.Regex("^Просмотрено$"), completed_movies),
                MessageHandler(filters.Regex("^Избранное$"), favorite_movies),
                CallbackQueryHandler(movie_info, pattern="^info__"),
                CallbackQueryHandler(movie_info, pattern="^add__"),
                CallbackQueryHandler(movie_info, pattern="^change__"),
                CallbackQueryHandler(movie_seasons, pattern="^seasons__"),
                CallbackQueryHandler(season_details, pattern="^season_details__"),
                CallbackQueryHandler(season_details, pattern="^episode__"),
            ],

        },
        fallbacks=[
            MessageHandler(filters.Regex("^Закрыть$"), close_movies)
        ],

    )

    application.add_handler(search_conv_handler)

    application.add_handler(movies_conv_handler)

    application.add_handler(CallbackQueryHandler(searching_select))

    application.add_handler(CommandHandler('start', start))

    application.add_handler(CommandHandler('statistics', statistics))

    application.add_handler(MessageHandler(filters.Regex("^Моя статистика$"), statistics))

    application.add_handler(MessageHandler(filters.Regex("^Мои фильмы$"), my_movies))

    application.run_polling()


if __name__ == "__main__":
    main()

# python kinokino_tg_bot.py
