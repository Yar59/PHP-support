import logging
from enum import Enum, auto

import phonenumbers
from telegram import (
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler,
)
from django.core.management.base import BaseCommand
from django.conf import settings

from telegram_bot.models import User, Task

logger = logging.getLogger(__name__)


class States(Enum):
    start = auto()
    authorization = auto()
    get_phone = auto()
    choose_role = auto()
    client = auto()
    worker = auto()
    manager = auto()
    work_choose = auto()
    current_work = auto()
    work_take = auto()


class Transitions(Enum):
    authorization_reject = auto()
    authorization_approve = auto()
    client = auto()
    worker = auto()
    manager = auto()
    worklist = auto()
    current_tasks = auto()


class Command(BaseCommand):
    help = 'Implemented to Django application telegram bot setup command'

    def handle(self, *args, **kwargs):
        updater = Updater(token=settings.TG_BOT_TOKEN)

        dispatcher = updater.dispatcher

        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', start),
            ],
            states={
                States.authorization:
                    [
                        CallbackQueryHandler(
                            callback=callback_approve_handler,
                            pass_chat_data=True
                        ),
                        MessageHandler(Filters.text, get_phone),
                    ],
                States.get_phone:
                    [
                        MessageHandler(Filters.text, handle_phone),
                        MessageHandler(Filters.contact, handle_phone),
                    ],
                States.choose_role:
                    [
                        CallbackQueryHandler(handle_role),
                    ],
                States.worker:
                    [
                        CallbackQueryHandler(choose_task_lvl1, pattern=f'^{Transitions.worklist}$'),
                        CallbackQueryHandler(choose_task_lvl1, pattern=f'^{Transitions.current_tasks}$'),
                    ],
                States.work_choose:
                    [
                    
                    ],
                States.current_work:
                    [
                        
                    ],
            },
            fallbacks=[
                CommandHandler('cancel', cancel),
                CommandHandler('start', cancel),
            ],
        )

        dispatcher.add_handler(conv_handler)

        updater.start_polling()
        updater.idle()


