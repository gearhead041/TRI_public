import re
from time import sleep
import schedule
import telebot
import datetime
import psycopg2
import pytz
import os
import logging
import random
from threading import Thread
from uuid import uuid4
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

LAGOS_TIME = pytz.timezone('Africa/Lagos')
logging.basicConfig(level=logging.INFO)
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_HOST = os.environ.get('DB_HOST')
DB_USER  = os.environ.get('DB_USER')
DB_NAME = os.environ.get('DB_NAME')
BOT_TOKEN = os.environ.get('BOT_TOKEN')

bot = telebot.TeleBot(BOT_TOKEN) # type: ignore


def connect_to_db(db_name):
  conn = psycopg2.connect(database=DB_NAME,
                          user=DB_USER,
                          password=DB_PASSWORD,
                          host=DB_HOST,
                          port="5432")
  cursor_obj = conn.cursor()
  return cursor_obj, conn


cursor_obj, conn = connect_to_db(DB_NAME)
user_table = """CREATE TABLE IF NOT EXISTS USERS (
        USERID INTEGER PRIMARY KEY NOT NULL,
        USER_NAME VARCHAR(50),
        Birthday VARCHAR(5),
        MESSAGEID VARCHAR(40)
        ); """

admin_table = """CREATE TABLE IF NOT EXISTS ADMINS (
            USERID INTEGER UNIQUE,
            MESSAGEID VARCHAR(40) UNIQUE,
            TOKEN VARCHAR(80) UNIQUE DEFAULT NULL,
            TOKEN_USED BOOLEAN DEFAULT FALSE
          );"""
          
broadcast_table =""" CREATE TABLE IF NOT EXISTS BROADCASTS (
                  ID SERIAL PRIMARY KEY ,
                  MESSAGE TEXT,
                  SCHEDULED_TIME VARCHAR(20),
                  SENT_WEEKLY BOOLEAN DEFAULT FALSE
                  );"""
                  
cursor_obj.execute(user_table)
logging.info("User Table Created/Confirmed to Exist")
cursor_obj.execute(admin_table)
logging.info("Admin Table Created/Confirmed to Exist")
cursor_obj.execute(broadcast_table)
logging.info("Broadcasts Table Created/Confirmed to Exist")
conn.commit()
#seeding database
cursor_obj.execute(""" INSERT INTO ADMINS (USERID,MESSAGEID) VALUES
                      (650582717,650582717)
                      ON CONFLICT (USERID) DO UPDATE SET
                      (USERID,MESSAGEID) = (650582717,650582717);
                   """)
cursor_obj.execute(""" INSERT INTO ADMINS (USERID,MESSAGEID) VALUES
                      (971314157,971314157)
                      ON CONFLICT (USERID) DO UPDATE SET
                      (USERID,MESSAGEID) = (971314157,971314157)
                   """)
conn.commit()
logging.info("Database seeded")
cursor_obj.close()

@bot.message_handler(commands=['start'])
def send_welcome(message):
  global user_id
  user_id = message.from_user.id
  global user_name
  user_name = message.from_user.first_name
  if len(check_user_in_database(user_id)) == 0:
    get_user_data(message)
  else:
    bot.send_message(message.chat.id,f"Welcome Back {user_name}!")
    return
  logging.info(f'User Clicked Start: ID - {user_id} Name - {user_name}')
  
