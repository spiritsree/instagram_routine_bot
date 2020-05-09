'''
This is an Instagram Bot program which does the routine work
automated using instagram_private_api module. You need to pass username
and password to login to and Instagram account.

Login details can be passed in 3 ways
    - commandling arguments
    - ENV variables (IG_USERNAME, IG_PASSWORD)
    - If not both then ask from user

For more details check the help

    $ instragram_routine_bot.py -H
'''

import json
import codecs
from datetime import datetime, date, timedelta
import os
import sys
import re
import logging
import configargparse

try:
    from instagram_private_api import (
        Client, ClientError, ClientLoginError,
        ClientCookieExpiredError, ClientLoginRequiredError, MediaRatios,
        __version__ as client_version)
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from instagram_private_api import (
        Client, ClientError, ClientLoginError,
        ClientCookieExpiredError, ClientLoginRequiredError, MediaRatios,
        __version__ as client_version)

try:
    from instagram_private_api_extensions import media
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from instagram_private_api_extensions import media


def get_logger(logger_name, level='info'):
    '''
    logger function
    '''
    log_formatter = logging.Formatter("%(asctime)s: [ %(levelname)8s ][ %(name)s ][%(funcName)s:%(lineno)d] — %(message)s")
    logging.basicConfig()
    logger = logging.getLogger(logger_name)
    if level == 'info':
        logger.setLevel(logging.INFO)
    elif level == 'warn':
        logger.setLevel(logging.WARNING)
    elif level == 'debug':
        logger.setLevel(logging.DEBUG)
    elif level == 'error':
        logger.setLevel(logging.ERROR)
    elif level == 'critical':
        logger.setLevel(logging.CRITICAL)
    else:
        logger.setLevel(logging.WARNING)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)
    logger.propagate = False
    return logger

def to_json(python_object):
    '''
    Covert to json
    '''
    if isinstance(python_object, bytes):
        return {'__class__': 'bytes',
                '__value__': codecs.encode(python_object, 'base64').decode()}
    raise TypeError(repr(python_object) + ' is not JSON serializable')

def from_json(json_object):
    '''
    Covert from json to encoded object
    '''
    if '__class__' in json_object and json_object['__class__'] == 'bytes':
        return codecs.decode(json_object['__value__'].encode(), 'base64')
    return json_object

def read_json_file(json_file, app_logger):
    '''
    Read json file data as object
    '''
    app_logger.debug('Reading json data from file {0!s}'.format(json_file))
    with open(json_file, 'r') as file_data:
        json_data = json.load(file_data, object_hook=from_json)
    return json_data

def write_json_file(json_file, json_object, app_logger):
    '''
    Write json object to a json file as json data
    '''
    app_logger.debug('Writing json data to file {0!s}'.format(json_file))
    with open(json_file, 'w') as outfile:
        json.dump(json_object, outfile, default=to_json)
        app_logger.debug('Writing json data complete...')
    return True


def onlogin_callback(api, new_cache_file, app_logger):
    '''
    Write the json cache object from successful login. The cache will be valid
    for 90 days.
    '''
    cache_settings = api.settings
    if write_json_file(new_cache_file, cache_settings, app_logger):
        app_logger.debug('Saved cache data to file {0!s}'.format(new_cache_file))

def get_arguments():
    '''
    Get commandline arguments
    '''
    parser = configargparse.ArgParser(description='Instagram Workflow Bot')
    parser.add_argument('-d', '--debug', action='store_true', env_var='ENABLE_DEBUG', help='Enable Debug')
    parser.add_argument('-l', '--level', dest='level', type=str, env_var='LOG_LEVEL',
                        help='Log level (info, warn, error, critical, debug)')
    parser.add_argument('-c', '--cache', dest='cache_file_path', type=str,
                        required=True, env_var='CACHE_FILE', help='Cache store file path')
    parser.add_argument('-u', '--username', dest='username', type=str, required=True, env_var='IG_USERNAME', help='Username')
    parser.add_argument('-p', '--password', dest='password', type=str, required=True, env_var='IG_PASSWORD', help='Password')
    parser.add_argument('--data-dir', dest='data_dir', type=str, required=True, env_var='DATA_DIR', help='Data Directory')
    parser.add_argument('-f', dest='enable_analytics', action='store_true', env_var='ENABLE_ANALYTICS',
                        help='Follower analysis for the user')
    parser.add_argument('--upload', dest='post_photo', action='store_true', env_var='ENABLE_UPLOAD',
                        help='Upload picture to feed')
    parser.add_argument('-i', '--iguser', dest='ig_user', type=str, env_var='IG_USER',
                        help='Username to analyze other than logged in user')
    args = parser.parse_args()
    return args