def start(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    if is_new_user(user_id):
        with open("agreement.pdf", "rb") as image:
            agreement = image.read()

        keyboard = [
            [InlineKeyboardButton("Принимаю", callback_data=str(Transitions.authorization_approve))],
            [InlineKeyboardButton("Отказываюсь", callback_data=str(Transitions.authorization_reject))],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_document(
            agreement,
            filename="Соглашение на обработку персональных данных.pdf",
            caption="Для использования сервиса, примите соглашение об обработке персональных данных",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return States.authorization
    else:
        keyboard = [
            [InlineKeyboardButton("Клиент", callback_data=str(Transitions.client))],
            [InlineKeyboardButton("Исполнитель", callback_data=str(Transitions.worker))],
            [InlineKeyboardButton("Менеджер", callback_data=str(Transitions.manager))],
        ]
        context.bot.send_message(
            chat_id=user_id,
            text=f"Клиент - разместить заказ\nИсполнитель - получить заказы\nМенеджер - для управляющих",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return States.choose_role


def callback_approve_handler(update: Update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id
    query = update.callback_query
    data = query.data

    if data == str(Transitions.authorization_approve):
        context.bot.send_message(
            chat_id=chat_id,
            text="Введите имя и фамилию"
        )
        return States.authorization
    elif data == str(Transitions.authorization_reject):
        context.bot.send_message(
            chat_id=chat_id,
            text="Без соглашения на обработку мы не можем оказать вам услугу"
        )
        return ConversationHandler.END


def get_phone(update: Update, context: CallbackContext) -> int:
    user_name = update.message.text
    context.user_data["user_id"] = update.message.from_user.id
    context.user_data["full_name"] = user_name
    split_name = user_name.split()
    if not validate_fullname(split_name):
        update.message.reply_text(
            "*Введите корректные имя и фамилию!*\nПример: Василий Петров",
            parse_mode="Markdown"
        )
    if validate_fullname(split_name):
        message_keyboard = [[
            KeyboardButton(
                "Отправить свой номер телефона", request_contact=True
            )
        ]]
        markup = ReplyKeyboardMarkup(
            message_keyboard, one_time_keyboard=True, resize_keyboard=True
        )
        update.message.reply_text(
            f"Введите телефон в формате +7... или нажав на кнопку ниже:",
            reply_markup=markup
        )
        return States.get_phone


def handle_phone(update: Update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id
    phone = update.message.contact.phone_number
    if not phone:
        phone = update.message.text
    check_number = validate_phonenumber(phone)
    if not check_number:
        context.bot.send_message(
            chat_id=chat_id,
            text="ВВеден невалидный номер, попробуйте снова."
        )
        return States.get_phone
    context.user_data["phone_number"] = phonenumbers.parse(phone, "RU")
    if is_new_user(context.user_data["user_id"]):
        save_user_data(context.user_data)
    chat_id = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat_id,
        text="*Вы прошли регистрацию*",
        parse_mode="Markdown"
    )
    keyboard = [
        [InlineKeyboardButton("Клиент", callback_data=str(Transitions.client))],
        [InlineKeyboardButton("Исполнитель", callback_data=str(Transitions.worker))],
        [InlineKeyboardButton("Менеджер", callback_data=str(Transitions.manager))],
    ]
    context.bot.send_message(
        chat_id=chat_id,
        text=f"Клиент - разместить заказ\nИсполнитель - получить заказы\nМенеджер - для управляющих",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return States.choose_role


def handle_role(update: Update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id
    user_role = get_user_role(chat_id)
    query = update.callback_query
    query.answer()
    data = query.data
    if data == str(Transitions.client):
        pass
        # TODO: Показать клаву клиента
        return States.client
    elif data == str(Transitions.worker):
        keyboard = [
            [InlineKeyboardButton("Список задач", callback_data=str(Transitions.worklist))],
            [InlineKeyboardButton("Текущие задачи", callback_data=str(Transitions.current_tasks))],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text(
            text="Выберете меню",
            reply_markup=reply_markup,
        )
        return States.worker
    elif data == str(Transitions.manager):
        if user_role == "Менеджер":
            pass
            # TODO: Показать клаву манагера
            return States.manager
        else:
            message = "К сожалению, вы не менеджер"
    keyboard = [
        [InlineKeyboardButton("Клиент", callback_data=str(Transitions.client))],
        [InlineKeyboardButton("Исполнитель", callback_data=str(Transitions.worker))],
        [InlineKeyboardButton("Менеджер", callback_data=str(Transitions.manager))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text=message,
        reply_markup=reply_markup,
    )
    return States.choose_role


def choose_task_lvl1(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    tasks = Task.objects.filter(status="WAIT")
    tasks_in_work = Task.objects.filter(status="WORK", worker=user_id)
    query = update.callback_query
    query.answer()
    data = query.data
    if data == str(Transitions.worklist):
        print(tasks)
        if tasks:
            return States.work_take
        else:
            update.message.reply_text(
                "Нам очень жаль, но на данный момент задачи отсутствуют",
                parse_mode="Markdown"
            )
            return States.worker
    if data == str(Transitions.current_tasks):
        print(tasks_in_work)
        if tasks_in_work:
            return States.current_work
        else:
            update.message.reply_text(
                "Нам очень жаль, но на данный момент задачи отсутствуют",
                parse_mode="Markdown"
            )
            return States.worker
    keyboard = [
        [InlineKeyboardButton("Список задач", callback_data=str(Transitions.worklist))],
        [InlineKeyboardButton("Текущие задачи", callback_data=str(Transitions.current_tasks))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text="Выберете задачу",
        reply_markup=reply_markup,
    )
    return States.worker


def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        'Надеюсь тебе понравился наш бот!'
    )

    return ConversationHandler.END


def is_new_user(user_id):
    return not User.objects.filter(tg_id=user_id).exists()


def save_user_data(data):
    phone = f"{data['phone_number'].country_code}{data['phone_number'].national_number}"
    User.objects.create(tg_id=data["user_id"], name=data["full_name"], phonenumber=phone)


def validate_fullname(fullname: list) -> bool | None:
    if len(fullname) > 1:
        return True


def validate_phonenumber(number):
    try:
        parsed_number = phonenumbers.parse(number, 'RU')
        return phonenumbers.is_valid_number_for_region(parsed_number, 'RU')
    except phonenumbers.phonenumberutil.NumberParseException:
        return False


def delete_user(user_id):
    User.objects.filter(tg_id__contains=user_id).delete()


def get_user_role(user_id):
    return User.objects.get(tg_id=user_id).role
