version: "2.0"

stories:

# Claim flow
- story: claim report with assistance
  steps:
  - intent: claim_report
  - action: utter_give_assistance
  - intent: affirm
  - action: utter_assistance_transfer

- story: claim report without customer info
  steps:
  - intent: claim_report
  - action: utter_give_assistance
  - intent: deny
  - action: customer_info_form
  - active_loop: customer_info_form
  - active_loop: null
  - slot_was_set:
    - customer_phone_number_confirmed: false
  - action: utter_claim_transfer

- story: claim report without claim subject
  steps:
  - intent: connected
  - action: utter_greet
  - intent: claim_report
  - action: utter_give_assistance
  - intent: deny
  - action: customer_info_form
  - active_loop: customer_info_form
  - active_loop: null
  - slot_was_set:
    - customer_phone_number_confirmed: true
  - action: action_set_subject_type
  - slot_was_set:
    - subject_type: null
  - action: utter_describe_incident
  - intent: claim_report
  - slot_was_set:
    - subject_type: null
  - action: utter_claim_transfer

- story: claim report with claim subject - path 1
  steps:
  - intent: connected
  - action: utter_greet
  - intent: claim_report
  - action: utter_give_assistance
  - intent: deny
  - action: customer_info_form
  - active_loop: customer_info_form
  - active_loop: null
  - slot_was_set:
    - customer_phone_number_confirmed: true
  - action: action_set_subject_type
  - slot_was_set:
    - subject_type: null
  - action: utter_describe_incident
  - intent: claim_report
  - slot_was_set:
    - subject_type: "any"
  - action: action_init_claim_report
  - action: claim_report_form
  - active_loop: claim_report_form
  - active_loop: null
  - action: utter_claim_transfer

- story: claim report with claim subject - path 2
  steps:
  - intent: connected
  - action: utter_greet
  - intent: claim_report
  - action: utter_give_assistance
  - intent: deny
  - action: customer_info_form
  - active_loop: customer_info_form
  - active_loop: null
  - slot_was_set:
    - customer_phone_number_confirmed: true
  - action: action_set_subject_type
  - slot_was_set:
    - subject_type: "any"
  - action: action_init_claim_report
  - action: claim_report_form
  - active_loop: claim_report_form
  - active_loop: null
  - action: utter_claim_transfer

