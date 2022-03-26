import requests
from aiogram.types import message

import config

# доступы к API
import zdrav_bot_code

API_LOGIN = config.API_LOGIN
PATIENT_INFO = config.PATIENT_INFO
RECORDINGS = config.RECORDINGS
CANCEL_RECORDING = config.CANCEL_RECORDING


# TODO продумать вариант повторной авторизации на случае обновления токена -
#  вроде как придумал -> см. zdrav_bot_code.repeat_auth()
# авторизация - ввод логина/пароля -> получение токена
def auth(login, password):
    return requests.post(API_LOGIN, json={'login': login, 'passwd': password})


# получение информации по методу, в котором обязательный параметр ТОЛЬКО токен
def only_token_data(method, token):
    return requests.get(method, headers={'Authorization': 'TOKEN ' + token}).json()


#  информация о пациенте
def get_patient_info(token):
    all_data = only_token_data(PATIENT_INFO, token)
    data = only_token_data(PATIENT_INFO, token).get("data")
    error = "error"
    if not all_data.get("success"):
        return error
    else:
        patient_info_dict = {"num": data.get("num"),
                             "lastname": data.get("lastname"),
                             "firstname": data.get("firstname"),
                             "secondname": data.get("secondname"),
                             "birthdatestr": data.get("birthdatestr"),
                             "phone": data.get("phone"),
                             "cellular": data.get("cellular"),
                             "email": data.get("email"),
                             "snils": data.get("snils"),
                             "address_proj": data.get("address_proj")
                             }
        return patient_info_dict


# информация о записях
def get_recordings(token):
    all_data = only_token_data(RECORDINGS, token)
    data = only_token_data(RECORDINGS, token).get("data")
    error = "error"
    if not all_data.get("success"):
        return error

    else:
        all_recordings = []

        for patient_recording in data:
            all_recordings.append({"rnumb_id": patient_recording.get("rnumb_id"),
                                  "dat_bgn": patient_recording.get("dat_bgn"),
                                  "dat_end": patient_recording.get("dat_end"),
                                  "cab": patient_recording.get("cab"),
                                  "spec": patient_recording.get("spec"),
                                  "srv_text": patient_recording.get("srv_text"),
                                  "doctor_id": patient_recording.get("doctor_id"),
                                  "firstname": patient_recording.get("firstname"),
                                  "lastname": patient_recording.get("lastname"),
                                  "secondname": patient_recording.get("secondname"),
                                  "depname": patient_recording.get("depname"),
                                  "addr": patient_recording.get("addr"),
                                  "phone": patient_recording.get("phone"),
                                  "paystatus": patient_recording.get("paystatus"),
                                  "calc_sum": patient_recording.get("calc_sum"),
                                  "is_telemed": patient_recording.get("is_telemed"),
                                  "url_telemed": patient_recording.get("url_telemed")
                                })

        return all_recordings


# отмена записи
def cancel_rec(token, rnumb_id):
    return requests.get(CANCEL_RECORDING, headers={'Authorization': 'TOKEN ' + token}, params={'rnumbID': rnumb_id})