welcome_message = lambda name: f"""
Hello {name}, I am your personal TRI assistant.
I am here to help you with being sound in mind, fervent in spirit🥳💃

There are a lot of things I can help you with
- Newsletter Updates from The Rabbi Institute 📰
- Daily Affirmations 🎶
- Register for TRI Bootcamps📝
and so much more...

I'm so excited to do this with you 😁😁
Get ready to build a superior mindset!! 💪🏾💪🏾
"""
def get_user_data(message):
  bot.send_message(message.chat.id,welcome_message(message.from_user.first_name), parse_mode='Markdown')
  
  keyboard = InlineKeyboardMarkup()
  keyboard.row(InlineKeyboardButton('January', callback_data ="JAN"),
                InlineKeyboardButton('February', callback_data ="FEB"),
                InlineKeyboardButton('March', callback_data ="MAR"))
  
  keyboard.row(InlineKeyboardButton('April', callback_data ="APR"),
                InlineKeyboardButton('May', callback_data ="MAY"),
                InlineKeyboardButton('June', callback_data ="JUN"))
  
  keyboard.row(InlineKeyboardButton('July', callback_data ="JUL"),
                InlineKeyboardButton('August', callback_data ="AUG"),
                InlineKeyboardButton('September', callback_data ="SEP"))
  
  keyboard.row(InlineKeyboardButton('October', callback_data ="OCT"),
                InlineKeyboardButton('November', callback_data ="NOV"),
                InlineKeyboardButton('December', callback_data ="DEC"))
  
  bot.send_message(message.chat.id,"What month were you born?", reply_markup= keyboard)

def is_month_data(query):
  return re.match(r'^([A-Za-z]){3}$', query.data) is not None

@bot.callback_query_handler(func=is_month_data)
def month_button(call):
    month_name = call.data[0:3].title()
    keyboard = InlineKeyboardMarkup()
    for x in range(4):
      row_buttons = []
      for y in range(1,8):
        row_buttons.append(InlineKeyboardButton(f"{(7*x)+y}", callback_data=month_name + str((7*x)+y)))
      keyboard.row(*row_buttons)
    keyboard.row(InlineKeyboardButton("29",callback_data= month_name + "29"),
                 InlineKeyboardButton("30",callback_data= month_name + "30"),
                 InlineKeyboardButton("31",callback_data= month_name + "31"))
    bot.send_message(call.message.chat.id, "Please choose a day:", reply_markup=keyboard)

def is_date_data(query):
  return re.match(r'^([A-Za-z]){3}\d{1,2}$', query.data) is not None
@bot.callback_query_handler(func=is_date_data)
def day_button(call):
  birth_month = call.data[0:3]
  if len(call.data) == 4:
    birth_day = call.data[-1:]
  else:
    birth_day = call.data[-2:]
  save_in_database(birth_month,birth_day,call.message.chat.id)
  bot.send_message(call.message.chat.id, "Thanks alot!")
  
def save_in_database(birth_month,birth_day, messageid):
  cursor_obj, conn = connect_to_db(DB_NAME)
  params =   (user_id,user_name, birth_month+birth_day, messageid)
  cursor_obj.execute(""" 
                    INSERT INTO USERS (USERID, USER_NAME, Birthday, MESSAGEID)
                    VALUES (%s,%s,%s,%s);
                    """,params)
  cursor_obj.close()
  conn.commit()
  logging.info(f"data saved: {user_name}, {user_id},{birth_month + birth_day},{messageid}")
  
def check_user_in_database(userid):
  # param = userid
  cursor_obj,conn = connect_to_db(DB_NAME)
  cursor_obj.execute(f"SELECT * FROM USERS WHERE USERID = %s", (str(userid),))
  rows = cursor_obj.fetchall()
  cursor_obj.close()
  conn.commit()
  return rows

@bot.message_handler(commands=['newbroadcast'])
def create_broadcast_message(message):
  if check_if_admin(message.from_user.id) is False:
    bot.send_message(message.chat.id, "Sorry you're not authorized for this action 🤧")
    return
  bot.send_message(message.chat.id,'Please send the text you want to broadcast. Use {name} (all small letters please) as placeholder for individual user names.')
  #insert message into database
  bot.register_next_step_handler(message, save_broadcast)

