Rock Paper Scissors Text Server
=======
A rps server that runs off of an email address.

Eventually I will have a description of how to set it up.

Usage
-------
To use any command, text it to the email that is configured with the server.

To add yourself to the database, text the command:
    
    add {username}
    
To see the list of scores and users, text the command:
    
    scores
    
To send a challenge to a user, text the command:

    rps {user} {{r} or {p} or {s}}
    
To see the list of your current games, text the command:

    games
    
To see the condensed list of these commands, text the command:

    help

Installation
-------
Generally, installation follows these steps:

1. Install [Python 2](https://www.python.org/download/)
2. Install [MySQLdb](http://sourceforge.net/projects/mysql-python/)
3. Setup a new database using the provided .sql file
4. Change the variables at the beginning of rps_server.py
5. Run rps_server.py
