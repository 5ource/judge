import logging

from flask import Flask, render_template, request
from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types

import urllib
import urllib.request
from bs4 import BeautifulSoup
import ssl
import six
import sys

app = Flask(__name__)

nl = "<br/>"

avg_words_per_doc = 1.0
mag_threshs = [2/avg_words_per_doc, 5/avg_words_per_doc, 15/avg_words_per_doc]
mag_decisions = ["no emotions", "little emotions", "medium emotions", "high emotions"]

#handling user input
@app.route('/form')
def form():
    return render_template('form.html')

def entity_sentiment_text(text):
    ret = "Entity sentiment:" + nl
    """Detects entity sentiment in the provided text."""
    client = language.LanguageServiceClient()

    if isinstance(text, six.binary_type):
        text = text.decode('utf-8')

    document = types.Document(
        content=text.encode('utf-8'),
        type=enums.Document.Type.PLAIN_TEXT)

    # Detect and send native Python encoding to receive correct word offsets.
    encoding = enums.EncodingType.UTF32
    if sys.maxunicode == 65535:
        encoding = enums.EncodingType.UTF16

    result = client.analyze_entity_sentiment(document, encoding)

    for entity in result.entities:
        ret+= str('Mentions: ') + nl
        ret+= str(u'Name: "{}"'.format(entity.name))+ nl
        for mention in entity.mentions:
            ret+= str(u'  Begin Offset : {}'.format(mention.text.begin_offset))+ nl
            ret+= str(u'  Content : {}'.format(mention.text.content))+ nl
            ret+= str(u'  Magnitude : {}'.format(mention.sentiment.magnitude))+nl
            ret+= str(u'  Sentiment : {}'.format(mention.sentiment.score))+ nl
            ret+= str(u'  Type : {}'.format(mention.type))+ nl
        ret+= str(u'Salience: {}'.format(entity.salience))+nl
        ret+= str(u'Sentiment: {}\n'.format(entity.sentiment))+ nl
    return ret
    
def count_words(text):
    word=1
    for i in text:
        if(i==' ' or i=='\n'):
            word=word+1
    return word

def determine_emo(mag, nwords):
    t = [6.19, 10.19, 14.19, 18.19]
    v = ["no emotions", "little emotions", "medium emotions", "high emotions", "extreme emotions"]
    m = 1000.0 * mag / nwords
    if m < t[0]:
        d = v[0]
    elif m < t[1]:
        d = v[1]
    elif m < t[2]:
        d = v[2]
    elif m < t[3]:
        d = v[3]
    else: d = v[4]
    return d
    
def judge_inflence(mag):
    #TODO: mag thesh might depend on number of sentences/words?
    if mag < mag_threshs[0]:
        decision = mag_decisions[0]
    elif mag >= mag_threshs[0] and mag <= mag_threshs[1]:
        decision = mag_decisions[1]
    elif mag >= mag_threshs[1] and mag <= mag_threshs[2]:
        decision = mag_decisions[2]
    elif mag > mag_threshs[2]:
        decision = mag_decisions[3]
    return decision

def judge(score, mag):
    score_thresh = [-0.75, -0.25, 0.25, 0.75]
    mag_thresh = 1
    decision = ""
    if score >= -1 and score <= score_thresh[0]: #-0.75:
        decision = "net strongly negative"
        #if mag > mag_thresh:
        #    decision = "clearly strongly negative"
        #else:
        #    decision = "not clearly strongly negative"
    elif score > score_thresh[0] and score <= score_thresh[1]:
        decision = "net negative"
        #if mag > mag_thresh:
        #    decision = "clearly negative"
        #else:
        #    decision = "not clearly negative?"
    elif score >  score_thresh[1] and score <  score_thresh[2]:
        decision = "net neutral"
        #if mag > mag_thresh:
        #    decision = "mixed"
        #else: decision = "neutral"
    elif score >= score_thresh[2] and score < score_thresh[3]:
        #if mag > mag_thresh:
        #    decision = "clearly positive"
        #else: decision = "not clearly positive?"
        decision = "positive"
    elif score >= score_thresh[3] and score <= 1:
        #if mag > mag_thresh:
        #    decision = "clearly strongly positive"
        #else:
        #    decision = "not clearly strongly positive?"
        decision = "strongly positive"
    else:
        decision = "unrecognized score"
    return decision

