import json
import random
from typing import Any, Text, Dict, List, Optional
#
from rasa_sdk import Action, Tracker
from rasa_sdk.events import AllSlotsReset
from rasa_sdk.events import SlotSet
from rasa_sdk.events import SessionStarted
from rasa_sdk.events import ActionExecuted
from rasa_sdk.events import Restarted
from rasa_sdk.events import EventType
from rasa_sdk.events import FollowupAction
from rasa_sdk.events import UserUtteranceReverted
from rasa_sdk.executor import CollectingDispatcher
#
#
from rasa_sdk import Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict

import re
import logging
import datetime
import csv


logger = logging.getLogger(__name__)

baza_szkody_dict = {}
with open("actions/baza_szkody_utf8.csv") as f:
    f_csv = csv.DictReader(f, delimiter=';')
    for row in f_csv:
        baza_szkody_dict[row['Nr szkody']] = row

baza_polisy_dict = {}
with open("actions/baza_polisy_utf8.csv") as f:
    f_csv = csv.DictReader(f, delimiter=';')
    for row in f_csv:
        baza_polisy_dict[row['Nr polisy']] = row

db_male_firstname = []
with open("actions/IMIONA_MESKIE.csv") as f:
    f_csv = csv.DictReader(f, delimiter=',')
    for row in f_csv:
        db_male_firstname.append(row['IMIĘ_PIERWSZE'])

db_female_firstname = []
with open("actions/IMIONA_ZENSKIE.csv") as f:
    f_csv = csv.DictReader(f, delimiter=',')
    for row in f_csv:
        db_male_firstname.append(row['IMIĘ_PIERWSZE'])

db_male_lastname = []
with open("actions/NAZWISKA_MESKIE.csv") as f:
    f_csv = csv.DictReader(f, delimiter=',')
    for row in f_csv:
        db_male_firstname.append(row['Nazwisko aktualne'])

db_female_lastname = []
with open("actions/NAZWISKA_ZENSKIE.csv") as f:
    f_csv = csv.DictReader(f, delimiter=',')
    for row in f_csv:
        db_male_firstname.append(row['Nazwisko aktualne'])


class ActionSessionStart(Action):

    def name(self) -> Text:
        return "action_session_start"

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[EventType]:
        logging.critical("Session started !!!")
        events = [ActionExecuted("action_listen")]
        metadata = tracker.get_slot("session_started_metadata")
        logging.critical(metadata)
        if metadata and "caller_contact_address" in metadata:
            caller_contact_address = metadata["caller_contact_address"]
            match = re.match("^\d+$", caller_contact_address)
            if match:
                events.append(SlotSet("customer_phone_number", caller_contact_address[2:]))
        if metadata and "callee_contact_address" in metadata:
            events.append(SlotSet("service_phone_number", metadata["callee_contact_address"]))
        events.append(SlotSet("validate_counter_given_customer_name", 0))
        events.append(SlotSet("validate_counter_customer_phone_number", 0))
        events.append(SlotSet("validate_counter_customer_phone_number_confirmed", 0))
        events.append(SlotSet("validate_counter_given_incident_number", 0))
        events.append(SlotSet("validate_counter_given_insurance_number", 0))
        events.append(SlotSet("validate_counter_given_insurance_type", 0))
        events.append(SlotSet("validate_counter_given_vehicle_number", 0))
        events.append(SlotSet("validate_counter_given_subject_type", 0))
        events.append(SlotSet("validate_counter_given_customer_pesel", 0))
        return events

class ActionAsrLowConfidence(Action):

    def name(self) -> Text:
        return "action_asr_low_confidence"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        metadata = tracker.latest_message["metadata"]
        logging.info(metadata)
        if "stop_playback_date" in metadata and not metadata["stop_playback_date"]:
            text = ""
        else:
            text = "Czy możesz powtórzyć?"
        bot_event = next(e for e in reversed(tracker.events) if e["event"] == "bot")
        custom = {
            "blocks": bot_event["data"]["custom"]["blocks"]
        }
        custom["blocks"][0]["text"] = text
        if tracker.get_latest_input_channel() in ("conpeek-voice", "conpeek-text"):
            dispatcher.utter_message(json_message=custom)
        else:
            dispatcher.utter_message(text=text)
        return [UserUtteranceReverted()]

