"""
This script imports conversations from ChatGPT to Bear. It uses the ChatGPT export file to generate a Bear note for each
conversation. The note contains a link to the conversation in ChatGPT, as well as the messages in the conversation. A
log file is used to keep track of which conversations have already been imported. The script can be called from the
command line.

Usage:

python3 chatgpt2bear.py <chat_export_path> [--bear_import_log <path>] [--max_messages <n>]

"""


import argparse
import json
import re
import logging
import subprocess
import time
import urllib.parse
import sys
import collections
from datetime import datetime
from typing import Dict, Set, Optional, Any

# Setting up logging
logging.basicConfig(
    filename="logfile.log",  # specify your log file name here
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Create a StreamHandler for stderr
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.INFO)  # Set the level to WARNING or ERROR as needed
stderr_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)

# Add the handler to the root logger
logging.getLogger().addHandler(stderr_handler)


def clean_title(title: str) -> str:
    """
    Cleans the title by replacing non-alphanumeric characters with underscores.

    Args:
        title (str): The title to clean.

    Returns:
        str: The cleaned title.
    """
    return re.sub(r"\W+", " ", title)


def escape_hashtags(text: str) -> str:
    """
    Escapes hashtags in the text by prepending a backslash.

    This is specific to Bear, which uses hashtags for tagging. If a #TAG is not escaped, Bear will interpret it as a
    tag.

    Args:
        text (str): The text to escape.

    Returns:
        str: The escaped text.

    Examples: >>> escape_hashtags("This is a #hashtag") 'This is a \\\\#hashtag'

    >>> escape_hashtags("Multiple ##hashtags in #text")
    'Multiple \\\\##hashtags in \\\\#text'

    >>> escape_hashtags("No hashtag here")
    'No hashtag here'

    >>> escape_hashtags("# First #Second")
    '# First \\\\#Second'

    >>> escape_hashtags("Backslash after  #\\\\aescaped")
    'Backslash after  \\\\#\\\\aescaped'
    """
    return re.sub(r"(?<!#)(#)(?![ ])", r"\\\1", text)


def escape_triple_backticks(text: str) -> str:
    """
    Escapes triple backticks in the text by prepending a backslash.

    This is specific to Bear, which uses triple backticks to denote code blocks.
    If a ``` is not escaped, Bear will interpret it as a code block.

    Args:
        text (str): The text to escape.

    Returns:
        str: The escaped text.


    """
    return re.sub(r"(?<!`)(```)", r"\\\1", text)


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
    """
    Formats the role by replacing the role name with an emoji.
    """
    if role == "user":
        return "👤"
    elif role == "assistant":
        return "🤖"
    else:
        return role


