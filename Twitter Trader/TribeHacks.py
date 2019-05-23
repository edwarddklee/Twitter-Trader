import string
import ast
import tweepy 
import requests
from textblob import TextBlob
import smtplib
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
import time

# allows the code run every 10 seconds
scheduler = BackgroundScheduler()
scheduler.start()

#-------------------------------------------- functions --------------------------------------------#

# simply uploaded tweet into a list
def simplify_text(text):
    result = []
    valid = []
    word = ''

    for char in text:
        if char not in string.whitespace:
            if char not in string.ascii_letters + "'":
                if word:
                    result.append(word)
                result.append(char)
                word = ''
            else:
                word = ''.join([word, char])
        else:
            if word:
                result.append(word)
                word = ''

    if word:
        result.append(word)
    
    for word in result:
        if "'s" in word:
            valid.append(word[:-2])
        elif "s'" in word:
            valid.append(word[:-1])
        elif word.isalpha():
            valid.append(word)

    return valid

# Algorithm to determine the sentiment/polarity
def polarity_test(text, split_text):
    positive_file = open("positive_polarity.txt", "r")
    positive_polarity = positive_file.read().split()
    negative_file = open("negative_polarity.txt", "r")
    negative_polarity = negative_file.read().split()

    testimonial = TextBlob(text)
    verdict_val = testimonial.sentiment.polarity
    verdict = ''

    for word in split_text:
        word = word.lower()
        if word in negative_polarity:
            verdict_val -= 0.6
        if word in positive_polarity:
            verdict_val += 0.6

    if verdict_val >= 0.95:
        verdict_val = 0.95
    if verdict_val <= -0.95:
        verdict_val = -0.95

    if verdict_val >= 0.7:
        verdict = "Strong indication for positive sentiment: "
    elif verdict_val >= 0.3:
        verdict = "Moderate indication for positive sentiment: "
    elif verdict_val >= 0.1:
        verdict = "Weak indication positive sentiment: "
    elif verdict_val >= -0.1:
        verdict = "Neutral indication for sentiment: "
    elif verdict_val >= -0.3:
        verdict = "Weak indication for negative sentiment: "
    elif verdict_val >= -0.7:
        verdict = "Moderate indication for negative sentiment: "
    else:
        verdict = "Strong indication for negative sentiment: "

    percent_verdict = verdict_val*100
    final_verdict = round(percent_verdict, 2)
    return (verdict , str(final_verdict) + "%")

# Searches through a given tweet and find what stock they are talking about
# Also finds the current price of the stock (for future references)
def stock_test(tweet_text):
    stocks = pd.read_csv("sp100ticker.csv")
    dict_stocks = stocks.set_index('Name')['Symbol'].to_dict()
    s_name = stocks['Name'].tolist()
    bd_tweet = simplify_text(tweet_text)
    for match in bd_tweet:
        if match in s_name:
            api_key = 'API_KEY_HERE'
            api_secret = 'API_SECRET_HERE'
            t_name = dict_stocks.get(match)
            stream_url = "https://cloud.iexapis.com/beta/stock/" + t_name + "/quote?token=" + api_secret
            r = requests.get(stream_url, stream = True) 
            dict_r = r.json()
            initial_price = dict_r.get('latestPrice')
            return polarity_test(tweet_text, bd_tweet), (match, initial_price)
        else:
            pass
    return None

#function that sends alert email to the user
def sendemail(from_addr, to_addr_list,
              subject, message,
              login, password,
              smtpserver='smtp.gmail.com:587'):
    header  = 'From: %s\n' % from_addr
    header += 'To: %s\n' % ','.join(to_addr_list)
    header += 'Subject: %s\n\n' % subject
    message = header + message
 
    server = smtplib.SMTP(smtpserver)
    server.starttls()
    server.login(login,password)
    problems = server.sendmail(from_addr, to_addr_list, message)
    server.quit()
    return problems 

#------------------------------------------ Main functions ------------------------------------------#

# Main function responsible for checking tweets
def scan_update():

    config = open("config.txt", 'r')
    config_split = config.read().split()
    username = config_split[3]
    personal_email = config_split[1]

    print("Currently Running...")
    #needed for OAuth
    consumer_key = 'CONSUMER_KEY_HERE'
    consumer_secret = 'CONSUMER_SECRET_HERE'
    access_token = 'ACCESS_TOKEN_HERE'
    access_token_secret = 'ACCESS_TOKEN_SECRET_HERE'

    #authorization process
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)

    #needed for API calls to Twitter
    api = tweepy.API(auth)

    #user ID to analyze tweets
    user_tweet = api.user_timeline(screen_name = username, count = 1, include_rts = True)

    for status in user_tweet:
        tweet_text = "\n" + status.text
        f = open("logs.txt", 'r+')
        old_txt = f.read()
        output_tweet = str(tweet_text.encode('utf-8'))
        if tweet_text not in old_txt:
            f.write(tweet_text)
            f.close()
            alert_message = stock_test(tweet_text)
            if alert_message != None:
                sendemail(from_addr    = 'TwitterTraderCypher@gmail.com', 
                        to_addr_list = [personal_email], 
                        subject      = 'TwitterTrader: ' + str(alert_message[1][0]) + ' (' + str(alert_message[0][1]) + ')', 
                        message      = "Stock: " + str(alert_message[1][0]) + '\n' + "Current Price: " + str(alert_message[1][1]) + '\n' + str(alert_message[0][0]) + str(alert_message[0][1]) + '\n\n' + '@' + username + ' recently tweeted: \n' + output_tweet[4:-1],
                        login        = "TwitterTraderCypher",
                        password     = 'Baylife888***')
        f.close()

# Main function responsible for running this code every 10 seconds
def main():
    scan_update()

    scheduler.add_job(scan_update, 'interval', seconds = 10)

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
