import datetime
from typing import Union
from re import compile
YOUTUBE_VIDEO_REG = compile(r"(https?://)?(www\.)?youtube\.(com|nl)/watch\?v=([-\w]+)")

replaces = [
    ('&quot;', '"'),
    ('&amp;', '&'),
    ('(', '\u0028'),
    (')', '\u0029'),
    ('[', '【'),
    (']', '】'),
    ("  ", " "),
    ("*", '"'),
    ("_", ' '),
    ("{", "\u0028"),
    ("}", "\u0029"),
    ("`", "'")
]
def trim_text(text: str, limit: int = 0):
    for r in replaces:
        text = text.replace(r[0], r[1])

    if limit:
        text = f"{text[:limit]}..." if len(text) > limit else text

    return text

def time_format(milliseconds: Union[int, float], use_names: bool = False) -> str:
    minutes, seconds = divmod(int(milliseconds / 1000), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    if use_names:

        times = []

        for time_, name in (
                (days, "ngày"),
                (hours, "giờ"),
                (minutes, "phút"),
                (seconds, "giây")
        ):
            if not time_:
                continue

            times.append(f"{time_} {name}")

        try:
            last_time = times.pop()
        except IndexError:
            last_time = None
            times = ["1 giây"]

        strings = ", ".join(t for t in times)

        if last_time:
            strings += f" và {last_time}" if strings else last_time

    else:

        strings = f"{minutes:02d}:{seconds:02d}"

        if hours:
            strings = f"{hours}:{strings}"

        if days:
            strings = (f"{days} ngày" if days > 1 else f"{days} ngày") + (f", {strings}" if strings != "00:00" else "")

    return strings


time_names = ["seconds", "minutes", "hours"]

def string_to_seconds(time):
    try:

        times = reversed([i for i in time.replace(" ", ":").split(':') if i.isdigit()])
        time_dict = {}

        for n, t in enumerate(times):
            time_dict[time_names[n]] = int(t)

        return datetime.timedelta(**time_dict).total_seconds()

    except:
        return

def percentage(part, whole):
    return int((part * whole) / 100.0)

sources = {
    "deezer": "https://i.ibb.co/Wz7kJYy/deezer.png",
    "soundcloud": "https://i.ibb.co/CV6NB6w/soundcloud.png",
    "spotify": "https://i.ibb.co/3SWMXj8/spotify.png",
    "youtube": "https://i.ibb.co/LCsCCWD/8198147-music-play-player-sound-stream-icon.png",
    "applemusic": "https://i.ibb.co/Dr4hbS5/applemusic.png",
    "twitch": "https://cdn3.iconfinder.com/data/icons/popular-services-brands-vol-2/512/twitch-512.png"
}

def music_source_image(sourcename):
    return sources.get(
        sourcename,
        "https://i.ibb.co/17CK6c1/764167636849917952.gif"
    )

perms_translations = {
    "add_reactions": "Thêm phản ứng",
    "administrator": "Quản trị viên",
    "attach_files": "Đính kèm tệp",
    "ban_members": "Ban thành viên",
    "change_nickname": "Thay đổi biệt danh",
    "connect": "Kết nối với kênh thoại",
    "create_instant_invite": "Tạo lời mời tức thì",
    "create_private_threads": "Tạo các chủ đề riêng tư",
    "create_public_threads": "Tạo các chủ đề công cộng",
    "deafen_members": "Thành viên điếc",
    "embed_links": "Liên kết nhúng",
    "kick_members": "Trục xuất thành viên",
    "manage_channels": "Quản lý các kênh",
    "manage_emojis_and_stickers": "Quản lý biểu tượng cảm xúc và nhãn dán",
    "manage_events": "Quản lý các sự kiện",
    "manage_guild": "Quản lý máy chủ",
    "manage_messages": "Quản lý tin nhắn",
    "manage_nicknames": "Quản lý biệt danh",
    "manage_roles": "Quản lý vai trò",
    "manage_threads": "Quản lý các chủ đề",
    "manage_webhooks": "Quản lý webhooks",
    "mention_everyone": "Đề cập @everyone và @here",
    "moderate_members": "Quản lí thành viên",
    "move_members": "Di chuyển các thành viên",
    "mute_members": "Các thành viên im lặng",
    "priority_speaker": "Ưu tiên nói",
    "read_message_history": "Đọc lịch sử tin nhắn",
    "read_messages": "Đọc tin nhắn",
    "request_to_speak": "Yêu cầu nói",
    "send_messages": "Gửi tin nhắn",
    "send_messages_in_threads": "Gửi tin nhắn đến các chủ đề",
    "send_tts_messages": "Gửi tin nhắn thoại",
    "speak": "Nói",
    "stream": "Phát trực tiếp",
    "use_application_commands": "Sử dụng lệnh Ứng dụng/bot",
    "use_embedded_activities": "Sử dụng các hoạt động ",
    "use_external_emojis": "Sử dụng biểu tượng cảm xúc bên ngoài",
    "use_external_stickers": "Sử dụng nhãn dán bên ngoài",
    "use_voice_activation": "Sử dụng phát hiện giọng nói tự động",
    "view_audit_log": "Xem nhật kí chỉnh sửa",  
    "view_channel": "Xem kênh",
    "view_guild_insights": "Xem phân tích máy chủ"
}
