# AceBot

For the convenience and ease of finding links via https://github.com/markerikson/react-redux-links

# Usage
To run the bot first create a Discord Bot User and get your token. You will also need a Github API token or you may risk hitting the rate limit.

```
ACEBOT_API_KEY=<your bot token> GITHUB_ACCESS_TOKEN=<your github token> python3 bot.py
```

To populate the dictionary (requires administrator privileges on server):

```
$repo https://github.com/markerikson/react-redux-links
```

It will download all related markdown files and will react to your message with a green checkmark when it is done.

```
$ace redux saga
```

Will perform a naïve search through the dictionary matching titles and descriptions. Titles are scored x2 and descriptions x1 for each keyword match. 

The top result will appear first. You have 10 seconds to respond with $more if you need more.



# Goals
Better delivery of more results, preferrably by DM.