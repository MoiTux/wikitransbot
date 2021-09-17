import json
import requests
import time

import tweepy


def get_since_id(file_path):
    try:
        with open(file_path, 'r') as f:
            return int(f.read())
    except FileNotFoundError:  # 1st time bot in ran
        return 1


def check_mentions(api, keywords, since_id, config):
    new_since_id = since_id
    for tweet in tweepy.Cursor(api.mentions_timeline, since_id=since_id).items():
        new_since_id = max(tweet.id, new_since_id)
        tweet_text = tweet.text.split(' ')

        if tweet_text[1] != config['trigger_keyword']:
            continue

        url = f"https://wikitrans.co/wp-admin/admin-ajax.php?action=jet_ajax_search&search_taxonomy%5D=&data%5Bvalue%5D={' '.join(tweet_text[2:])}"
        response = requests.get(url)
        if response.status_code == 200:
            api.update_status(
                config['answer_template'] % (tweet.author.screen_name, response.json()['data']['posts'][0]['link']),
                tweet.id,
            )
    return new_since_id


def main():
    config = json.load(open('config.json', 'r'))
    twitter_config = config['twitter']
    last_id_file = config['last_id_file']

    # Twitter things
    auth = tweepy.OAuthHandler(twitter_config['twitter_api_key'], twitter_config['twitter_api_key_secret'])
    auth.set_access_token(twitter_config['twitter_access_token'], twitter_config['twitter_access_token_secret'])
    api = tweepy.API(auth)

    since_id = get_since_id(last_id_file)

    while True:
        since_id = check_mentions(api, ["article"], since_id, config)
        with open(last_id_file, 'w') as f:
            f.write(str(since_id))  # So if the bot crashes we know where to start
        print("Sleeping")
        time.sleep(config['sleep_time'])


if __name__ == "__main__":
    main()