def save_broadcast(message):
  if message.text == '/cancel':
    cancel_action(message)
    return
  if message.text.startswith('/'):
    bot.send_message(message.chat.id, "Sorry you can't use a command as a broadcast message. Please try again.")
    bot.register_next_step_handler(message, save_broadcast)
    return
  cursor_obj, conn = connect_to_db(DB_NAME)
  cursor_obj.execute(f"""INSERT INTO BROADCASTS (Message)
                       VALUES (%s);
                      """, (message.text,))
  conn.commit()
  cursor_obj.execute("""SELECT MAX(ID) FROM BROADCASTS""")
  broadcast_id = cursor_obj.fetchone()[0] #type: ignore
  cursor_obj.close()
  logging.info(f"broadcast message saved: {message.text}")
  bot.send_message(message.chat.id,'Message saved.')
  keyboard = InlineKeyboardMarkup()
  keyboard.row(InlineKeyboardButton('Yes', callback_data =f"YES_{broadcast_id}"),
                InlineKeyboardButton('No', callback_data =f"NO_{broadcast_id}"))
  keyboard.row(InlineKeyboardButton('Edit Message', callback_data =f"EDIT_{broadcast_id}"), 
                InlineKeyboardButton('Delete Message', callback_data =f"DELETE_{broadcast_id}"))
  bot.send_message(message.chat.id,"Do you wish to send the message to users now? If you selct no you'll be given an option to schedule it or add it to the weekly messages.",reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data[0:4] == "YES_")
def broadcast_message(call):
  broadcast_id = call.data.split('_')[1]
  cursor_obj, conn = connect_to_db(DB_NAME)
  cursor_obj.execute(f"SELECT * FROM BROADCASTS WHERE ID={broadcast_id}")
  message = cursor_obj.fetchone()[1] #type: ignore
  if message == None:
    bot.send_message(call.message.chat.id, "Message not found. It may have been deleted by you or another admin.")
    return
  cursor_obj.execute(f"SELECT * FROM USERS")
  rows = cursor_obj.fetchall()
  cursor_obj.close()
  for x in rows:
    userid,username, birthday, chat_id = x
    bot.send_message(chat_id, message.format(name=username))
  bot.send_message(call.message.chat.id, "Messages sent.")
  logging.info(f'Message with Id {broadcast_id} sent to all users')
  
@bot.callback_query_handler(func=lambda call: call.data[0:3] == "NO_") 
def cancel_broadcast(call):
  broadcast_id = call.data.split("_")[1].strip()
  keyboard = InlineKeyboardMarkup()
  keyboard.row(InlineKeyboardButton('Yes', callback_data =f"YESCH_{broadcast_id}"), 
               InlineKeyboardButton('No', callback_data =f"NOSCH_{broadcast_id}"))
  bot.send_message(call.message.chat.id, "Broadcast cancelled. Do wish to schedule the message?", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data[0:5] == "YESCH")
def schedule_broadcast(call):
  broadcast_id = call.data.split('_')[1]
  bot.send_message(call.message.chat.id, "Please enter the date you wish to send the message in the format: DD/MM/YYYY. All messages will be sent by 12PM")
  bot.register_next_step_handler(call.message, schedule_broadcast_message, broadcast_id)

@bot.callback_query_handler(func=lambda call: call.data[0:5] == "NOSCH")
def dont_schedule_broadcast(call):
  broadcast_id = call.data.split('_')[1]
  bot.send_message(call.message.chat.id, "Do you want me to put it on the weekly random schedule? Reply with 'Yes' or 'No'. Weekly Messages are sent by 8AM.")
  bot.register_next_step_handler(call.message, random_schedule_broadcast, broadcast_id)

