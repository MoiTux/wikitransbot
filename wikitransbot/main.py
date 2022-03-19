import json
import logging
import requests
import time

from pytwitter import Api


class Bot:

    def __init__(self):
        self.config = json.load(open('/etc/wikitransbot/config.json', 'r', encoding='utf-8'))

        logging.basicConfig(filename=self.config['logfile_path'], filemode='w+')

        # TODO: move  in conf ?
        self.wikitransbot_id = 1457666990554894337
        self.api = self.get_twitter_api()
        self.since_id_file_path = self.config['last_id_file']
        self.since_id = self.get_since_id()
        self.keyword = self.config['trigger_keyword']
        self.sleep_time = self.config['sleep_time']

    def get_twitter_api(self):
        twitter_config = self.config['twitter']
        return Api(
            consumer_key=twitter_config['twitter_api_key'],
            consumer_secret=twitter_config['twitter_api_key_secret'],
            access_token=twitter_config['twitter_access_token'],
            access_secret=twitter_config['twitter_access_token_secret'],
        )

    def get_since_id(self):
        try:
            with open(self.since_id_file_path, 'r') as f:
                return int(f.read())
        except FileNotFoundError:  # 1st time bot in ran
            return 1

    def build_search_article_url(self, *, tweet_text):
        splitted_tweet = tweet_text.split(self.keyword + ' ')

        # Trigger word not found
        if len(splitted_tweet) == 1:
            return ""

        base_url = "https://wikitrans.co/wp-admin/admin-ajax.php"
        parameters = "?action=jet_ajax_search&search_taxonomy%5D=&data%5Bvalue%5D="
        url = base_url + parameters
        return f"{url}{splitted_tweet[1]}"

    def tweet(self, *, text, to):
        self.api.create_tweet(
            text=text,
            reply_in_reply_to_tweet_id=to,
            reply_exclude_reply_user_ids=[],
        )
        logging.info('Answer sent to #{tweet.id} with message {text}')

    def sleep(self):
        time.sleep(self.sleep_time)
        logging.info("Sleeping")

    def run(self):
        while True:
            try:
                tweets = self.api.get_mentions(user_id=self.wikitransbot_id, since_id=self.since_id).data
                for tweet in tweets:
                    new_since_id = max(int(tweet.id), self.since_id)

                    request_url = self.build_search_article_url(tweet_text=tweet.text)
                    if not request_url:
                        continue
                    logging.info('New tweet found from {tweet.author} (#{tweet.id}) saying "{tweet.text}"')

                    response = requests.get(request_url)
                    if response.status_code == 200:
                        data = response.json()['data']
                        if data['post_count'] == 0:
                            self.tweet(text=self.config['no_answer_template'], to=tweet.id)
                        else:
                            self.tweet(text=self.config['answer_template'] % (data['posts'][0]['link']), to=tweet.id)
                self.since_id = new_since_id
                with open(self.since_id_file_path, 'w') as f:
                    f.write(str(new_since_id))  # So if the bot crashes we know where to start

            except Exception as e:
                logging.warning(str(e))

            self.sleep()


if __name__ == "__main__":
    bot = Bot()
    bot.run()
