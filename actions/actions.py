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
from rasa_sdk.types import DomainDict
import re
import logging
import datetime
import pytz



logger = logging.getLogger(__name__)

class ActionSessionStart(Action):

    def name(self) -> Text:
        return "action_session_start"

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[EventType]:

        logging.critical("Session started !!!")
        events = [SessionStarted()]
        metadata = tracker.get_slot("session_started_metadata")
        logging.critical(metadata)
        if metadata and "caller_contact_address" in metadata:
            events.append(SlotSet("customer_phone_number", metadata["caller_contact_address"]))
        if metadata and "service_phone_number" in metadata:
            events.append(SlotSet("callee_id", metadata["callee_contact_address"]))

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