def random_schedule_broadcast(message, *args):
  if message.text == '/cancel':
    cancel_action(message)
    return
  broadcast_id = args[0]
  if message.text.lower() == 'yes':
    cursor_obj, conn = connect_to_db(DB_NAME)
    cursor_obj.execute(f'UPDATE BROADCASTS SET SENT_WEEKLY = TRUE WHERE ID={broadcast_id}')
    conn.commit()
    cursor_obj.close()
    logging.info(f"Broadcast {broadcast_id} scheduled for weekly random messages.")
    bot.send_message(message.chat.id,'Message saved and scheduled for weekly random messages. 👍')
  elif message.text.lower() == 'no':
    bot.send_message(message.chat.id,'Message saved and not scheduled.')
  else:
    bot.send_message(message.chat.id, 'Sorry wrong input. Please try again')
    bot.register_next_step_handler(message,random_schedule_broadcast, broadcast_id )

def schedule_broadcast_message(message, *args):
  if message.text == '/cancel':
    cancel_action(message)
    return
  date_time = message.text
  broadcast_id = args[0]
  cursor_obj, conn = connect_to_db(DB_NAME)
  cursor_obj.execute(f"UPDATE BROADCASTS SET SCHEDULED_TIME = %s WHERE ID=%s", (date_time,broadcast_id))  
  conn.commit()
  conn.close()
  bot.send_message(message.chat.id, 'Broadcast successfully scheduled. ✅')

def send_scheduled_broadcasts():
  cursor_obj, conn = connect_to_db(DB_NAME)
  cursor_obj.execute(f"SELECT * FROM BROADCASTS WHERE SCHEDULED_TIME IS NOT NULL")
  rows = cursor_obj.fetchall()
  for x in rows:
    id, message, scheduled_time, *remaining_values = x
    #this will work if the bot is hosted in a different timezone
    current_time = datetime.datetime.now(LAGOS_TIME).strftime("%d/%m/%Y")
    if scheduled_time == current_time:
      cursor_obj.execute(f"SELECT * FROM USERS")
      users = cursor_obj.fetchall()
      for y in users:
        userid, username, birthday, chat_id = y
        bot.send_message(chat_id, message.format(name=username))
      logging.info(f"Broadcast {id} sent.")
      cursor_obj.execute("DELETE FROM BROADCASTS WHERE ID=%s", (str(id),))
      conn.commit()
      logging.info(f"Broadcast {id} deleted.")
  cursor_obj.close()
  logging.info("Scheduled Broadcasts checked.")

# List to hold the broadcasts that have been sent already this week 
#TODO shift to database
SENT_WEEKLY_BROADCASTS = set()
def send_weekly_broadcasts():
  logging.info('About to send weekly broadcasts')
  cursor_obj, conn = connect_to_db(DB_NAME)
  cursor_obj.execute(f"SELECT * FROM BROADCASTS WHERE SENT_WEEKLY = TRUE")
  rows = cursor_obj.fetchall()
  messages = []
  for x in rows:
    id, message, *other_data = x
    messages.append(message)
  if len(SENT_WEEKLY_BROADCASTS) == len(messages):
    SENT_WEEKLY_BROADCASTS.clear()
  message_to_send = random.choice(messages)
  logging.info("picked a message:")
  logging.info(message_to_send[:120])
  while message_to_send in SENT_WEEKLY_BROADCASTS:
    logging.info("picking another one:")
    message_to_send = random.choice(messages) #Make sure we pick one that has not been sent this week
  logging.info("picked another message:")
  logging.info(message_to_send[:120])
  cursor_obj.execute(f"SELECT * FROM USERS")
  users = cursor_obj.fetchall()
  cursor_obj.close()
  for y in users:
    userid, username, birthday, chat_id = y
    bot.send_message(chat_id, message_to_send.format(name=username))
  SENT_WEEKLY_BROADCASTS.add(message_to_send)
  logging.info(f"Broadcast message:\n{message_to_send[:20]}\nsent.")
  