class ActionNluLowConfidence(Action):

    def name(self) -> Text:
        return "action_nlu_low_confidence"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        metadata = tracker.latest_message["metadata"]
        logging.info(metadata)
        if "stop_playback_date" in metadata and not metadata["stop_playback_date"]:
            text = ""
        else:
            text = "Czy możesz powtórzyć?"
        bot_event = next(e for e in reversed(tracker.events) if e["event"] == "bot")
        custom = {
            "blocks": bot_event["data"]["custom"]["blocks"]
        }
        custom["blocks"][0]["text"] = text
        if tracker.get_latest_input_channel() in ("conpeek-voice", "conpeek-text"):
            dispatcher.utter_message(json_message=custom)
        else:
            dispatcher.utter_message(text=text)
        return [UserUtteranceReverted()]

class ActionOutOfScope(Action):

    def name(self) -> Text:
        return "action_out_of_scope"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        bot_event = next(e for e in reversed(tracker.events) if e["event"] == "bot")
        if bot_event.get("data").get("custom").get("out_of_scope"):
            text = bot_event["data"]["custom"]["blocks"][0]["text"]
            custom = bot_event.get("data").get("custom")
        else:
            text = "Niestety, nie wiem co mam powiedzieć. Wróćmy proszę do tematu rozmowy. "
            text += bot_event["data"]["custom"]["blocks"][0]["text"]
            custom = {
                "out_of_scope": True,
                "blocks": bot_event["data"]["custom"]["blocks"]
            }
            custom["blocks"][0]["text"] = text
        if tracker.get_latest_input_channel() in ("conpeek-voice", "conpeek-text"):
            dispatcher.utter_message(json_message=custom)
        else:
            dispatcher.utter_message(text=text)
        return [UserUtteranceReverted()]

class ActionNeedAssistanceQuestion(Action):

    def name(self) -> Text:
        return "action_need_assistance_question"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        logging.critical('Started action_need_assistance_question')
        entity_subject = tracker.get_slot("subject")
        if not entity_subject or entity_subject == 'MOTOR':
            logging.critical('dispatcher.utter_message(response=utter_give_assistance)')
            dispatcher.utter_message(response='utter_give_assistance')
            return [FollowupAction('action_listen')]
        else:
            return [FollowupAction('customer_info_form')]


class ValidateCustomerInfoForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_customer_info_form"

    def validate_given_customer_name(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict,) -> Dict[Text, Any]:
        if not slot_value:
            slot_value = "-"
        validate_limit = 2
        validate_counter = tracker.get_slot("validate_counter_given_customer_name")
        validate_counter += 1
        logging.critical(f"validate_counter_given_customer_name: {validate_counter}")
        words = slot_value.split()
        if (len(words) == 2) \
            and ((words[0].upper() in db_male_firstname) or (words[0].upper() in db_female_firstname) or (words[0].upper() in db_male_lastname) or (words[0].upper() in db_female_lastname)) \
            and ((words[1].upper() in db_male_firstname) or (words[1].upper() in db_female_firstname) or (words[1].upper() in db_male_lastname) or (words[1].upper() in db_female_lastname)):
            slots = {
                "given_customer_name": slot_value.title(),
                "validate_counter_given_customer_name": 0
            }
        else:
            if validate_counter > validate_limit:
                slots = {
                    "given_customer_name": slot_value,
                    "validate_counter_given_customer_name": 0
                }
            else:
                dispatcher.utter_message(response="utter_retry")
                slots = {
                    "given_customer_name": None,
                    "validate_counter_given_customer_name": validate_counter
                }
        return slots

    def validate_customer_phone_number(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict,) -> Dict[Text, Any]:
        if not slot_value:
            slot_value = "empty"
        validate_limit = 2
        validate_counter = tracker.get_slot("validate_counter_customer_phone_number")
        validate_counter += 1
        words = re.split('-|\s', slot_value)
        words = [x for x in words if x]
        customer_phone_number = ""
        for word in words:
            if word.isdigit():
                customer_phone_number += word
        match =re.match("^\d+$", customer_phone_number)
        if match:
            slots = {
                "customer_phone_number": customer_phone_number,
                "validate_counter_customer_phone_number": 0
            }
        else:
            if validate_counter > validate_limit:
                slots = {
                    "customer_phone_number": slot_value,
                    "customer_phone_number_confirmed": False,
                    "validate_counter_customer_phone_number": 0
                }
            else:
                dispatcher.utter_message(response="utter_retry")
                slots = {
                    "customer_phone_number": None,
                    "validate_counter_customer_phone_number": validate_counter
                }
        return slots

    def validate_customer_phone_number_confirmed(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict, ) -> Dict[Text, Any]:
        validate_limit = 0
        validate_counter = tracker.get_slot("validate_counter_customer_phone_number_confirmed")
        validate_counter += 1
        latest_intent = tracker.get_intent_of_latest_message()
        if latest_intent == "affirm":
            slots = {
                "customer_phone_number_confirmed": True,
                "validate_counter_customer_phone_number_confirmed": 0
            }
        else:
            if validate_counter > validate_limit:
                slots = {
                    "customer_phone_number_confirmed": False,
                    "validate_counter_customer_phone_number_confirmed": 0
                }
            else:
                dispatcher.utter_message(response="utter_retry")
                slots = {
                    "customer_phone_number_confirmed": None,
                    "validate_counter_customer_phone_number_confirmed": validate_counter
                }
        return slots

class ValidateClaimReportForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_claim_report_form"

    async def required_slots(self, slots_mapped_in_domain: List[Text], dispatcher: "CollectingDispatcher", tracker: "Tracker", domain: "DomainDict",) -> Optional[List[Text]]:
        required_slots = ["given_incident_time"] + slots_mapped_in_domain + ["given_insurance_type"]
        return required_slots

    async def extract_given_incident_time(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> Dict[Text, Any]:
        logging.critical("extract_given_incident_time")
        given_incident_time = tracker.get_slot("given_incident_time")
        duckling_time = tracker.get_slot("time")
        if given_incident_time:
            logging.critical(f"Slot given_incident_time exists with value {given_incident_time}")
            return {"given_incident_time": given_incident_time}
        elif duckling_time:
            logging.critical(f"Slot time exists with value {duckling_time}")
            return {"given_incident_time": duckling_time}
        return {"given_incident_time": None}

    async def extract_given_insurance_type(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> Dict[Text, Any]:
        logging.critical("extract_given_insurance_type")
        given_insurance_type = tracker.get_slot("given_insurance_type")
        entity_insurance_type = tracker.get_slot("insurance_type")
        if given_insurance_type:
            logging.critical(f"Slot given_insurance_type exists with value {given_insurance_type}")
            return {"given_insurance_type": given_insurance_type}
        elif entity_insurance_type:
            logging.critical(f"Slot insurance_type exists with value {entity_insurance_type}")
            return {"given_insurance_type": entity_insurance_type}
        return {"given_insurance_type": None}

    async def validate_given_incident_time(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict,) -> Dict[Text, Any]:
        logging.critical("validate_given_incident_time ")
        requested_slot  =tracker.get_slot("requested_slot")
        if requested_slot != "given_incident_time":
            return []
        validate_limit = 2
        validate_counter = tracker.get_slot("validate_counter_given_incident_number")
        validate_counter += 1
        logging.critical(slot_value)
        if slot_value:
            given_incident_time = slot_value.split("T")[0]
            slots = {
                "given_incident_time": given_incident_time,
                "validate_counter_given_incident_number": 0
            }
        else:
            if validate_counter > validate_limit:
                slots = {
                    "given_incident_time": "-",
                    "validate_counter_given_incident_number": 0
                }
            else:
                dispatcher.utter_message(response="utter_retry")
                slots = {
                    "given_incident_time": None,
                    "validate_counter_given_incident_number": validate_counter
                }
        return slots

    async def validate_given_insurance_number(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict,) -> Dict[Text, Any]:
        logging.critical("validate_given_insurance_number "*3)
        if not slot_value:
            slot_value = "empty"
        validate_limit = 2
        validate_counter = tracker.get_slot("validate_counter_given_insurance_number")
        validate_counter += 1
        words = re.split('-|\s', slot_value)
        words = [x for x in words if x]
        given_insurance_number = ""
        for word in words:
            if word.isdigit():
                given_insurance_number += word
        match =re.match("^9\d{11}$", given_insurance_number)
        logging.critical(f"Got insurance number: {given_insurance_number} with matching result: {match}")
        if match and given_insurance_number in baza_polisy_dict:
            logging.critical(f"Insurance {given_insurance_number} found in database.")
            system_subject_type = baza_polisy_dict[given_insurance_number]["Przedmiot ubezpieczenia"]
            system_customer_pesel = baza_polisy_dict[given_insurance_number]["Pesel ubezpieczonego"]
            system_customer_name = baza_polisy_dict[given_insurance_number]["Imię i nazwisko ubezpieczonego"]
            system_vehicle_number = baza_polisy_dict[given_insurance_number]["Nr rejestracyjny / adres"]
            slots = {
                "given_insurance_number": given_insurance_number.upper(),
                "system_insurance_number": given_insurance_number.upper(),
                "system_subject_type": system_subject_type,
                "system_customer_pesel": system_customer_pesel,
                "system_customer_name": system_customer_name,
                "system_vehicle_number": system_vehicle_number,
                "validate_counter_given_insurance_number": 0
            }
            logging.critical("Setting slots:")
            logging.critical(slots)
        else:
            if validate_counter > validate_limit:
                slots = {
                    "given_insurance_number": slot_value,
                    "validate_counter_given_insurance_number": 0
                }
            else:
                dispatcher.utter_message(response="utter_retry")
                slots = {
                    "given_insurance_number": None,
                    "validate_counter_given_insurance_number": validate_counter
                }
        return slots

    async def validate_given_insurance_type(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict,) -> Dict[Text, Any]:
        logging.critical("validate_given_insurance_type ")
        requested_slot  =tracker.get_slot("requested_slot")
        if requested_slot != "given_insurance_type":
            return []
        if not slot_value:
            slot_value = "empty"
        validate_limit = 2
        validate_counter = tracker.get_slot("validate_counter_given_insurance_type")
        validate_counter += 1
        logging.critical(f"validate_counter_given_insurance_type: {validate_counter}")
        given_insurance_type = slot_value
        if given_insurance_type in ["internal", "external"]:
            slots = {
                "given_insurance_type": given_insurance_type,
                "validate_counter_given_insurance_type": 0
            }
        else:
            if validate_counter > validate_limit:
                slots = {
                    "given_insurance_type": slot_value,
                    "validate_counter_given_insurance_type": 0
                }
            else:
                dispatcher.utter_message(response="utter_retry")
                slots = {
                    "given_insurance_type": None,
                    "validate_counter_given_insurance_type": validate_counter
                }
        return slots

    async def validate_given_vehicle_number(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict,) -> Dict[Text, Any]:
        logging.critical("validate_given_vehicle_number ")
        if not slot_value:
            slot_value = "empty"
        if slot_value == '-':
            slots = {
                "given_vehicle_number": slot_value,
                "validate_counter_given_vehicle_number": 0
            }
            return slots
        validate_limit = 2
        validate_counter = tracker.get_slot("validate_counter_given_vehicle_number")
        validate_counter += 1
        logging.critical(f"validate_counter_given_vehicle_number: {validate_counter}")
        words = re.split('\s', slot_value)
        words = [x for x in words if x]
        given_vehicle_number = ""
        for word in words:
            given_vehicle_number += word.upper()
        match =re.match("^[A-Z0-9]*$", given_vehicle_number)
        if match:
            slots = {
                "given_vehicle_number": given_vehicle_number,
                "validate_counter_given_vehicle_number": 0
            }
        else:
            if validate_counter > validate_limit:
                slots = {
                    "given_vehicle_number": slot_value,
                    "validate_counter_given_vehicle_number": 0
                }
            else:
                dispatcher.utter_message(response="utter_retry")
                slots = {
                    "given_vehicle_number": None,
                    "validate_counter_given_vehicle_number": validate_counter
                }
        return slots

class ValidateIncidentNumberForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_incident_number_form"

    def validate_given_incident_number(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict,) -> Dict[Text, Any]:
        logging.critical("validate_given_incident_number ")
        if not slot_value:
            slot_value = "empty"
        validate_limit = 2
        validate_counter = tracker.get_slot("validate_counter_given_incident_number")
        validate_counter += 1
        words = re.split('\s', slot_value)
        words = [x for x in words if x]
        given_incident_number = ""
        for word in words:
            if word in ["minus", "myślnik"]:
                word = "-"
            given_incident_number += word.upper()
        given_incident_number = given_incident_number.replace("-", "")
        given_incident_number = given_incident_number.translate({8211: None})
        logging.critical(f"Numer zgłoszenia wprowadzony: {slot_value}")
        logging.critical(f"Numer zgłoszenia po modyfikacji: {given_incident_number}")
        match1 =re.match("^[WH]\d{12}$", given_incident_number, re.IGNORECASE)
        match2 =re.match("^[WH]\d{14}$", given_incident_number, re.IGNORECASE)
        match = False
        if match1:
            match = True
        elif match2:
            match = True
            given_incident_number = given_incident_number[:13] + "-" + given_incident_number[-2:]
        logging.critical(f"Got incident number: {given_incident_number} with matching result: {match}")
        if match and given_incident_number in baza_szkody_dict:
            subject_type_map = {
                'Pojazd': 'MOTOR',
                'Nieruchomość': 'PROPERTY',
                'Szkoda osobowa': 'PERSONAL'
            }
            logging.critical(f"Incident {given_incident_number} found in database.")
            incident_missing_documents_list = None
            incident_documents_submission_date = None
            incident_inspection_date = None
            incident_withdrawal_amount = None
            if baza_szkody_dict[given_incident_number]["Czy brakuje dokumentów"] == "Tak":
                incident_missing_documents_list = baza_szkody_dict[given_incident_number]["Jakich dokumentów brakuje"]
            if baza_szkody_dict[given_incident_number]["Wpływ dokumentów ostatnich (data)"]:
                incident_documents_submission_date = baza_szkody_dict[given_incident_number]["Wpływ dokumentów ostatnich (data)"]
            if baza_szkody_dict[given_incident_number]["Czy zostały zlecone oględziny"] == "Tak":
                incident_inspection_date = baza_szkody_dict[given_incident_number]["data oględzin"]
            if baza_szkody_dict[given_incident_number]["Kwota wypłaty"] and int(baza_szkody_dict[given_incident_number]["Kwota wypłaty"]) > 0:
                incident_withdrawal_amount = baza_szkody_dict[given_incident_number]["Kwota wypłaty"]
            system_agent_email = baza_szkody_dict[given_incident_number]["Email opiekuna"]
            system_insurance_number = baza_szkody_dict[given_incident_number]["Nr polisy"]
            system_subject_type = subject_type_map[baza_szkody_dict[given_incident_number]["Rodzaj przedmiotu"]]
            system_customer_name = baza_szkody_dict[given_incident_number]["Imię i nazwisko poszkodowanego"]
            system_customer_pesel = baza_szkody_dict[given_incident_number]["Pesel poszkodowanego"]
            system_vehicle_number = baza_szkody_dict[given_incident_number]["Nr rejestracyjny"]
            slots = {
                "given_incident_number": given_incident_number,
                "system_incident_number": given_incident_number,
                "system_insurance_number": system_insurance_number,
                "system_subject_type": system_subject_type,
                "system_customer_name": system_customer_name,
                "system_customer_pesel": system_customer_pesel,
                "system_vehicle_number": system_vehicle_number,
                "system_agent_email": system_agent_email,
                "incident_number_verified": True,
                "incident_missing_documents_list": incident_missing_documents_list,
                "incident_documents_submission_date": incident_documents_submission_date,
                "incident_inspection_date": incident_inspection_date,
                "incident_withdrawal_amount": incident_withdrawal_amount,
                "validate_counter_given_incident_number": 0
            }
            logging.critical("Setting slots:")
            logging.critical(slots)
        else:
            if validate_counter > validate_limit:
                slots = {
                    "given_incident_number": slot_value,
                    "incident_number_verified": False,
                    "validate_counter_given_incident_number": 0
                }
            else:
                dispatcher.utter_message(response="utter_retry")
                slots = {
                    "given_incident_number": None,
                    "incident_number_verified": False,
                    "validate_counter_given_incident_number": validate_counter
                }
        return slots

class ValidateInsuranceNumberForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_insurance_number_form"

    def validate_given_insurance_number(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict,) -> Dict[Text, Any]:
        if not slot_value:
            slot_value = "empty"
        validate_limit = 2
        validate_counter = tracker.get_slot("validate_counter_given_insurance_number")
        validate_counter += 1
        words = re.split('-|\s', slot_value)
        words = [x for x in words if x]
        given_insurance_number = ""
        for word in words:
            if word.isdigit():
                given_insurance_number += word
        match =re.match("^9\d{11}$", given_insurance_number)
        logging.critical(f"Got insurance number: {given_insurance_number} with matching result: {match}")
        if match and given_insurance_number in baza_polisy_dict:
            logging.critical(f"Insurance {given_insurance_number} found in database.")
            next_installment_number = None
            next_installment_amount = None
            next_installment_date = None
            insurance_payment_2_amount = baza_polisy_dict[given_insurance_number]["Kwota płatności 2"]
            insurance_payment_2_date = baza_polisy_dict[given_insurance_number]["Termin płatności 2"]
            if baza_polisy_dict[given_insurance_number]["Czy opłacona 2?"] == "TAK":
                insurance_payment_2_done = True
            else:
                insurance_payment_2_done = False
                next_installment_number = 2
                next_installment_amount = insurance_payment_2_amount
                next_installment_date = insurance_payment_2_date
            insurance_payment_1_amount = baza_polisy_dict[given_insurance_number]["Kwota płatności 1"]
            insurance_payment_1_date = baza_polisy_dict[given_insurance_number]["Termin płatności 1"]
            if baza_polisy_dict[given_insurance_number]["Czy opłacona 1?"] == "TAK":
                insurance_payment_1_done = True
            else:
                insurance_payment_1_done = False
                next_installment_number = 1
                next_installment_amount = insurance_payment_1_amount
                next_installment_date = insurance_payment_1_date
            insurance_active = baza_polisy_dict[given_insurance_number]["Polisa aktywna"]
            insurance_end_date = baza_polisy_dict[given_insurance_number]["Data zakończenia"]
            system_subject_type = baza_polisy_dict[given_insurance_number]["Przedmiot ubezpieczenia"]
            system_customer_pesel = baza_polisy_dict[given_insurance_number]["Pesel ubezpieczonego"]
            system_customer_name = baza_polisy_dict[given_insurance_number]["Imię i nazwisko ubezpieczonego"]
            system_vehicle_number = baza_polisy_dict[given_insurance_number]["Nr rejestracyjny / adres"]
            slots = {
                "given_insurance_number": given_insurance_number.upper(),
                "system_insurance_number": given_insurance_number.upper(),
                "insurance_number_verified": True,
                "system_subject_type": system_subject_type,
                "system_customer_pesel": system_customer_pesel,
                "system_customer_name": system_customer_name,
                "system_vehicle_number": system_vehicle_number,
                "insurance_payment_1_amount": insurance_payment_1_amount,
                "insurance_payment_1_done": insurance_payment_1_done,
                "insurance_payment_1_date": insurance_payment_1_date,
                "insurance_payment_2_amount": insurance_payment_2_amount,
                "insurance_payment_2_done": insurance_payment_2_done,
                "insurance_payment_2_date": insurance_payment_2_date,
                "insurance_active": insurance_active,
                "insurance_end_date": insurance_end_date,
                "next_installment_number": next_installment_number,
                "next_installment_amount": next_installment_amount,
                "next_installment_date": next_installment_date,
                "validate_counter_given_insurance_number": 0
            }
            logging.critical("Setting slots:")
            logging.critical(slots)
        else:
            if validate_counter > validate_limit:
                slots = {
                    "given_insurance_number": slot_value,
                    "insurance_number_verified": False,
                    "validate_counter_given_insurance_number": 0
                }
            else:
                dispatcher.utter_message(response="utter_retry")
                slots = {
                    "given_insurance_number": None,
                    "insurance_number_verified": False,
                    "validate_counter_given_insurance_number": validate_counter
                }
        return slots

class ValidateCustomerAuthenticationForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_customer_authentication_form"

    async def required_slots(self, slots_mapped_in_domain: List[Text], dispatcher: "CollectingDispatcher", tracker: "Tracker", domain: "DomainDict",) -> Optional[List[Text]]:
        required_slots = ["given_subject_type"] + slots_mapped_in_domain
        return required_slots

    async def extract_given_subject_type(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> Dict[Text, Any]:
        logging.critical("extract_given_subject_type")
        given_subject_type = tracker.get_slot("given_subject_type")
        entity_subject = tracker.get_slot("subject")
        if given_subject_type:
            logging.critical(f"Slot given_subject_type exists with value {given_subject_type}")
            return {"given_subject_type": given_subject_type}
        elif entity_subject:
            logging.critical(f"Slot subject exists with value {entity_subject}")
            return {"given_subject_type": entity_subject}
        return {"given_subject_type": None}

    def validate_given_subject_type(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict,) -> Dict[Text, Any]:
        logging.critical("validate_given_subject_type")
        requested_slot  =tracker.get_slot("requested_slot")
        if requested_slot != "given_subject_type":
            return []
        if not slot_value:
            slot_value = "-"
        validate_limit = 2
        validate_counter = tracker.get_slot("validate_counter_given_subject_type")
        validate_counter += 1
        given_subject_type = slot_value
        if given_subject_type in ["PERSONAL", "MOTOR", "PROPERTY"]:
            slots = {
                "given_subject_type": given_subject_type,
                "validate_counter_given_subject_type": 0
            }
        else:
            if validate_counter > validate_limit:
                slots = {
                    "given_subject_type": slot_value,
                    "validate_counter_given_subject_type": 0
                }
            else:
                dispatcher.utter_message(response="utter_retry")
                slots = {
                    "given_subject_type": None,
                    "validate_counter_given_subject_type": validate_counter
                }
        logging.critical(slots)
        return slots

    def validate_given_customer_name(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict,) -> Dict[Text, Any]:
        logging.critical("validate_given_customer_name")
        if not slot_value:
            slot_value = "-"
        validate_limit = 2
        validate_counter = tracker.get_slot("validate_counter_given_customer_name")
        validate_counter += 1
        words = slot_value.split()
        given_customer_name = slot_value.title()
        if (len(words) == 2) \
            and ((words[0].upper() in db_male_firstname) or (words[0].upper() in db_female_firstname) or (words[0].upper() in db_male_lastname) or (words[0].upper() in db_female_lastname)) \
            and ((words[1].upper() in db_male_firstname) or (words[1].upper() in db_female_firstname) or (words[1].upper() in db_male_lastname) or (words[1].upper() in db_female_lastname)):
            slots = {
                "given_customer_name": given_customer_name,
                "validate_counter_given_customer_name": 0
            }
        else:
            if validate_counter > validate_limit:
                slots = {
                    "given_customer_name": slot_value,
                    "validate_counter_given_customer_name": 0
                }
            else:
                dispatcher.utter_message(response="utter_retry")
                slots = {
                    "given_customer_name": None,
                    "validate_counter_given_customer_name": validate_counter
                }
        return slots

    def validate_given_customer_pesel(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict,) -> Dict[Text, Any]:
        if not slot_value:
            slot_value = "-"
        validate_limit = 2
        validate_counter = tracker.get_slot("validate_counter_given_customer_pesel")
        validate_counter += 1
        given_customer_pesel = ""
        words = slot_value.split()
        for word in words:
            if word.isdigit():
                given_customer_pesel += word
        prog = re.compile('^\d{11}$', re.IGNORECASE)
        match = prog.match(given_customer_pesel)
        logging.critical(f"Got customer pesel: {given_customer_pesel} from slot_value: {slot_value} with matching result: {match}")
        if match :
            slots = {
                "given_customer_pesel": given_customer_pesel,
                "validate_counter_given_customer_pesel": 0
            }
        else:
            if validate_counter > validate_limit:
                slots = {
                    "given_customer_pesel": slot_value,
                    "validate_counter_given_customer_pesel": 0
                }
            else:
                dispatcher.utter_message(response="utter_retry")
                slots = {
                    "given_customer_pesel": None,
                    "validate_counter_given_customer_pesel": validate_counter
                }
        logging.critical(slots)
        return slots

class ActionSetGivenSubjectType(Action):

    def name(self) -> Text:
        return "action_set_given_subject_type"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        events = []
        subject = tracker.get_slot("subject")
        if subject in ["MOTOR", "PROPERTY", "PERSONAL"]:
            events.append(SlotSet("given_subject_type", subject))
        return events

class ActionInitClaimReport(Action):

    def name(self) -> Text:
        return "action_init_claim_report"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        events = []
        subject_type = tracker.get_slot("subject")
        if subject_type != "MOTOR":
            events.append(SlotSet("given_vehicle_number", "-"))
        return events

class ActionSetIncidentStatusPath(Action):

    def name(self) -> Text:
        return "action_set_incident_status_path"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        events = []
        incident_status_path = tracker.get_slot("incident_status_path")
        incident_status_path_flag = True
        if not incident_status_path:
            latest_intent = tracker.get_intent_of_latest_message()
            logging.critical(f"Intent for status path: {latest_intent}")
            if latest_intent == "incident_status_consultant_direct":
                incident_status_path = "consultant_direct"
            elif latest_intent == "incident_status_manager_message":
                incident_status_path = "manager_message"
            elif latest_intent == "incident_status_bot_info_inspection":
                incident_status_path = "bot_info_inspection"
            elif latest_intent == "incident_status_bot_info_withdrawal":
                incident_status_path = "bot_info_withdrawal"
            elif latest_intent == "incident_status_bot_info_documents":
                incident_status_path = "bot_info_documents"
            else:
                incident_status_path = None
                incident_status_path_flag = False
                logging.critical("No status path !!!")
        logging.critical(f"Setting slot incident_status_path to {incident_status_path}")
        events.append(SlotSet("incident_status_path", incident_status_path))
        return events

class ActionSetIncidentStatusPathFlag(Action):

    def name(self) -> Text:
        return "action_set_incident_status_path_flag"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        events = []
        incident_status_path = tracker.get_slot("incident_status_path")
        incident_status_path_flag = False
        if incident_status_path:
            incident_status_path_flag = True
        logging.critical(f"Setting slot incident_status_path_flag to {incident_status_path_flag}")
        events.append(SlotSet("incident_status_path_flag", incident_status_path_flag))
        return events

class ActionSetCustomerQuestionPath(Action):

    def name(self) -> Text:
        return "action_set_customer_question_path"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        events = []
        customer_question_path = tracker.get_slot("customer_question_path")
        if not customer_question_path:
            latest_intent = tracker.get_intent_of_latest_message()
            logging.critical(f"Intent for customer question path: {latest_intent}")
            if latest_intent == "customer_question_payments":
                customer_question_path = "bot_info_payments"
            elif latest_intent == "customer_question_validity":
                customer_question_path = "bot_info_validity"
            else:
                customer_question_path = None
                logging.critical("No customer question path !!!")
        logging.critical(f"Setting slot customer_question_path to {customer_question_path}")
        events.append(SlotSet("customer_question_path", customer_question_path))
        return events


class ActionSelectUtterIncidentStatus(Action):

    def name(self) -> Text:
        return "action_select_utter_incident_status"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        events = []
        incident_status_path = tracker.get_slot("incident_status_path")
        if incident_status_path == "bot_info_inspection":
            incident_inspection_date = tracker.get_slot("incident_inspection_date")
            if incident_inspection_date:
                dispatcher.utter_message(response="utter_incident_status_inspection")
            else:
                dispatcher.utter_message(response="utter_incident_status_no_inspection")
        elif incident_status_path == "bot_info_withdrawal":
            incident_withdrawal_amount = tracker.get_slot("incident_withdrawal_amount")
            if incident_withdrawal_amount:
                dispatcher.utter_message(response="utter_incident_status_withdrawal")
            else:
                dispatcher.utter_message(response="utter_incident_status_no_withdrawal")
        elif incident_status_path == "bot_info_documents":
            incident_documents_submission_date = tracker.get_slot("incident_documents_submission_date")
            incident_missing_documents_list = tracker.get_slot("incident_missing_documents_list")
            if incident_documents_submission_date:
                if incident_missing_documents_list:
                    dispatcher.utter_message(response="utter_incident_status_date_list")
                else:
                    dispatcher.utter_message(response="utter_incident_status_date_no_list")
            else:
                if incident_missing_documents_list:
                    dispatcher.utter_message(response="utter_incident_status_no_date_list")
                else:
                    dispatcher.utter_message(response="utter_incident_status_no_date_no_list")
        elif incident_status_path == "consultant_direct":
            dispatcher.utter_message(response="utter_incident_status_transfer")
        elif incident_status_path == "manager_message":
            dispatcher.utter_message(response="utter_incident_status_message")
        else:
            dispatcher.utter_message(response="utter_error")
        events.append(FollowupAction('action_listen'))
        return events

class ActionSelectUtterCustomerQuestion(Action):

    def name(self) -> Text:
        return "action_select_utter_customer_question"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        events = []
        customer_question_path = tracker.get_slot("customer_question_path")
        if customer_question_path == "bot_info_payments":
            insurance_payment_1_done = tracker.get_slot("insurance_payment_1_done")
            insurance_payment_2_done = tracker.get_slot("insurance_payment_2_done")
            if insurance_payment_1_done and insurance_payment_2_done:
                dispatcher.utter_message(response="utter_customer_question_payment_done")
            else:
                dispatcher.utter_message(response="utter_customer_question_payment_waiting")
        elif customer_question_path == "bot_info_validity":
            insurance_active = tracker.get_slot("insurance_active")
            if insurance_active:
                dispatcher.utter_message(response="utter_customer_question_insurance_active")
            else:
                dispatcher.utter_message(response="utter_customer_question_insurance_inactive")
        else:
            dispatcher.utter_message(response="utter_error")
        events.append(FollowupAction('action_listen'))
        return events

class ActionPerformCustomerAuthentication(Action):

    def name(self) -> Text:
        return "action_perform_customer_authentication"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        events = []
        system_subject_type = tracker.get_slot("system_subject_type")
        system_customer_name = tracker.get_slot("system_customer_name")
        system_customer_pesel = tracker.get_slot("system_customer_pesel")
        given_subject_type = tracker.get_slot("given_subject_type")
        given_customer_name = tracker.get_slot("given_customer_name")
        given_customer_pesel = tracker.get_slot("given_customer_pesel")

        auth_level = 0

        # Compare customer name
        logging.critical(f"system_customer_name: {system_customer_name}, given_customer_name: {given_customer_name}")
        system_customer_name_set = set(system_customer_name.split(' '))
        given_customer_name_set = set(given_customer_name.split(' '))
        if system_customer_name_set == given_customer_name_set:
            auth_level += 1

        # Compare subject type
        logging.critical(f"system_subject_type: {system_subject_type}, given_subject_type: {given_subject_type}")
        if system_subject_type == given_subject_type:
            auth_level += 1

        # Compare customer pesel
        logging.critical(f"system_customer_pesel: {system_customer_pesel}, given_customer_pesel: {given_customer_pesel}")
        if system_customer_pesel == given_customer_pesel:
            auth_level += 1

        if auth_level > 1:
            events.append(SlotSet("customer_authenticated", True))
        else:
            events.append(SlotSet("customer_authenticated", False))
        return events

