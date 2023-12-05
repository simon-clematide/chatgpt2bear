# Importing ChatGPT Conversations to Bear
This repository contains a Python script for importing conversations from the export format. It also includes a Node.js server for handling the callback from the Bear application when a new note is created. The server appends the note information to the `bear_import_log.jsonl` file. The Python script reads from the `bear_import_log.jsonl` file to determine which conversations have already been imported. It then generates a URL for creating a note in Bear with the conversation's content. It uses the `generate_bear_url` function which creates a `bear://` URL that includes the conversation's details and a callback URL (`x-success`) pointing to the Node.js server. The script calls `create_note_in_bear` which uses the `open` subprocess to launch the URL scheme, causing the Bear app to create a new note. Once the note is created, the Bear app calls the `x-success` URL with details about the note. This action is handled by the `server.js` script running the Node.js server. `server.js` receives the success callback and appends the new note information to the `bear_import_log.jsonl` file. The Python script then writes an entry to the `bear_import_log.jsonl` file indicating that the conversation has been imported, to prevent re-importing in the future.

## Requirements
- Python 3.6+ 
- Node.js 12.0+
- Bear App

## Installation
1. Clone this repository.
2. Install the Node.js dependencies: `npm install`

## Usage
1. Export your conversations from ChatGPT via the web interface. And download the zip file that contains all files.
   Unzip the archive and put `conversations.json` into the export directory.
2. If you have the developer tools installed: `make import`
3. Alternatively: Run the Python script with the path to the JSON file: `python chatgpt2bear.py --mode import --chat_export_path export/conversations.json`
4. The script will generate a `bear://` URL for each conversation and open it in the Bear app.
5. The Bear app will call the Node.js server with the note information. The server will append the note information to
   the `bear_import_log.jsonl` file. The Python script will then write an entry to the `bear_import_log.jsonl` file
   indicating that the conversation has been imported, to prevent re-importing in the future.

## Functionality and modes
 - **import mode**: The script reads from the `conversion_import.jsonl` file to determine which conversations have
   already been imported to the Bear application. If the file doesn't exist, it will be created. If a conversation has
   already been imported, it will be skipped. A conversation is considered imported if it has a corresponding entry in
   the `bear_import_log.jsonl` file and if the property 'exists_in_bear' is set to `true`. If `exists_in_bear` is
   `false`, the conversation will be re-imported.

 ```bash
$ python3 chatgpt2bear.py --mode import --chat_export_path chat_export.json --import_log_path bear_import_log.jsonl --max_messages 3
```
 - **check mode**: The script reads from the `conversion_import.jsonl` file to determine which conversations have
   already been imported to the Bear application. It then asks bear to open the note. If the note does not exist an
   error will be reported. After processing all conversations, the script will update `conversion_import.jsonl` file
   with the `exists_in_bear` property set to `true` for all conversations that exist in Bear. The next time an import is
   run, these conversations will be skipped.
 
 ```bash
$ python3 chatgpt2bear.py --mode check_bear_notes_exist --import_log_path bear_import_log.jsonl --max_messages 3
```

## Example
Here's an example of the script running in the terminal:


Here's a description of the flow:

`chatgpt2bear.py` is run from the command line with arguments pointing to the `chat_export.json` and optional parameters for
the `bear_import_log.jsonl` file and max_messages.

The script reads from `bear_import_log.jsonl` to determine which conversations have already been imported to the Bear application.

For each conversation that hasn't been imported, the script generates a URL for creating a note in Bear with the conversation's content. It uses the `generate_bear_url` function which creates a `bear://` URL that includes the conversation's details and a callback URL (`x-success`) pointing to the Node.js server.

The script calls `create_note_in_bear` which uses the `open` subprocess to launch the URL scheme, causing the Bear app to create a new note.

Once the note is created, the Bear app calls the `x-success` URL with details about the note. This action is handled by the `server.js` script running the Node.js server.

`server.js` receives the success callback and appends the new note information to the `bear_import_log.jsonl` file.

`chatgpt2bear.py` then writes an entry to the `bear_import_log.jsonl` file indicating that the conversation has been imported, to prevent re-importing in the future.

This ASCII flowchart represents the interaction between the command line script, the Bear application, and the Node.js server, outlining the import process and the subsequent logging of the import.

The given data structure appears to be a JSON object representing a conversation or a series of interactions, likely within a messaging or task management system. Here's a breakdown of its components:


1. **Overall Structure**: The root of the JSON object has several fields including `title`, `create_time`,
   `update_time`, `mapping`, `moderation_results`, `current_node`, `plugin_ids`, `conversation_id`,
   `conversation_template_id`, and `gizmo_id`. The `mapping` field contains the bulk of the data, representing a tree
   structure of messages and interactions.

2. **Timestamps**: The `create_time` and `update_time` are Unix timestamps (number of seconds since January 1, 1970),
   indicating when the object was created and last updated.

3. **Mapping**: Within `mapping`, each key appears to be a unique identifier for a node (or message) in the
   conversation. Each node contains: - `id`: The unique identifier for the node. - `message`: An object containing
   details about the message, including the author's role, content, status, and metadata. Some `message` objects are
   `null`, suggesting either a placeholder or a non-message action. - `parent`: The identifier of the parent node in the
   conversation, if applicable. - `children`: An array of identifiers representing the node's children in the
   conversation flow.

