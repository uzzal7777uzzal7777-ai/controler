import os
import telebot
from telebot import types

# Bot Configuration
TOKEN = "8655619720:AAEoktF8J9JbAIwcvQf6WgXOqO8SXiPQvOA"
ADMIN_ID = 6913254882  # Apanar Admin ID

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# In-memory storage
user_channels = {}  # {user_id: [channel_usernames]}
post_cache = {}     # {user_id: {"target": "", "text": "", "photo": None, "buttons": []}}
broadcast_mode = set() # Admin broadcast tracking

# Main Menu Keyboard (Persistent Keyboard at the bottom)
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # Common user buttons
    btn_create = types.KeyboardButton("✨ Create Post")
    btn_add_ch = types.KeyboardButton("📢 Add Channel")
    btn_my_ch = types.KeyboardButton("📁 My Channels")
    btn_settings = types.KeyboardButton("⚙️ Settings")
    
    markup.add(btn_create, btn_add_ch)
    markup.add(btn_my_ch, btn_settings)

    # Main Admin extra button
    if user_id == ADMIN_ID:
        btn_admin = types.KeyboardButton("👑 Admin Broadcast")
        markup.add(btn_admin)

    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    welcome_text = (
        "👋 <b>Welcome to Controller Bot!</b>\n\n"
        "I can help you manage your Telegram channels and groups professionally with rich posts, inline buttons, and multi-channel publishing.\n\n"
        "👇 <b>Select an option from the menu keyboard below:</b>"
    )
    bot.send_message(user_id, welcome_text, reply_markup=get_main_keyboard(user_id))

# Reply Keyboard Button Handlers
@bot.message_handler(func=lambda message: message.text in ["✨ Create Post", "📢 Add Channel", "📁 My Channels", "⚙️ Settings", "👑 Admin Broadcast"])
def handle_menu_buttons(message):
    user_id = message.from_user.id
    text = message.text

    if text == "📢 Add Channel":
        bot.send_message(
            user_id, 
            "➕ <b>How to add a channel/group:</b>\n\n"
            "1. Add this bot to your channel/group as an <b>Administrator</b> with post permissions.\n"
            "2. Send your channel username or ID here (e.g., <code>@mychannel</code> or <code>-100123456789</code>)."
        )
        bot.register_next_step_handler(message, save_user_channel)

    elif text == "📁 My Channels":
        channels = user_channels.get(user_id, [])
        if not channels:
            bot.send_message(user_id, "❌ You haven't added any channels yet. Click <b>📢 Add Channel</b> first.")
        else:
            ch_list = "\n".join([f"• <b>{ch}</b>" for ch in channels])
            bot.send_message(user_id, f"📁 <b>Your Connected Channels/Groups:</b>\n\n{ch_list}")

    elif text == "✨ Create Post":
        channels = user_channels.get(user_id, [])
        if not channels:
            bot.send_message(user_id, "⚠️ Please add at least one channel/group using <b>📢 Add Channel</b> before creating a post.")
            return

        markup = types.InlineKeyboardMarkup()
        for ch in channels:
            markup.add(types.InlineKeyboardButton(ch, callback_data=f"sel_ch_{ch}"))
        
        bot.send_message(user_id, "🎯 <b>Select a channel/group where you want to publish:</b>", reply_markup=markup)

    elif text == "⚙️ Settings":
        bot.send_message(user_id, "⚙️ <b>Settings:</b>\n\n• Bot Status: Active\n• Auto-Notification: ON\n• Language: English")

    elif text == "👑 Admin Broadcast" and user_id == ADMIN_ID:
        broadcast_mode.add(user_id)
        bot.send_message(user_id, "📢 <b>Admin Broadcast Mode:</b>\n\nSend the text or photo you want to broadcast to all connected channels/groups.")

# Save Channel Handler
def save_user_channel(message):
    user_id = message.from_user.id
    channel = message.text.strip()
    
    if not channel.startswith("@") and not channel.startswith("-"):
        bot.send_message(user_id, "❌ Invalid format. Please send username starting with @ or channel ID starting with -100.")
        return

    if user_id not in user_channels:
        user_channels[user_id] = []
    
    if channel not in user_channels[user_id]:
        user_channels[user_id].append(channel)
    
    bot.send_message(user_id, f"✅ Channel/Group <b>{channel}</b> successfully added!")

# Inline Callback Queries for Post Creation Workflow
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    data = call.data

    if data.startswith("sel_ch_"):
        ch_name = data.replace("sel_ch_", "")
        post_cache[user_id] = {"target": ch_name, "text": "", "photo": None, "buttons": []}
        bot.answer_callback_query(call.id)
        bot.send_message(user_id, f"✅ Target set to: <b>{ch_name}</b>\n\nNow send the <b>Text</b> or <b>Photo with caption</b> for your post:")
        bot.register_next_step_handler(call.message, receive_post_content)

    elif data == "add_url_button":
        bot.answer_callback_query(call.id)
        bot.send_message(user_id, "🔗 Send button details in this format:\n<code>Button Text - https://example.com</code>")
        bot.register_next_step_handler(call.message, receive_url_button)

    elif data == "publish_post":
        bot.answer_callback_query(call.id)
        post_data = post_cache.get(user_id)
        if not post_data:
            bot.send_message(user_id, "❌ No post data found. Start over using /start or bottom buttons.")
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
            
            bot.send_message(user_id, f"🎉 <b>Successfully posted to {target}!</b>")
        except Exception as e:
            bot.send_message(user_id, f"❌ Failed to post. Make sure the bot is an Admin in <b>{target}</b>.\n\nError: <code>{e}</code>")

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
    bot.send_message(user_id, "✨ <b>Post preview saved!</b> Choose an option below:", reply_markup=markup)

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
        bot.send_message(user_id, f"✅ Button <b>{btn_text}</b> added successfully!", reply_markup=markup)
    except Exception:
        bot.send_message(user_id, "❌ Wrong format! Send like:\n<code>Click Here - https://t.me/...</code>")

# Admin Broadcast Handler
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
                
    bot.send_message(admin_id, f"📢 <b>Broadcast Completed!</b> Sent to {success_count} destinations.")

if __name__ == "__main__":
    print("Bot is active and running...")
    bot.infinity_polling()
