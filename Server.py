from flask import Flask
from flask import request
import time
import openai
import json
import re
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import tweepy
import torch

SUICIDE_MODEL_NAME = "mrm8488/distilroberta-base-finetuned-suicide-depression"
OPEN_API_KEY = ""

openai.api_key = OPEN_API_KEY

# loading the model only at the time of initialization
# classifier = pipeline("text-classification", model=DEPRESSION_MODEL_NAME)
tokenizer = AutoTokenizer.from_pretrained(SUICIDE_MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(SUICIDE_MODEL_NAME)

app = Flask(__name__)

def calculate_mhi(depression, anxiety, stress):
	return round((depression + anxiety + stress) / 3, 2)

def parse_result(result_string):
	values = re.findall("\d+\.\d+", result_string)
	depression = float(values[0])
	stress = float(values[1])
	anxiety = float(values[2])
	return depression, stress, anxiety

@app.route("/", methods=['POST'])
def processTweets():
	PROMPT = "Determine a value between 0 and 1 for the total depressive index, total stress index, and total anxiety index in the following Tweets combined, where a higher value corresponds to more indicators in the content of the Tweets. Only return three values corresponding to the three indices stated. These values must contain a decimal point, for example, 0 should be returned as 0.0"
	data = request.get_json()

	depression_model_score = 0.0
	num_tweets = 0

	for key, value in data.items():
		PROMPT += "\n" + key + ") " + value
		num_tweets += 1
		depression_model_score += get_depression_score_ML(value)

	completion = openai.ChatCompletion.create(
		model="gpt-3.5-turbo",
		messages=[
			{"role": "user", "content": PROMPT}
		],
		temperature=0)

	result_string = completion.choices[0].message.content
	print(result_string)

	depression, stress, anxiety = parse_result(result_string)
	depression_model_score = depression_model_score / num_tweets

	result = {}
	result['mhi'] = calculate_mhi(depression, anxiety, stress)
	result['depression'] = round((depression + depression_model_score) / 2, 2)
	result['anxiety'] = anxiety
	result['stress'] = stress
	json_result = json.dumps(result)

	return json_result


def get_depression_score_ML(tweet):
	print(tweet)
	inputs = tokenizer(tweet, return_tensors="pt")
	outputs = model(**inputs)

	softmax_output = torch.nn.functional.softmax(outputs.logits, dim=1)
	return softmax_output[0, 0].item()


def retrieve_tweets_with_secret(username, consumer_key, consumer_secret, access_token, access_token_secret):
	# Authenticate with Twitter API
	auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
	auth.set_access_token(access_token, access_token_secret)
	api = tweepy.API(auth)

	# Download tweets
	tweets = api.user_timeline(screen_name=username, count=200, tweet_mode='extended')

	return tweets


if __name__ == "__main__":
	app.run(host="0.0.0.0")