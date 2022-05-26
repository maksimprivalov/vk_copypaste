import telebot
import vk_api
import requests
import os
import json
import time
import shutil

from auth_data import token_VK, token_TG
from telebot import types

bot = telebot.TeleBot(token_TG)
session = vk_api.VkApi(token_VK)
posts_count = "10"
group_name = ""
channal_name = ""

old_posts_id = []
fresh_posts_id = []
work_posts_id = []

########################################################## START
@bot.message_handler(commands=['start'])
def welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Добавить группу")
    markup.add(item1)
    bot.send_message(message.from_user.id, 'Добрый день. Этот бот предназначен для копирования контента из ВК в Телеграм.', reply_markup=markup)

########################################################## CHATTING
@bot.message_handler(content_types=['text'])
def start(message):
    global group_name
    global channal_name
    if message.text == "Добавить группу":
        bot.send_message(message.from_user.id, "Вставьте домен вашей группы:", reply_markup = types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, get_group_name)

    if message.text == "Обновить посты":
        bot.send_message(message.from_user.id, "Происходит обновление", reply_markup = types.ReplyKeyboardRemove())
        get_wall_posts(group_name, channal_name)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Добавить группу")
        item2 = types.KeyboardButton("Обновить посты")
        markup.add(item1, item2)
        bot.send_message(message.from_user.id, "Обработка постов закончена!", reply_markup = markup)

########################################################## Получить домен группы
def get_group_name(message):
    global group_name
    global channal_name
    group_name = message.text
    url = f"https://api.vk.com/method/groups.getById?group_id={group_name}&access_token={token_VK}&v=5.52"
    req = requests.get(url)
    src = req.json()
    try:
        group = src['response']
        bot.send_message(message.from_user.id, "Группа добавлена!\nДобавьте бота в чат/канал и разрешите ему выкладывать посты, после вставте имя канала с @. Например @durov_russia")
        bot.register_next_step_handler(message, get_channal_name)
    except Exception:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Добавить группу")
        item2 = types.KeyboardButton("Обновить посты")
        markup.add(item1, item2)
        bot.send_message(message.from_user.id, "Такой группы не существует. Или вы неправильно указали домен. Домен это часть после vk.com/\nНапример для vk.com/vk доменом будет vk", reply_markup = markup)

########################################################## Получить ник канала
def get_channal_name(message):
    global group_name
    global channal_name
    channal_name = message.text
    try:
        id_to_del = bot.send_message(channal_name, "test").message_id
        bot.delete_message(channal_name, id_to_del)
        bot.send_message(message.from_user.id, "Канал добавлен. Происходит обработка постов.")
        get_wall_posts(group_name, channal_name)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Добавить группу")
        item2 = types.KeyboardButton("Обновить посты")
        markup.add(item1, item2)
        bot.send_message(message.from_user.id, "Обработка постов закончена!", reply_markup = markup)
        shutil.rmtree(f"./{group_name}")
    except Exception:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Добавить группу")
        item2 = types.KeyboardButton("Обновить посты")
        markup.add(item1, item2)
        bot.send_message(message.from_user.id, "Вы не разрешили боту делать посты или неправльно указали имя канала", reply_markup = markup)

########################################################## Функция получения контента из постов
def get_wall_posts(group_name, channal_name):
    global old_posts_id
    global fresh_posts_id
    global work_posts_id
    fresh_posts_id = []
    photo_quality = ["photo_2560","photo_1280","photo_807","photo_604","photo_130","photo_75"]

    #собираем ID новых постов в массив fresh_posts_id и сравниваем fresh и old, получаем массив work в котором id новых постов
    url = f"https://api.vk.com/method/wall.get?domain={group_name}&count={posts_count}&access_token={token_VK}&v=5.52"
    req = requests.get(url)
    src = req.json()
    posts = src["response"]["items"]
    for fresh_post_id in posts:
        fresh_post_id = fresh_post_id["id"]
        fresh_posts_id.append(fresh_post_id)
    work_posts_id = [work_posts_id for work_posts_id in fresh_posts_id if work_posts_id not in set(old_posts_id)]
    old_posts_id = fresh_posts_id
    if len(work_posts_id) == 0:
        return None

    #Создаем папку для фото
    if not os.path.exists(f"{group_name}"):
        os.mkdir(group_name)
        os.mkdir(f"{group_name}/files")

########################################################## Извлечение и публикация постов
    for post in posts:
        post_id = post["id"]
        if post_id in work_posts_id:
            text_post = post["text"]
            if text_post != "":
                bot.send_message(channal_name, text_post)
            if "attachments" in post:
                post = post["attachments"]
                photo_post_count = 0
                for post_item_photo in post:
                    if post_item_photo["type"] == "photo":
                        for pq in photo_quality:
                            if pq in post_item_photo["photo"]:
                                post_photo = post_item_photo["photo"][pq]
                                post_id_counter = str(post_id) + f"_{photo_post_count}"
                                resourse = requests.get(post_photo)
                                with open(f"{group_name}/files/{post_id_counter}.jpg", "wb") as img_file:
                                    img_file.write(resourse.content)
                                photo_link = open(f"{group_name}/files/{post_id_counter}.jpg", 'rb')
                                try:
                                    bot.send_photo(channal_name, photo_link)
                                except Exception:
                                    print("Слишком много постов!")
                                    time.sleep(60)
                                    photo_post_count += 1
                                break

bot.polling(none_stop=True,interval=1 )