def read_conversation_import(log_path: str) -> Dict[str, str]:
    """
    Reads the import log file and returns the import log as a dictionary.

    Args:
        log_path (str): The path to the import log file.

    Returns:
        Dict[str, str]: The import log, where the keys are conversation IDs and the values are bear note IDs.
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


def generate_openai_url(message):
    """Return markdown URL with link to OpenAI chat and text "ChatGPT Link"

    Args:
        message (Dict): Dictionary containing conversation details, including the conversation_id.

    Returns:
        str: A markdown-formatted string that contains a hyperlink to the OpenAI chat.
    """
    conversation_id = message.get("conversation_id", "")
    return f"[ChatGPT Link](https://chat.openai.com/c/{conversation_id})"


def generate_bear_url(message:Dict[Any,Any], conversation_id: str) -> str:
    """
    Generates a Bear URL for a conversation.
    """
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


def callback(url: str) -> None:
    """
    Request an x-callback-url to be processed by Bear.

    Args:
        url (str): The Bear URL.
    """
    subprocess.run(["open", "-g", url], stdout=subprocess.PIPE)


def import_chats(
    chat_export_path: str, bear_import_log: str, max_messages: int
) -> None:
    """
    Imports chats from the ChatGPT export file to Bear.
    """
    conversation_import = read_conversation_import(bear_import_log)
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
                bear_import_log,
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
        if item.get("exists_in_bear", False):
            logging.info(f"Conversation {conversation_id} already exists in Bear.")
            existing_conversations += 1
            continue
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
        callback(url)
        time.sleep(1)
        # write_conversation_import_entry(log_path, conversation_id, bear_note_id)
        new_ids.add(conversation_id)
    print(f"Existing conversations: {existing_conversations}")
    print(f"Imported conversations: {imported_conversations}")
    print(f"Total conversations: {existing_conversations + imported_conversations}")

    return new_ids


def launch_node_server() -> Optional[subprocess.Popen]:
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


def check_notes_exist(
    bear_import_log: str, max_messages: int, force_check: bool = False
) -> None:
    """
    This function reads the conversation import log file and processes each conversation up to a maximum number of
    messages.

    Args:
        conversation_import_log (str): The path to the conversation import log file. This file should be in JSONL
        format, where each line is a JSON object representing a conversation.

        max_messages (int): The maximum number of
        messages to process. If this number is reached, the function will stop processing messages and return.
        :param bear_import_log:
        :param force_check:
    """

    stats = collections.Counter()
    logging.info(
        f"Checking if notes exist for conversations in {bear_import_log}"
    )
    messages_processed = 0
    # truncate the file "conversation_check.jsonl"
    with open("conversation_check.jsonl", "w"):
        pass
    with open(bear_import_log, "r") as f:
        server_process = launch_node_server()
        if server_process is None:
            return

        for line in f:
            if messages_processed > max_messages:
                break

            data = json.loads(line)
            if "bear_id" not in data:
                logging.info(
                    f"Skipping conversation {data['conversation_id']} with no bear_id in data {data}"
                )
                stats["NO-BEAR-ID"] += 1
                continue
            if "exists_in_bear" in data and not force_check:
                logging.info(
                    f"Skipping conversation {data['conversation_id']} with exists_in_bear in data {data}"
                )
                stats["EXISTS-IN-BEAR"] += 1
                continue
            logging.info(
                f"Checking if note exists for conversation {data['conversation_id']} in data {data}"
            )
            messages_processed += 1
            bear_id = data["bear_id"]
            x_error_url = (
                f"http://localhost:3000/bear-missing?conversation_id={data['conversation_id']}"
                f"&identifier={bear_id}"
            )
            callback_url = (
                f"bear://x-callback-url/open-note?id={bear_id}"
                f"&x-success=http://localhost:3000/bear-exists"
                f"&show_window=no&"
                f"x-error={urllib.parse.quote(x_error_url)}"
            )
            callback(callback_url)
            time.sleep(0.1)  # Wait for a second to avoid overwhelming the server
        server_process.terminate()
    exists_db = {}
    with open("conversation_check.jsonl", "r") as f:
        for line in f:
            data = json.loads(line)
            exists_db[data["bear_id"]] = data["exists_in_bear"]
            stats[f'EXISTS-IN-BEAR-{data["exists_in_bear"]}'] += 1

    with open(bear_import_log, "r") as f:
        import_db = {}
        for line in f:
            data = json.loads(line)
            import_db[data["bear_id"]] = data
            if data["bear_id"] not in exists_db:
                logging.info(f"Missing bear_id {data['bear_id']} in exists_db")

                continue
            else:
                import_db[data["bear_id"]]["exists_in_bear"] = exists_db[
                    data["bear_id"]
                ]

    with open(bear_import_log, "w") as f:
        for bear_id, data in import_db.items():
            f.write(json.dumps(data) + "\n")
    logging.info(f"Stats: {stats}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import ChatGPT conversations to Bear")
    parser.add_argument(
        "--chat_export_path", help="Path to the ChatGPT export JSON file"
    )
    parser.add_argument(
        "--bear_import_log",
        "-c",
        default="bear_import_log.jsonl",
        help="Path to the import log JSONL file",
    )
    parser.add_argument(
        "--mode",
        default="import",
        choices=["import", "check_bear_notes_exist"],
        help=(
            "Mode to run in. 'import' or 'check_bear_notes_exist'"
            "'check_bear_notes_exist' will check if notes in the "
            "bear_import_log.jsonl exist in Bear."
        ),
    )

    parser.add_argument(
        "--force_check",
        action="store_true",
        help="Perform check in bear even if exists_in_bear is set",
    )
    parser.add_argument(
        "--max_messages",
        "-m",
        type=int,
        default=1000,
        help="Maximum number of messages to import or check",
    )
    args = parser.parse_args()

    if args.mode == "check_bear_notes_exist":
        check_notes_exist(
            bear_import_log=args.bear_import_log,
            max_messages=args.max_messages,
            force_check=args.force_check,
        )
    elif args.mode == "import":
        import_chats(args.chat_export_path, args.bear_import_log, args.max_messages)