4. **Message Details**: Each `message` object within a node includes: - An `id`, which is the same as the node
   identifier. - `author`: Information about the message's author, including the role (e.g., `system`, `user`,
   `assistant`) and metadata. - `create_time` and `update_time`: Timestamps for when the message was created and last
   updated. - `content`: Contains the `content_type` (e.g., `text`) and `parts`, which is an array of text strings
   constituting the message content. - `status`: Indicates the status of the message (e.g., `finished_successfully`). -
   `end_turn`, `weight`, `metadata`: Other properties related to the message handling and processing.

5. **Conversation Flow**: The `parent` and `children` fields indicate the flow of conversation. For instance, the node
   with `id` "d1efedb1-be79-4619-baee-db8c36830e50" is a parent to two other nodes, indicating that it likely represents
   an initial message or action to which there were two responses.

6. **Current Node**: The `current_node` field holds the identifier of the node that is currently active or last
   interacted with.

7. **Metadata**: Fields like `moderation_results`, `plugin_ids`, `conversation_id`, `conversation_template_id`, and
   `gizmo_id` likely hold additional data for internal use, such as moderation status, plugin associations, and
   conversation categorization.

In summary, this JSON object is structured to represent a threaded conversation with various interaction nodes, each
containing details about messages, their authors, and the temporal sequence of the conversation. The conversation
involves a system, a user, and an assistant, with messages detailing actions like adding OCR noise to text.

```JSON
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ConversationStructure",
  "description": "A schema for conversation data structure including messages and their relations",
  "type": "object",
  "properties": {
    "title": {
      "type": "string",
      "description": "The title of the conversation or interaction."
    },
    "create_time": {
      "type": "number",
      "description": "UNIX timestamp representing the creation time of the conversation."
    },
    "update_time": {
      "type": "number",
      "description": "UNIX timestamp representing the last update time of the conversation."
    },
    "mapping": {
      "type": "object",
      "additionalProperties": {
        "$ref": "#/definitions/messageNode"
      },
      "description": "A collection of message nodes, each representing an interaction or a message in the conversation."
    },
    "moderation_results": {
      "type": "array",
      "description": "An array to store results of any moderation that has been performed."
    },
    "current_node": {
      "type": "string",
      "description": "The identifier of the most recent or current interaction node."
    },
    "plugin_ids": {
      "type": ["array", "null"],
      "description": "An array of plugin identifiers if plugins are used in the conversation system."
    },
    "conversation_id": {
      "type": "string",
      "description": "A unique identifier for the entire conversation."
    },
    "conversation_template_id": {
      "type": ["string", "null"],
      "description": "The identifier for a template from which this conversation may have been instantiated, if applicable."
    },
    "gizmo_id": {
      "type": ["string", "null"],
      "description": "An identifier for a specific feature or tool (gizmo) used within the conversation, if any."
    }
  },
  "required": [
    "title",
    "create_time",
    "update_time",
    "mapping",
    "current_node",
    "conversation_id"
  ],
  "definitions": {
    "messageNode": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "A unique identifier for the message node."
        },
        "message": {
          "type": ["object", "null"],
          "properties": {
            "id": {
              "type": "string"
            },
            "author": {
              "type": "object",
              "properties": {
                "role": {
                  "type": "string",
                  "description": "The role of the author, such as 'system', 'user', or 'assistant'."
                },
                "name": {
                  "type": ["string", "null"],
                  "description": "The name of the author. It can be null if the name is not provided."
                },
                "metadata": {
                  "type": "object",
                  "additionalProperties": true,
                  "description": "Additional metadata about the author or the message."
                }
              },
              "required": ["role"]
            },
            "create_time": {
              "type": ["number", "null"],
              "description": "The creation time of the message as a UNIX timestamp."
            },
            "update_time": {
              "type": ["number", "null"],
              "description": "The last update time of the message as a UNIX timestamp."
            },
            "content": {
              "type": "object",
              "properties": {
                "content_type": {
                  "type": "string",
                  "description": "The type of content, such as 'text'."
                },
                "parts": {
                  "type": "array",
                  "items": {
                    "type": "string"
                  },
                  "description": "The components of the message content."
                }
              },
              "required": ["content_type", "parts"]
            },
            "status": {
              "type": "string",
              "description": "The processing status of the message, e.g., 'finished_successfully'."
            },
            "end_turn": {
              "type": ["boolean", "null"],
              "description": "A flag indicating whether the message concludes a turn in the conversation."
            },
            "weight": {
              "type": "number",
              "description": "A numerical value indicating the importance or relevance of the message."
            },
            "metadata": {
              "type": "object",
              "additionalProperties": true,
              "description": "A flexible container for additional information related to the message."
            }
          },
          "required": [
            "id",
            "author",
            "content",
            "status",
            "weight",
            "metadata"
          ]
        },
        "parent": {
          "type": ["string", "null"],
          "description": "The identifier of the parent node, establishing the message hierarchy."
        },
        "children": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "An array of identifiers for the child nodes, representing responses or follow-up interactions."
        }
      },
      "required": [
        "id",
        "children"
      ]
    }
  }
}
```