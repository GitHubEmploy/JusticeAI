from flask import jsonify, abort, make_response

import util

util.load_src_dir_to_sys_path()
from postgresql_db.models import *
from rasa.rasa_classifier import RasaClassifier
from services import mlService
from services.responseStrings import Responses

from nlp_service.app import db

# Globals
from src.postgresql_db.models import Conversation, ClaimCategory

minimum_percent_difference = 0.3

# Rasa Classifier
rasaClassifier = RasaClassifier()
rasaClassifier.train(force_train=False)


def classify_claim_category(conversation_id, message):
    if conversation_id is None or message is None:
        abort(make_response(jsonify(message="Must provide conversation_id and message"), 400))

    # Retrieve conversation
    conversation = db.session.query(Conversation).get(conversation_id)

    # Classify claim category based on message
    claim_category = __classify_claim_category(message)

    # Set conversation's claim category
    conversation.claim_category = {
        'ask_lease_termination': ClaimCategory.LEASE_TERMINATION,
        'ask_rent_change': ClaimCategory.RENT_CHANGE,
        'ask_nonpayment': ClaimCategory.NONPAYMENT,
        'ask_deposit': ClaimCategory.DEPOSITS
    }[claim_category]

    # Get first fact based on claim category
    ml_request = mlService.submit_claim_category(conversation.claim_category)
    first_fact_id = ml_request['fact_id']

    # Retrieve the Fact from DB
    first_fact = db.session.query(Fact).get(first_fact_id)

    # Save first fact as current fact
    conversation.current_fact = first_fact

    # Commit
    db.session.commit()

    # Generate next message
    first_fact_question = Responses.fact_question(first_fact.name)
    message = Responses.chooseFrom(Responses.category_acknowledge).format(
        claim_category=conversation.claim_category.value.lower().replace("_", " "),
        first_question=first_fact_question)

    return jsonify({
        "message": message
    })


def classify_fact_value(conversation_id, message):
    if conversation_id is None or message is None:
        abort(make_response(jsonify(message="Must provide conversation_id and message"), 400))

    # Retrieve conversation
    conversation = db.session.query(Conversation).get(conversation_id)

    # Retrieve current_fact from conversation
    current_fact = conversation.current_fact

    # Extract entity from message based on current fact
    question = None

    fact_entity_value = __extract_entity(current_fact.name, message)
    if fact_entity_value is not None:
        # Pass fact with extracted entity to ML service
        ml_request = mlService.submit_resolved_fact(conversation, current_fact, fact_entity_value)
        new_fact_id = ml_request['fact_id']

        # Retrieve the Fact from DB
        if new_fact_id:
            new_fact = db.session.query(Fact).get(new_fact_id)

            # Set current_fact to new_fact (returned from ML service)
            conversation.current_fact = new_fact

            # Generate question for next fact (returned from ML service)
            question = Responses.fact_question(new_fact.name)
        else:
            question = "FACT DUMP: "
            for fact_entity in conversation.fact_entities:
                question += "{}:{}, ".format(fact_entity.fact.name, fact_entity.value)
    else:
        question = Responses.chooseFrom(Responses.clarify)

    # Commit
    db.session.commit()

    return jsonify({
        "message": question
    })


def __classify_claim_category(message):
    classify_dict = rasaClassifier.classify_problem_category(message)
    print(classify_dict)

    # Return the claim category, or None if the answer was insufficient in determining one
    if __is_answer_sufficient(classify_dict):
        determined_problem_category = classify_dict['intent']
        print("Confidence: {}%".format(round(determined_problem_category['confidence'], 3) * 100))
        print("Intent: {}".format(determined_problem_category['name']))
        return determined_problem_category['name']
    else:
        return None


def __extract_entity(current_fact_name, message):
    classify_dict = rasaClassifier.classify_fact(current_fact_name, message)
    print(classify_dict)

    # Return the fact value, or None if the answer was insufficient in determining one
    if __is_answer_sufficient(classify_dict):
        determined_intent = classify_dict['intent']
        print("Confidence: {}%".format(round(determined_intent['confidence'], 3) * 100))
        print("Intent: {}".format(determined_intent['name']))
        return determined_intent['name']
    else:
        return None


# Determine confidence of returned intent
def __is_answer_sufficient(classify_dict):
    if len(classify_dict['intent_ranking']) > 1:
        percent_difference = RasaClassifier.intent_percent_difference(classify_dict)
        print("Percent Difference: {}%".format(round(percent_difference, 3) * 100))
        if percent_difference < minimum_percent_difference:
            return False
    return True
