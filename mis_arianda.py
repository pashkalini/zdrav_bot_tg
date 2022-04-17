import datetime

import requests
from aiogram.types import message

import config

# доступы к API
API_LOGIN = config.API_LOGIN
PATIENT_INFO = config.PATIENT_INFO
RECORDINGS = config.RECORDINGS
CANCEL_RECORDING = config.CANCEL_RECORDING
SPEC_LIST = config.SPEC_LIST
DOC_LIST = config.DOC_LIST
RNUMB_LIST = config.RNUMB_LIST
RNUMB_INFO = config.RNUMB_INFO
RNUMB_REC = config.RNUMB_REC
HISTORY_LIST = config.HISTORY_LIST
HISTORY_PDF = config.HISTORY_PDF


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
    data = all_data.get("data")
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
    data = all_data.get("data")
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


# запись - список специальностей
def get_spec_list(token):
    all_data = requests.get(SPEC_LIST, headers={'Authorization': 'TOKEN ' + token},
                            params={'beginDate': '2015-02-01', 'endDate': '2115-02-01'}).json()
    data = all_data.get("data")
    error = "error"

    if not all_data.get("success"):
        return error
    else:
        all_spec = []

        for spec in data:
            all_spec.append({"spec_id": spec.get("keyid"),
                             "spec_text": spec.get("text")
                             })

        return all_spec


# запись - список докторов
def get_doc_list(token, spec_id):
    all_data = requests.get(DOC_LIST, headers={'Authorization': 'TOKEN ' + token},
                            params={'specID': spec_id, 'beginDate': '2015-02-01', 'endDate': '2115-02-01'}).json()
    data = all_data.get("data")
    error = "error"

    if not all_data.get("success"):
        return error
    else:
        all_doc = []

        for doc in data:
            all_doc.append({"doc_id": doc.get("doctorid"),
                            "doc_l_name": doc.get("l_name"),
                            "doc_f_name": doc.get("f_name"),
                            "doc_s_name": doc.get("s_name"),
                            # не используем то, что ниже
                            "doc_note": doc.get("note"),
                            "doc_dat_bgn": doc.get("dat_bgn"),
                            "doc_dat_end": doc.get("dat_end"),
                            "doc_rcount": doc.get("rcount"),
                            "doc_srvlist": doc.get("dat_srvlist")
                            })

        return all_doc


# запись - список номерков
def get_rnumb_list(token, spec_id, doc_id):
    all_data = requests.get(RNUMB_LIST, headers={'Authorization': 'TOKEN ' + token},
                            params={'doctorID': doc_id, 'specID': spec_id,
                                    'beginDate': '2015-02-01', 'endDate': '2115-02-01'}).json()
    data = all_data.get("data")
    error = "error"

    if not all_data.get("success"):
        return error
    else:
        all_rnumb = []

        for rnumb in data:
            all_rnumb.append({"rnumb_id": rnumb.get("rnumbid"),
                              "rnumb_dat_begin": rnumb.get("dat_begin_str"),
                              "rnumb_dat_end": rnumb.get("dat_end_str"),

                              "rnumb_depid": rnumb.get("depid"),
                              "rnumb_depname": rnumb.get("depname"),
                              "rnumb_paystatus": rnumb.get("paystatus"),
                              "rnumb_is_interval": rnumb.get("is_interval"),
                              "rnumb_interval_id": rnumb.get("interval_id"),
                              "rnumb_is_telemed": rnumb.get("is_telemed")
                              })

        return all_rnumb


# запись - инфо о талоне для подтверждения
def get_rnumb_info(token, rnumb_id):
    all_data = requests.get(RNUMB_INFO, headers={'Authorization': 'TOKEN ' + token},
                            params={'rnumbID': rnumb_id}).json()
    data = all_data.get("data")
    error = "error"

    if not all_data.get("success"):
        return error
    else:
        all_info = []

    for info in data:
        all_info.append({"rnumb_id": info.get("rnumb_id"),
                         "rnumb_dat_begin": info.get("dat_bgn"),
                         "rnumb_dat_end": info.get("dat_end"),
                         "rnumb_cab": info.get("cab"),
                         "rnumb_spec": info.get("spec"),
                         "rnumb_srv_text": info.get("srv_text"),
                         "rnumb_doctor_id": info.get("doctor_id"),
                         "rnumb_doc_lname": info.get("lastname"),
                         "rnumb_doc_fname": info.get("firstname"),
                         "rnumb_doc_sname": info.get("secondname"),
                         "rnumb_depname": info.get("depname"),
                         "rnumb_addr": info.get("addr"),
                         "rnumb_phone": info.get("phone"),
                         "rnumb_paystatus": info.get("paystatus"),
                         "rnumb_calc_sum": info.get("calc_sum"),
                         "rnumb_is_telemed": info.get("is_telemed"),
                         "rnumb_url_telemed": info.get("url_telemed")
                         })

    return all_info


# запись - запись на талон
def create_rec(token, rnumb_id):
    return requests.get(RNUMB_REC, headers={'Authorization': 'TOKEN ' + token}, params={'rnumbID': rnumb_id})


# заключения - список посещений
def get_history_list(token):
    today = datetime.datetime.today()
    f_today = datetime.datetime.strftime(today, '%Y-%m-%d')
    all_data = requests.get(HISTORY_LIST, headers={'Authorization': 'TOKEN ' + token},
                            params={'start': '1', 'end': '10000', 'beginDate': '2015-02-01', 'endDate': f_today}).json()
    data = all_data.get("data")
    error = "error"

    if not all_data.get("success"):
        return error
    else:
        all_visits = []

        for visit in data:
            all_visits.append({"keyid": visit.get('keyid'),
                               "typetext": visit.get('typetext'),
                               "typehistory": visit.get('typehistory'),
                               "dat": visit.get('dat'),
                               "doctor": visit.get('doctor'),
                               "doctorid": visit.get('doctorid'),
                               "spec": visit.get('spec'),
                               "sortcode": visit.get('sortcode'),
                               "dep_name": visit.get('dep_name'),
                               "sched_exists_for_dd_on_visit": visit.get('sched_exists_for_dd_on_visit')
                               })

        return all_visits


def get_visit_pdf(visit_tp, visit_id):
    return requests.get(HISTORY_PDF, params={'tp': visit_tp, 'id': visit_id})
