const express = require('express');
const fs = require('fs');
const app = express();
const port = 3000;

app.get('/success', (req, res) => {
  const noteId = req.query.identifier; // The ID assigned by Bear to the new note
  const noteTitle = req.query.title; // The title of the new note
  const chatId = req.query.conversation_id; // The ChatGPT conversation ID
  const noteLength = req.query.characters; // number of characters in the note

  let data = {
    bear_id: noteId,
    title: noteTitle,
    conversation_id: chatId, // Storing the ChatGPT conversation ID
    bear_import_timestamp: Date.now(), // Current timestamp
    bear_import_ISO8601_date: new Date().toISOString(), // ISO 8601 format timestamp
    note_characters: noteLength,
  };
  
  // Append to the JSONL file
  fs.appendFileSync('bear_import_log.jsonl', JSON.stringify(data) + '\n', { flag: 'a' });
  res.send('<script>window.close();</script>');
});

app.get('/bear-exists', (req, res) => {
  const bearId = req.query.identifier;
  let data = {
    bear_id: bearId,
    exists_in_bear: true,
  };

  // Append to the JSONL file
  fs.appendFileSync('conversation_check.jsonl', JSON.stringify(data) + '\n', { flag: 'a' }); 


  //res.send('<script>window.close();</script>');
  //res.send(`Note with ID ${bearId} already exists in Bear. Please delete it and try again.`);  
  res.send('<script>window.close();</script>');

});
app.get('/bear-missing', (req, res) => {
  const bearId = req.query.identifier;
  const conversation_id = req.query.conversation_id;
  console.log(`Conversation_ID: ${conversation_id} bearId: ${bearId}`);
  let data = {
    bear_id: bearId,
    conversation_id: conversation_id,
    exists_in_bear: false,
  };

  // Append to the JSONL file
  fs.appendFileSync('conversation_check.jsonl', JSON.stringify(data) + '\n', { flag: 'a' }); 

  //res.send('<script>window.close();</script>');
  //res.send(`Note with ID ${bearId} cannot be found in Bear. Please try again.`);
  res.send('<script>window.close();</script>');
});

app.listen(port, () => {
  console.log(`Server listening at http://localhost:${port}`);
  process.stdout.write("Server started\n"); // Sends a message to stdout
});
