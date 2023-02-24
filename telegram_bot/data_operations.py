import phonenumbers

from telegram_bot.models import User


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
