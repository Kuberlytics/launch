from twitter import *
import datetime, traceback
import json
import time
import sys

def twitter_init(cf_t):
    """Function to set initial
    Args: A configuration dictionary.

    Returns: A configuration dictionary.
    """
    cf_t['names_path']=cf_t['path']+cf_t['config']+"/"+cf_t['file']
    cf_t['data_path']=cf_t['path']+cf_t['data']
    return cf_t


def read_screen_names(cf_t):
    """Function to return screen names from a file.
    Args: A configuration file.

    Returns: A python list of twitter handles.
    """

    names = set()
    f = open(cf_t['names_path'], 'r')
    for line in f:
        names.add(line.strip())
    f.close()
    return names

def create_twitter_auth(cf_t):
        """Function to create a twitter object
           Args: cf_t is

           Returns: Nothing
            """
        # When using twitter stream you must authorize.
        # these tokens are necessary for user authentication
        # create twitter API object

        auth = OAuth(cf_t['access_token'], cf_t['access_token_secret'], cf_t['consumer_key'], cf_t['consumer_secret'])

        try:
            # create twitter API object
            twitter = Twitter(auth = auth)
        except TwitterHTTPError:
            traceback.print_exc()
            time.sleep(cf_t['sleep_interval'])

        return twitter



def get_profiles(twitter, names, cf_t):
    """Function write profiles to a file with the form *data-user-profiles.json*
       Args: names is a list of names
             cf_t is a list of twitter config
       Returns: Nothing
        """

    # file name for daily tracking
    file_dt = datetime.datetime.now()
    filename = file_dt.strftime('%Y-%m-%d-user-profiles.json')
    w_profile = open("%s/profiles/%s"%(cf_t['data_path'], filename), 'w')

    # now we loop through them to pull out more info, in blocks of 100.
#    for n in range(0, len(_names), 100):
#        names = _names[n:n+100]
    for name in names:
        print("Searching twitter for User profile: ",name)
        try:
            # create a subquery, looking up information about these users
            # twitter API docs: https://dev.twitter.com/docs/api/1/get/users/lookup
            subquery = twitter.users.lookup(screen_name = name)
            sub_start_time = time.time()
            for user in subquery:
                # now save user info
                w_profile.write(json.dumps(user))
                w_profile.write("\n")
            sub_elapsed_time = time.time() - sub_start_time;
            if sub_elapsed_time < cf_t['sleep_interval']:
                time.sleep(cf_t['sleep_interval'] + 1 - sub_elapsed_time)
        except TwitterHTTPError:
            traceback.print_exc()
            time.sleep(cf_t['sleep_interval'])
            continue
    w_profile.close()

# check the max tweet id in last round
def last_tweet(screen_name, cf_t):
    tweet_id = -1;
    try:
        f = open("%s/timeline/%s.json"%(cf_t['data_path'], screen_name), 'r')
        for line in f:
            print(line)
            j = json.loads(line)
            print(j)
            i = j['id']
            print(i)
        #This was erroring out.
        tweet_id = max(tweet_id, i);
        #tweetId=-1
        f.close()
    except IOError:
        #f = open('%s.json'%screen_name, 'a')
        f = open("%s/timeline/%s.json"%(cf_t['data_path'], screen_name), 'r')
        f.close()
    return tweet_id


def user_time_line(twitter, screenName, cf_t):
    print ("Working on %s..."%screenName)

    last = last_tweet(screenName,cf_t)

    #f = open('%s.json'%screenName, 'a')
    f = open("%s/timeline/%s.json"%(cf_t['data_path'], screenName), 'a')

    # twitter allows 180 usertimeline requests per 15 min window
    # i.e. 5 seconds interval between consecutive requests
    interval = cf_t['sleep_interval']

    count = 200

    curr_max = 0;
    prev_max = 0;
    ret = 0;
    # tracking pulled tweets so that only save unique tweets
    tweetIds = set()
    more = True
    while (more):
        results = []
        try:
            if (0 == curr_max):
                results = twitter.statuses.user_timeline(screen_name = screenName, count = count)
                if len(results) == 0:
                    time.sleep(interval)
                    return ret;
                ret = results[0]['id']
                curr_max = results[-1]['id']
            else:
                results = twitter.statuses.user_timeline(screen_name = screenName, count = count, max_id = curr_max)
                if len(results) == 0:
                    time.sleep(interval)
                    return ret;
                prev_max = curr_max;
                curr_max = results[-1]['id']

            if (curr_max == prev_max):
                # reach the end of all possible results
                break

            start_time = time.time();

            for status in results:
                if status['id'] not in tweetIds: # uniqueness
                    if status['id'] <= last: # already seen, no more new tweets from this point
                        more = False
                        break;

                    tweetIds.add(status['id'])
                    try:
                        f.write(json.dumps(status))
                        f.write('\n')
                    except ValueError:
                        # json parser error
                        traceback.print_exc()
                        continue

            elapsed_time = time.time() - start_time;
            if (interval + 1 - elapsed_time) > 0:
                time.sleep(interval + 1 - elapsed_time)
        except TwitterHTTPError:
            #
            traceback.print_exc()
            time.sleep(interval)
            break;
        except KeyboardInterrupt:
            f.flush()
            f.close()
            raise KeyboardInterrupt

    f.flush()
    f.close()

    print ("Got %d new tweets for %s..."%(len(tweetIds), screenName))
    return ret
