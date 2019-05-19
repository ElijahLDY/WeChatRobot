import itchat
# import全部消息类型
from itchat.content import *
import time
import re
import os

msg_information = {}


def info_text(func):
    def msg_solve(msg):
        msg_time = msg['CreateTime']  # 信息发送的时间
        msg_time_rec = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 接受消息的时间
        msg_from = itchat.search_friends(userName=msg['FromUserName'])['NickName']  # 在好友列表中查询发送信息的好友昵称
        msg_id = msg['MsgId']  # 每条信息的id
        msg_content = None  # 储存信息的内容
        msg_share_url = None  # 储存分享的链接，比如分享的文章和音乐

        # 如果发送的消息是文本或者好友推荐
        if msg['Type'] == 'Text' or msg['Type'] == 'Friends':
            msg_content = msg['Text']
        # 如果发送的消息是附件、视屏、图片、语音
        elif msg['Type'] == "Attachment" or msg['Type'] == "Video" or \
                msg['Type'] == 'Picture' or \
                msg['Type'] == 'Recording':
            msg_content = msg['FileName']  # 内容就是他们的文件名
            msg['Text'](str(msg_content))  # 下载文件
        # 如果消息是推荐的名片
        elif msg['Type'] == 'Card':
            msg_content = msg['RecommendInfo']['NickName'] + '的名片'  # 内容就是推荐人的昵称和性别
            if msg['RecommendInfo']['Sex'] == 1:
                msg_content += '性别为男'
            else:
                msg_content += '性别为女'
        # 如果消息为分享的位置信息
        elif msg['Type'] == 'Map':
            x, y, location = re.search(
                "<location x=\"(.*?)\" y=\"(.*?)\".*label=\"(.*?)\".*", msg['OriContent']).group(1, 2, 3)
            if location is None:
                msg_content = r"纬度->" + x.__str__() + " 经度->" + y.__str__()  # 内容为详细的地址
            else:
                msg_content = r"" + location
        # 如果消息为分享的音乐或者文章，详细的内容为文章的标题或者是分享的名字
        elif msg['Type'] == 'Sharing':
            msg_content = msg['Text']
            msg_share_url = msg['Url']  # 记录分享的url

        msg_information.update(
            {
                msg_id: {
                    "msg_time": msg_time,
                    "msg_time_rec": msg_time_rec,
                    "msg_from": msg_from,
                    "msg_type": msg["Type"],
                    "msg_content": msg_content,
                    "msg_share_url": msg_share_url
                }
            }
        )

        if msg['ToUserName'] == "filehelper":
            if msg['Type'] == 'Text' and msg["Text"] == "退出":
                itchat.logout()
            return
        # print("%s :%s" % (name, msg['Text']))
        # itchat.send(msg["Text"], toUserName='filehelper')
        else:
            back = func(msg)
            return back
    return msg_solve


# 处理文本类消息
# 包括文本、位置、名片、通知、分享
# @itchat.msg_register([TEXT, MAP, CARD, NOTE, SHARING])
@itchat.msg_register([TEXT, MAP, CARD, SHARING])
@info_text
def text_reply(msg):
    # 微信里，每个用户和群聊，都使用很长的ID来区分
    # msg['FromUserName']就是发送者的ID
    # 将消息的类型和文本内容返回给发送者，'filehelper'表示文件传输助手
    itchat.send('%s: %s' % (msg['Type'], msg['Text']), msg['FromUserName'])
    print('[%s] %s(%s): %s' % (msg['CreateTime'], msg['FromUserName'], msg['Type'], msg['Text']))


# 处理多媒体类消息
# 包括图片、录音、文件、视频
@itchat.msg_register([PICTURE, RECORDING, ATTACHMENT, VIDEO])
@info_text
def download_files(msg):
    # msg['Text']是一个文件下载函数
    # 传入文件名，将文件下载下来
    msg['Text'](msg['FileName'])
    # 把下载好的文件再发回给发送者
    # return '@%s@%s' % ({'Picture': 'img', 'Video': 'vid'}.get(msg['Type'], 'fil'), msg['FileName'])
    itchat.send(('@%s@%s' % ({'Picture': 'img', 'Video': 'vid'}.get(msg['Type'], 'fil'), msg['FileName'])),
                msg['FromUserName'])
    print('[%s] %s(%s): %s' % (msg['CreateTime'], msg['FromUserName'], msg['Type'], msg['FileName']))


# 处理好友添加请求
@itchat.msg_register(FRIENDS)
def add_friend(msg):
    # 该操作会自动将新好友的消息录入，不需要重载通讯录
    itchat.add_friend(**msg['Text'])
    # 加完好友后，给好友打个招呼
    itchat.send_msg('Nice to meet you!', msg['RecommendInfo']['UserName'])


# 处理群聊消息
@itchat.msg_register(TEXT, isGroupChat=True)
@info_text
def text_reply(msg):
    if msg['isAt']:
        # itchat.send(u'@%s\u2005I received: %s' % (msg['ActualNickName'], msg['Content']), msg['FromUserName'])
        print('[%s] %s(%s): %s' % (msg['CreateTime'], msg['FromUserName'], msg['Type'], msg['Content']))


# 这个是用于监听是否有消息撤回
@itchat.msg_register(NOTE, isFriendChat=True, isGroupChat=True, isMpChat=True)
def information(msg):
    # 这里如果这里的msg['Content']中包含消息撤回和id，就执行下面的语句
    if '撤回了一条消息' in msg['Content']:
        old_msg_id = re.search("<msgid>(.*?)</msgid>", msg['Content']).group(1)  # 在返回的content查找撤回的消息的id
        old_msg = msg_information.get(old_msg_id)  # 得到消息

        if len(old_msg_id) < 11:  # 如果发送的是表情包
            itchat.send_file(old_msg["msg_content"], toUserName='filehelper')
        else:  # 发送撤回的提示给文件助手
            msg_body = "告诉你一个秘密~" + "\n" \
                       + old_msg.get('msg_from') + " 撤回了 " + old_msg.get("msg_type") + " 消息" + "\n" \
                       + old_msg.get('msg_time_rec') + "\n" \
                       + "撤回了什么 ⇣" + "\n" \
                       + r"" + old_msg.get('msg_content')
            # 如果是分享的文件被撤回了，那么就将分享的url加在msg_body中发送给文件助手
            if old_msg['msg_type'] == "Sharing":
                msg_body += "\n就是这个链接➣ " + old_msg.get('msg_share_url')

            # 将撤回消息发送到文件助手
            itchat.send_msg(msg_body, toUserName='filehelper')
            # 有文件的话也要将文件发送回去
            if old_msg["msg_type"] == "Picture" \
                    or old_msg["msg_type"] == "Recording" \
                    or old_msg["msg_type"] == "Video" \
                    or old_msg["msg_type"] == "Attachment":
                file = '@fil@%s' % (old_msg['msg_content'])
                itchat.send(msg=file, toUserName='filehelper')
                os.remove(old_msg['msg_content'])
            # 删除字典旧消息
            msg_information.pop(old_msg_id)


# callback after successfully logged in
def lc():
    print("Finash Login!")


# callback after logged out
def ec():
    print("exit Succefully!!")


itchat.auto_login(enableCmdQR=True, loginCallback=lc, exitCallback=ec)

# 这两句无法正常运行
itchat.send_image('gz.gif', toUserName='filehelper')
itchat.send('@img@gz.gif', 'filehelper')

# 绑定消息响应事件后，让itchat运行起来，监听消息
itchat.run()