@bot.callback_query_handler(func=lambda call: call.data[0:6] == "DELETE")
def delete_broadcast(call):
  broadcast_id = call.data[7:]
  cursor_obj, conn = connect_to_db(DB_NAME)
  cursor_obj.execute(f"DELETE FROM BROADCASTS WHERE ID={broadcast_id}")
  bot.send_message(call.message.chat.id, "Broadcast deleted.")
  logging.info(f"Broadcast {broadcast_id} deleted.")
  conn.commit()
  cursor_obj.close()

@bot.callback_query_handler(func=lambda call: call.data[0:4] == "EDIT")
def edit_broadcast(call):
  broadcast_id = call.data.split('_')[1]
  cursor_obj, conn = connect_to_db(DB_NAME)
  cursor_obj.execute(f"SELECT * FROM BROADCASTS WHERE ID={broadcast_id}")
  message = cursor_obj.fetchone()[1] #type: ignore
  cursor_obj.close()
  bot.send_message(call.message.chat.id, "This is the saved message.")
  bot.send_message(call.message.chat.id, message)
  bot.send_message(call.message.chat.id, "Please enter the new message. Send /cancel to cancel operation")
  bot.register_next_step_handler(call.message, update_broadcast_message, broadcast_id)

def update_broadcast_message(message, *args):
  if message.text == '/cancel':
    cancel_action(message)
    return
  cursor_obj,conn  = connect_to_db(DB_NAME)
  broadcast_id = args[0]
  cursor_obj.execute("UPDATE BROADCASTS SET MESSAGE = %s WHERE ID=%s", (message.text, str(broadcast_id)))
  conn.commit()
  cursor_obj.close()
  bot.send_message(message.chat.id, "Message updated.")
  logging.info(f"Broadcast {broadcast_id} updated.")

@bot.message_handler(commands=['listbroadcasts'])
def list_broadcasts(message):
  #Check if user is authorized to use this command
  if check_if_admin(message.from_user.id) is False:
    bot.send_message(message.chat.id, "Sorry you're not authorized for this action 🤧")
    return
  cursor_obj, conn = connect_to_db(DB_NAME)
  cursor_obj.execute(f"SELECT * FROM BROADCASTS")
  rows = cursor_obj.fetchall()
  cursor_obj.close()
  if len(rows) == 0:
    bot.send_message(message.chat.id, "No broadcasts found.")
    return
  for x in rows:
    id, broadcast_message, scheduled_time, sent_weekly = x
    message_string = f"{id}. {broadcast_message[:100]+'...'} \nScheduled: {scheduled_time}\nSent Weekly: {sent_weekly}"
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton('Edit', callback_data=f'EDIT_{id}'), 
                 InlineKeyboardButton('Delete', callback_data=f'DELETE_{id}'),
                 )
    keyboard.row(InlineKeyboardButton('Schedule/Reschedule',callback_data=f'YESCH_{id}'))
    bot.send_message(message.chat.id, message_string, reply_markup=keyboard)
  logging.info("Broadcasts listed.") 

def check_if_admin(userid):
  cursor_obj,conn = connect_to_db(DB_NAME)
  cursor_obj.execute('SELECT * FROM ADMINS')
  admins_data = cursor_obj.fetchall()
  cursor_obj.close()
  admins_ids = []
  logging.info(f'Checking id: {userid}')
  for admin in admins_data:
    admin_id, messageid, *token_data = admin
    if admin_id != None:
      admins_ids.append(int(admin_id.strip()))
  if int(userid) not in admins_ids:
    
    return False
  else:
    return True

@bot.message_handler(commands=['addadmin'])
def add_admin(message):
  #Check if user is authorized to use this command
  if check_if_admin(message.from_user.id) is False:
    bot.send_message(message.chat.id, "Sorry you're not authorized for this action 🤧")
    return
  bot.send_message(message.chat.id, "I'll generate a token for the new admin. Please send it to them and ask them to use the /newadmin command to register.")
  #Generate token
  token = uuid4()
  cursor_obj, conn = connect_to_db(DB_NAME)
  cursor_obj.execute(f"INSERT INTO ADMINS (TOKEN) VALUES ('{token}')")
  conn.commit()
  cursor_obj.close()
  bot.send_message(message.chat.id, f"Token: `{token}`", parse_mode='Markdown')
  
