import phonenumbers

from .models import Task, User


def is_new_user(user_id):
    return not User.objects.filter(user_id=user_id).exists()


def task_in_work(task):
    in_work = Task.Proc.WORK
    return task['status'] is in_work


def save_user_data(data):
    phone = f"{data['phonenumber'].country_code}{data['phonenumber'].national_number}"
    User.objects.create(user_id=data["user_id"],
                        role=data['role'],
                        tg_id=data["tg_id"],
                        phonenumber=phone,)


def validate_phonenumber(number):
    try:
        parsed_number = phonenumbers.parse(number, 'RU')
        return phonenumbers.is_valid_number_for_region(parsed_number, 'RU')
    except phonenumbers.phonenumberutil.NumberParseException:
        return False


def delete_user(user_id):
    User.objects.filter(user_id__contains=user_id).delete()
