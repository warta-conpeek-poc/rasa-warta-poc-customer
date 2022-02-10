import json
import random
from typing import Any, Text, Dict, List
#
from rasa_sdk import Action, Tracker
from rasa_sdk.events import AllSlotsReset
from rasa_sdk.events import SlotSet
from rasa_sdk.events import SessionStarted
from rasa_sdk.events import ActionExecuted
from rasa_sdk.events import Restarted
from rasa_sdk.events import EventType
from rasa_sdk.events import FollowupAction
from rasa_sdk.executor import CollectingDispatcher
#
#
from rasa_sdk import Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict

import re
import logging
import datetime
import pytz
import csv


logger = logging.getLogger(__name__)

baza_szkody_dict = {}
with open("actions/baza_szkody_utf8.csv") as f:
    f_csv = csv.DictReader(f, delimiter=';')
    for row in f_csv:
        baza_szkody_dict[row['Nr szkody']] = row
    logging.critical(baza_szkody_dict["W202112160034-01"])

baza_polisy_dict = {}
with open("actions/baza_polisy_utf8.csv") as f:
    f_csv = csv.DictReader(f, delimiter=';')
    for row in f_csv:
        baza_polisy_dict[row['Nr polisy']] = row
    # logging.critical(baza_polisy_dict)

class ActionSessionStart(Action):

    def name(self) -> Text:
        return "action_session_start"

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[EventType]:

        logging.critical("Session started !!!")
        events = [SessionStarted(), ActionExecuted("action_listen")]
        metadata = tracker.get_slot("session_started_metadata")
        logging.critical(metadata)
        if metadata and "caller_contact_address" in metadata:
            # events.append(SlotSet("customer_phone_number", metadata["caller_contact_address"]))
            events.append(SlotSet("customer_phone_number", "501003003"))
            # events.append(SlotSet("caller_contact_address", None))
        if metadata and "callee_contact_address" in metadata:
            events.append(SlotSet("service_phone_number", metadata["callee_contact_address"]))

        return events

class ActionAllSlotsReset(Action):

    def name(self) -> Text:
        return "action_all_slots_reset"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(text="Wszystkie dane zostały zresetowane.")
        return [AllSlotsReset()]

class ActionRestarted(Action):

    def name(self) -> Text:
        return "action_restarted"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(text="Konwersacja została zrestartowana.")
        return [Restarted()]

class ActionLowConfidence(Action):

    def name(self) -> Text:
        return "action_low_confidence"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        utter_list = []
        metadata = tracker.latest_message["metadata"]
        logging.info(metadata)
        if "stop_playback_date" in metadata and not metadata["stop_playback_date"]:
            utter_list.append("")
        else:
            utter_list.append("Czy możesz powtórzyć?")
        text_message = random.choice(utter_list)
        custom_message = {
            "blocks": [
                {
                    "text": text_message,
                }
            ]
        }
        if tracker.get_latest_input_channel() == "conpeek-voice":
            dispatcher.utter_message(json_message=custom_message)
        else:
            dispatcher.utter_message(text=text_message)

class ValidateCustomerInfoForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_customer_info_form"

    def validate_confirm_customer_phone_number(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict,) -> Dict[Text, Any]:
        confirm_limit = 2
        customer_info_form_confirm_counter = tracker.get_slot("customer_info_form_confirm_counter")
        logging.critical(f"customer_info_form_confirm_counter: {customer_info_form_confirm_counter}")
        if customer_info_form_confirm_counter:
            customer_info_form_confirm_counter += 1
        else:
            customer_info_form_confirm_counter = 1
        latest_intent = tracker.get_intent_of_latest_message()
        if latest_intent == "affirm":
            return {"customer_info_form_confirm_counter": 0, "confirm_customer_phone_number": True}
        else:
            if customer_info_form_confirm_counter > confirm_limit:
                return {"customer_info_form_confirm_counter": 0, "confirm_customer_phone_number": False, "customer_phone_number": "unconfirmed"}
            else:
                return {"customer_info_form_confirm_counter": customer_info_form_confirm_counter, "confirm_customer_phone_number": None, "customer_phone_number": None}

class ActionSetSubjectType(Action):

    def name(self) -> Text:
        return "action_set_subject_type"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        events = []
        subject_type = tracker.get_slot("subject_type")
        events.append(SlotSet("subject_type", subject_type))
        return events

class ActionInitClaimReport(Action):

    def name(self) -> Text:
        return "action_init_claim_report"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        events = []
        subject_type = tracker.get_slot("subject_type")
        if subject_type != "vehicle":
            events.append(SlotSet("vehicle_number", "-"))
        return events

