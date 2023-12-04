"""
This script imports conversations from ChatGPT to Bear. It uses the ChatGPT export file to generate a Bear note for each
conversation. The note contains a link to the conversation in ChatGPT, as well as the messages in the conversation. A
log file is used to keep track of which conversations have already been imported. The script can be called from the
command line.

Usage:

python3 chatgpt2bear.py <chat_export_path> [--conversation_import_path <path>] [--max_messages <n>]



"""


import argparse
import json
import re
import logging
import subprocess
import time
import urllib.parse
import sys
from datetime import datetime
from typing import Dict, Set

# Setting up logging
logging.basicConfig(
    filename="logfile.log",  # specify your log file name here
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Create a StreamHandler for stderr
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.WARNING)  # Set the level to WARNING or ERROR as needed

# Add the handler to the root logger
logging.getLogger().addHandler(stderr_handler)


def escape_hashtags(text: str) -> str:
    """
    Escapes hashtags in the text by prepending a backslash.

    This is specific to Bear, which uses hashtags for tagging. If a #TAG is not escaped, Bear will interpret it as a tag.
    
    Args:
        text (str): The text to escape.

    Returns:
        str: The escaped text.

    Examples:
    >>> escape_hashtags("This is a #hashtag")
    'This is a \\\\#hashtag'

    >>> escape_hashtags("Multiple ##hashtags in #text")
    'Multiple \\\\##hashtags in \\\\#text'

    >>> escape_hashtags("No hashtag here")
    'No hashtag here'

    >>> escape_hashtags("# First #Second")
    '# First \\\\#Second'

    >>> escape_hashtags("Backslash after  #\\\\aescaped")
    'Backslash after  \\\\#\\\\aescaped'
    """
    return re.sub(r"(?<![\#])(#)(?![ ])", r"\\\1", text)

def escape_triple_backticks(text: str) -> str:
    """
    Escapes triple backticks in the text by prepending a backslash.

    This is specific to Bear, which uses triple backticks to denote code blocks. If a ``` is not escaped, Bear will interpret it as a code block.
    
    Args:
        text (str): The text to escape.

    Returns:
        str: The escaped text.


    """
    return re.sub(r"(?<![\`])(```)", r"\\\1", text)

def read_conversation_import(log_path: str) -> Dict[str, str]:
    """
    Reads the import log file and returns the import log as a dictionary.

    Args:
        log_path (str): The path to the import log file.

    Returns:
        Dict[str, str]: The import log.
    """
    conversation_import = {}
    try:
        with open(log_path, "r") as log_file:
            for line in log_file:
                if line.strip():  # Make sure the line is not empty
                    entry = json.loads(line.strip())
                    conversation_import[entry["conversation_id"]] = entry.get(
                        "bear_note_id"
                    )
    except FileNotFoundError:
        logging.warning(f"Log file {log_path} not found. Will create a new one.")
    return conversation_import


def write_conversation_import_entry(
    log_path: str, conversation_id: str, bear_note_id: str
) -> None:
    """
    Writes an entry to the import log file.

    Args:
        log_path (str): The path to the import log file.
        conversation_id (str): The ID of the chat.
        bear_note_id (str): The ID of the Bear note.
    """
    with open(log_path, "a") as log_file:
        log_file.write(
            json.dumps(
                {"conversation_id": conversation_id, "bear_note_id": bear_note_id}
            )
            + "\n"
        )


def clean_title(title: str) -> str:
    """
    Cleans the title by replacing non-alphanumeric characters with underscores.

    Args:
        title (str): The title to clean.

    Returns:
        str: The cleaned title.
    """
    return re.sub(r"\W+", " ", title)


def get_formatted_date(create_time):
    """Return the date in YYYY-MM format from a timestamp.

    Args:
        create_time (float): The timestamp to convert.

    Returns:
        str: The formatted date in YYYY-MM format.

    Example:
    >>> get_formatted_date(1609459200)  # 2021-01-01 00:00:00 UTC
    '2021-01'
    >>> get_formatted_date(1625097600)  # 2021-07-01 00:00:00 UTC
    '2021-07'
    """
    # If create_time is not provided, use the current time
    if create_time is None:
        create_time = datetime.now().timestamp()

    # Convert the timestamp to a datetime object
    date_time_obj = datetime.fromtimestamp(create_time)

    # Format the datetime object to YYYY-MM format
    formatted_date = date_time_obj.strftime("%Y-%m")

    return formatted_date


def format_role(role: str) -> str:
    if role == "user":
        return "👤"
    elif role == "assistant":
        return "🤖"
    else:
        return role


def generate_openai_url(message):
    """Return markdown URL with link to OpenAI chat and text "ChatGPT Link"

    Args:
        message (Dict): Dictionary containing conversation details, including the conversation_id.

    Returns:
        str: A markdown-formatted string that contains a hyperlink to the OpenAI chat.
    """
    conversation_id = message.get("conversation_id", "")
    return f"[ChatGPT Link](https://chat.openai.com/c/{conversation_id})"


