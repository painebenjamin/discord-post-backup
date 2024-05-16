# Discord Post Backup

Backs up post-style discord channels including discussion and attachments using direct API queries.

This script does *not* require setting up an app through the Discord developer portal.

## Output Format

- Posts are organized by *channel ID* and *post ID*.
- Attachments are organized by *channel ID*, *post ID* and *attachment ID.*
- A rudimentary index is created to make navigation easy. Open the created `index.html` in your browser to navigate posts.

## How to Use

1. Download python through your method of choice
2. Run `pip install -r requirements.txt` to install prerequisites
3. Open `token.txt`, enter your authentication token (see below for instructions on retrieving this.)
4. Open `channels.txt`, enter your desired channel ID's, one per line.
5. Run `python backup-posts.py`

## How to Get Your Authentication Token
                                                                                                                                            
1. Open Discord in your browser and log in.
2. Open DevTools (F12)
3. Go to the Network tab
4. Refresh the page
5. Find a request to Discord.com, and click on it
6. Go to the Headers tab
7. Find the Authorization header
8. Copy the value

Do NOT share this token with anyone. This is temporary, and after awhile you will need to refresh it.
