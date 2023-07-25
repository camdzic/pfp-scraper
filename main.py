import requests
import os
import time
import yaml
import re
import threading

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

token = config['creds']['token']
max_limit = config['creds']['limit_per_channel']
num_threads = config['creds']['threads']
check_images = config['creds']['check_images']

scraped_count = {}

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_messages(channel):
    all_messages = []
    has_more_messages = True
    before_id = None

    while has_more_messages and len(all_messages) < max_limit:
        limit = min(max_limit - len(all_messages), 100)

        url = f"https://discord.com/api/v10/channels/{channel}/messages?limit={limit}"

        if before_id:
            url += f"&before={before_id}"

        headers = {
            "Authorization": f"{token}",
            "Content-Type": "application/json",
        }

        response = requests.get(url, headers=headers)

        json_response = response.json()

        if isinstance(json_response, list) and json_response:
            all_messages.extend(json_response)
            before_id = json_response[-1].get('id', None)
        else:
            has_more_messages = False

    return all_messages

def clear_folder():
    folder = 'images'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')

def save_to_file(data, file):
    if(check_images == True):
        response = requests.get(data)

        if response.status_code == 404:
            with open(f"images/{file}.txt", 'a') as f:
                f.write(data)
                scraped_count[file] = scraped_count.get(file, 0) + 1
    else:
        with open(f"images/{file}.txt", 'a') as f:
            f.write(data)
            scraped_count[file] = scraped_count.get(file, 0) + 1

def process_message(message, key):
    if 'attachments' in message:
        for attachment in message['attachments']:
            if 'proxy_url' in attachment:
                save_to_file(attachment['proxy_url'] + "\n", key)
    if 'embeds' in message:
        for embed in message['embeds']:
            if 'thumbnail' in embed and 'proxy_url' in embed['thumbnail']:
                save_to_file(embed['thumbnail']['proxy_url'] + "\n", key)
            if 'image' in embed:
                save_to_file(embed['image']['proxy_url'] + "\n", key)
    if message['content']:
        message_links = re.findall(r'https?:\/\/[^\s]+', message['content'])
        if message_links:
            for link in message_links:
                save_to_file(link + "\n", key)

def run_module(key, value):
    print(f'Starting to scrape "{key}" module...')

    threads = []
    for channel in value:
        messages = get_messages(channel)
        for message in messages:
            thread = threading.Thread(target=process_message, args=(message, key,))
            threads.append(thread)
            thread.start()

    for thread in threads:
        thread.join()

    print(f'Finished scraping {scraped_count.get(key, 0)} images from "{key}" module.')

def run_code():
    print("Starting to scrape images...")
    clear_folder()

    module_keys = list(config['modules'].keys())
    num_modules = len(module_keys)

    for i in range(0, num_modules, num_threads):
        threads = []
        
        for j in range(num_threads):
            if i + j < num_modules:
                key = module_keys[i + j]
                value = config['modules'][key]
                thread = threading.Thread(target=run_module, args=(key, value,))
                threads.append(thread)
                thread.start()

        for thread in threads:
            thread.join()

    total = sum(scraped_count.values())
    print(f'Finished scraping images with total count of: {total} images.')

    while True:
        time.sleep(1)

try:
    if not os.path.exists('images'):
        os.makedirs('images')

    clear_console()
    run_code()
except Exception as e:
    print(e)