class ActionSetStatusPath(Action):

    def name(self) -> Text:
        return "action_set_status_path"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        events = []
        status_path = tracker.get_slot("status_path")
        if not status_path:
            latest_intent = tracker.get_intent_of_latest_message()
            logging.critical(f"Intent for status path: {latest_intent}")
            if latest_intent == "claim_status_consultant_direct":
                status_path = "consultant_direct"
            elif latest_intent == "claim_status_manager_message":
                status_path = "manager_message"
            elif latest_intent == "claim_status_bot_info_inspection":
                status_path = "bot_info_inspection"
            elif latest_intent == "claim_status_bot_info_withdrawal":
                status_path = "bot_info_withdrawal"
            elif latest_intent == "claim_status_bot_info_documents":
                status_path = "bot_info_documents"
            else:
                status_path = None
                logging.critical("No status path !!!")
        logging.critical(f"Setting slot status_path to {status_path}")
        events.append(SlotSet("status_path", status_path))
        return events

class ActionGetIncidentInfo(Action):

    def name(self) -> Text:
        return "action_get_incident_info"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        events = []
        incident_number = "".join(tracker.latest_message['text'].split())
        logging.critical(incident_number)
        prog = re.compile("^[wh]\d{12}(?:-\d{2})*$", re.IGNORECASE)
        match = prog.match(incident_number)
        logging.critical(f"Incident number: {incident_number}")
        logging.critical(f"Match: {match}")
        if match:
            events.append(SlotSet("incident_number", incident_number))
            if incident_number in baza_szkody_dict:
                logging.critical("Incident found in baza_szkody.")
                incident_missing_documents_list = None
                incident_documents_submission_date = None
                incident_inspection_date = None
                incident_withdrawal_amount = None
                logging.critical(baza_szkody_dict[incident_number])
                if baza_szkody_dict[incident_number]["Czy brakuje dokumentów"] == "Tak":
                    incident_missing_documents_list = baza_szkody_dict[incident_number]["Jakich dokumentów brakuje"]
                if baza_szkody_dict[incident_number]["Wpływ dokumentów ostatnich (data)"]:
                    incident_documents_submission_date = baza_szkody_dict[incident_number]["Wpływ dokumentów ostatnich (data)"]
                if baza_szkody_dict[incident_number]["Czy zostały zlecone oględziny"] == "Tak":
                    incident_inspection_date = baza_szkody_dict[incident_number]["data oględzin"]
                if baza_szkody_dict[incident_number]["Kwota wypłaty"] and int(baza_szkody_dict[incident_number]["Kwota wypłaty"]) > 0:
                    incident_withdrawal_amount = baza_szkody_dict[incident_number]["Kwota wypłaty"]
                incident_agent_email = baza_szkody_dict[incident_number]["Email opiekuna"]
                events.append(SlotSet("incident_missing_documents_list", incident_missing_documents_list))
                events.append(SlotSet("incident_documents_submission_date", incident_documents_submission_date))
                events.append(SlotSet("incident_inspection_date", incident_inspection_date))
                events.append(SlotSet("incident_withdrawal_amount", incident_withdrawal_amount))
                events.append(SlotSet("incident_agent_email", incident_agent_email))
                logging.critical(incident_missing_documents_list)
                logging.critical(incident_documents_submission_date)
                logging.critical(incident_inspection_date)
                logging.critical(incident_withdrawal_amount)
                logging.critical(incident_agent_email)
        return events

class ActionSelectUtterStatusBotInfo(Action):

    def name(self) -> Text:
        return "action_select_utter_status_bot_info"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        events = []
        status_path = tracker.get_slot("status_path")
        if status_path == "bot_info_inspection":
            incident_inspection_date = tracker.get_slot("incident_inspection_date")
            if incident_inspection_date:
                events.append(FollowupAction("utter_status_inspection"))
            else:
                events.append(FollowupAction("utter_status_no_inspection"))
        elif status_path == "bot_info_withdrawal":
            incident_withdrawal_amount = tracker.get_slot("incident_withdrawal_amount")
            if incident_withdrawal_amount:
                events.append(FollowupAction("utter_status_withdrawal"))
            else:
                events.append(FollowupAction("utter_status_no_withdrawal"))
        elif status_path == "bot_info_documents":
            incident_documents_submission_date = tracker.get_slot("incident_documents_submission_date")
            incident_missing_documents_list = tracker.get_slot("incident_missing_documents_list")
            if incident_documents_submission_date:
                if incident_missing_documents_list:
                    events.append(FollowupAction("utter_status_date_list"))
                else:
                    events.append(FollowupAction("utter_status_date_no_list"))
            else:
                if incident_missing_documents_list:
                    events.append(FollowupAction("utter_status_no_date_list"))
                else:
                    events.append(FollowupAction("utter_status_no_date_no_list"))
        else:
            events.append(FollowupAction("utter_error"))
        return events

class ActionPerformCustomerAuthentication(Action):

    def name(self) -> Text:
        return "action_perform_customer_authentication"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        events = []
        events.append(SlotSet("customer_authenticated", True))
        return events