def generate_bear_url(message, conversation_id):
    title = message.get("title", "Untitled")
    title = urllib.parse.quote(title)

    messages = message.get("mapping", {})
    text = generate_openai_url(message) + "\n\n"
    for message_data in messages.values():
        msg = message_data.get("message")
        if msg:
            author = msg.get("author", {}).get("role", "")
            content = msg.get("content", {})
            if "parts" in content:
                if not content["parts"][0]:
                    continue

            if author == "user" and "parts" in content:
                user_parts = [
                    escape_triple_backticks(escape_hashtags(t))
                    for t in content.get("parts", [])
                    if isinstance(t, str) and t.strip()
                ]

                user_parts[0] = user_parts[0].strip()
                user_parts[-1] = user_parts[-1].strip()
                text_parts = ["```"] + user_parts + ["```"]
            elif "parts" in content:
                text_parts = [
                    escape_hashtags(t)
                    for t in content.get("parts", [])
                    if isinstance(t, str) and t.strip()
                ]
            else:
                continue
            logging.info(f"content: {content}")
            text += f"{format_role(author)}\n" + "\n".join(text_parts) + "\n\n"
    text_encoded = urllib.parse.quote(text)

    create_time = message.get("create_time", datetime.now().timestamp())
    date = get_formatted_date(create_time)

    # Add the conversation_id as a query parameter to the x-success URL
    x_success_url = f"http://localhost:3000/success?conversation_id={conversation_id}&characters={len(text)}"

    url = (
        f"bear://x-callback-url/create?"
        f"title={title}&text={text_encoded}&tags=chatgpt/archive/{date}&x-success={urllib.parse.quote(x_success_url)}"
    )
    return url


def create_note_in_bear(url: str) -> None:
    """
    Opens the Bear URL to create a note.

    Args:
        url (str): The Bear URL.
    """
    subprocess.run(["open", "-g", url], stdout=subprocess.PIPE)


def import_chats(
    chat_export_path: str, conversation_import_path: str, max_messages: int
) -> None:
    """
    Imports chats from the ChatGPT export file to Bear.
    """
    conversation_import = read_conversation_import(conversation_import_path)
    try:
        with open(chat_export_path, "r", encoding="utf-8") as export_file:
            data = json.load(export_file)

        server_process = launch_node_server()
        if server_process is None:
            return

        try:
            processed_ids = parse_messages(
                data,
                set(conversation_import.keys()),
                max_messages,
                conversation_import_path,
            )
            logging.info(f"Processed {processed_ids} conversations.")
        finally:
            server_process.terminate()
            logging.info("Server process terminated.")

    except FileNotFoundError:
        logging.error(f"Export file {chat_export_path} not found.")
    except json.JSONDecodeError:
        logging.error("Export file is not a valid JSON.")


def parse_messages(
    data, processed_ids: Set[str], max_messages: int, log_path: str
) -> Set[str]:
    """
    Parses messages and creates notes in Bear for new conversations.

    Returns:
        Set[str]: The IDs of the new conversations.
    """
    new_ids = set()
    messages = 0
    existing_conversations = 0
    imported_conversations = 0
    for item in data:
        conversation_id = item.get("conversation_id")
        if conversation_id in processed_ids:
            logging.info(f"Conversation {conversation_id} already imported.")
            existing_conversations += 1
            continue
        if messages >= max_messages:
            logging.info(f"Max messages reached: {max_messages}")
            break
        conversation_id = item.get("conversation_id")
        if conversation_id in processed_ids:
            print(f"Conversation {conversation_id} already imported.")
            existing_conversations += 1
            continue  # Skip if already imported
        messages += 1
        imported_conversations += 1
        url = generate_bear_url(item, conversation_id)
        logging.info(f"Creating note for conversation {conversation_id}.")
        create_note_in_bear(url)
        time.sleep(2)
        # write_conversation_import_entry(log_path, conversation_id, bear_note_id)
        new_ids.add(conversation_id)
    print(f"Existing conversations: {existing_conversations}")
    print(f"Imported conversations: {imported_conversations}")
    print(f"Total conversations: {existing_conversations + imported_conversations}")

    return new_ids


def launch_node_server() -> subprocess.Popen:
    """
    Launches the Node.js server.

    Returns:
        subprocess.Popen: The server process.
    """
    try:
        server_process = subprocess.Popen(
            ["node", "server.js"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        time.sleep(3)
        if server_process.poll() is not None:
            stderr = server_process.stderr.read().decode("utf-8")
            print(f"Server failed to start with error: {stderr}")
            return None
        else:
            print("Server is running.")
            return server_process
    except Exception as e:
        print(f"An error occurred while starting the server: {e}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import ChatGPT conversations to Bear")
    parser.add_argument("chat_export_path", help="Path to the ChatGPT export JSON file")
    parser.add_argument(
        "--conversation_import_path",
        default="conversation_import.jsonl",
        help="Path to the import log JSONL file",
    )
    parser.add_argument(
        "--max_messages",
        type=int,
        default=1000,
        help="Maximum number of messages to import",
    )
    args = parser.parse_args()

    import_chats(
        args.chat_export_path, args.conversation_import_path, args.max_messages
    )
