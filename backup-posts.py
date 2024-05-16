# Copyright (c) 2024 Benjamin Paine <painebenjamin@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import os
import json
import jinja2
import requests

from typing import Dict, Iterable, Tuple, Union, List, Any

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(HERE, "token.txt")
CHANNELS_FILE = os.path.join(HERE, "channels.txt")
DOWNLOAD_DIR = os.path.join(HERE, "channels")
TEMPLATES_DIR = os.path.join(HERE, "templates")
INDEX_TEMPLATE = os.path.join(TEMPLATES_DIR, "index.j2")
CHANNEL_TEMPLATE = os.path.join(TEMPLATES_DIR, "channel.j2")
POST_TEMPLATE = os.path.join(TEMPLATES_DIR, "post.j2")

TOKEN = open(TOKEN_FILE).read().strip()
CHANNEL_IDS = [int(line.strip()) for line in open(CHANNELS_FILE).readlines()]


def get_channel_metadata(channel_id: int) -> Dict:
    """
    Get metadata for a channel
    """
    headers = {"Authorization": TOKEN}
    response = requests.get(
        f"https://discord.com/api/v9/channels/{channel_id}", headers=headers
    )
    response.raise_for_status()
    return response.json()


def get_post_data(channel_id: int, *thread_ids: int) -> Union[Dict, Tuple[Dict]]:
    """
    Gets post data from one or more thread IDs.
    """
    headers = {"Authorization": TOKEN}
    payload = {"thread_ids": [str(thread_id) for thread_id in thread_ids]}
    response = requests.post(
        f"https://discord.com/api/v9/channels/{channel_id}/post-data",
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    data = response.json()
    thread_data = [data["threads"][str(thread_id)] for thread_id in thread_ids]
    return tuple(thread_data)


def get_thread_messages(channel_id: int, page_size: int = 50) -> Iterable[Dict]:
    """
    Retrieve messages from a channel
    """
    headers = {"Authorization": TOKEN}
    parameters = {"limit": page_size}
    while True:
        response = requests.get(
            f"https://discord.com/api/v9/channels/{channel_id}/messages",
            headers=headers,
            params=parameters,
        )
        response.raise_for_status()
        data = response.json()
        if not data:
            break
        for message in data:
            yield message
        parameters["before"] = data[-1]["id"]


def retrieve_threads(channel_id: int, page_size: int = 10) -> Iterable[Dict]:
    """
    Retrieve threads from a channel
    """
    headers = {"Authorization": TOKEN}
    parameters: Dict[str, Union[str, bool, int]] = {
        "limit": page_size,
        "sort_order": "desc",
        "sort_by": "last_message_time",
        "archived": True,
    }
    offset = 0
    while True:
        parameters["offset"] = offset
        response = requests.get(
            f"https://discord.com/api/v9/channels/{channel_id}/threads/search",
            headers=headers,
            params=parameters,
        )
        response.raise_for_status()
        data = response.json()
        if not data:
            break
        thread_data = get_post_data(
            channel_id, *[thread["id"] for thread in data["threads"]]
        )
        for thread, thread_datum in zip(data["threads"], thread_data):
            thread["data"] = thread_datum
            if thread_datum["first_message"]:
                post_channel_id = thread_datum["first_message"]["channel_id"]
                thread["messages"] = list(get_thread_messages(post_channel_id))
                yield thread
        offset += page_size
        if not data["has_more"]:
            break


def download_attachments(directory: str, attachments: List[Dict]) -> None:
    """
    Download attachments from a message
    """
    headers = {"Authorization": TOKEN}
    for attachment in attachments:
        attachment_url = attachment["url"]
        attachment_dir = os.path.join(directory, attachment["id"])
        os.makedirs(attachment_dir, exist_ok=True)
        attachment_path = os.path.join(attachment_dir, attachment["filename"])
        if not os.path.exists(attachment_path):
            response = requests.get(attachment_url, headers=headers)
            response.raise_for_status()
            with open(attachment_path, "wb") as file:
                file.write(response.content)


def write_channel_index(
    channel_id: int, posts: List[Dict], **channel_metadata: Any
) -> str:
    """
    Write an index file for the posts
    """
    posts.sort(
        key=lambda post: post["data"]["first_message"]["timestamp"], reverse=True
    )
    with open(CHANNEL_TEMPLATE) as file:
        template = jinja2.Template(file.read())
    index_path = os.path.join(DOWNLOAD_DIR, str(channel_id), "index.html")
    with open(index_path, "w") as file:
        file.write(template.render(posts=posts, **channel_metadata))
    return index_path


def write_index(channels: List[Dict]) -> str:
    """
    Write an index file for the channels
    """
    with open(INDEX_TEMPLATE) as file:
        template = jinja2.Template(file.read())
    index_path = os.path.join(DOWNLOAD_DIR, "index.html")
    with open(index_path, "w") as file:
        file.write(template.render(channels=channels))
    return index_path


def write_post(channel_id: int, post: Dict) -> str:
    """
    Write a post file
    """
    with open(POST_TEMPLATE) as file:
        template = jinja2.Template(file.read())
    post_path = os.path.join(
        DOWNLOAD_DIR, str(channel_id), str(post["id"]), "index.html"
    )
    post["messages"].sort(key=lambda message: message["timestamp"])
    with open(post_path, "w") as file:
        file.write(template.render(**post))
    return post_path


def main() -> None:
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    channels = []
    for channel_id in CHANNEL_IDS:
        print(f"Processing channel {channel_id}")
        posts = []
        channel_metadata = get_channel_metadata(channel_id)
        channels.append(channel_metadata)
        channel_dir = os.path.join(DOWNLOAD_DIR, str(channel_id))
        os.makedirs(channel_dir, exist_ok=True)
        for i, thread in enumerate(retrieve_threads(channel_id)):
            print(f"Processing thread {thread['id']} ({i + 1})")
            thread_dir = os.path.join(channel_dir, thread["id"])
            thread_data_file = os.path.join(thread_dir, "data.json")
            attachments_dir = os.path.join(thread_dir, "attachments")
            os.makedirs(attachments_dir, exist_ok=True)
            with open(thread_data_file, "w") as file:
                json.dump(thread, file, indent=2)
            attachments = thread["data"]["first_message"]["attachments"]
            if attachments:
                download_attachments(attachments_dir, attachments)
            for message in thread["messages"]:
                attachments = message["attachments"]
                if attachments:
                    download_attachments(attachments_dir, attachments)
            post_path = write_post(channel_id, thread)
            print(f"Wrote post to {post_path}")
            posts.append(thread)
        index_path = write_channel_index(channel_id, posts, **channel_metadata)
        print(f"Wrote channel index to {index_path}")
    index_path = write_index(channels)
    print(f"Wrote index to {index_path}")


if __name__ == "__main__":
    main()
