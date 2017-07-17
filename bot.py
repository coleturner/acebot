import discord
from discord.ext import commands
import asyncio
import base64
import json
import os
import os.path
import time
import math
import regex
from functools import cmp_to_key
import threading
import urllib.request
from urllib.parse import urlparse
from multiprocessing import Pool
import traceback
import datetime

bot = commands.Bot(command_prefix='$', description="Hello! My name is ~~acemarke~~AceBot. If you need help just ask.")
settings = {}
settingsFile = "settings.json"

dictionary = {}
dictionaryFile = "dictionary.json"

search_cache = {}

syncing_game = discord.Game(name='Syncing...')
access_token = os.environ['GITHUB_ACCESS_TOKEN']

ACKNOWLEDGE_EMOJI = '🆗'
SUCCESS_EMOJI = '✅'
PROHIBITED_EMOJI = '👎'

MARKDOWN_URL_REGEX = r'(\[([^\]]*)]\(([^)]*)\))'
LINK_LIST_REGEX = r'\*\*(.+?)\*\*\s+(http[s]?:\/\/(?:[a-zA-Z]|[0-9]|[$-_@.&+#]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)\s+([^\n]+)'

def get_json_from_url(url):
    print(f"Loading {url}")
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode('utf-8', errors='ignore'))
        return data

def get_json_file(file):
    if os.path.isfile(file):
        with open(file) as data_file:
            try:
                data = json.load(data_file)
            except json.decoder.JSONDecodeError:
                data = {}
    else:
        data = {}
    return data

def put_json_file(file, data):
    with open(file, 'w+') as outfile:
        json.dump(data, outfile)
    return True

def is_markdown_link(str):
    regex.match(MARKDOWN_URL_REGEX, str)

def import_blob(repo, path, markdown, parent):
    global MARKDOWN_URL_REGEX, dictionary

    if parent.startswith('./'):
        parent = parent.strip('./')

    parent = f"{repo}/{parent}"
    # First we parse for links as text
    markdown_by_line = markdown.split("\n")
    for index, line in enumerate(markdown_by_line):
        for (links_with_titles) in regex.findall(MARKDOWN_URL_REGEX, line):
            (whole_match, text, url) = links_with_titles
            #print(f"Imported {text} to {url}")
            if url.startswith('./'):
                url = f"https://github.com/{repo}/{url.strip('./')}"
            
            description = ""
            if len(markdown_by_line) > index + 1:
                next_line = markdown_by_line[index + 1].lstrip()
                if (
                    next_line is not None and
                    not next_line.startswith('-') and
                    not is_markdown_link(next_line)
                ):
                    description = next_line

            link = {
                'title': text,
                'titleLower': text.lower(),
                'description': description,
                'descriptionLower': description.lower(),
                'parent': parent,
                'url': url
            }

            dictionary[text] = link

    # Then we parse lists of links
    for (link_list) in regex.findall(LINK_LIST_REGEX, markdown):
        (text, url, description) = link_list
        if url.startswith('./'):
                url = f"https://github.com/{repo}/{url.strip('./')}"
        link = {
            'title': text,
            'titleLower': text.lower(),
            'description': description,
            'descriptionLower': description.lower(),
            'parent': parent,
            'url': url
        }

        dictionary[text] = link


async def sync_with_repo(repo):
    global settings, settingsFile, dictionary, dictionaryFile, access_token

    parse_result = urlparse(repo)
    repoName = parse_result.path.strip("/")
    url = f"https://api.github.com/repos/{repoName}/git/trees/master?recursive=1&access_token={access_token}"
    data = get_json_from_url(url)

    # reset the dictionary and populate
    dictionary = {}
    for branch in data['tree']:
        pathname = branch['path'].lower()
        if pathname.endswith('.md') and not pathname.startswith('.'):
            blob_data = get_json_from_url(f"{branch['url']}?access_token={access_token}")
            contents = base64.b64decode(blob_data['content']).decode('utf-8', errors='ignore')
            import_blob(repo, branch['path'], contents, pathname)

    put_json_file(dictionaryFile, dictionary)
    put_json_file(settingsFile, settings)

