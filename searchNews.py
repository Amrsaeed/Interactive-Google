from goose import Goose
import json
from requests import get
import tldextract
import logging
import re
from flask import Flask, render_template
from flask_ask import Ask, statement, question, session

logging.basicConfig()

json_data = {}
resultCursor = 1
query = ""
state = 0
textContinueFlag = False

app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger("flask_ask").setLevel(logging.DEBUG)

def save_session():
    session.attributes['data'] = json_data
    session.attributes['cursor'] = resultCursor
    session.attributes['query'] = query
    session.attributes['state'] = state
    session.attributes['textFlag'] = textContinueFlag

def load_session():
    global json_data
    json_data = session.attributes.get('data', {})
    global resultCursor
    resultCursor = session.attributes.get('cursor', 1)
    global query
    query = session.attributes.get('query', "")
    global state
    state = session.attributes.get('state', 0)
    global textContinueFlag
    textContinueFlag = session.attributes.get('textFlag', False)

def clear_session():
    global json_data
    global resultCursor
    global query
    global state
    global textContinueFlag
    json_data = {}
    resultCursor = 1
    query = ""
    state = 0
    textContinueFlag = False

def retrieve_results(query):
    print(resultCursor, query)
    SITE = 'https://www.googleapis.com/customsearch/v1?key=AIzaSyAI8OQaCQjpVtWXQJ6K0Mhb_HPkLL8KgWo&cx=000510991857172859853:minhpsxrsus&q=' + \
           query + '&start=' + str(resultCursor) + '&num=1'
    response = get(SITE)
    json_data = json.loads(response.text)
    print(json_data)
    return json_data


def clean_text(json_data, resultCursor):
    ext = tldextract.extract(json_data['items'][0]['link'])
    print(ext.domain)

    inner_response = get(json_data['items'][0]['link'])
    extractor = Goose()
    article = extractor.extract(raw_html=inner_response.content)
    text = article.cleaned_text
    text = text.encode('utf-8')
    return text


def extract_data(query):
    data = retrieve_results(query)
    global json_data
    json_data = data
    title = data['items'][0]['title']
    title = title.encode('utf-8')
    domain = tldextract.extract(data['items'][0]['link']).domain
    domain = domain.encode('utf-8')

    return json_data, title, domain


def bad_command():
    return question(render_template('badArgument'))


@ask.launch
def launch_prompt():
    clear_session()
    return question(render_template('welcome'))


@ask.intent('SearchIntent', mapping={'searchQuery': 'query'})
def search_intent(searchQuery):
    clear_session()
    global query, state
    query = searchQuery
    data, title, domain = extract_data(query)

    if len(data['items']) == 0:
        return statement(render_template('noResult'))

    state = 1
    save_session()
    return question(render_template('resultHeading', headingNumber=resultCursor, headingTitle=title, headingSource=domain)).reprompt(render_template('repeatQuery'))


@ask.intent('ResultIntent')
def result_intent():
    load_session()
    text = clean_text(json_data, resultCursor)
    global state
    sentences = text.split('.')
    if len(text) == 0:
        title = json_data['items'][0]['title']
        link = json_data['items'][0]['link']
        state = 1
        save_session()
        return question(render_template('noTextFound')).simple_card(title, link)

    sentencesFlag = False
    if len(sentences) > 1:
        sentencesFlag = True
        text = sentences[0] + '.'
    if len(sentences) > 2:
        sentencesFlag = True
        text += sentences[1] + '.'
    if len(sentences) > 3:
        sentencesFlag = True
        text += sentences[2] + '.'

    if sentencesFlag:
        text += " Would you like to continue?"
        global textContinueFlag
        textContinueFlag = True

    print('---------')
    print(text)
    print(sentences)

    state = 2
    save_session()
    return question(text).reprompt(render_template('repeatQuery'))


@ask.intent('AMAZON.NextIntent')
def next_intent():
    if state == 0:
        return bad_command()
    load_session()
    global resultCursor
    resultCursor += 1
    _, title, domain = extract_data(query)
    save_session()
    return question(render_template('resultHeading', headingNumber=resultCursor, headingTitle=title, headingSource=domain)).reprompt(render_template('repeatQuery'))


@ask.intent('AMAZON.PreviousIntent')
def previous_intent():
    global state
    if state == 0:
        return bad_command()

    load_session()

    if state == 1:
        global resultCursor
        if resultCursor == 1:
            return bad_command()
        resultCursor -= 1
        _, title, domain = extract_data(query)
        save_session()
        return question(render_template('resultHeading', headingNumber=resultCursor, headingTitle=title, headingSource=domain)).reprompt(render_template('repeatQuery'))
    elif state == 2:
        state = 1
        save_session()
        return question(render_template('backToResults', headingNumber=resultCursor)).reprompt(render_template('repeatQuery'))


@ask.intent('AMAZON.YesIntent')
def yes_intent():
    load_session()
    global textContinueFlag

    if state == 0:
        return bad_command()

    elif state == 1:
        global resultCursor
        resultCursor += 1
        _, title, domain = extract_data(query)
        save_session()
        print('------')
        print(title, domain)
        return question(render_template('resultHeading', headingNumber=resultCursor, headingTitle=title,
                                        headingSource=domain)).reprompt(render_template('repeatQuery'))
    elif state == 2 and textContinueFlag:
        text = clean_text(json_data, resultCursor)
        index = 0
        print('000000000')
        sentences = text.split('.')

        if len(sentences) > 1:
            index = 1
        if len(sentences) > 2:
            index = 2
        if len(sentences) > 3:
            index = 3

        text = ""
        for i in range(index, len(sentences)):
            text += sentences[i] + '.'

        print(text)

        textContinueFlag = False
        save_session()
        if len(text) >= 1000:
            return question(text[0:1000]).reprompt(render_template('repeatQuery'))
        else:
            return question(text[0:]).reprompt(render_template('repeatQuery'))
    else:
        return bad_command()



@ask.intent('AMAZON.NoIntent')
def no_intent():
    global state
    if state == 0:
        return bad_command()

    elif state == 1:
        return
    else:
        state = 1
        save_session()
        global resultCursor
        return question(render_template('backToResults', headingNumber=resultCursor))


@ask.intent('AMAZON.StopIntent')
def cancel_intent():
    return statement('Have a good day!')

@ask.intent('AMAZON.HelpIntent')
def help_intent():
    return


@ask.session_ended
def session_ended():
    return "", 200
if __name__ == '__main__':

    app.run(debug=True)