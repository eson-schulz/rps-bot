import time, poplib, MySQLdb, sys, smtplib, logging
import urllib, re
from email import parser

help_text = """
Hello %s,
Available commands:
add <user_name>
rps <user> <r/p/s>
scores
games
help
"""

new_help_text = """
To get started, text back
a new username like this:
add BobSmith
"""

# Change these variables

# Email
FROM_ADDRESS = 'username@gmail.com' 
FROM_PASSWORD = 'password'

# Database
HOST = 'localhost'
DATABASE_USERNAME = 'root'
DATABASE_PASSWORD = 'password'
DATABASE_NAME = 'Name'

# Time between checks
DAY_SLEEP = 20
MIDDLE_SLEEP = 20
NIGHT_SLEEP = 120


def get_first_text_part(msg):
    maintype = msg.get_content_maintype()
    if maintype == 'multipart':
        for part in msg.get_payload():
            if part.get_content_maintype() == 'text':
                return part.get_payload()
    elif maintype == 'text':
        return msg.get_payload()

class User(object):
	name = None
	phone = None

	def __init__(self, name, phone):
		self.name = name
		self.phone = phone

class RPSBot(object):

	# A List of email objects
	emails = []

	# The database in which we store the Users and 
	db = None

	# The cursor for the database
	cursor = None

	"""
	Main class for the RPS Bot
	"""

	def read_emails(self):
		"""
		Sets emails to the ones in the inbox
		"""
		try:
			pop_conn = poplib.POP3_SSL('pop.gmail.com')

			#Username for gmail
			pop_conn.user(FROM_ADDRESS)

			#Password for gmail
			pop_conn.pass_(FROM_PASSWORD)

			#Get messages from server:
			messages_total = len(pop_conn.list()[1])
			messages = [pop_conn.retr(i) for i in range(1, messages_total + 1)]
			
			#for i in range(1, messages_total + 1):
			#	pop_conn.dele(i)
			
			# Concat message pieces:
			messages = ["\n".join(mssg[1]) for mssg in messages]
			#Parse message into an email object:
			messages = [parser.Parser().parsestr(mssg) for mssg in messages]
			
			pop_conn.quit()
		except:
			messages = ()

		for mssg in messages:
			print "Read email from: " + mssg['from']
		#either messages[0]['from'] or ['subject']
		self.emails = messages

		print "Checked Emails" 

	def process_emails(self):
		commands = ("add", "help", "scores", "games", "rps")
		"""
		Processes the emails
		"""
		if(len(self.emails) == 0):
			return;

		for message in self.emails:
			sender = message['from']
			body = get_first_text_part(message)
				
			if(sender == FROM_ADDRESS):
				continue;
			if not str(body.replace(" ", "").replace("\n", "")) == "":
				separated_message = body.replace("\n", " ").split(" ")
			elif not str(message['subject']).replace(" ", "").replace("\n", "") == "":
				separated_message = message['subject'].replace("\n", " ").split(" ")
			else:
				separated_message = ("no",)
			
			command = str(separated_message[0].lower())

			if(command not in commands):
				self.send_email(sender, "Not a valid command. Use 'help' to see the valid list.")
				continue

			if(command == "help"):
				user_name = self.database_get_user(sender)
				if(user_name != "None"):
					self.send_email(sender, help_text % user_name)
				else:
					self.send_email(sender, new_help_text)
			elif(command == "scores"):
				self.send_scores(sender)
			elif(command == "games"):
				self.send_games(sender)
			elif(len(separated_message) >= 3 and command == "rps"):
				self.send_challenge(sender, separated_message[1].replace("\n", ""), separated_message[2].replace("\n", ""))

			elif(len(separated_message) >= 2 and command == "add"):
				self.add_user(separated_message[1].replace("\n", ""), sender)

			else:
				self.send_email(sender, "Not a valid command. Use 'help' to see the valid list.")
				
		emails = []

	def add_user(self, name, phone):
		"""
		Makes sure the user is safe to add to the userbase, and
		adds him if true
		"""
		users = self.database_get_users()
		if(len(users) != 0):
			for user in users:
				if user[1] == phone:
					self.send_email(phone, "You are already in the database.")
					return;
				if user[0].lower() == name.lower():
					self.send_email(phone, "Username already taken.")
					return;
				if len(name) > 10:
					self.send_email(phone, "Please choose a username equal to or less than 10 characters.")
					return;


			# Cuts out the + and 1 at the beginning of a phone number
			if phone[:1] == "+":
				phone = phone[1:]
				phone_num_size = len(phone[0:phone.find("@")])

				if phone_num_size > 10:
					phone = phone[phone_num_size - 10:]

			print "Adding:", name, "to the database with phone number:", phone
			if(self.database_add_user(name, phone)):
				self.send_email(phone, "Username successfully added.")
			else:
				self.send_email(phone, "Username failed, try again.")

	def send_email(self, phone, message):

		print "Sending: " + message.replace("\n", " ")

		server = smtplib.SMTP('smtp.gmail.com:587')
		server.ehlo()
		server.starttls()
		server.login(FROM_ADDRESS, FROM_PASSWORD)
		server.sendmail(FROM_ADDRESS, phone, message)
		server.quit()

	def send_scores(self, phone):
		users = self.database_get_users()
		message = ""
		message += "----------- W-L-T"
		if(len(users) != 0):
			for user in users:
				#Ex: Bob------- 5/1/2
				line = "{} {}-{}-{}".format(str(user[0]).ljust(10).replace(" ", "-"), str(user[2]), str(user[3]), str(user[4]))
				if(len(message + line) > 130):
					self.send_email(phone, message)
					message = ""
					message += line
				else:
					message += "\n"
					message += line

		self.send_email(phone, message)

	def send_games(self, sender):
		user = str(self.database_get_user(sender)[0])
		print user
		if(user == 'None'):
			self.send_email(sender, "You must first create a username.")
			return

		games = self.database_get_games(user)
		print games
		if(games == ()):
			self.send_email(sender, "You don't have any open games currently.")
			return
		else:
			message = ""
			for game in games:
				if(game[0] == user):
					message += "O - {} is still thinking.".format(game[1])
				else:
					message += "Y - {} is waiting for you.".format(game[0])
				message += "\n"
			self.send_email(sender, message)
			return

	def send_challenge(self, sender, receiver, choice):
		"""                 (phone) (user_name) (r, p, s)
		Sends a challenge, or responds to one if prompted
		"""
		user = self.database_get_user(sender)[0]
		receiver_phone = self.database_get_phone(receiver)

		if(user.lower() == receiver.lower()):
			self.send_email(sender, "Nice try, but you can't challenge yourself to a game.")
			return;

		if(not self.database_valid_user(receiver)):
			self.send_email(sender, "Not a valid user, try again.")
			return;

		if(user == "None"):
			self.send_email(sender, "You must first add yourself to the users. Use 'help' for more info.")
			return;

		if not choice in ('r', 'p', 's'):
			self.send_email(sender, "Not a valid choice. Use either r, p, or s")
			return;


		game_type = self.database_game_exists(user, receiver)

		if(game_type == "None"):
			worked = self.database_add_game(choice, user, receiver)
			if(not worked):
				self.send_email(sender, "Game failed to create, try again.")
				return;
			else:
				self.send_email(receiver_phone, "You've been challenged to a game by {0}. Respond with\nrps {0} <r, p, or s>".format(user))
				self.send_email(sender, "Challenge sent.")
				print "Added game created by: " + user + " To: " + receiver
				return;

		elif(game_type == "Already"):
			self.send_email(sender, "You've already created a game, wait for a response.")
			return;

		elif(game_type == "Response"):
			print "Response Game"
			self.finish_game(user, receiver, choice)

		else:
			self.send_email(sender, "Error with rps, try again.")
			return;

	def finish_game(self, sender, receiver, choice):
		"""
		Finishes a game
		"""
		opposing_choice = self.database_get_delete_game(receiver, sender)

		sender_phone = self.database_get_phone(sender)
		receiver_phone = self.database_get_phone(receiver)

		if(opposing_choice == "Fail"):
			self.send_email(sender_phone, "Can't finish game, try again.")
			return;
		else:
			win_text = "Victory! {} beats {} vs {}."
			lose_text = "Defeat! {} loses against {} vs {}."
			tie_text = "Tie! {} ties {} vs {}."

			converted_choice = self.convert(choice)
			converted_opposing = self.convert(opposing_choice)

			#Sender wins
			if (self.beats(choice, opposing_choice) == "Yes"):
				self.send_email(sender_phone, win_text.format(converted_choice, converted_opposing, receiver))
				self.send_email(receiver_phone, lose_text.format(converted_opposing, converted_choice, sender))
				
				logging.info("{}({}) beat {}({})".format(sender, choice, receiver, opposing_choice))
				self.database_add_win(sender)
				self.database_add_loss(receiver)

			#Receiver wins
			elif (self.beats(choice, opposing_choice) == "No"):
				self.send_email(sender_phone, lose_text.format(converted_choice, converted_opposing, receiver))
				self.send_email(receiver_phone, win_text.format(converted_opposing, converted_choice, sender))
				
				logging.info("{}({}) lost to {}({})".format(sender, choice, receiver, opposing_choice))
				self.database_add_win(receiver)
				self.database_add_loss(sender)

			#Tie
			else:
				self.send_email(sender_phone, tie_text.format(converted_choice, converted_opposing, receiver))
				self.send_email(receiver_phone, tie_text.format(converted_opposing, converted_choice, sender))
				
				logging.info("{}({}) tied {}({})".format(sender, choice, receiver, opposing_choice))
				self.database_add_tie(receiver)
				self.database_add_tie(sender)


	def beats(self, first, second):
		if(first == second):
			return "Tie"
		elif(first == 'r' and second == 's' or first == 's' and second == 'p' or first == 'p' and second == 'r'):
			return "Yes"
		else:
			return "No"

	def convert(self, choice):
		if(choice.lower() == "r"):
			return "Rock"
		if(choice.lower() == "p"):
			return "Paper"
		if(choice.lower() == "s"):
			return "Scissors"


	#                                      Database methods                                 #
	def database_init(self):
		self.db = MySQLdb.connect(HOST,DATABASE_USERNAME,DATABASE_PASSWORD,DATABASE_NAME)


		self.cursor = self.db.cursor()

	def database_close(self):
		self.db.close

	#                                      Database USERS table methods                                 #

	def database_add_user(self, name, phone):
		"""
		Adds a new user to the database.
		Returns false if the user was not added
		"""
		sql = "INSERT INTO USERS(USER_NAME, PHONE_NUMBER, WINS, LOSSES, TIES) VALUES(%r, %r, 0, 0, 0)"

		try:
			self.cursor.execute(sql % (name, phone))	
			self.db.commit()
		except:
			self.db.rollback()
			print "Can't write user:", sys.exc_info()[0]
			return False

		return True

	def database_add_loss(self, name):
		"""
		Adds 1 to the loss number
		Returns false if it failed
		"""
		sql = "UPDATE USERS SET LOSSES = LOSSES + 1 WHERE USER_NAME = %r"

		try:
			self.cursor.execute(sql % (name))
			self.db.commit()
		except:
			self.db.rollback()
			print "Can't add 1 to loss for: " + name
			return False

		return True

	def database_add_tie(self, name):
		"""
		Adds 1 to the tie number
		Returns false if it failed
		"""
		sql = "UPDATE USERS SET TIES = TIES + 1 WHERE USER_NAME = %r"

		try:
			self.cursor.execute(sql % (name))
			self.db.commit()
		except:
			self.db.rollback()
			print "Can't add 1 to tie for: " + name
			return False

		return True	

	def database_add_win(self, name):
		"""
		Adds 1 to the win number
		Returns false if it failed
		"""
		sql = "UPDATE USERS SET WINS = WINS + 1 WHERE USER_NAME = %r"

		try:
			self.cursor.execute(sql % (name))
			self.db.commit()
		except:
			self.db.rollback()
			print "Can't add 1 to wins for: " + name
			return False

		return True

	def database_get_users(self):
		"""
		Returns all of the users in the database
		"""
		sql = "SELECT * FROM USERS ORDER BY (WINS - LOSSES) DESC, TIES DESC"

		try:
			self.cursor.execute(sql)
			return self.cursor.fetchall()
		except:
			print "Can't get the users from the database:", sys.exc_info()[0]
			return ()

	def database_get_user(self, phone):
		"""
		Returns the name of the user given the phone
		If the user doesn't exist, it returns 'None'
		"""
		sql = "SELECT USER_NAME FROM USERS WHERE PHONE_NUMBER = %r"

		try:
			self.cursor.execute(sql % phone)
			result = self.cursor.fetchall()
			if(result == ()):
				return "None"
			else:
				return result[0]
		except:
			print "Can't get the users from the database:", sys.exc_info()[0]
			return ()

	def database_get_phone(self, user):
		"""
		Returns the name of the phone given the user
		If the phone doesn't exist, it returns 'None'
		"""
		sql = "SELECT PHONE_NUMBER FROM USERS WHERE USER_NAME = %r"

		try:
			self.cursor.execute(sql % user)
			result = self.cursor.fetchall()
			if(result == ()):
				return "None"
			else:
				return result[0]
		except:
			print "Can't get the phones from the database:", sys.exc_info()[0]
			return ()

	def database_valid_user(self, user):
		"""
		Returns a boolean if the user is in the database or not
		"""

		sql = "SELECT USER_NAME FROM USERS WHERE USER_NAME = %r"

		try:
			self.cursor.execute(sql % user)
			result = self.cursor.fetchall()
			if(result == ()):
				return False
			else:
				return True
		except:
			print "Can't get the users from the database:", sys.exc_info()[0]
			return ()

	#                                      Database GAMES table methods                                 #

	def database_add_game(self, choice, user, receiver):
		"""
		Adds a game to the database
		"""

		sql = "INSERT INTO GAMES(CHOICE, SENDER_NAME, RECEIVER_NAME) VALUES(%r, %r, %r)"

		try:
			self.cursor.execute(sql % (choice, user, receiver))	
			self.db.commit()
		except:
			self.db.rollback()
			print "Can't write game:", sys.exc_info()[0]
			return False

		return True

	def database_game_exists(self, sender, receiver):
		"""
		Tells if there is a game between the users
		Returns "None" if there is no game
		Returns "Already" if there is a game started by the sender
		Returns "Response" if there is a game started by the receiver
		Returns "Error" if there is an error
		"""

		sql = "SELECT SENDER_NAME, RECEIVER_NAME FROM GAMES"

		try:
			self.cursor.execute(sql)
			results = self.cursor.fetchall()
			if(results == ()):
				return "None"
			else:
				for game in results:
					sender_name = str(game[0]).lower()
					receiver_name = str(game[1]).lower()
					if(sender_name == sender.lower() and receiver_name == receiver.lower()):
						return "Already"
					if(sender_name== receiver.lower() and receiver_name == sender.lower()):
						return "Response"
				return "None"
		except:
			print "Can't get the games from the database:", sys.exc_info()[0]
			return "Error"

	def database_get_games(self, user):
		"""
		Returns all the games that the user
		is currently in
		"""

		sql = "SELECT SENDER_NAME, RECEIVER_NAME FROM GAMES WHERE SENDER_NAME = %r or RECEIVER_NAME = %r"

		try:
			self.cursor.execute(sql % (user, user))
			results = self.cursor.fetchall()
			return results
		except:
			print "Can't get the games from the database:", sys.exc_info()[0]
			return ()

	def database_get_delete_game(self, sender, receiver):
		"""
		Returns the choice of the game,
		and deletes the game from the database
		"""

		sql = "SELECT SENDER_NAME, RECEIVER_NAME, CHOICE FROM GAMES"

		try:
			if True:
				self.cursor.execute(sql)
				results = self.cursor.fetchall()

				if(results == ()):
					return "Fail"
				else:
					for game in results:
						sender_name = str(game[0]).lower()
						receiver_name = str(game[1]).lower()
						if(sender_name == sender.lower() and receiver_name == receiver.lower()):
							choice = str(game[2]).lower()
							worked = self.database_delete_game(sender_name, receiver_name)
							if(not worked):
								print "Can't delete database."
								return "Fail"
							return choice

					print "Can't find specified game to delete."
					return "Fail";
		except:
			print "Can't get the games from the database:", sys.exc_info()[0]
			return "Fail"

	def database_delete_game(self, sender, receiver):
		"""
		Deletes the given game from the database_init
		"""

		sql = "DELETE FROM GAMES WHERE SENDER_NAME = %r AND RECEIVER_NAME = %r"

		try:
			self.cursor.execute(sql % (sender, receiver))	
			self.db.commit()
		except:
			self.db.rollback()
			print "Can't delete game:", sys.exc_info()[0]
			return False

		return True



bot = RPSBot()

bot.database_init()

logging.basicConfig(filename='games.log',level=logging.DEBUG)

#The amount of hours since last restarting the mysql database
time_since_reset = 0

current = time.localtime()[3] - 6

while True:
	bot.read_emails()
	time.sleep(1)
	bot.process_emails()

	if(not (time.localtime()[3] - 6) == current):
		current = time.localtime()[3] - 6
		time_since_reset += 1

	if(time_since_reset > 5):
		print "Resetting Database"
		bot.database_init()
		time_since_reset = 0

	if(current > 1 and current < 6):
		time.sleep(NIGHT_SLEEP)
	elif(current > 16 or current < 8):
		time.sleep(MIDDLE_SLEEP)
	else:
		time.sleep(DAY_SLEEP)