def read_binary_file(file_path, app_logger):
    '''
    Read a binary file and return data
    '''
    app_logger.debug('Getting image data')
    if os.path.isfile(file_path):
        with open(file_path, mode='rb') as image_file:
            image_data = image_file.read()
            return image_data
    else:
        app_logger.debug('Given image {0!s} does not exist'.format(file_path))
        return None

def read_file(file_path, app_logger):
    '''
    Read a file and return content
    '''
    app_logger.debug('Getting file data')
    if os.path.isfile(file_path):
        with open(file_path, mode='r') as text_file:
            text_data = text_file.read()
            return text_data
    else:
        app_logger.debug('Given file {0!s} does not exist'.format(file_path))
        return None


def get_dates():
    '''
    This will return an array of current and previoud date
    '''
    today = date.today().strftime('%Y%m%d')
    yesterday = (date.today() - timedelta(days=1)).strftime('%Y%m%d')
    return [today, yesterday]


def get_missing_item(a_list, b_list):
    '''
    Get all items missing from b_list which is in a_list
    '''
    d_list = []
    d_list = [x for x in a_list if x not in b_list]
    return d_list

def store_analytics(u_name, a_dir, f_list, app_logger):
    '''
    Function to store the details in a json file and compare with
    previous day data. Returns json object upon completion.

    response: {"status": "Success", "data_file": data_file}
    '''
    dates = get_dates()
    app_logger.debug('Analysing and comparing the data for user {0!s}'.format(u_name))
    store_response = {"status": "notok", "data_file": ""}
    f_data = {}
    f_data[u_name] = {}
    f_data[u_name]['followers'] = f_list
    f_data[u_name]['total_followers'] = len(f_list)
    f_data[u_name]['new_followers'] = []
    f_data[u_name]['dropped_followers'] = []
    store_today = '{0!s}/analytics_{1!s}.json'.format(a_dir, dates[0])
    store_yesterday = '{0!s}/analytics_{1!s}.json'.format(a_dir, dates[1])
    # Load data from old store file
    f_old_data = {}
    if os.path.isfile(store_yesterday):
        f_old_data = read_json_file(store_yesterday, app_logger)
    # Get delta
    f_old_list = f_old_data.get(u_name).get('followers')
    if f_old_list:
        app_logger.debug('Previous data exist and comapring now')
        f_data[u_name]['dropped_followers'] = get_missing_item(f_old_list, f_list)
        f_data[u_name]['new_followers'] = get_missing_item(f_list, f_old_list)
    f_data[u_name]['total_dropped_followers'] = len(f_data[u_name]['dropped_followers'])
    f_data[u_name]['total_new_followers'] = len(f_data[u_name]['new_followers'])
    if f_data[u_name]['total_dropped_followers'] > 0:
        app_logger.debug('Dropped followers {0}'.format(f_data[u_name]['dropped_followers']))
    if write_json_file(store_today, f_data, app_logger):
        app_logger.debug('Written the followers data for IG User {0!s}'.format(u_name))
    store_response['status'] = "ok"
    store_response['data_file'] = store_today
    return store_response

