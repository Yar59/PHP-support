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
from telegram_bot.data_operations import (
    is_new_user,
    save_user_data,
    validate_fullname,
    validate_phonenumber,
    get_user_role,
)

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
    show_worker_tasks = auto()
    take_work = auto()


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
    take = auto()
    tech = auto()
    unaccepted = auto()
    expired = auto()
    create_message = auto()


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
                        CallbackQueryHandler(show_available_tasks, pattern=f'^{Transitions.worklist}$'),
                        CallbackQueryHandler(show_worker_tasks, pattern=f'^{Transitions.current_tasks}$'),
                    ],
                States.show_worker_tasks:
                    [
                        CallbackQueryHandler(handle_role, pattern=f'^{Transitions.worker}$'),
                        CallbackQueryHandler(take_work, pattern=f'^{Transitions.take}$'),
                        CallbackQueryHandler(show_worker_task),
                    ],
                # States.manager:
                #     [
                #         MessageHandler(show_unaccepted)
                #         [InlineKeyboardButton(show_unaccepted, callback_data=str(Transitions.manager))],
                #     ],

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
            keyboard = [
                [InlineKeyboardButton("Обращение в техподдержку", callback_data=str(Transitions.tech))],
                [InlineKeyboardButton("Непринятые заказы", callback_data=str(Transitions.unaccepted))],
                [InlineKeyboardButton("Заказы с истекшим сроком", callback_data=str(Transitions.expired))],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.message.reply_text(
                text="Выберете меню",
                reply_markup=reply_markup,
            )
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


def show_available_tasks(update: Update, context: CallbackContext) -> int:
    """Показывает доступные задачи"""
    user_id = update.effective_user.id
    tasks = Task.objects.filter(status="WAIT")

    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("В меню", callback_data=str(Transitions.worker))],
    ]
    if len(tasks):
        message = "Выберите задачи"
        for task in tasks:
            message += f'Заказ №{task.id}, {task.task[:30]}\n\n'
            keyboard.append([InlineKeyboardButton(f"К заказу {task.id}", callback_data=str(task.id))])
    else:
        message = "Нам очень жаль, но на данный момент задачи отсутствуют"
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text=message,
        reply_markup=reply_markup,
    )
    return States.show_worker_tasks


def show_worker_tasks(update: Update, context: CallbackContext) -> int:
    """Показывает задачи, которые исполнитель уже принял"""
    user_id = update.effective_user.id
    tasks_in_work = User.objects.get(tg_id=user_id).worker_tasks.all()
    query = update.callback_query
    query.answer()

    keyboard = [
        [InlineKeyboardButton("В меню", callback_data=str(Transitions.worker))],
    ]
    if len(tasks_in_work):
        message = "Задачи в работе:\n\n"
        for task in tasks_in_work:
            message += f'Заказ №{task.id}, {task.task[:30]}\n\n'
            keyboard.append([InlineKeyboardButton(f"К заказу {task.id}", callback_data=str(task.id))])
    else:
        message = "Нам очень жаль, но на данный момент задачи отсутствуют"
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text=message,
        reply_markup=reply_markup,
    )
    return States.show_worker_tasks


def show_worker_task(update: Update, context: CallbackContext) -> int:
    """Показывает задачу по id, если задача взята, дает связаться с заказчиком, иначе дает принять задачу"""
    chat_id = update.effective_chat.id
    query = update.callback_query
    query.answer()
    data = query.data

    task = Task.objects.get(id=int(data))
    context.user_data['current_task'] = int(data)
    message = f'Заказ №{task.id}\n\n{task.task}'
    keyboard = [
        [InlineKeyboardButton("В меню", callback_data=str(Transitions.worker))],
    ]
    try:
        worker_id = task.worker.tg_id
    except AttributeError:
        worker_id = None
    if worker_id == chat_id:
        keyboard.append([InlineKeyboardButton("Написать заказчику", callback_data=str(Transitions.create_message))])
    else:
        keyboard.append([InlineKeyboardButton("Взять заказ", callback_data=str(Transitions.take))])
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text=message,
        reply_markup=reply_markup,
    )
    return States.show_worker_tasks

# def choose_task_list(update: Update, context: CallbackContext) -> int:
#     user_id = update.effective_user.id
#     tasks = Task.objects.filter(status="WAIT")
#     phone = update.message.contact.phone_number
#     query = update.callback_query
#     query.answer()
#     data = query.data
#     if data == str(Transitions.worklist):
#         if len(tasks):
#             for task in tasks:
#                 keyboard = [
#                     [InlineKeyboardButton("Взять", callback_data=str(Transitions.take))],
#                 ]
#                 message = "Возьмите задание",
#
#             return States.work_choose
#         else:
#             keyboard = [
#                 [InlineKeyboardButton("Назад", callback_data=str(Transitions.worklist))],
#             ]
#             message = "Нам очень жаль, но на данный момент задачи отсутствуют"
#     if data == str(Transitions.take):
#         Task.objects.create(user__number=phone)
#     reply_markup = InlineKeyboardMarkup(keyboard)
#     query.message.reply_text(
#         text=message,
#         reply_markup=reply_markup,
#     )
#     return States.work_choose


def take_work(update: Update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id
    task_id = context.user_data['current_task']
    query = update.callback_query
    query.answer()
    data = query.data
    user = User.objects.get(tg_id=chat_id)
    task = Task.objects.get(id=task_id)
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data=str(Transitions.worklist))],
        [InlineKeyboardButton("Взять", callback_data=str(Transitions.take))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text="Выберете задачу",
        reply_markup=reply_markup,
    )
    return States.current_work


def show_unaccepted(update: Update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id
    tasks = Task.objects.filter(status="WAIT")
    message = f'Непринятые задачи найдены\n\n{tasks}\n\n '
    keyboard = [
        [InlineKeyboardButton("В меню менеджера", callback_data=str(Transitions.manager))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        chat_id,
        text=message,
        reply_markup=reply_markup,
    )
    return States.handle_task


def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        'Надеюсь тебе понравился наш бот!'
    )

    return ConversationHandler.END
