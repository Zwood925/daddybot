**DADDYBOT**

This is my first attempt at .py scripting to make something useful for myself where I wrote in every line of code myself, with no copy and pasting. 

Right now, it runs on completely open-source software and can do a couple basic things;

!weather **city-name**
    gives a 3 day forecast for the given city, with a high, a low, and conditions for the days

!read **book-name**
    adds a book to a sql library of books I have read. Right now it just keeps me from adding the same book more than once. The idea is that the !book_rec function will check against this list and make sure it doesn't give a bunch of books I have read already. That's not in here yet though.

    **UPDATE** Now it automatically recognizes who is typing the command based on their Discord username, saves it to their specific list, and asks follow up questions to build a solid SQL row. It asks for author, rating, what series it's a part of and what they liked about it. It also keeps you from adding the same book more than once. 

!stats
    prints out a scoreboard showing how many books my wife and I have logged in the database. (I wrote a script that migrated both of our lists, her's was an excel sheet and mine was just a text list so they both took some finagling to get that right) 

!book_rec 
    takes a title of a book and sends it to a local llm with a custom prompt to get 5 recommendations for books like the given title. 

    **UPDATE** I got this wired up to the database. Now it checks my SQL database to see what I've already read so it doesn't recommend those, but it also checks wifey's list and prioritizes recommending books she's loved. 
    I did have to add a thing to chunk the AI's text because apparently she will ramble and break Discord's limit of 2000 characters.

*Tech Stack
    Python and dependencies/library- discord, aiohttp, python-dotenv
    
    Database- sqlite3

    Ai- Local Ollama(llama3.1:8b)

    