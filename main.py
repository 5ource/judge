import logging

from flask import Flask, render_template, request
from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types

import urllib
import urllib.request
from bs4 import BeautifulSoup
import ssl

app = Flask(__name__)

nl = "<br/>"

#handling user input
@app.route('/form')
def form():
    return render_template('form.html')

@app.route('/submitted', methods=['POST'])
def submitted_form():
    ret_str = ""
    #name = request.form['name']
    #email = request.form['email']
    url = request.form['site_url']
    #comments = request.form['comments']

    annotations =  analyze(get_txt_from_url(url))
    score, magnitude = get_score_and_magnitude(annotations)
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
        ret_str+="Mag = "+ sentence.sentiment.magnitude
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