@bot.message_handler(commands=['newadmin'])
def new_admin(message):
  #Check if user already authorized
  if check_if_admin(message.from_user.id) is True:
    bot.send_message(message.chat.id, "You've been made an admin already.")
    return
  bot.send_message(message.chat.id, "Please enter the token you received from the admin.")
  bot.register_next_step_handler(message, confirm_token)

def confirm_token(message):
  if message.text == '/cancel':
    cancel_action(message)
    return
  cursor_obj, conn = connect_to_db(DB_NAME)
  token = message.text
  cursor_obj.execute(f'SELECT * FROM ADMINS WHERE TOKEN = %s',(token,))
  result = cursor_obj.fetchone()
  user_id, message_id, db_token, token_used = result #type: ignore
  if db_token is None:
    bot.send_message(message.chat.id, 'This token is unauthorized')
    return
  elif  token_used is True:
    bot.send_message(message.chat.id, 'Token used already')
    return
  else:
    cursor_obj.execute(f'INSERT INTO ADMINS (USERID, MESSAGEID, TOKEN_USED) VALUES({message.from_user.id}, {message.chat.id}, {True})')
    conn.commit()
    bot.send_message(message.chat.id, "You are now an admin")
    logging.info(f'New admin with Id {message.from_user.id} added')
  cursor_obj.close()

@bot.message_handler(commands=['cancel'])
def cancel_command(message):
  cancel_action(message)

def cancel_action(message):
  bot.send_message(message.chat.id, 'Action cancelled')

def check_birthdays():
  cursor_obj,conn = connect_to_db(DB_NAME)
  cursor_obj.execute('SELECT * FROM USERS')
  rows = cursor_obj.fetchall()
  cursor_obj.close()
  for x in rows:
    userid, username, birthday, chat_id = x
    current_date = datetime.datetime.now(LAGOS_TIME).strftime("%b%d")
    if birthday == current_date:
      bot.send_message(chat_id,f"Happy Birthday {username}!! 🥳🥳🎉🎉")
  logging.info("Checked for birthdays")

@bot.message_handler(commands=['welcomemessage'])
def view_welcome_message(message):
  if not check_if_admin(message.from_user.id):
    bot.send_message(message.chat.id, 'You are not authorized to use this command')
    return
  bot.send_message(message.chat.id, welcome_message('{name_goes_here}'), parse_mode='Markdown')
  
@bot.message_handler(commands=['help'])
def help_command(message):
  bot.send_message(message.chat.id, "This is your personal TRI Bot.")
  if check_if_admin(message.from_user.id):
    bot.send_message(message.chat.id,'Admin Commands and Description:')
    bot.send_message(message.chat.id,"""/newbroadcast - Create a new broadcast message\n
/listbroadcasts - List all broadcast messages\n
/addadmin - Add a new admin\n
/newadmin - Register as a new admin\n
/cancel - Cancel an action\n
/welcomemessage - View welcome message new users would see\n
/help - Show this help message""") 
    logging.info(f'Sent admin commands to {message.from_user.id}')
#default message handler
@bot.message_handler()
def scratch_head(message):
  bot.send_message(message.chat.id, 'Sorry I don''t get that. ')

schedule.every().day.at("12:00",LAGOS_TIME).do(send_scheduled_broadcasts) #type: ignore
schedule.every().day.at("08:00",LAGOS_TIME).do(send_weekly_broadcasts) #type: ignore
schedule.every().day.at("12:00",LAGOS_TIME).do(check_birthdays) #type: ignore

def schedule_checker():
  while True:
    schedule.run_pending()
    sleep(1)
    
Thread(target=schedule_checker).start()

bot.infinity_polling(logger_level=logging.INFO)

