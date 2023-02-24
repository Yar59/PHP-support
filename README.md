# PHP-support bot
Telegram бот по оказанию поддержки и выполнению задач.
Данный бот поддерживает авторизацию, разделение ролей(клиент, исполнитель, менеджер поддержки), получение подписки, а также произведение оплаты за выполненную работу.
Редактирование данных пользователей производится в админ разделе.

## Установка

1) Клонировать проект:
```
git clone https://github.com/Yar59/PHP-support.git
```

2) Установить виртуальное окружение:
```
python3 -m venv /path/to/new/virtual/environment
```

3) Активировать окружение:
```
sourse /path/to/new/virtual/environment/bin/activate
```

4) Установить зависимости:
```
pip install -r requiremenets.txt
```

5) Создать `.env` файл для ваших секретных ключей:
```
touch .env
```

6) Записать в .env следующие переменные:
* TG_BOT_TOKEN='Ваш телеграм токен'  [Получают при создании у отца ботов](https://t.me/botfather)
* USER_ID='ID вашей личной страницы Telegram' [узнать можно тут](https://t.me/username_to_id_bot)
* ALLOWED_HOSTS='Адреса вашего сервера'
* SECRET_KEY='Секретный ключ проекта'
* DEBUG=False (При выполнении отладки следует установить True)

7) Выполнить миграции
```
python3 manage.py migrate
```

8) Создание админа, для редактирования пользовательских данных (/admin)
```
python3 manage.py createsuperuser
```

## Запуск бота
```
python3 manage.py telegran-bot
```

## Запуск админки
* Для доступа в админку (/admin)
```
python3 manage.py runserver
```