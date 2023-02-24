import logging
from enum import Enum, auto
from textwrap import dedent

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
from django.utils import timezone

from telegram_bot.models import User, Subscription, Task


logger = logging.getLogger(__name__)


class States(Enum):
    start = auto()
    authorization = auto()
    get_phone = auto()
    choose_role = auto()
    client = auto()
    worker = auto()
    manager = auto()
    handle_subscriptions = auto()
    handle_task = auto()
    show_client_tasks = auto()
    handle_subscribe = auto()
    handle_payment = auto()
    work_choose = auto()
    current_work = auto()
    work_take = auto()


class Transitions(Enum):
    authorization_reject = auto()
    authorization_approve = auto()
    client = auto()
    worker = auto()
    manager = auto()
    subscriptions = ()
    create_task = auto()
    tasks = auto()
    subscribe = auto()
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
                States.client:
                    [
                        CallbackQueryHandler(show_subscriptions, pattern=f'^{Transitions.subscriptions}$'),
                        CallbackQueryHandler(create_task, pattern=f'^{Transitions.create_task}$'),
                        CallbackQueryHandler(show_client_tasks, pattern=f'^{Transitions.tasks}$'),
                    ],
                States.handle_subscriptions:
                    [
                        CallbackQueryHandler(handle_role, pattern=f'^{Transitions.client}$'),
                        CallbackQueryHandler(subscribe, pattern=f'^{Transitions.subscribe}$'),
                    ],
                States.handle_subscribe:
                    [
                        CallbackQueryHandler(handle_role, pattern=f'^{Transitions.client}$'),
                        CallbackQueryHandler(handle_payment),
                    ],
                States.handle_payment:
                    [
                        CallbackQueryHandler(handle_role, pattern=f'^{Transitions.client}$'),
                        CallbackQueryHandler(create_subscription),
                    ],
                States.handle_task:
                    [
                        MessageHandler(Filters.text, register_task),
                        CallbackQueryHandler(show_subscriptions, pattern=f'^{Transitions.subscribe}$'),
                        CallbackQueryHandler(handle_role, pattern=f'^{Transitions.client}$'),
                    ],
                States.show_client_tasks:
                    [
                        CallbackQueryHandler(handle_role, pattern=f'^{Transitions.client}$'),
                        CallbackQueryHandler(show_client_task),
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
    try:
        phone = update.message.contact.phone_number
    except AttributeError:
        phone = update.message.text
    check_number = validate_phonenumber(phone)
    if not check_number:
        context.bot.send_message(
            chat_id=chat_id,
            text="Введен невалидный номер, попробуйте снова."
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
        keyboard = [
            [InlineKeyboardButton("Подписки", callback_data=str(Transitions.subscriptions))],
            [InlineKeyboardButton("Оформить заказ", callback_data=str(Transitions.create_task))],
            [InlineKeyboardButton("История заказов", callback_data=str(Transitions.tasks))],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text(
            text="Куда отправимся?",
            reply_markup=reply_markup,
        )
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


def show_subscriptions(update: Update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id
    query = update.callback_query
    query.answer()
    subscriptions = User.objects.get(tg_id=chat_id).subscriptions.filter(starts_at__lte=timezone.now(), end_at__gte=timezone.now())
    if len(subscriptions):
        message = ''.join([f'{subscription.lvl}, которая истекает {subscription.end_at}\n' for subscription in subscriptions])
    else:
        message = 'У вас нет активных подписок'
    keyboard = [
        [InlineKeyboardButton("Оформить подписку", callback_data=str(Transitions.subscribe))],
        [InlineKeyboardButton("В меню", callback_data=str(Transitions.client))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text=message,
        reply_markup=reply_markup,
    )
    return States.handle_subscriptions


def handle_payment(update: Update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id
    query = update.callback_query
    query.answer()
    data = query.data
    price = ''
    if data == 'economy':
        message = 'Стоимость подписки 100$'
        price = '100'
    elif data == 'default':
        message = 'Стоимость подписки 200$'
        price = '200'
    elif data == 'vip':
        message = 'Стоимость подписки 300$'
        price = '300'
    keyboard = [
        [InlineKeyboardButton("Оплатить подписку", callback_data=price)],
        [InlineKeyboardButton("В меню", callback_data=str(Transitions.client))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text=message,
        reply_markup=reply_markup,
    )
    return States.handle_payment


def create_subscription(update: Update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id
    query = update.callback_query
    query.answer()
    data = query.data
    user = User.objects.get(tg_id=chat_id)
    starts_at = timezone.now()
    end_at = starts_at + timezone.timedelta(days=30)
    if data == '100':
        subscription_level = 'Экономный'
    elif data == '200':
        subscription_level = 'Стандарт'
    elif data == '300':
        subscription_level = 'ВИП'
    Subscription.objects.create(user=user, lvl=subscription_level, starts_at=starts_at, end_at=end_at)
    keyboard = [
        [InlineKeyboardButton("В меню", callback_data=str(Transitions.client))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text='Подписка успешно оплачена',
        reply_markup=reply_markup,
    )
    return States.handle_subscriptions


def create_task(update: Update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("В меню", callback_data=str(Transitions.client))],
    ]
    subscriptions = User.objects.get(tg_id=chat_id).subscriptions.filter(starts_at__lte=timezone.now(),
                                                                         end_at__gte=timezone.now())
    if len(subscriptions):
        message = dedent('''
            Для того чтобы создать задачу, отправьте задание в текстовом формате
            Не указывайте в задаче паролей/логинов или других чувствительных данных
        ''')
    else:
        message = 'У вас нет активных подписок'
        keyboard.append([InlineKeyboardButton("К подпискам", callback_data=str(Transitions.subscribe))])
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text=message,
        reply_markup=reply_markup,
    )
    return States.handle_task


def register_task(update: Update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id
    text = update.effective_message.text

    user = User.objects.get(tg_id=chat_id)
    Task.objects.create(client=user, task=text, created_at=timezone.now())

    message = f'Задача успешно создана\n\nТекст:\n{text}\n\nМы оповестим Вас как только найдем исполнителя '
    keyboard = [
        [InlineKeyboardButton("В меню", callback_data=str(Transitions.client))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        chat_id,
        text=message,
        reply_markup=reply_markup,
    )
    return States.handle_task


def show_client_tasks(update: Update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("В меню", callback_data=str(Transitions.client))],
    ]
    message = 'Ваши заказы:\n'
    tasks = User.objects.get(tg_id=chat_id).client_tasks.all()

    if len(tasks):
        for task in tasks:
            message += f'Заказ №{task.id}, {task.task[:30]}\n\n'
            keyboard.append([InlineKeyboardButton(f"К заказу {task.id}", callback_data=str(task.id))])
    else:
        message += 'Вы еще не создавали заказов'

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text=message,
        reply_markup=reply_markup,
    )
    return States.show_client_tasks


def subscribe(update: Update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id
    query = update.callback_query
    query.answer()
    message = dedent('''
        Тарифы:
        Эконом - до 5 заявок в месяц на помощь, по заявке ответят в течение суток
        Стандарт - до 15 заявок в месяц, возможность закрепить подрядчика за собой, заявка будет рассмотрена в течение часа
        VIP - до 60 заявок в месяц, возможность увидеть контакты подрядчика, заявка будет рассмотрена в течение часа 
    ''')
    keyboard = [
        [InlineKeyboardButton("Эконом - 100$", callback_data='economy')],
        [InlineKeyboardButton("Стандарт - 200$", callback_data='default')],
        [InlineKeyboardButton("♂dungeon master♂ - 300$", callback_data='vip')],
        [InlineKeyboardButton("В меню", callback_data=str(Transitions.client))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text=message,
        reply_markup=reply_markup,
    )
    return States.handle_subscribe


def show_client_task(update: Update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id
    query = update.callback_query
    query.answer()
    data = query.data

    task = Task.objects.get(id=int(data))

    message = f'Заказ №{task.id}\n\n{task.task}'
    keyboard = [
        [InlineKeyboardButton("В меню", callback_data=str(Transitions.client))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text=message,
        reply_markup=reply_markup,
    )
    return States.show_client_tasks


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
