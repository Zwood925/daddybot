**DADDYBOT**

This is my first attempt at .py scripting to make something useful for myself where I wrote in every line of code myself, with no copy and pasting. 

Right now, it runs on completely open-source software and can do a couple basic things;

!weather **city-name**
    gives a 3 day forecast for the given city, with a high, a low, and conditions for the days

!read **book-name**
    adds a book to a sql library of books I have read. Right now it just keeps me from adding the same book more than once. The idea is that the !book_rec function will check against this list and make sure it doesn't give a bunch of books I have read already. That's not in here yet though.

!book_rec 
    takes a title of a book and sends it to a local llm with a custom prompt to get 5 recommendations for books like the given title. 

*Tech Stack
    Python and dependencies/library- discord, aiohttp, python-dotenv
    
    Database- sqlite3

    Ai- Local Ollama(llama3.1:8b)

    