def do_authenticate(args, app_logger):
    '''
    Authenticate using user and password
    '''
    app_logger.debug('Authenticating against Instagram')
    try:
        cache_file = args.cache_file_path
        if not os.path.isfile(cache_file):
            app_logger.debug('Unable to find file: {0!s}'.format(cache_file))
            app_logger.debug('Continuing with new login...')
            api = Client(args.username, args.password,
                         on_login=lambda x: onlogin_callback(x, args.cache_file_path, app_logger))
        else:
            app_logger.debug('Loading cache from file: {0!s}'.format(cache_file))
            cached_settings = read_json_file(cache_file, app_logger)
            #with open(cache_file) as file_data:
            #    cached_settings = json.load(file_data, object_hook=from_json)
            device_id = cached_settings.get('device_id')
            app_logger.debug('Reusing auth settings...')
            api = Client(args.username, args.password, settings=cached_settings)
    except (ClientCookieExpiredError, ClientLoginRequiredError) as auth_err:
        app_logger.debug('ClientCookieExpiredError/ClientLoginRequiredError: {0!s}'.format(auth_err))
        app_logger.debug('Login expired...')
        app_logger.debug('Doing relogin with same UA and settings...')
        api = Client(args.username, args.password, device_id=device_id,
                     on_login=lambda x: onlogin_callback(x, args.cache_file_path, app_logger))
    except ClientLoginError as auth_err:
        app_logger.critical('ClientLoginError {0!s}'.format(auth_err))
        sys.exit(9)
    except ClientError as auth_err:
        app_logger.critical('ClientError {0!s} (Code: {1:d}, Response: {2!s})'.format(auth_err.msg, auth_err.code, auth_err.error_response))
        sys.exit(9)
    except Exception as auth_err:
        app_logger.critical('Unexpected Exception: {0!s}'.format(auth_err))
        sys.exit(99)
    cookie_expiry = api.cookie_jar.auth_expires
    app_logger.debug('Cookie Expiry: {0!s}'.format(datetime.fromtimestamp(cookie_expiry).strftime('%Y-%m-%dT%H:%M:%SZ')))
    return api

def get_userid(client, user_name, app_logger):
    '''
    Get userid given a username
    '''
    app_logger.debug('Getting user id of IG user {0!s}'.format(user_name))
    user_info = client.username_info(user_name)
    user_id = user_info.get('user')['pk']
    app_logger.debug('User id of IG user {0!s} is {1}'.format(user_name, user_id))
    return user_id

def get_followers(client, user_id, rank_token, app_logger):
    '''
    Get followers for a given user id. This will return number of users and
    the list of followers as a json object.

    Get the list using pagination with max_id
    '''
    app_logger.debug('Getting followers of IG user {0!s}'.format(user_id))
    followers = []
    f_list_data = []
    f_results = client.user_followers(user_id, rank_token)
    f_list_data.extend(f_results.get('users', []))
    next_max_id = f_results.get('next_max_id')
    while next_max_id:
        f_results = client.user_followers(user_id, rank_token, max_id=next_max_id)
        f_list_data.extend(f_results.get('users', []))
        next_max_id = f_results.get('next_max_id')
    f_list_data.sort(key=lambda x: x['username'])
    for each_user in f_list_data:
        followers.append(each_user['username'])
    app_logger.debug('Collected all the followers of user {0!s}'.format(user_id))
    return followers

def get_token_uuid(app_logger):
    '''
    Function to generate rank token UUID
    '''
    app_logger.debug('Generating rank token...')
    rank_token = Client.generate_uuid()
    app_logger.debug('Generated rank token is {0!s}'.format(rank_token))
    return rank_token

def follow_user(client, u_id, app_logger):
    '''
    Follow the specified user
    '''
    app_logger.debug('Following user with id {0}'.format(u_id))
    f_response = client.friendships_create(u_id)
    if f_response['status'] == 'ok':
        app_logger.debug('Successfully followed user with id {0}'.format(u_id))

def unfollow_user(client, u_id, app_logger):
    '''
    Follow the specified user
    '''
    app_logger.debug('Unfollowing user with id {0}'.format(u_id))
    f_response = client.friendships_destroy(u_id)
    if f_response['status'] == 'ok':
        app_logger.debug('Successfully unfollowed user with id {0}'.format(u_id))

def follow_status(client, u_id, app_logger):
    '''
    Get follow status of a give userd id of user ids

    response --> {'friendship_statuses': {'uid1': {'following': True, ... } } }
    '''
    app_logger.debug('Getting follow status of give user ids')
    if re.match(r'^\d+^', str(u_id)):
        app_logger.debug('Single id given')
        f_temp_status = client.friendships_show(u_id)
        f_status = {}
        f_status['friendship_statuses'] = {}
        f_status['friendship_statuses'][u_id] = f_temp_status
    else:
        app_logger.debug('Multiple ids given')
        f_status = client.friendships_show_many(u_id)
    app_logger.debug('Successfully got the status of given ids')
    return f_status