def keywords_match(keywords, value):
    matches = []

    for keyword in keywords:
        if keyword in value:
            matches.append(keyword)

    if len(matches) > 0:
        return matches

    return None

def dictionary_matches(keywords):
    global dictionary

    keyword_key = " ".join(keywords)

    if keyword_key in search_cache:
        return search_cache[keyword_key]

    keywords_split = list(map(lambda x: x.lower(), keywords))
    matches = []
    for key, link in dictionary.items():
        str = link['titleLower'] + ' ' + link['description']
        if keywords_match(keywords_split, str) is not None:
            matches.append(link)

    def sort_matches(link):
        matches_title = keywords_match(keywords_split, link['titleLower']) or []
        matches_description = keywords_match(keywords_split, link['descriptionLower']) or []
        return (len(matches_title) * 2) + len(matches_description)

    search_cache[keyword_key] = sorted(matches, key=sort_matches, reverse=True)
    return search_cache[keyword_key]
    

@bot.command(pass_context=True, help="Find a link for a set of keywords")
async def ace(ctx, *keywords):
    global ACKNOWLEDGE_EMOJI, SUCCESS_EMOJI, PROHIBITED_EMOJI, syncing_game, settings, dictionary
    
    await bot.send_typing(ctx.message.channel)
    matches = dictionary_matches(keywords)

    if len(dictionary) is None:
        await bot.say("My dictionary is currently empty. I cannot query at this time.")
        return

    if matches is None:
        await bot.say(f"No matches for {', '.join(keywords_split)} @ https://github.com/{settings['repo']}#readme")
        return

    total_matches = len(matches)
    attempt_index = 1

    while len(matches) is not 0:
        for link in matches[0:attempt_index]:
            rich_embed = discord.Embed(
                title=link['title'],
                description=f"via <{link['parent']}>\n\n{link['description']}",
                type='link',
                url=link['url']
            )

            await bot.send_message(ctx.message.channel, embed=rich_embed)
        
        matches = matches[attempt_index:]
        attempt_index = 3

        if len(matches) > 0:
            await bot.say(f"For more results ({total_matches - len(matches)}/{total_matches}), say $more")
            msg = await bot.wait_for_message(timeout=10, author=ctx.message.author, content='$more')
            
            if msg is None:
                break




            

@bot.command(pass_context=True, help="Set the link repository URL and scrapes topics.")
async def repo(ctx, repo):
    global ACKNOWLEDGE_EMOJI, SUCCESS_EMOJI, PROHIBITED_EMOJI, syncing_game
    
    if not ctx.message.author.server_permissions.administrator:
        await bot.add_reaction(ctx.message, PROHIBITED_EMOJI)
        return

    await bot.add_reaction(ctx.message, ACKNOWLEDGE_EMOJI)
    await bot.change_presence(game=syncing_game, afk=True)
    
    try:
        await sync_with_repo(repo)
    except urllib.error.HTTPError as e:
        await bot.say(f"Could not find repository {repo} on GitHub because {e}")

    await bot.change_presence(game=None, afk=False)
    await bot.remove_reaction(ctx.message, ACKNOWLEDGE_EMOJI, bot.user)
    await bot.add_reaction(ctx.message, SUCCESS_EMOJI)


    if ctx.message.channel.permissions_for(ctx.message.channel.server.me).manage_messages:
        await bot.delete_message(ctx.message)

            
    
@bot.event
async def on_ready():
    global dictionary, settings, settingsFile, dictionaryFile
    
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    settings = get_json_file(settingsFile)
    dictionary = get_json_file(dictionaryFile)


    

bot.run(os.environ['ACEBOT_API_KEY'])