@app.route('/submitted', methods=['POST'])
def submitted_form():
    ret_str = ""
    #name = request.form['name']
    #email = request.form['email']
    url = request.form['site_url']
    text = request.form['text_box']
    #comments = request.form['comments']
    #googl nlp analyze
    if len(text) < 100:
        TESTING = 0
        if TESTING:
            text = "This guy is a total idiot. Can you believe what deep shit he is in?"
        else:
            text = get_txt_from_url(url)       
    annotations =  analyze(text)
    #conclude from results
    score, magnitude    = get_score_and_magnitude(annotations)
    n_words             = count_words(text)

    ret_str += "metric = " + str(determine_emo(magnitude, n_words)) + nl+\
    "n words = "+str(n_words) + nl
    return ret_str
    #ret_str += entity_sentiment_text(text) + nl
    ret_str += "Final weight decision influence = " + judge_inflence(magnitude/n_words) + nl +\
    ", polarity = "+ judge(score, magnitude) + " based on score = " + str(score) + "and mag raw/scaled = "+str(magnitude)+"/"+\
    str(magnitude/n_words)+ nl+\
    "mag thresholds = " + str(mag_threshs) + nl +\
    "mag names = "+ str(mag_decisions) + nl +\
    "n words = "+str(n_words) + nl
    
    if 1:
        return ret_str
    #score between -1 and 1
    #magnitude between 0 and Inf, not normalized by size of text
    mag_str = translate_magnitude(magnitude, len(annotations.sentences))
    score_str = translate_score(score)

    ret_str += score_str + nl + mag_str + nl +"numSentences=" + str(len(annotations.sentences)) + nl
    max_pos_score_text, max_neg_score_text = get_extremes(annotations)
    ret_str += "most positive sentence (score = "+ str(max_pos_score_text[0]) + " or " + translate_score(max_pos_score_text[0]) +\
    "):" + max_pos_score_text[1].content + nl
    ret_str += "most negative sentence (score = "+ str(max_neg_score_text[0]) + " or " + translate_score(max_neg_score_text[0]) +\
    "):" + max_neg_score_text[1].content + nl
    ret_str += get_score_and_magntitude_perSentence(annotations)
    return ret_str
    #overr
    return render_template(
        'submitted_form.html',
        name=name,
        email=email,
        site=url,
        comments=comments)

@app.route('/')
def hello():
	return 'Hello YouTube'

@app.route('/test')
def test():
    #print ("test")
    return analyze("Python is the best programming language ever!")
    
def translate_magnitude(magnitude, text_size):
    return "magnitude = " + str(magnitude/text_size)

#map score to meaning
def translate_score(score):
    if score >= -1 and score <= -0.75:
        return "strongly negative"
    elif score > -0.75 and score <= -0.25:
        return "negative"
    elif score > -0.25 and score < 0.25:
        return "neutral"
    elif score >= 0.25 and score < 0.75:
        return "positive"
    elif score >= 0.75 and score <= 1:
        return "strongly positive"
    else:
        return "unrecognized score"

def get_weighted_avg_of_sent_prod_score_mag(annotations):
    count = 0.0
    weighted_sum = 0.0
    for sentence in annotations.sentences:
        sent_score  = sentence.sentiment.score
        sent_mag    = sentence.sentiment.magnitude
        weighted_sum += sent_score * sent_mag
        count += 1
    return weighted_sum/count

def get_score_and_magntitude_perSentence(annotations):
    ret_str = ""
    score = annotations.document_sentiment.score
    magnitude = annotations.document_sentiment.magnitude
    ret_str+=('Overall Sentiment: score of {} with magnitude of {}'.format(
    score, magnitude))
    ret_str+=nl
    for index, sentence in enumerate(annotations.sentences):
        sentence_sentiment = sentence.sentiment.score
        ret_str+=('Sentence {} has a sentiment score of {}'.format(
            index, sentence_sentiment))
        ret_str+="Mag = "+ str(sentence.sentiment.magnitude)
        if sentence_sentiment > 0.75 or sentence_sentiment < -0.75: 
            ret_str += sentence.text.content
        ret_str+=nl
    return ret_str

def get_extremes(annotations):
    max_neg_score_text = [0, ""]
    max_pos_score_text = [0, ""]
    for sentence in annotations.sentences:
        if sentence.sentiment.score >= 0:
            if sentence.sentiment.score > max_pos_score_text[0]:
                max_pos_score_text = [sentence.sentiment.score, sentence.text]
        elif sentence.sentiment.score < 0:
             if sentence.sentiment.score < max_neg_score_text[0]:
                max_neg_score_text = [sentence.sentiment.score, sentence.text]          
    return [max_pos_score_text, max_neg_score_text]

def get_score_and_magnitude(annotations):
    score = annotations.document_sentiment.score
    magnitude = annotations.document_sentiment.magnitude
    return [score, magnitude]
    
def print_result(annotations):
    ret_str = ""
    score = annotations.document_sentiment.score
    magnitude = annotations.document_sentiment.magnitude
    for index, sentence in enumerate(annotations.sentences):
        sentence_sentiment = sentence.sentiment.score
        ret_str+=('Sentence {} has a sentiment score of {}'.format(
            index, sentence_sentiment))
        ret_str+= str(sentence.sentiment.magnitude)
        ret_str+="\n"

    ret_str+=('Overall Sentiment: score of {} with magnitude of {}'.format(
        score, magnitude))
    return ret_str

#run google nlp on text to retrieve animosity
def analyze(text):
    """Run a sentiment analysis request on text within a passed filename."""
    client = language.LanguageServiceClient()

    #with open(movie_review_filename, 'r') as review_file:
    #    # Instantiates a plain text document.
    #    content = review_file.read()
    content = text

    document = types.Document(
        content=content,
        type=enums.Document.Type.PLAIN_TEXT)
    annotations = client.analyze_sentiment(document=document)

    # Print the results
    #return print_result(annotations)
    #return 'pealing_done'
    return annotations

#download html and extract text from possibly html
def get_txt_from_url(url_arg):
    url =  url_arg
    #url_arg = "https://voxeu.org/article/artificial-intelligence-algorithmic-pricing-and-collusion"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(url_arg) as url:
        html = url.read()
        
    soup = BeautifulSoup(html)

    # kill all script and style elements
    for script in soup(["script", "style"]):
        script.extract()    # rip it out

    # get text
    text = soup.get_text()

    # break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    text = '\n'.join(chunk for chunk in chunks if chunk)
    return text

if __name__ == '__main__':
	app.run(host='127.0.0.1', port=8080, debug=True)