def post_photo(client, u_dir, c_dir, app_logger):
    '''
    Post photo WIP
    '''
    p_file = ''
    c_file = ''
    app_logger.debug('Uploading image from path {0!s}'.format(u_dir))
    files = os.listdir(u_dir)
    for each_file in files:
        if re.match(r'.*?\.jpg$', each_file.lower()):
            p_file = each_file
            break
    c_file = os.path.splitext(p_file)[0] + '.txt'
    if p_file:
        image_file = '{0!s}/{1!s}'.format(u_dir, p_file)
        caption_file = '{0!s}/{1!s}'.format(u_dir, c_file)
        caption_data = ''
        if os.path.isfile(caption_file):
            caption_data = read_file(caption_file, app_logger)
        else:
            app_logger.debug('Caption file does not exist')
        photo_data, photo_size = media.prepare_image(image_file, aspect_ratios=MediaRatios.standard)
        upload_response = client.post_photo(photo_data, photo_size, caption=caption_data)
        if upload_response['status'] == 'ok':
            app_logger.debug('Image "{0!s}" uploaded Successfully'.format(image_file))
            os.rename(image_file, '{0!s}/{1!s}'.format(c_dir, p_file))
            if os.path.isfile(caption_file):
                os.rename(caption_file, '{0!s}/{1!s}'.format(c_dir, c_file))
            return True
        return False
    app_logger.debug('Image file does not exist')
    return False

def do_analytics(client, args, userid, rank_token, app_logger):
    '''
    Function to do the analytics
    '''
    # Verify analytics dir exist (/data/analytics)
    analytics_dir = '{0!s}/analytics'.format(args.data_dir.rstrip('/'))
    if not os.path.exists(analytics_dir):
        os.mkdir(analytics_dir)

    # check today's file exist
    dates = get_dates()
    store_today = '{0!s}/analytics_{1!s}.json'.format(analytics_dir, dates[0])
    if os.path.isfile(store_today):
        app_logger.debug('Analytics data for the day exists. Skipping.')
    else:
        followers = get_followers(client, userid, rank_token, app_logger)
        store_response = store_analytics(args.ig_user, analytics_dir, followers, app_logger)
        if store_response['status'] == 'ok':
            app_logger.debug('Successfully written the analytics data in %s', store_response['data_file'])

def do_upload(client, args, app_logger):
    '''
    Function to do upload photos
    '''
    upload_dir = '{0!s}/upload'.format(args.data_dir.rstrip('/'))
    completed_dir = '{0!s}/completed'.format(args.data_dir.rstrip('/'))

    if os.path.exists(upload_dir):
        if os.path.exists(completed_dir):
            os.mkdir(completed_dir)
        if post_photo(client, upload_dir, completed_dir, app_logger):
            app_logger.debug('Successfully posted photo')
    else:
        app_logger.debug('Upload dir does not exist. Skipping...')

def main(args):
    '''
    Main funtion
    '''
    app_name = sys.modules[__name__].__file__.split(".")[0]

    # Logger setup
    if args.debug:
        app_logger = get_logger(app_name, 'debug')
    elif args.level:
        app_logger = get_logger(app_name, args.level)
    app_logger.info('Client version: %s', client_version)
    device_id = None

    # IG User selection
    if args.ig_user:
        args.upload = False
    else:
        args.ig_user = args.username

    # IG Authentication
    client = do_authenticate(args, app_logger)
    rank_token = get_token_uuid(app_logger)
    ig_user_id = get_userid(client, args.ig_user, app_logger)

    # Follower Analytics routine
    if args.enable_analytics:
        do_analytics(client, args, ig_user_id, rank_token, app_logger)

    # Image upload routine
    if args.post_photo:
        do_upload(client, args, app_logger)


if __name__ == '__main__':
    ARGS_LIST = get_arguments()
    main(ARGS_LIST)
