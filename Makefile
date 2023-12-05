# 

import:
	python3 chatgpt2bear.py --mode import  -c bear_import_log.jsonl --chat_export_path export/conversations.json

#: check if all notes are imported
check:
	python3 chatgpt2bear.py --mode check_bear_notes_exist --bear_import_log bear_import_log.jsonl 