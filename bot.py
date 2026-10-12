import os
import telebot
from telebot import types

# Bot Configuration
TOKEN = "8655619720:AAG6qYbDiLjv8G_pR7Nt8kBJF003GCldAd0"
ADMIN_ID = 6913254882  # Apanar Admin ID

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# In-memory storage
user_channels = {}  # {user_id: [channel_usernames]}
post_cache = {}     # {user_id: {"text": "", "photo": None, "buttons": []}}
broadcast_mode = set() # Admin broadcast tracking

@bot.message_handler(commands=['start'])
def ctl_start(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✨ Create Post", callback_data="create_post"),
        types.InlineKeyboardButton("📢 Add Channel", callback_data="add_channel"),
        types.InlineKeyboardButton("📁 My Channels", callback_data="my_channels"),
        types.InlineKeyboardButton("⚙️ Settings", callback_data="settings")
    )
    
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("📢 Admin Broadcast", callback_data="admin_broadcast"))

    welcome_text = (
        "👋 <b>Welcome to Channel Control Bot!</b>\n\n"
        "I can help you manage your Telegram channels and groups professionally with rich posts, inline buttons, and multi-channel publishing.\n\n"
        "Use the menu below to get started:"
    )
    bot.send_message(user_id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    data = call.data

    if data == "add_channel":
        bot.answer_callback_query(call.id)
        bot.send_message(
            user_id, 
            "➕ **How to add a channel/group:**\n\n"
            "1. Add this bot to your channel/group as an **Administrator** with post permissions.\n"
            "2. Send your channel username or ID here (e.g., `@mychannel` or `-100123456789`)."
        )
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, save_user_channel)

    elif data == "my_channels":
        bot.answer_callback_query(call.id)
        channels = user_channels.get(user_id, [])
        if not channels:
            bot.send_message(user_id, "❌ You haven't added any channels yet. Click 'Add Channel' first.")
        else:
            ch_list = "\n".join([f"• {ch}" for ch in channels])
            bot.send_message(user_id, f"📁 **Your Connected Channels/Groups:**\n\n{ch_list}")

    elif data == "create_post":
        bot.answer_callback_query(call.id)
        channels = user_channels.get(user_id, [])
        if not channels:
            bot.send_message(user_id, "⚠️ Please add at least one channel/group using 'Add Channel' before creating a post.")
            return

        markup = types.InlineKeyboardMarkup()
        for ch in channels:
            markup.add(types.InlineKeyboardButton(ch, callback_data=f"sel_ch_{ch}"))
        
        bot.send_message(user_id, "🎯 **Select a channel/group where you want to publish the post:**", reply_markup=markup)

    elif data.startswith("sel_ch_"):
        ch_name = data.replace("sel_ch_", "")
        post_cache[user_id] = {"target": ch_name, "text": "", "photo": None, "buttons": []}
        bot.answer_callback_query(call.id)
        bot.send_message(user_id, f"✅ Target set to: <b>{ch_name}</b>\n\nNow send the **Text** or **Photo with caption** for your post:")
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, receive_post_content)

    elif data == "add_url_button":
        bot.answer_callback_query(call.id)
        bot.send_message(user_id, "🔗 Send button details in this format:\n`Button Text - https://example.com`")
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, receive_url_button)

    elif data == "publish_post":
        bot.answer_callback_query(call.id)
        post_data = post_cache.get(user_id)
        if not post_data:
            bot.send_message(user_id, "❌ No post data found. Start over using /start.")
            return

        target = post_data["target"]
        text = post_data["text"]
        photo = post_data["photo"]
        buttons = post_data["buttons"]

        markup = types.InlineKeyboardMarkup()
        for btn in buttons:
            markup.add(types.InlineKeyboardButton(btn['text'], url=btn['url']))

        try:
            if photo:
                bot.send_photo(target, photo, caption=text, reply_markup=markup if buttons else None)
            else:
                bot.send_message(target, text, reply_markup=markup if buttons else None)
            
            bot.send_message(user_id, f"✅ **Successfully posted to {target}!** 🎉")
        except Exception as e:
            bot.send_message(user_id, f"❌ Failed to post. Make sure the bot is an Admin in {target}.\nError: {e}")

    elif data == "admin_broadcast" and user_id == ADMIN_ID:
        bot.answer_callback_query(call.id)
        broadcast_mode.add(user_id)
        bot.send_message(user_id, "📢 **Admin Broadcast Mode:** Send the message/photo you want to broadcast to all connected users and channels.")

def save_user_channel(message):
    user_id = message.from_user.id
    channel = message.text.strip()
    if not channel.startswith("@") and not channel.startswith("-"):
        bot.send_message(user_id, "❌ Invalid format. Please use `@channelusername` or valid chat ID.")
        return

    if user_id not in user_channels:
        user_channels[user_id] = []
    
    if channel not in user_channels[user_id]:
        user_channels[user_id].append(channel)
    
    bot.send_message(user_id, f"✅ Channel/Group <b>{channel}</b> successfully added!")

def receive_post_content(message):
    user_id = message.from_user.id
    if user_id not in post_cache:
        return

    if message.photo:
        post_cache[user_id]["photo"] = message.photo[-1].file_id
        post_cache[user_id]["text"] = message.caption or ""
    else:
        post_cache[user_id]["text"] = message.text or ""

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add URL Button", callback_data="add_url_button"),
        types.InlineKeyboardButton("🚀 Publish Now", callback_data="publish_post")
    )
    bot.send_message(user_id, "✨ **Post preview saved!** What would you like to do next?", reply_markup=markup)

def receive_url_button(message):
    user_id = message.from_user.id
    if user_id not in post_cache:
        return

    try:
        parts = message.text.split("-")
        btn_text = parts[0].strip()
        btn_url = parts[1].strip()
        post_cache[user_id]["buttons"].append({"text": btn_text, "url": btn_url})
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("➕ Add Another Button", callback_data="add_url_button"),
            types.InlineKeyboardButton("🚀 Publish Now", callback_data="publish_post")
        )
        bot.send_message(user_id, f"✅ Button **{btn_text}** added successfully!", reply_markup=markup)
    except Exception:
        bot.send_message(user_id, "❌ Wrong format! Send like: `Click Here - https://t.me/...`")

@bot.message_handler(func=lambda msg: msg.from_user.id in broadcast_mode)
def process_admin_broadcast(message):
    admin_id = message.from_user.id
    broadcast_mode.remove(admin_id)
    
    success_count = 0
    for uid, channels in user_channels.items():
        for ch in channels:
            try:
                if message.photo:
                    bot.send_photo(ch, message.photo[-1].file_id, caption=message.caption or "")
                else:
                    bot.send_message(ch, message.text)
                success_count += 1
            except Exception:
                pass
                
    bot.send_message(admin_id, f"📢 Broadcast completed! Sent successfully to {success_count} destinations.")

if __name__ == "__main__":
    print("Bot is running smoothly...")
    bot.infinity_polling()
